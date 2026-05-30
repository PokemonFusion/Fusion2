"""Reusable offline outcome harness for battle mechanics.

The helpers in this module are intentionally test-only.  They let tests build a
small battle directly from dex data, execute one deterministic move or residual
phase, and assert on structured snapshots instead of relying on live Evennia
sessions.
"""

from __future__ import annotations

import builtins
import copy
import random
import re
import sys
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from .helpers import load_modules


def normalize_key(value: Any) -> str:
    """Return the dex-style key used for loose name matching."""

    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


@dataclass(frozen=True)
class MoveSpec:
    """Minimal move definition for outcome tests that do not need dex data."""

    name: str = "Tackle"
    power: int = 40
    type: str = "Normal"
    category: str = "Physical"
    accuracy: int | float | bool = 100
    priority: int = 0
    flags: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PokemonSpec:
    """Minimal Pokemon definition for deterministic battle outcome tests."""

    name: str = "Testmon"
    level: int = 50
    hp: int = 200
    max_hp: int = 200
    types: Sequence[str] = ("Normal",)
    ability: Any = None
    item: Any = None
    moves: Sequence[Any] = ()
    status: Any = None
    gender: str = "N"
    base_stats: int | Mapping[str, int] = 120
    fully_evolved: bool | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class OutcomeResult:
    """Structured result returned by a deterministic outcome run."""

    battle: Any
    user: Any
    target: Any
    move: Any | None
    before: "BattleSnapshot"
    after: "BattleSnapshot"
    damage: tuple["DamageSnapshot", ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotMixin:
    """Small mapping-compatible layer for typed snapshots."""

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)


@dataclass(frozen=True)
class PokemonSnapshot(SnapshotMixin):
    """Stable, assertion-friendly view of one Pokemon's battle state."""

    name: str
    species: str
    hp: int
    max_hp: int
    status: Any
    types: list[str]
    ability: str
    item: str
    ability_state: dict[str, Any]
    stats: dict[str, int]
    boosts: dict[str, int]
    tempvals: dict[str, Any]
    volatiles: list[str]
    moves: list[str]
    last_move: dict[str, Any]
    immune: Any
    fainted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "species": self.species,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "status": self.status,
            "types": list(self.types),
            "ability": self.ability,
            "item": self.item,
            "ability_state": dict(self.ability_state),
            "stats": dict(self.stats),
            "boosts": dict(self.boosts),
            "tempvals": dict(self.tempvals),
            "volatiles": list(self.volatiles),
            "moves": list(self.moves),
            "last_move": dict(self.last_move),
            "immune": self.immune,
            "fainted": self.fainted,
        }


@dataclass(frozen=True)
class SideSnapshot(SnapshotMixin):
    """Stable, assertion-friendly view of one battle side."""

    conditions: list[str] = field(default_factory=list)
    condition_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    hazards: dict[str, Any] = field(default_factory=dict)
    screens: dict[str, Any] = field(default_factory=dict)
    volatiles: dict[str, Any] = field(default_factory=dict)
    slot_conditions: dict[str, list[str]] = field(default_factory=dict)
    slot_condition_state: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conditions": list(self.conditions),
            "condition_state": {
                key: dict(value) for key, value in self.condition_state.items()
            },
            "hazards": dict(self.hazards),
            "screens": dict(self.screens),
            "volatiles": dict(self.volatiles),
            "slot_conditions": {slot: list(values) for slot, values in self.slot_conditions.items()},
            "slot_condition_state": {
                slot: {key: dict(value) for key, value in conditions.items()}
                for slot, conditions in self.slot_condition_state.items()
            },
        }


@dataclass(frozen=True)
class BattleSnapshot(SnapshotMixin):
    """Stable, assertion-friendly view of the battle state relevant to tests."""

    user: PokemonSnapshot
    target: PokemonSnapshot
    user_side: SideSnapshot
    target_side: SideSnapshot
    weather: str
    terrain: str
    pseudo_weather: list[str]
    pseudo_weather_state: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "target": self.target.to_dict(),
            "user_side": self.user_side.to_dict(),
            "target_side": self.target_side.to_dict(),
            "weather": self.weather,
            "terrain": self.terrain,
            "pseudo_weather": list(self.pseudo_weather),
            "pseudo_weather_state": {
                key: dict(value) for key, value in self.pseudo_weather_state.items()
            },
        }


@dataclass(frozen=True)
class DamageSnapshot(SnapshotMixin):
    """Stable debug view of one ``apply_damage`` call."""

    move_name: str
    source: str
    target: str
    per_hit: tuple[int, ...]
    total: int
    power: tuple[int, ...]
    random_rolls: tuple[float, ...]
    critical: tuple[bool, ...]
    stab: tuple[float, ...]
    type_effectiveness: tuple[float, ...]
    attack: tuple[int, ...]
    defense: tuple[int, ...]
    update_hp: bool
    spread: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "move_name": self.move_name,
            "source": self.source,
            "target": self.target,
            "per_hit": list(self.per_hit),
            "total": self.total,
            "power": list(self.power),
            "random_rolls": list(self.random_rolls),
            "critical": list(self.critical),
            "stab": list(self.stab),
            "type_effectiveness": list(self.type_effectiveness),
            "attack": list(self.attack),
            "defense": list(self.defense),
            "update_hp": self.update_hp,
            "spread": self.spread,
        }


@dataclass(frozen=True)
class RandomControl:
    """Queued random values for deterministic percentage-branch tests.

    Values are consumed in call order.  Use ``random_values`` for percentage
    checks such as accuracy, critical hits, and secondary effects.  Use
    ``randint_values`` for damage variance, sleep duration, or similar integer
    rolls.
    """

    random_values: Sequence[float] = ()
    randint_values: Sequence[int] = ()
    uniform_values: Sequence[float] = ()
    choice_indices: Sequence[int] = ()
    choices_indices: Sequence[int] = ()


class ControlledRandom(random.Random):
    """``random.Random`` compatible queue-backed RNG for outcome tests."""

    def __init__(self, seed: int = 0, control: RandomControl | None = None):
        super().__init__(seed)
        control = control or RandomControl()
        self._random_values = deque(control.random_values)
        self._randint_values = deque(control.randint_values)
        self._uniform_values = deque(control.uniform_values)
        self._choice_indices = deque(control.choice_indices)
        self._choices_indices = deque(control.choices_indices)

    def random(self) -> float:
        if self._random_values:
            value = float(self._random_values.popleft())
            if not 0 <= value <= 1:
                raise AssertionError(f"random() override must be between 0 and 1, got {value!r}")
            return value
        return super().random()

    def randint(self, a: int, b: int) -> int:
        if self._randint_values:
            value = int(self._randint_values.popleft())
            if value < a or value > b:
                raise AssertionError(f"randint({a}, {b}) override out of range: {value!r}")
            return value
        return super().randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        if self._uniform_values:
            value = float(self._uniform_values.popleft())
            low = min(a, b)
            high = max(a, b)
            if value < low or value > high:
                raise AssertionError(f"uniform({a}, {b}) override out of range: {value!r}")
            return value
        return super().uniform(a, b)

    def choice(self, seq):
        if self._choice_indices:
            index = int(self._choice_indices.popleft())
            return seq[index % len(seq)]
        return super().choice(seq)

    def choices(self, population, weights=None, *, cum_weights=None, k: int = 1):
        if self._choices_indices:
            result = []
            for _ in range(k):
                if self._choices_indices:
                    index = int(self._choices_indices.popleft())
                    result.append(population[index % len(population)])
                else:
                    result.extend(
                        super().choices(
                            population,
                            weights=weights,
                            cum_weights=cum_weights,
                            k=1,
                        )
                    )
            return result
        return super().choices(population, weights=weights, cum_weights=cum_weights, k=k)


def chance_roll(succeeds: bool) -> float:
    """Return a queued ``random()`` value that forces a percentage branch."""

    return 0.0 if succeeds else 0.999999


def percent_roll(chance_percent: float, succeeds: bool) -> float:
    """Return a roll that proves a percentage threshold branch.

    ``percent_check`` succeeds only when ``chance > random()``.  A successful
    roll is therefore just below the threshold, while a failed roll is exactly
    at the threshold.
    """

    chance = max(0.0, min(1.0, float(chance_percent) / 100.0))
    if succeeds:
        return max(0.0, chance - 0.000001)
    return chance


class _OutcomeUnset:
    def __repr__(self) -> str:
        return "UNSET"


UNSET = getattr(builtins, "_PF2_OUTCOME_HARNESS_UNSET", None)
if UNSET is None:
    UNSET = _OutcomeUnset()
    setattr(builtins, "_PF2_OUTCOME_HARNESS_UNSET", UNSET)


@dataclass(frozen=True)
class PokemonExpectation:
    """Expected post-outcome state for one side of a contract test.

    Fields left unset are ignored.  ``hp_delta`` is relative to the side's
    pre-outcome HP, while ``boosts`` and ``ability_state`` assert only the
    supplied keys so each contract can stay focused.
    """

    hp: Any = UNSET
    hp_delta: Any = UNSET
    hp_less_than: Any = UNSET
    hp_greater_than: Any = UNSET
    species: Any = UNSET
    status: Any = UNSET
    types: Sequence[str] | None = None
    ability: Any = UNSET
    immune: Any = UNSET
    item: Any = UNSET
    fainted: Any = UNSET
    moves: Sequence[str] | None = None
    last_move: Mapping[str, Any] | None = None
    stats: Mapping[str, int] | None = None
    boosts: Mapping[str, int] | None = None
    ability_state: Mapping[str, Any] | None = None
    tempvals: Mapping[str, Any] | None = None
    volatiles: Sequence[str] | None = None


@dataclass
class ProofCalledMove:
    """Small deterministic move object used to prove move-calling callbacks."""

    name: str = "Proof Called Move"
    target_side: str = "target"
    boosts: Mapping[str, int] = field(default_factory=dict)
    damage: int = 0
    status: Any = UNSET
    volatile: str | None = None
    power: int = 0
    type: str = "Normal"
    category: str = "Status"
    accuracy: int | float | bool = True
    priority: int = 0
    pp: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.key = normalize_key(self.name)
        self.id = self.key
        self.flags = dict((self.raw or {}).get("flags", {}) or {})

    def onHit(self, user, target, battle=None):
        recipient = user if self.target_side == "user" else target
        if recipient is None:
            return False
        if self.damage:
            recipient.hp = max(0, int(getattr(recipient, "hp", 0) or 0) - int(self.damage))
        if self.boosts:
            from pokemon.utils.boosts import apply_boost

            apply_boost(recipient, dict(self.boosts), source=user, effect=self)
        if self.status is not UNSET:
            if battle and hasattr(battle, "apply_status_condition"):
                battle.apply_status_condition(recipient, self.status, source=user, effect=self)
            elif hasattr(recipient, "setStatus"):
                recipient.setStatus(self.status)
            else:
                recipient.status = self.status
        if self.volatile and hasattr(recipient, "volatiles"):
            recipient.volatiles.setdefault(self.volatile, True)
        if battle is not None:
            called = getattr(battle, "called_moves", None)
            if called is None:
                called = []
                setattr(battle, "called_moves", called)
            called.append(self.name)
        return True


@dataclass
class MoveQueueProbe:
    """Minimal queue object for proving queue-manipulating move callbacks."""

    action: Any = field(default_factory=lambda: SimpleNamespace(name="queued-action"))
    prioritized: Any = None
    will_move_target: Any = None

    def will_move(self, target):
        self.will_move_target = target
        return self.action

    def prioritize_action(self, action):
        self.prioritized = action


@dataclass(frozen=True)
class BattleExpectation:
    """Expected post-outcome field and side state for a contract test."""

    weather: Any = UNSET
    terrain: Any = UNSET
    pseudo_weather: Sequence[str] | None = None
    pseudo_weather_state: Mapping[str, Mapping[str, Any]] | None = None
    user_side_conditions: Sequence[str] | None = None
    target_side_conditions: Sequence[str] | None = None
    user_side_condition_state: Mapping[str, Mapping[str, Any]] | None = None
    target_side_condition_state: Mapping[str, Mapping[str, Any]] | None = None
    user_side_hazards: Mapping[str, Any] | None = None
    target_side_hazards: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DamageExpectation:
    """Expected damage debug state for one or more damage events."""

    event_count: int | None = None
    total: Any = UNSET
    per_hit: Sequence[int] | None = None
    power: Sequence[int] | int | None = None
    random_rolls: Sequence[float] | float | None = None
    critical: Sequence[bool] | bool | None = None
    stab: Sequence[float] | float | None = None
    type_effectiveness: Sequence[float] | float | None = None
    attack: Sequence[int] | int | None = None
    defense: Sequence[int] | int | None = None
    move_name: str | None = None


@dataclass(frozen=True)
class MoveOutcomeContract:
    """Declarative proof that one deterministic move produces expected state."""

    name: str
    move: str | MoveSpec | Any
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    expect_damage: DamageExpectation | None = None
    seed: int = 0
    random_control: RandomControl | None = None
    full_turn: bool = False
    opponent_move: str | MoveSpec | Any | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class MoveEventOutcomeContract:
    """Declarative proof for callback-driven move behavior."""

    name: str
    move: str | MoveSpec | Any
    event: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    target_is_ally: bool = False
    game_type: str | None = None
    battle_extra: Mapping[str, Any] = field(default_factory=dict)
    user_side_hazards: Mapping[str, Any] | None = None
    target_side_hazards: Mapping[str, Any] | None = None
    expect_result: Any = UNSET
    expect_queue_prioritized: Any = UNSET
    expect_called_moves: Sequence[str] | None = None
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ResidualOutcomeContract:
    """Declarative proof that residual effects produce expected state."""

    name: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class AbilityStartOutcomeContract:
    """Declarative proof that entry/start ability callbacks produce expected state."""

    name: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    enter_sides: Sequence[str] = ("user",)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class AbilityFlagOutcomeContract:
    """Declarative proof that an ability flag gates a move outcome."""

    name: str
    move: str | MoveSpec | Any
    mechanic: str = "ability_flag_protection"
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class PostBattleAbilityOutcomeContract:
    """Declarative proof for post-battle ability item resolution."""

    name: str
    mechanic: str = "ability_post_battle_item"
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    thrown_ball: str | None = None
    caught: bool = False
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class RunExpectation:
    """Expected result metadata for a flee attempt."""

    success: Any = UNSET
    reason: Any = UNSET
    battle_over: Any = UNSET


@dataclass(frozen=True)
class RunOutcomeContract:
    """Declarative proof for flee/escape behavior."""

    name: str
    mechanic: str = "ability_escape"
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    battle_type: str = "wild"
    expect_run: RunExpectation = field(default_factory=RunExpectation)
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class BeforeMoveOutcomeContract:
    """Declarative proof for before-move status or ability gates."""

    name: str
    move: str | MoveSpec | Any = "Tackle"
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    checks: int = 1
    expect_prevented: Any = UNSET
    expect_prevented_history: Sequence[bool] | None = None
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class SwitchOutcomeContract:
    """Declarative proof for switch-out ability hooks."""

    name: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ItemEventOutcomeContract:
    """Declarative proof for held-item ability event paths."""

    name: str
    event: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    expect_result: Any = UNSET
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ItemCallbackOutcomeContract:
    """Declarative proof for held item callbacks or metadata."""

    name: str
    item: Any
    event: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    owner: str = "user"
    target_side: str | None = "target"
    source_side: str | None = "user"
    pokemon_side: str | None = "user"
    held: bool = True
    battle_extra: Mapping[str, Any] = field(default_factory=dict)
    move: str | MoveSpec | Any | None = None
    move_extra: Mapping[str, Any] = field(default_factory=dict)
    expect_move_attrs: Mapping[str, Any] | None = None
    status: Any = UNSET
    boosts: Mapping[str, int] | None = None
    relay_value: Any = UNSET
    effect_id: str | None = None
    effect_name: str | None = None
    effect_type: str | None = None
    expect_result: Any = UNSET
    expect_boosts: Mapping[str, int] | None = None
    expect_item_attrs: Mapping[str, Any] | None = None
    expect_raw: Mapping[str, Any] | None = None
    expect_user_attrs: Mapping[str, Any] | None = None
    expect_target_attrs: Mapping[str, Any] | None = None
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class SpeciesOutcomeContract:
    """Declarative proof for species/form dex metadata and battle construction."""

    name: str
    species: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    expect_metadata: Mapping[str, Any] = field(default_factory=dict)
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class FormChangeOutcomeContract:
    """Declarative proof that a battle trigger changes a Pokemon's form."""

    name: str
    trigger: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    item: Any = None
    event: str | None = None
    move: str | MoveSpec | Any | None = None
    battle_extra: Mapping[str, Any] = field(default_factory=dict)
    direct_forme: str | None = None
    expect_result: Any = UNSET
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_battle: BattleExpectation = field(default_factory=BattleExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class AbilityEventOutcomeContract:
    """Declarative proof for a targeted ability callback event."""

    name: str
    event: str
    mechanic: str = ""
    covers: Sequence[str] = ()
    user: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="User"))
    target: PokemonSpec = field(default_factory=lambda: PokemonSpec(name="Target"))
    owner: str = "user"
    target_side: str | None = "target"
    source_side: str | None = "user"
    pokemon_side: str | None = None
    target_is_ally: bool = False
    game_type: str | None = None
    move: str | MoveSpec | Any | None = None
    move_extra: Mapping[str, Any] = field(default_factory=dict)
    item: Any = None
    status: Any = UNSET
    boosts: Mapping[str, int] | None = None
    relay_value: Any = UNSET
    effect_id: str | None = None
    effect_type: str | None = None
    expect_result: Any = UNSET
    expect_boosts: Mapping[str, int] | None = None
    expect_user: PokemonExpectation = field(default_factory=PokemonExpectation)
    expect_target: PokemonExpectation = field(default_factory=PokemonExpectation)
    seed: int = 0
    random_control: RandomControl | None = None

    def __str__(self) -> str:
        return self.name


def coverage_id(kind: str, name: Any) -> str:
    """Return a stable coverage subject id such as ``move:willowisp``."""

    return f"{normalize_key(kind)}:{normalize_key(name)}"


def _move_subject(move: str | MoveSpec | Any) -> tuple[str, ...]:
    name = move if isinstance(move, str) else getattr(move, "name", "")
    return (coverage_id("move", name),) if name else ()


def status_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    status: Any,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for direct major-status application."""

    return MoveOutcomeContract(
        name=name,
        mechanic="status_outcome",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_target=PokemonExpectation(hp_delta=0, status=status),
    )


def boost_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    boosts: Mapping[str, int],
    affects: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for stat-stage changes."""

    if affects not in {"user", "target"}:
        raise ValueError("affects must be 'user' or 'target'")
    expect_user = PokemonExpectation(hp_delta=0, boosts=boosts if affects == "user" else None)
    expect_target = PokemonExpectation(hp_delta=0, boosts=boosts if affects == "target" else None)
    return MoveOutcomeContract(
        name=name,
        mechanic="stat_boost",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user or PokemonSpec(name="Booster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=expect_user,
        expect_target=expect_target,
    )


def healing_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_hp: int,
    user: PokemonSpec,
    target: PokemonSpec | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for direct HP recovery moves."""

    return MoveOutcomeContract(
        name=name,
        mechanic="healing",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user,
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp=expected_hp),
        expect_target=PokemonExpectation(hp_delta=0),
    )


def drain_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_user_hp: int,
    expected_target_hp: int,
    user: PokemonSpec,
    target: PokemonSpec,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for damage plus drain healing."""

    return MoveOutcomeContract(
        name=name,
        mechanic="drain",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user,
        target=target,
        move=move,
        expect_user=PokemonExpectation(hp=expected_user_hp),
        expect_target=PokemonExpectation(hp=expected_target_hp),
    )


def recoil_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_user_hp: int,
    expected_target_hp: int,
    user: PokemonSpec,
    target: PokemonSpec | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for damage plus recoil."""

    return MoveOutcomeContract(
        name=name,
        mechanic="recoil",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user,
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp=expected_user_hp),
        expect_target=PokemonExpectation(hp=expected_target_hp),
    )


def damage_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_damage: int,
    expected_power: Sequence[int] | int | None = None,
    expected_per_hit: Sequence[int] | None = None,
    expected_random_rolls: Sequence[float] | float | None = None,
    expected_critical: Sequence[bool] | bool | None = False,
    expected_stab: Sequence[float] | float | None = None,
    expected_type_effectiveness: Sequence[float] | float | None = None,
    expected_attack: Sequence[int] | int | None = None,
    expected_defense: Sequence[int] | int | None = None,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    random_control: RandomControl | None = None,
    covers: Sequence[str] | None = None,
    mechanic: str = "damage",
) -> MoveOutcomeContract:
    """Build a contract for exact deterministic damage."""

    per_hit = expected_per_hit
    if per_hit is None:
        per_hit = (expected_damage,) if expected_damage else ()
    critical = expected_critical
    if critical is False and len(tuple(per_hit)) > 1:
        critical = tuple(False for _ in per_hit)
    control = random_control or RandomControl(
        random_values=(percent_roll(100 / 24, False),),
        randint_values=(100,),
    )
    return MoveOutcomeContract(
        name=name,
        mechanic=mechanic,
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user or PokemonSpec(name="Attacker"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        random_control=control,
        expect_target=PokemonExpectation(hp_delta=-expected_damage),
        expect_damage=DamageExpectation(
            event_count=1,
            total=expected_damage,
            per_hit=per_hit,
            power=expected_power,
            random_rolls=expected_random_rolls,
            critical=critical,
            stab=expected_stab,
            type_effectiveness=expected_type_effectiveness,
            attack=expected_attack,
            defense=expected_defense,
        ),
    )


def secondary_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    succeeds: bool,
    chance: int = 30,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    expect_user: PokemonExpectation | None = None,
    expect_target: PokemonExpectation | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract for forcing one secondary-effect branch."""

    return MoveOutcomeContract(
        name=name,
        mechanic="secondary_effect",
        covers=tuple(_move_subject(move) if covers is None else covers),
        user=user or PokemonSpec(name="Attacker"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        random_control=RandomControl(
            random_values=(percent_roll(100 / 24, False), percent_roll(chance, succeeds)),
            randint_values=(100,),
        ),
        expect_user=expect_user or PokemonExpectation(),
        expect_target=expect_target or PokemonExpectation(),
    )


def callback_damage_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_damage: int,
    expected_power: Sequence[int] | int | None,
    expected_per_hit: Sequence[int] | None = None,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    random_control: RandomControl | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract proving callback-driven damage or power."""

    return damage_contract(
        name=name,
        move=move,
        expected_damage=expected_damage,
        expected_power=expected_power,
        expected_per_hit=expected_per_hit,
        user=user,
        target=target,
        random_control=random_control,
        covers=covers,
        mechanic="callback_damage",
    )


def combo_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    expected_damage: int,
    expected_power: Sequence[int] | int | None,
    expected_per_hit: Sequence[int] | None = None,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    random_control: RandomControl | None = None,
    covers: Sequence[str] | None = None,
) -> MoveOutcomeContract:
    """Build a contract proving known move-combo damage behavior."""

    return damage_contract(
        name=name,
        move=move,
        expected_damage=expected_damage,
        expected_power=expected_power,
        expected_per_hit=expected_per_hit,
        user=user,
        target=target,
        random_control=random_control,
        covers=covers,
        mechanic="combo_move",
    )


def ability_immunity_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    ability: str,
    immune: str,
    expected_target_hp: int,
    target: PokemonSpec,
    user: PokemonSpec | None = None,
    ability_state: Mapping[str, Any] | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for an ability blocking or absorbing a move."""

    subjects = tuple(covers or (*_move_subject(move), coverage_id("ability", ability)))
    return MoveOutcomeContract(
        name=name,
        mechanic="ability_immunity",
        covers=subjects,
        user=user or PokemonSpec(name="Caster"),
        target=target,
        move=move,
        expect_target=PokemonExpectation(
            hp=expected_target_hp,
            status=0,
            immune=immune,
            ability_state=ability_state,
        ),
    )


def weather_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    weather: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that start weather."""

    return MoveOutcomeContract(
        name=name,
        mechanic="weather",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0),
        expect_target=PokemonExpectation(hp_delta=0),
        expect_battle=BattleExpectation(weather=weather, pseudo_weather=(weather,)),
    )


def terrain_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    terrain: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that start terrain."""

    return MoveOutcomeContract(
        name=name,
        mechanic="terrain",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0),
        expect_target=PokemonExpectation(hp_delta=0),
        expect_battle=BattleExpectation(terrain=terrain, pseudo_weather=(terrain,)),
    )


def side_condition_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    condition: str,
    target_hazards: Mapping[str, Any] | None = None,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that set foe-side conditions or hazards."""

    return MoveOutcomeContract(
        name=name,
        mechanic="side_condition",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0),
        expect_target=PokemonExpectation(hp_delta=0),
        expect_battle=BattleExpectation(
            target_side_conditions=(condition,),
            target_side_hazards=target_hazards,
        ),
    )


def volatile_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    volatile: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that add a volatile to the target."""

    return MoveOutcomeContract(
        name=name,
        mechanic="volatile",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0),
        expect_target=PokemonExpectation(hp_delta=0, volatiles=(volatile,)),
    )


def forced_switch_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that force the target out."""

    return MoveOutcomeContract(
        name=name,
        mechanic="forced_switch",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Caster"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0),
        expect_target=PokemonExpectation(
            hp_delta=0,
            tempvals={"switch_out": True, "dragged_out": True},
        ),
    )


def self_switch_contract(
    *,
    name: str,
    move: str | MoveSpec | Any,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for moves that mark the user to switch out."""

    return MoveOutcomeContract(
        name=name,
        mechanic="self_switch",
        covers=tuple(covers or _move_subject(move)),
        user=user or PokemonSpec(name="Pivot"),
        target=target or PokemonSpec(name="Target"),
        move=move,
        expect_user=PokemonExpectation(hp_delta=0, tempvals={"switch_out": True}),
    )


def residual_item_contract(
    *,
    name: str,
    item: str,
    expected_hp: int,
    user: PokemonSpec,
    covers: Sequence[str] = (),
) -> ResidualOutcomeContract:
    """Build a contract for held item residual effects."""

    return ResidualOutcomeContract(
        name=name,
        mechanic="item_residual",
        covers=tuple(covers or (coverage_id("item", item),)),
        user=user,
        expect_user=PokemonExpectation(hp=expected_hp, item=item),
        expect_target=PokemonExpectation(hp_delta=0),
    )


def secondary_chance_contract(
    *,
    name: str,
    succeeds: bool,
    expected_boosts: Mapping[str, int],
    move: MoveSpec | None = None,
    chance: int = 30,
    covers: Sequence[str] = (),
) -> MoveOutcomeContract:
    """Build a contract for forcing a secondary-effect chance branch."""

    test_move = move or MoveSpec(
        name="Chance Drop",
        power=40,
        accuracy=True,
        raw={
            "target": "normal",
            "secondary": {"chance": chance, "boosts": {"atk": -1}},
        },
    )
    return MoveOutcomeContract(
        name=name,
        mechanic="random_branch",
        covers=tuple(covers),
        user=PokemonSpec(name="Attacker"),
        target=PokemonSpec(name="Target"),
        move=test_move,
        random_control=RandomControl(
            random_values=(chance_roll(False), chance_roll(succeeds)),
            randint_values=(100,),
        ),
        expect_target=PokemonExpectation(boosts=expected_boosts),
    )


STAT_ALIASES = {
    "attack": "atk",
    "atk": "atk",
    "defense": "def",
    "def": "def",
    "def_": "def",
    "special_attack": "spa",
    "spa": "spa",
    "special_defense": "spd",
    "spd": "spd",
    "speed": "spe",
    "spe": "spe",
    "accuracy": "accuracy",
    "evasion": "evasion",
}


def _lookup_dex_entry(dex: Mapping[str, Any], name: str) -> Any:
    wanted = normalize_key(name)
    for key in (name, name.lower(), name.title(), name.replace(" ", "")):
        if key in dex:
            return dex[key]
    for key, entry in dex.items():
        entry_name = getattr(entry, "name", key)
        if normalize_key(key) == wanted or normalize_key(entry_name) == wanted:
            return entry
    raise KeyError(f"{name!r} was not found in the loaded dex data")


def _dex_module():
    load_modules()
    import pokemon.dex as dex_mod  # type: ignore

    return dex_mod


def dex_item(name: str):
    """Return an isolated Item object from the loaded item dex."""

    dex_mod = _dex_module()
    return copy.deepcopy(_lookup_dex_entry(getattr(dex_mod, "ITEMDEX", {}), name))


def dex_ability(name: str):
    """Return an isolated Ability object from the loaded ability dex."""

    dex_mod = _dex_module()
    return copy.deepcopy(_lookup_dex_entry(getattr(dex_mod, "ABILITYDEX", {}), name))


def dex_pokemon(name: str):
    """Return an isolated Pokemon species/form entry from the loaded dex."""

    dex_mod = _dex_module()
    return copy.deepcopy(_lookup_dex_entry(getattr(dex_mod, "POKEDEX", {}), name))


def dex_move(name: str, **overrides: Any):
    """Return a BattleMove built from the loaded move dex.

    Common overrides may be supplied as keyword arguments, for example
    ``accuracy=True`` to make a normally inaccurate status move deterministic.
    ``raw`` may contain additional raw dex keys.
    """

    modules = load_modules()
    BattleMove = modules["BattleMove"]
    dex_mod = _dex_module()
    entry = _lookup_dex_entry(getattr(dex_mod, "MOVEDEX", {}), name)
    raw = copy.deepcopy(getattr(entry, "raw", {}) or {})
    raw.update(copy.deepcopy(overrides.pop("raw", {}) or {}))

    if "power" in overrides:
        raw["basePower"] = overrides.pop("power")
    if "move_type" in overrides:
        raw["type"] = overrides.pop("move_type")
    if "type" in overrides:
        raw["type"] = overrides.pop("type")
    if "category" in overrides:
        raw["category"] = overrides.pop("category")
    if "accuracy" in overrides:
        raw["accuracy"] = overrides.pop("accuracy")
    if "priority" in overrides:
        raw["priority"] = overrides.pop("priority")
    if "flags" in overrides:
        raw["flags"] = overrides.pop("flags")
    raw.update(overrides)

    display_name = str(raw.get("name") or getattr(entry, "name", name))
    return BattleMove(
        name=display_name,
        key=normalize_key(display_name),
        power=int(raw.get("basePower", getattr(entry, "power", 0)) or 0),
        accuracy=raw.get("accuracy", getattr(entry, "accuracy", 100)),
        priority=int(raw.get("priority", 0) or 0),
        type=raw.get("type", getattr(entry, "type", None)),
        raw=raw,
        pp=raw.get("pp", getattr(entry, "pp", None)),
    )


def explicit_move(spec: MoveSpec):
    """Return a BattleMove from a direct test move specification."""

    modules = load_modules()
    BattleMove = modules["BattleMove"]
    raw = {
        "name": spec.name,
        "basePower": spec.power,
        "type": spec.type,
        "category": spec.category,
        "accuracy": spec.accuracy,
        "priority": spec.priority,
        "flags": dict(spec.flags),
    }
    raw.update(dict(spec.raw))
    return BattleMove(
        name=spec.name,
        key=normalize_key(spec.name),
        power=spec.power,
        accuracy=spec.accuracy,
        priority=spec.priority,
        type=spec.type,
        raw=raw,
    )


def _is_move_spec(value: Any) -> bool:
    """Return True for MoveSpec instances, including ones created before reloads."""

    return isinstance(value, MoveSpec) or (
        value.__class__.__name__ == "MoveSpec"
        and all(hasattr(value, attr) for attr in ("name", "power", "accuracy", "priority", "raw"))
    )


def make_move(move: str | MoveSpec | Any):
    """Coerce a move name, MoveSpec, or BattleMove-like object into BattleMove."""

    if isinstance(move, str):
        return dex_move(move)
    if _is_move_spec(move):
        return explicit_move(move)
    return move


def _stats_from_spec(spec: PokemonSpec):
    modules = load_modules()
    Stats = modules["Stats"]
    if isinstance(spec.base_stats, int):
        value = spec.base_stats
        return Stats(
            hp=value,
            attack=value,
            defense=value,
            special_attack=value,
            special_defense=value,
            speed=value,
        )
    return Stats(**dict(spec.base_stats))


def _coerce_ability(ability: Any):
    if ability is None or hasattr(ability, "call"):
        return ability
    if isinstance(ability, str):
        if not normalize_key(ability):
            return None
        return dex_ability(ability)
    return ability


def _coerce_item(item: Any):
    if item is None:
        return None
    if isinstance(item, str):
        return dex_item(item)
    if hasattr(item, "call"):
        return copy.deepcopy(item)
    if isinstance(item, Mapping):
        load_modules()
        from pokemon.dex.entities import Item  # type: ignore

        name = str(item.get("name", "Test Item"))
        return Item.from_dict(name, dict(item))
    return item


def pokemon_spec_from_dex(
    name: str,
    *,
    level: int = 50,
    hp: int | None = None,
    max_hp: int | None = None,
    ability: str | None = None,
    item: Any = None,
    moves: Sequence[Any] = (),
) -> PokemonSpec:
    """Create a PokemonSpec from POKEDEX data."""

    dex_mod = _dex_module()
    entry = _lookup_dex_entry(getattr(dex_mod, "POKEDEX", {}), name)
    stats = getattr(entry, "base_stats", None)
    stat_map = {
        "hp": getattr(stats, "hp", 100),
        "attack": getattr(stats, "attack", getattr(stats, "atk", 100)),
        "defense": getattr(stats, "defense", getattr(stats, "def_", 100)),
        "special_attack": getattr(stats, "special_attack", getattr(stats, "spa", 100)),
        "special_defense": getattr(stats, "special_defense", getattr(stats, "spd", 100)),
        "speed": getattr(stats, "speed", getattr(stats, "spe", 100)),
    }
    resolved_max_hp = max_hp if max_hp is not None else 200
    resolved_hp = hp if hp is not None else resolved_max_hp
    resolved_ability = ability
    if resolved_ability is None:
        abilities = getattr(entry, "abilities", {}) or {}
        first = next(iter(abilities.values()), None)
        resolved_ability = getattr(first, "name", None) if first is not None else None
    if isinstance(resolved_ability, str) and not normalize_key(resolved_ability):
        resolved_ability = None
    return PokemonSpec(
        name=str(getattr(entry, "name", name)),
        level=level,
        hp=resolved_hp,
        max_hp=resolved_max_hp,
        types=tuple(getattr(entry, "types", []) or ("Normal",)),
        ability=resolved_ability,
        item=item,
        moves=moves,
        base_stats=stat_map,
        fully_evolved=not bool(getattr(entry, "evos", []) or []),
    )


def _apply_spec(battle, pokemon, spec: PokemonSpec) -> None:
    pokemon.name = spec.name
    pokemon.species = spec.name
    pokemon.base_species = spec.name
    pokemon.level = spec.level
    pokemon.hp = spec.hp
    pokemon.max_hp = spec.max_hp
    pokemon.types = list(spec.types)
    pokemon.gender = spec.gender
    pokemon.base_stats = _stats_from_spec(spec)
    pokemon.ability = _coerce_ability(spec.ability)
    pokemon.moves = [make_move(move) for move in spec.moves]
    if spec.status:
        if hasattr(pokemon, "setStatus"):
            pokemon.setStatus(spec.status, source=pokemon, battle=battle)
        else:
            pokemon.status = spec.status
    if spec.fully_evolved is not None:
        pokemon.fully_evolved = spec.fully_evolved
    for key, value in spec.extra.items():
        setattr(pokemon, key, copy.deepcopy(value))
    item = _coerce_item(spec.item)
    if item is not None:
        battle.set_item(pokemon, item)


def _make_rng(
    *,
    seed: int,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
):
    if rng is not None and random_control is not None:
        raise ValueError("Pass either rng or random_control, not both")
    if rng is not None:
        return rng
    if random_control is not None:
        return ControlledRandom(seed=seed, control=random_control)
    return random.Random(seed)


def build_outcome_battle(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
):
    """Build a deterministic two-Pokemon battle from specs."""

    from .helpers import build_battle

    user_spec = user or PokemonSpec(name="User")
    target_spec = target or PokemonSpec(name="Target")
    battle, user_pokemon, target_pokemon = build_battle(
        attacker_types=list(user_spec.types),
        defender_types=list(target_spec.types),
    )
    battle.rng = _make_rng(seed=seed, rng=rng, random_control=random_control)
    battle.debug = False
    battle.log_action = lambda *_args, **_kwargs: None
    _apply_spec(battle, user_pokemon, user_spec)
    _apply_spec(battle, target_pokemon, target_spec)
    return battle, user_pokemon, target_pokemon


def _refresh_pokemon_stats(pokemon) -> None:
    """Refresh calculated battle stats after a form/base-stat change."""

    if hasattr(pokemon, "_battle_stats"):
        try:
            pokemon.stats = pokemon._battle_stats()
        except Exception:
            pass


def _species_metadata(entry: Any) -> dict[str, Any]:
    raw = copy.deepcopy(getattr(entry, "raw", {}) or {})
    abilities = raw.get("abilities")
    if not isinstance(abilities, Mapping):
        abilities = {
            str(slot): _effect_name(ability)
            for slot, ability in (getattr(entry, "abilities", {}) or {}).items()
        }
    base_stats = raw.get("baseStats")
    if not isinstance(base_stats, Mapping):
        stats = getattr(entry, "base_stats", None)
        base_stats = {
            "hp": getattr(stats, "hp", 0),
            "atk": getattr(stats, "attack", getattr(stats, "atk", 0)),
            "def": getattr(stats, "defense", getattr(stats, "def_", 0)),
            "spa": getattr(stats, "special_attack", getattr(stats, "spa", 0)),
            "spd": getattr(stats, "special_defense", getattr(stats, "spd", 0)),
            "spe": getattr(stats, "speed", getattr(stats, "spe", 0)),
        }
    return {
        "name": str(getattr(entry, "name", raw.get("name", ""))),
        "types": list(getattr(entry, "types", raw.get("types", [])) or []),
        "baseSpecies": raw.get("baseSpecies"),
        "forme": raw.get("forme"),
        "changesFrom": raw.get("changesFrom"),
        "battleOnly": raw.get("battleOnly"),
        "requiredItem": raw.get("requiredItem"),
        "requiredAbility": raw.get("requiredAbility"),
        "requiredMove": raw.get("requiredMove"),
        "abilities": _stable_mapping(abilities),
        "baseStats": _stable_mapping(base_stats),
    }


def run_species_outcome(
    *,
    species: str,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Build one species/form into battle and expose stable dex metadata."""

    entry = dex_pokemon(species)
    user_spec = pokemon_spec_from_dex(species)
    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user_spec,
        target=PokemonSpec(name="Species Proof Target"),
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    _refresh_pokemon_stats(user_pokemon)
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
        metadata={"species": _species_metadata(entry)},
    )


def canonical_boosts(boosts: Mapping[str, Any] | None) -> dict[str, int]:
    """Return boosts under stable Showdown-style short keys."""

    result = {key: 0 for key in ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")}
    for key, value in (boosts or {}).items():
        canonical = STAT_ALIASES.get(str(key), str(key))
        if canonical in result:
            result[canonical] = int(value or 0)
    return result


def canonical_stats(pokemon) -> dict[str, int]:
    """Return battle-relevant raw stat values under short stat keys."""

    result = {key: 0 for key in ("atk", "def", "spa", "spd", "spe")}
    attr_names = {
        "atk": ("atk", "attack"),
        "def": ("def", "defense"),
        "spa": ("spa", "special_attack"),
        "spd": ("spd", "special_defense"),
        "spe": ("spe", "speed"),
    }
    stats_sources = (
        getattr(pokemon, "stats", None),
        getattr(pokemon, "base_stats", None),
    )
    for key, names in attr_names.items():
        value = UNSET
        for name in names:
            if hasattr(pokemon, name):
                value = getattr(pokemon, name)
                break
        if value is UNSET:
            for source in stats_sources:
                if isinstance(source, Mapping):
                    for name in names:
                        if name in source:
                            value = source[name]
                            break
                elif source is not None:
                    for name in names:
                        if hasattr(source, name):
                            value = getattr(source, name)
                            break
                if value is not UNSET:
                    break
        try:
            result[key] = int(value if value is not UNSET else 0)
        except (TypeError, ValueError):
            result[key] = 0
    return result


def _effect_name(effect: Any) -> str:
    if effect is None:
        return ""
    raw = getattr(effect, "raw", None)
    if isinstance(raw, Mapping) and raw.get("name"):
        return str(raw["name"])
    return str(getattr(effect, "name", effect) or "")


def _stable_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _stable_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_stable_value(item) for item in value]
    return _effect_name(value) or value.__class__.__name__


def _stable_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return {str(key): _stable_value(value) for key, value in (mapping or {}).items()}


def snapshot_side(side) -> SideSnapshot:
    """Capture assertion-friendly side conditions and hazards."""

    if side is None:
        return SideSnapshot()
    slot_conditions = {}
    slot_condition_state = {}
    for slot, conditions in (getattr(side, "slot_conditions", {}) or {}).items():
        slot_conditions[str(slot)] = sorted(str(key) for key in (conditions or {}).keys())
        slot_condition_state[str(slot)] = {
            str(key): _stable_mapping(value if isinstance(value, Mapping) else {})
            for key, value in (conditions or {}).items()
        }
    conditions = getattr(side, "conditions", {}) or {}
    return SideSnapshot(
        conditions=sorted(str(key) for key in conditions.keys()),
        condition_state={
            str(key): _stable_mapping(value if isinstance(value, Mapping) else {})
            for key, value in conditions.items()
        },
        hazards=_stable_mapping(getattr(side, "hazards", {}) or {}),
        screens=_stable_mapping(getattr(side, "screens", {}) or {}),
        volatiles=_stable_mapping(getattr(side, "volatiles", {}) or {}),
        slot_conditions=slot_conditions,
        slot_condition_state=slot_condition_state,
    )


def snapshot_pokemon(pokemon) -> PokemonSnapshot:
    """Capture stable, assertion-friendly Pokemon battle state."""

    item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
    ability = getattr(pokemon, "ability", None)
    last_move = getattr(pokemon, "last_move", None)
    return PokemonSnapshot(
        name=str(getattr(pokemon, "name", "")),
        species=str(getattr(pokemon, "species", "")),
        hp=int(getattr(pokemon, "hp", 0) or 0),
        max_hp=int(getattr(pokemon, "max_hp", 0) or 0),
        status=getattr(pokemon, "status", 0) or 0,
        types=list(getattr(pokemon, "types", []) or []),
        ability=_effect_name(ability),
        item=_effect_name(item),
        ability_state=_stable_mapping(getattr(pokemon, "abilityState", {}) or {}),
        stats=canonical_stats(pokemon),
        boosts=canonical_boosts(getattr(pokemon, "boosts", {}) or {}),
        tempvals=_stable_mapping(getattr(pokemon, "tempvals", {}) or {}),
        volatiles=sorted(str(key) for key in (getattr(pokemon, "volatiles", {}) or {}).keys()),
        moves=[_effect_name(move) for move in (getattr(pokemon, "moves", []) or [])],
        last_move={
            "name": _effect_name(last_move),
            "pp": getattr(last_move, "pp", None),
        },
        immune=getattr(pokemon, "immune", None),
        fainted=bool(getattr(pokemon, "is_fainted", False) or getattr(pokemon, "hp", 0) <= 0),
    )


def snapshot_battle(battle, user, target) -> BattleSnapshot:
    """Capture the relevant battle state for outcome assertions."""

    field = getattr(battle, "field", None)
    user_part = battle.participant_for(user) if battle else None
    target_part = battle.participant_for(target) if battle else None
    pseudo_weather = getattr(field, "pseudo_weather", {}) or {} if field else {}
    return BattleSnapshot(
        user=snapshot_pokemon(user),
        target=snapshot_pokemon(target),
        user_side=snapshot_side(user_part.side if user_part else None),
        target_side=snapshot_side(target_part.side if target_part else None),
        weather=str(getattr(field, "weather", "") or "") if field else "",
        terrain=str(getattr(field, "terrain", "") or "") if field else "",
        pseudo_weather=sorted(str(key) for key in pseudo_weather.keys()) if field else [],
        pseudo_weather_state={
            str(key): _stable_mapping(value if isinstance(value, Mapping) else {})
            for key, value in pseudo_weather.items()
        } if field else {},
    )


def _debug_ints(debug: Mapping[str, Any], key: str) -> tuple[int, ...]:
    return tuple(int(value) for value in debug.get(key, []) or [])


def _debug_floats(debug: Mapping[str, Any], key: str) -> tuple[float, ...]:
    return tuple(float(value) for value in debug.get(key, []) or [])


def _debug_bools(debug: Mapping[str, Any], key: str) -> tuple[bool, ...]:
    return tuple(bool(value) for value in debug.get(key, []) or [])


def snapshot_damage(attacker, target, move, result, *, update_hp: bool, spread: bool) -> DamageSnapshot:
    """Capture stable damage debug data from one damage application."""

    debug = getattr(result, "debug", {}) or {}
    final_damage = _debug_ints(debug, "damage")
    per_hit = _debug_ints(debug, "per_hit_damage") or final_damage
    return DamageSnapshot(
        move_name=str(getattr(move, "name", "")),
        source=str(getattr(attacker, "name", "")),
        target=str(getattr(target, "name", "")),
        per_hit=per_hit,
        total=sum(final_damage or per_hit),
        power=_debug_ints(debug, "power"),
        random_rolls=_debug_floats(debug, "rand"),
        critical=_debug_bools(debug, "critical"),
        stab=_debug_floats(debug, "stab"),
        type_effectiveness=_debug_floats(debug, "type_effectiveness"),
        attack=_debug_ints(debug, "attack"),
        defense=_debug_ints(debug, "defense"),
        update_hp=update_hp,
        spread=spread,
    )


@contextmanager
def capture_damage_snapshots():
    """Collect ``DamageSnapshot`` instances while a move outcome runs."""

    from pokemon.battle import damage as damage_mod  # type: ignore

    original_apply_damage = damage_mod.apply_damage
    snapshots: list[DamageSnapshot] = []

    def wrapped_apply_damage(attacker, target, move, battle=None, *args, **kwargs):
        result = original_apply_damage(attacker, target, move, battle=battle, *args, **kwargs)
        snapshots.append(
            snapshot_damage(
                attacker,
                target,
                move,
                result,
                update_hp=bool(kwargs.get("update_hp", True)),
                spread=bool(kwargs.get("spread", False)),
            )
        )
        return result

    damage_mod.apply_damage = wrapped_apply_damage
    try:
        yield snapshots
    finally:
        damage_mod.apply_damage = original_apply_damage


def move_action(battle, pokemon, move, *, target_pokemon=None):
    """Build a move Action using participant targets."""

    load_modules()
    from pokemon.battle.actions import Action, ActionType  # type: ignore

    participant = battle.participant_for(pokemon)
    if participant is None:
        raise AssertionError(f"{pokemon!r} is not in the battle")
    if target_pokemon is None:
        raw_target = (getattr(move, "raw", {}) or {}).get("target")
        target = participant if raw_target == "self" else battle.opponent_of(participant)
    else:
        target = battle.participant_for(target_pokemon)
    return Action(
        actor=participant,
        action_type=ActionType.MOVE,
        target=target,
        move=move,
        pokemon=pokemon,
        priority=getattr(move, "priority", 0),
    )


def run_move_outcome(
    *,
    move: str | MoveSpec | Any,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
    full_turn: bool = False,
    opponent_move: str | MoveSpec | Any | None = None,
) -> OutcomeResult:
    """Execute one deterministic move and return before/after snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    battle_move = make_move(move)
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    action = move_action(battle, user_pokemon, battle_move, target_pokemon=target_pokemon)
    with capture_damage_snapshots() as damage_snapshots:
        if full_turn:
            actions = [action]
            if opponent_move is not None:
                target_move = make_move(opponent_move)
                actions.append(move_action(battle, target_pokemon, target_move, target_pokemon=user_pokemon))
            battle.execute_turn(actions)
        else:
            battle.use_move(action)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        damage=tuple(damage_snapshots),
    )


def _make_target_ally(battle, user_pokemon, target_pokemon) -> None:
    user_participant = battle.participant_for(user_pokemon)
    target_participant = battle.participant_for(target_pokemon)
    if user_participant is not None:
        if target_pokemon not in user_participant.pokemons:
            user_participant.pokemons.append(target_pokemon)
        if target_pokemon not in user_participant.active:
            user_participant.active.append(target_pokemon)
        target_pokemon.side = getattr(user_participant, "side", None)
        if target_pokemon.side is not None:
            target_pokemon.side.pokemons = user_participant.pokemons
            target_pokemon.side.active = user_participant.active
    if target_participant is not None and target_participant is not user_participant:
        target_participant.pokemons = [poke for poke in target_participant.pokemons if poke is not target_pokemon]
        target_participant.active = [poke for poke in target_participant.active if poke is not target_pokemon]
        if getattr(target_participant, "side", None) is not None:
            target_participant.side.pokemons = target_participant.pokemons
            target_participant.side.active = target_participant.active


def _set_side_hazards(battle, pokemon, hazards: Mapping[str, Any] | None) -> None:
    if hazards is None:
        return
    participant = battle.participant_for(pokemon)
    side = getattr(participant, "side", None) if participant is not None else None
    if side is None:
        return
    side.hazards = dict(hazards)
    if hasattr(side, "sync_hazard_conditions"):
        side.sync_hazard_conditions()


def _resolve_move_callback(move, event: str):
    callback = getattr(move, event, None)
    if callable(callback):
        return callback
    raw = getattr(move, "raw", None)
    if isinstance(raw, Mapping):
        cb_name = raw.get(event)
        if cb_name:
            from pokemon.battle.callbacks import resolve_callback_from_modules

            return resolve_callback_from_modules(cb_name, "pokemon.dex.functions.moves_funcs")
    return None


def run_move_event_outcome(
    *,
    move: str | MoveSpec | Any,
    event: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    target_is_ally: bool = False,
    game_type: str | None = None,
    battle_extra: Mapping[str, Any] | None = None,
    user_side_hazards: Mapping[str, Any] | None = None,
    target_side_hazards: Mapping[str, Any] | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Invoke a move callback with deterministic battle state."""

    from pokemon.battle.callbacks import invoke_callback

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    if game_type is not None:
        battle.gameType = game_type
    if target_is_ally:
        _make_target_ally(battle, user_pokemon, target_pokemon)
    for key, value in (battle_extra or {}).items():
        if key == "terrain":
            battle.setTerrain(value, source=user_pokemon)
        else:
            setattr(battle, str(key), copy.deepcopy(value))
    _set_side_hazards(battle, user_pokemon, user_side_hazards)
    _set_side_hazards(battle, target_pokemon, target_side_hazards)

    battle_move = make_move(move)
    callback = _resolve_move_callback(battle_move, event)
    if not callable(callback):
        raise AssertionError(f"{getattr(battle_move, 'name', move)} has no {event} callback")

    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    if event == "onHit":
        event_result = invoke_callback(callback, user_pokemon, target_pokemon, battle=battle)
    elif event == "onTry":
        event_result = invoke_callback(callback, user_pokemon, target_pokemon, battle_move, battle=battle)
    elif event == "onTryHit":
        event_result = invoke_callback(callback, target_pokemon, user_pokemon, battle_move, battle=battle)
    elif event == "onHitField":
        event_result = invoke_callback(callback, user_pokemon, battle=battle)
    else:
        event_result = invoke_callback(
            callback,
            user_pokemon,
            target_pokemon,
            battle=battle,
            move=battle_move,
        )
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    queue = getattr(battle, "queue", None)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        metadata={
            "move_event_result": _stable_value(event_result),
            "queue_prioritized": bool(getattr(queue, "prioritized", None)),
            "called_moves": tuple(str(name) for name in getattr(battle, "called_moves", []) or []),
        },
    )


def run_residual_outcome(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Execute only the residual phase and return before/after snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    battle.residual()
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
    )


def run_ability_start_outcome(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    enter_sides: Sequence[str] = ("user",),
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Trigger deterministic battle-entry callbacks and return snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    for side in enter_sides:
        if side == "user":
            battle.on_enter_battle(user_pokemon)
        elif side == "target":
            battle.on_enter_battle(target_pokemon)
        else:
            raise ValueError("enter_sides values must be 'user' or 'target'")
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
    )


def run_post_battle_ability_outcome(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    thrown_ball: str | None = None,
    caught: bool = False,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Resolve post-battle ability effects and return before/after snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    resolver = getattr(battle, "resolve_post_battle_abilities", None)
    if not callable(resolver):
        raise AssertionError("Battle.resolve_post_battle_abilities is not available")
    resolver(caught=caught, thrown_ball=thrown_ball)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
    )


def run_run_outcome(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    battle_type: str = "wild",
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Execute one flee attempt and return before/after snapshots plus metadata."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    modules = load_modules()
    BattleType = modules["BattleType"]
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    normalized = normalize_key(battle_type)
    if normalized == "trainer":
        battle.type = BattleType.TRAINER
    elif normalized == "wild":
        battle.type = BattleType.WILD
    else:
        raise ValueError("battle_type must be 'wild' or 'trainer'")
    participant = battle.participant_for(user_pokemon)
    action = Action(actor=participant, action_type=ActionType.RUN, pokemon=user_pokemon)
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    battle.execute_actions([action])
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    result = dict(getattr(battle, "_flee_result", {}) or {})
    result["battle_over"] = bool(getattr(battle, "battle_over", False))
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
        metadata={"run": result},
    )


def run_before_move_outcome(
    *,
    move: str | MoveSpec | Any = "Tackle",
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    checks: int = 1,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Run the before-move gate without resolving the full move."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    battle_move = make_move(move)
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    history = []
    for _ in range(max(1, int(checks))):
        history.append(bool(battle.status_prevents_move(user_pokemon, battle_move)))
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        metadata={"before_move_prevented": history[-1], "before_move_prevented_history": tuple(history)},
    )


def run_switch_outcome(
    *,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Run a switch-out event for the user and return before/after snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    battle.on_switch_out(user_pokemon)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
    )


def run_item_event_outcome(
    *,
    event: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Run a focused held-item event and return before/after snapshots."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    normalized = normalize_key(event)
    if normalized == "eat":
        event_result = battle.eat_item(user_pokemon, source=target_pokemon, effect="test:item-event")
    elif normalized == "take":
        event_result = battle.take_item(user_pokemon, source=target_pokemon, effect="test:item-event")
    elif normalized in {"removeused", "use"}:
        event_result = battle.remove_item(user_pokemon, source=target_pokemon, effect="test:item-event", used=True)
    else:
        raise ValueError("event must be 'eat', 'take', or 'remove_used'")
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=None,
        before=before,
        after=after,
        metadata={"item_event_result": _stable_value(event_result)},
    )


def _apply_battle_extra(battle, source_pokemon, extra: Mapping[str, Any] | None) -> None:
    for key, value in (extra or {}).items():
        if key == "terrain":
            battle.setTerrain(value, source=source_pokemon)
        elif key == "field_terrain":
            field = getattr(battle, "field", None)
            if field is not None:
                field.terrain = value
        elif key == "weather":
            battle.setWeather(value, source=source_pokemon)
        elif key == "pseudo_weather":
            battle.add_pseudo_weather(value, source=source_pokemon)
        else:
            setattr(battle, str(key), copy.deepcopy(value))


def _assign_held_item_without_events(battle, pokemon, item: Any):
    """Give a Pokemon an item without firing item start/form callbacks."""

    item_obj = _coerce_item(item)
    if item_obj is None:
        return None
    pokemon.item = item_obj
    if hasattr(pokemon, "held_item"):
        pokemon.held_item = getattr(item_obj, "name", str(item_obj))
    pokemon.item_state = battle.init_effect_state(item_obj, target=pokemon)
    pokemon.last_item = getattr(item_obj, "name", str(item_obj))
    return item_obj


def run_form_change_outcome(
    *,
    trigger: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    item: Any = None,
    event: str | None = None,
    move: str | MoveSpec | Any | None = None,
    battle_extra: Mapping[str, Any] | None = None,
    direct_forme: str | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Run a deterministic form-change trigger and capture before/after state."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    extra = dict(battle_extra or {})
    participant_mega_evolved = bool(extra.pop("participant_mega_evolved", False))
    _apply_battle_extra(battle, user_pokemon, extra)
    if participant_mega_evolved:
        participant = battle.participant_for(user_pokemon)
        if participant is not None:
            setattr(participant, "mega_evolved", True)
            side = getattr(participant, "side", None)
            if side is not None:
                setattr(side, "mega_evolved", True)
    battle_move = make_move(move) if move is not None else None
    metadata: dict[str, Any] = {}

    normalized_trigger = normalize_key(trigger)
    if normalized_trigger in {"takeitem", "take", "clearitem", "clear"}:
        if item is not None:
            battle.set_item(user_pokemon, _coerce_item(item))
            _refresh_pokemon_stats(user_pokemon)
        before = snapshot_battle(battle, user_pokemon, target_pokemon)
        if normalized_trigger in {"clearitem", "clear"}:
            metadata["form_change_result"] = battle.set_item(user_pokemon, None)
        else:
            removed = battle.take_item(user_pokemon)
            metadata["removed_item"] = _effect_name(removed)
            metadata["form_change_result"] = removed is not None
    else:
        if normalized_trigger in {"enter", "switchin"} and item is not None:
            _assign_held_item_without_events(battle, user_pokemon, item)
        elif normalized_trigger in {"mega", "megaevolution", "pendingmega", "lockchoicesmega"} and item is not None:
            battle.set_item(user_pokemon, _coerce_item(item))
            _refresh_pokemon_stats(user_pokemon)
        before = snapshot_battle(battle, user_pokemon, target_pokemon)
        if normalized_trigger in {"setitem", "item"}:
            metadata["form_change_result"] = battle.set_item(user_pokemon, _coerce_item(item))
        elif normalized_trigger in {"enter", "switchin"}:
            metadata["form_change_result"] = battle.on_enter_battle(user_pokemon)
        elif normalized_trigger in {"mega", "megaevolution"}:
            metadata["form_change_result"] = battle.perform_mega_evolution(user_pokemon)
            metadata["mega_failure_reason"] = getattr(user_pokemon, "mega_evolution_failed_reason", "")
        elif normalized_trigger in {"pendingmega", "lockchoicesmega"}:
            user_pokemon.pending_mega = True
            battle.lock_choices()
            metadata["form_change_result"] = getattr(user_pokemon, "last_mega_evolution_result", False)
            metadata["mega_failure_reason"] = getattr(user_pokemon, "mega_evolution_failed_reason", "")
        elif normalized_trigger in {"abilityevent", "ability"}:
            if event is None:
                raise ValueError("ability_event form contracts require an event")
            ability = _coerce_ability(getattr(user_pokemon, "ability", None))
            if ability is None:
                raise AssertionError(f"{user_pokemon.name} has no ability for {event}")
            user_pokemon.ability = ability
            metadata["form_change_result"] = _stable_value(
                ability.call(
                    event,
                    battle=battle,
                    effect_state=battle.init_effect_state(ability, target=user_pokemon),
                    pokemon=user_pokemon,
                    user=user_pokemon,
                    target=target_pokemon,
                    source=user_pokemon,
                    move=battle_move,
                )
            )
        elif normalized_trigger in {"moveevent", "move"}:
            if event is None:
                raise ValueError("move_event form contracts require an event")
            if battle_move is None:
                raise ValueError("move_event form contracts require a move")
            from pokemon.battle.callbacks import invoke_callback

            callback = _resolve_move_callback(battle_move, event)
            if not callable(callback):
                raise AssertionError(f"{getattr(battle_move, 'name', move)} has no {event} callback")
            metadata["form_change_result"] = _stable_value(
                invoke_callback(
                    callback,
                    user_pokemon,
                    target_pokemon,
                    battle=battle,
                    move=battle_move,
                )
            )
        elif normalized_trigger in {"direct", "formechange"}:
            if not direct_forme:
                raise ValueError("direct form contracts require direct_forme")
            metadata["form_change_result"] = user_pokemon.formeChange(
                direct_forme,
                battle=battle,
                source=user_pokemon,
            )
        else:
            raise ValueError(f"Unsupported form-change trigger: {trigger}")

    _refresh_pokemon_stats(user_pokemon)
    _refresh_pokemon_stats(target_pokemon)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        metadata=metadata,
    )


@contextmanager
def _patched_item_random(battle):
    """Route item callbacks that use module-level random through battle.rng."""

    items_funcs = sys.modules.get("pokemon.dex.functions.items_funcs")
    if items_funcs is None:
        try:
            from pokemon.dex.functions import items_funcs as imported_items_funcs
        except Exception:
            yield
            return
        items_funcs = imported_items_funcs
    if items_funcs is None:
        yield
        return

    old_random = getattr(items_funcs, "random", None)
    rng = getattr(battle, "rng", None)
    if rng is None or not hasattr(rng, "random"):
        yield
        return
    items_funcs.random = rng.random
    try:
        yield
    finally:
        if old_random is None:
            try:
                delattr(items_funcs, "random")
            except AttributeError:
                pass
        else:
            items_funcs.random = old_random


def run_item_callback_outcome(
    *,
    item: Any,
    event: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    owner: str = "user",
    target_side: str | None = "target",
    source_side: str | None = "user",
    pokemon_side: str | None = "user",
    held: bool = True,
    battle_extra: Mapping[str, Any] | None = None,
    move: str | MoveSpec | Any | None = None,
    move_extra: Mapping[str, Any] | None = None,
    status: Any = UNSET,
    boosts: Mapping[str, int] | None = None,
    relay_value: Any = UNSET,
    effect_id: str | None = None,
    effect_name: str | None = None,
    effect_type: str | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Invoke a held-item callback or inspect item metadata."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    owner_pokemon = _contract_side(owner, user_pokemon, target_pokemon)
    if owner_pokemon is None:
        raise ValueError("owner must resolve to a Pokemon")
    item_obj = _coerce_item(item)
    if item_obj is None:
        raise AssertionError(f"Unknown item for {event}: {item}")
    if held:
        battle.set_item(owner_pokemon, item_obj)
        item_obj = getattr(owner_pokemon, "item", None) or item_obj
    _apply_battle_extra(battle, user_pokemon, battle_extra)

    battle_move = make_move(move) if move is not None else None
    if battle_move is not None:
        for key, value in (move_extra or {}).items():
            setattr(battle_move, str(key), copy.deepcopy(value))
    mutable_boosts = dict(boosts or {})
    kwargs: dict[str, Any] = {"battle": battle}
    target_arg = _contract_side(target_side, user_pokemon, target_pokemon)
    source_arg = _contract_side(source_side, user_pokemon, target_pokemon)
    pokemon_arg = _contract_side(pokemon_side, user_pokemon, target_pokemon)
    if target_arg is not None:
        kwargs["target"] = target_arg
    if source_arg is not None:
        kwargs["source"] = source_arg
    if pokemon_arg is not None:
        kwargs["pokemon"] = pokemon_arg
    if battle_move is not None:
        kwargs["move"] = battle_move
    if status is not UNSET:
        kwargs["status"] = status
    if boosts is not None:
        kwargs["boost"] = mutable_boosts
        kwargs["boosts"] = mutable_boosts
    if effect_id is not None or effect_name is not None or effect_type is not None:
        kwargs["effect"] = SimpleNamespace(
            id=effect_id or "",
            name=effect_name or effect_id or "",
            effectType=effect_type or "",
        )

    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    normalized = normalize_key(event)
    event_result = UNSET
    if normalized not in {"metadata", "noop", "none"}:
        args = () if relay_value is UNSET else (relay_value,)
        with _patched_item_random(battle):
            event_result = item_obj.call(event, *args, **kwargs)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        metadata={
            "item_callback_result": _stable_value(event_result) if event_result is not UNSET else UNSET,
            "item_callback_boosts": canonical_boosts(mutable_boosts),
            "item": item_obj,
        },
    )


def _contract_side(side: str | None, user, target):
    if side == "user":
        return user
    if side == "target":
        return target
    if side is None:
        return None
    raise ValueError("side values must be 'user', 'target', or None")


def run_ability_event_outcome(
    *,
    event: str,
    user: PokemonSpec | None = None,
    target: PokemonSpec | None = None,
    owner: str = "user",
    target_side: str | None = "target",
    source_side: str | None = "user",
    pokemon_side: str | None = None,
    target_is_ally: bool = False,
    game_type: str | None = None,
    move: str | MoveSpec | Any | None = None,
    move_extra: Mapping[str, Any] | None = None,
    item: Any = None,
    status: Any = UNSET,
    boosts: Mapping[str, int] | None = None,
    relay_value: Any = UNSET,
    effect_id: str | None = None,
    effect_type: str | None = None,
    seed: int = 0,
    rng: Any | None = None,
    random_control: RandomControl | None = None,
) -> OutcomeResult:
    """Invoke a single ability callback with structured battle objects."""

    battle, user_pokemon, target_pokemon = build_outcome_battle(
        user=user,
        target=target,
        seed=seed,
        rng=rng,
        random_control=random_control,
    )
    if game_type is not None:
        battle.gameType = game_type
    if target_is_ally:
        user_participant = battle.participant_for(user_pokemon)
        target_participant = battle.participant_for(target_pokemon)
        if user_participant is not None:
            if target_pokemon not in user_participant.pokemons:
                user_participant.pokemons.append(target_pokemon)
            if target_pokemon not in user_participant.active:
                user_participant.active.append(target_pokemon)
            target_pokemon.side = getattr(user_participant, "side", None)
            if target_pokemon.side is not None:
                target_pokemon.side.pokemons = user_participant.pokemons
                target_pokemon.side.active = user_participant.active
        if target_participant is not None and target_participant is not user_participant:
            target_participant.pokemons = [poke for poke in target_participant.pokemons if poke is not target_pokemon]
            target_participant.active = [poke for poke in target_participant.active if poke is not target_pokemon]
            if getattr(target_participant, "side", None) is not None:
                target_participant.side.pokemons = target_participant.pokemons
                target_participant.side.active = target_participant.active
    owner_pokemon = _contract_side(owner, user_pokemon, target_pokemon)
    if owner_pokemon is None:
        raise ValueError("owner must resolve to a Pokemon")
    ability = _coerce_ability(getattr(owner_pokemon, "ability", None))
    if ability is None:
        raise AssertionError(f"{owner_pokemon.name} has no ability for {event}")
    owner_pokemon.ability = ability
    battle_move = make_move(move) if move is not None else None
    if battle_move is not None:
        for key, value in (move_extra or {}).items():
            setattr(battle_move, str(key), copy.deepcopy(value))
    event_item = _coerce_item(item) if item is not None else None
    mutable_boosts = dict(boosts or {})
    kwargs: dict[str, Any] = {
        "battle": battle,
        "effect_state": battle.init_effect_state(ability, target=owner_pokemon),
    }
    target_arg = _contract_side(target_side, user_pokemon, target_pokemon)
    source_arg = _contract_side(source_side, user_pokemon, target_pokemon)
    pokemon_arg = _contract_side(pokemon_side, user_pokemon, target_pokemon)
    if target_arg is not None:
        kwargs["target"] = target_arg
    if source_arg is not None:
        kwargs["source"] = source_arg
    if pokemon_arg is not None:
        kwargs["pokemon"] = pokemon_arg
    if battle_move is not None:
        kwargs["move"] = battle_move
    if event_item is not None:
        kwargs["item"] = event_item
    if status is not UNSET:
        kwargs["status"] = status
    if boosts is not None:
        kwargs["boost"] = mutable_boosts
        kwargs["boosts"] = mutable_boosts
    if effect_id is not None or effect_type is not None:
        kwargs["effect"] = SimpleNamespace(id=effect_id or "", effectType=effect_type or "")
    before = snapshot_battle(battle, user_pokemon, target_pokemon)
    args = () if relay_value is UNSET else (relay_value,)
    event_result = ability.call(event, *args, **kwargs)
    after = snapshot_battle(battle, user_pokemon, target_pokemon)
    return OutcomeResult(
        battle=battle,
        user=user_pokemon,
        target=target_pokemon,
        move=battle_move,
        before=before,
        after=after,
        metadata={
            "ability_event_result": _stable_value(event_result),
            "ability_event_boosts": canonical_boosts(mutable_boosts),
        },
    )


def assert_pokemon_expectation(
    result: OutcomeResult,
    side: str,
    expected: PokemonExpectation,
) -> None:
    """Assert one side of an OutcomeResult against focused expectations."""

    before = getattr(result.before, side)
    after = getattr(result.after, side)
    label = f"{side} ({after.name})"

    if expected.hp is not UNSET:
        assert after.hp == expected.hp, f"{label} hp"
    if expected.hp_delta is not UNSET:
        assert after.hp - before.hp == expected.hp_delta, f"{label} hp delta"
    if expected.hp_less_than is not UNSET:
        assert after.hp < expected.hp_less_than, f"{label} hp less than"
    if expected.hp_greater_than is not UNSET:
        assert after.hp > expected.hp_greater_than, f"{label} hp greater than"
    if expected.species is not UNSET:
        assert after.species == expected.species, f"{label} species"
    if expected.status is not UNSET:
        assert after.status == expected.status, f"{label} status"
    if expected.types is not None:
        assert after.types == list(expected.types), f"{label} types"
    if expected.ability is not UNSET:
        assert after.ability == expected.ability, f"{label} ability"
    if expected.immune is not UNSET:
        assert after.immune == expected.immune, f"{label} immune"
    if expected.item is not UNSET:
        assert after.item == expected.item, f"{label} item"
    if expected.fainted is not UNSET:
        assert after.fainted is expected.fainted, f"{label} fainted"
    if expected.moves is not None:
        assert after.moves == list(expected.moves), f"{label} moves"
    if expected.last_move is not None:
        for key, value in expected.last_move.items():
            assert after.last_move.get(str(key)) == value, f"{label} last_move.{key}"
    if expected.stats is not None:
        for key, value in expected.stats.items():
            canonical = STAT_ALIASES.get(str(key), str(key))
            assert after.stats[canonical] == value, f"{label} {canonical} stat"
    if expected.volatiles is not None:
        assert after.volatiles == sorted(str(value) for value in expected.volatiles), f"{label} volatiles"
    if expected.boosts is not None:
        for key, value in expected.boosts.items():
            canonical = STAT_ALIASES.get(str(key), str(key))
            assert after.boosts[canonical] == value, f"{label} {canonical} boost"
    if expected.ability_state is not None:
        for key, value in expected.ability_state.items():
            assert after.ability_state.get(str(key)) == value, f"{label} ability_state.{key}"
    if expected.tempvals is not None:
        for key, value in expected.tempvals.items():
            assert after.tempvals.get(str(key)) == value, f"{label} tempvals.{key}"


def assert_battle_expectation(
    result: OutcomeResult,
    expected: BattleExpectation,
) -> None:
    """Assert field and side state against focused expectations."""

    after = result.after
    if expected.weather is not UNSET:
        assert after.weather == expected.weather, "field weather"
    if expected.terrain is not UNSET:
        assert after.terrain == expected.terrain, "field terrain"
    if expected.pseudo_weather is not None:
        assert after.pseudo_weather == sorted(str(value) for value in expected.pseudo_weather), "field pseudo_weather"
    if expected.pseudo_weather_state is not None:
        for key, mapping in expected.pseudo_weather_state.items():
            state = after.pseudo_weather_state.get(str(key))
            assert state is not None, f"field pseudo_weather_state.{key}"
            for state_key, value in mapping.items():
                assert state.get(str(state_key)) == value, f"field pseudo_weather_state.{key}.{state_key}"
    if expected.user_side_conditions is not None:
        assert after.user_side.conditions == sorted(str(value) for value in expected.user_side_conditions), "user side conditions"
    if expected.target_side_conditions is not None:
        assert after.target_side.conditions == sorted(str(value) for value in expected.target_side_conditions), "target side conditions"
    if expected.user_side_condition_state is not None:
        for key, mapping in expected.user_side_condition_state.items():
            state = after.user_side.condition_state.get(str(key))
            assert state is not None, f"user side condition_state.{key}"
            for state_key, value in mapping.items():
                assert state.get(str(state_key)) == value, f"user side condition_state.{key}.{state_key}"
    if expected.target_side_condition_state is not None:
        for key, mapping in expected.target_side_condition_state.items():
            state = after.target_side.condition_state.get(str(key))
            assert state is not None, f"target side condition_state.{key}"
            for state_key, value in mapping.items():
                assert state.get(str(state_key)) == value, f"target side condition_state.{key}.{state_key}"
    if expected.user_side_hazards is not None:
        for key, value in expected.user_side_hazards.items():
            assert after.user_side.hazards.get(str(key)) == value, f"user side hazard {key}"
    if expected.target_side_hazards is not None:
        for key, value in expected.target_side_hazards.items():
            assert after.target_side.hazards.get(str(key)) == value, f"target side hazard {key}"


def _expected_tuple(value: Sequence[Any] | Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return (value,)


def assert_damage_expectation(
    result: OutcomeResult,
    expected: DamageExpectation | None,
) -> None:
    """Assert captured damage debug state against a focused expectation."""

    if expected is None:
        return

    events = result.damage
    per_hit = tuple(hit for event in events for hit in event.per_hit)
    powers = tuple(value for event in events for value in event.power)
    random_rolls = tuple(value for event in events for value in event.random_rolls)
    critical = tuple(value for event in events for value in event.critical)
    stab = tuple(value for event in events for value in event.stab)
    effectiveness = tuple(value for event in events for value in event.type_effectiveness)
    attack = tuple(value for event in events for value in event.attack)
    defense = tuple(value for event in events for value in event.defense)

    if expected.event_count is not None:
        assert len(events) == expected.event_count, "damage event count"
    if expected.total is not UNSET:
        assert sum(event.total for event in events) == expected.total, "total damage"
    if expected.per_hit is not None:
        assert per_hit == tuple(int(value) for value in expected.per_hit), "per-hit damage"
    if expected.power is not None:
        assert powers == tuple(int(value) for value in _expected_tuple(expected.power)), "damage power"
    if expected.random_rolls is not None:
        assert random_rolls == tuple(float(value) for value in _expected_tuple(expected.random_rolls)), "damage random rolls"
    if expected.critical is not None:
        assert critical == tuple(bool(value) for value in _expected_tuple(expected.critical)), "damage critical flags"
    if expected.stab is not None:
        assert stab == tuple(float(value) for value in _expected_tuple(expected.stab)), "damage STAB"
    if expected.type_effectiveness is not None:
        assert effectiveness == tuple(float(value) for value in _expected_tuple(expected.type_effectiveness)), "damage type effectiveness"
    if expected.attack is not None:
        assert attack == tuple(int(value) for value in _expected_tuple(expected.attack)), "damage attack"
    if expected.defense is not None:
        assert defense == tuple(int(value) for value in _expected_tuple(expected.defense)), "damage defense"
    if expected.move_name is not None:
        assert events and events[0].move_name == expected.move_name, "damage move name"


def assert_move_outcome(contract: MoveOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative move outcome contract."""

    result = run_move_outcome(
        move=contract.move,
        user=contract.user,
        target=contract.target,
        seed=contract.seed,
        random_control=contract.random_control,
        full_turn=contract.full_turn,
        opponent_move=contract.opponent_move,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    assert_damage_expectation(result, contract.expect_damage)
    return result


def assert_move_event_outcome(contract: MoveEventOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative move callback contract."""

    result = run_move_event_outcome(
        move=contract.move,
        event=contract.event,
        user=contract.user,
        target=contract.target,
        target_is_ally=contract.target_is_ally,
        game_type=contract.game_type,
        battle_extra=contract.battle_extra,
        user_side_hazards=contract.user_side_hazards,
        target_side_hazards=contract.target_side_hazards,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_result is not UNSET:
        assert result.metadata.get("move_event_result") == contract.expect_result, "move event result"
    if contract.expect_queue_prioritized is not UNSET:
        assert result.metadata.get("queue_prioritized") is contract.expect_queue_prioritized, "queue prioritized"
    if contract.expect_called_moves is not None:
        assert result.metadata.get("called_moves") == tuple(contract.expect_called_moves), "called moves"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_residual_outcome(contract: ResidualOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative residual outcome contract."""

    result = run_residual_outcome(
        user=contract.user,
        target=contract.target,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_ability_start_outcome(contract: AbilityStartOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative ability-entry outcome contract."""

    result = run_ability_start_outcome(
        user=contract.user,
        target=contract.target,
        enter_sides=contract.enter_sides,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_ability_flag_outcome(contract: AbilityFlagOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative ability-flag move contract."""

    result = run_move_outcome(
        move=contract.move,
        user=contract.user,
        target=contract.target,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_post_battle_ability_outcome(contract: PostBattleAbilityOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative post-battle ability contract."""

    result = run_post_battle_ability_outcome(
        user=contract.user,
        target=contract.target,
        thrown_ball=contract.thrown_ball,
        caught=contract.caught,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    return result


def assert_run_outcome(contract: RunOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative flee outcome contract."""

    result = run_run_outcome(
        user=contract.user,
        target=contract.target,
        battle_type=contract.battle_type,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    run_result = result.metadata.get("run", {})
    if contract.expect_run.success is not UNSET:
        assert run_result.get("success") == contract.expect_run.success, "run success"
    if contract.expect_run.reason is not UNSET:
        assert run_result.get("reason") == contract.expect_run.reason, "run reason"
    if contract.expect_run.battle_over is not UNSET:
        assert run_result.get("battle_over") == contract.expect_run.battle_over, "run battle_over"
    return result


def assert_before_move_outcome(contract: BeforeMoveOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative before-move outcome contract."""

    result = run_before_move_outcome(
        move=contract.move,
        user=contract.user,
        target=contract.target,
        checks=contract.checks,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_prevented is not UNSET:
        assert result.metadata.get("before_move_prevented") == contract.expect_prevented, "before move prevented"
    if contract.expect_prevented_history is not None:
        assert result.metadata.get("before_move_prevented_history") == tuple(contract.expect_prevented_history), "before move prevented history"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    return result


def assert_switch_outcome(contract: SwitchOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative switch-out outcome contract."""

    result = run_switch_outcome(
        user=contract.user,
        target=contract.target,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    return result


def assert_item_event_outcome(contract: ItemEventOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative held-item event contract."""

    result = run_item_event_outcome(
        event=contract.event,
        user=contract.user,
        target=contract.target,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_result is not UNSET:
        assert result.metadata.get("item_event_result") == contract.expect_result, "item event result"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    return result


def assert_item_callback_outcome(contract: ItemCallbackOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative item callback or metadata contract."""

    result = run_item_callback_outcome(
        item=contract.item,
        event=contract.event,
        user=contract.user,
        target=contract.target,
        owner=contract.owner,
        target_side=contract.target_side,
        source_side=contract.source_side,
        pokemon_side=contract.pokemon_side,
        held=contract.held,
        battle_extra=contract.battle_extra,
        move=contract.move,
        move_extra=contract.move_extra,
        status=contract.status,
        boosts=contract.boosts,
        relay_value=contract.relay_value,
        effect_id=contract.effect_id,
        effect_name=contract.effect_name,
        effect_type=contract.effect_type,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_result is not UNSET:
        assert result.metadata.get("item_callback_result") == contract.expect_result, "item callback result"
    if contract.expect_boosts is not None:
        actual_boosts = result.metadata.get("item_callback_boosts") or {}
        for key, value in contract.expect_boosts.items():
            canonical = STAT_ALIASES.get(str(key), str(key))
            assert actual_boosts.get(canonical) == value, f"item callback boost {canonical}"
    item = result.metadata.get("item")
    if contract.expect_item_attrs is not None:
        for key, value in contract.expect_item_attrs.items():
            assert _stable_value(getattr(item, str(key), None)) == value, f"item attr {key}"
    if contract.expect_move_attrs is not None:
        assert result.move is not None, "item callback move"
        for key, value in contract.expect_move_attrs.items():
            assert _stable_value(getattr(result.move, str(key), None)) == value, f"move attr {key}"
    if contract.expect_raw is not None:
        raw = getattr(item, "raw", {}) or {}
        for key, value in contract.expect_raw.items():
            assert _stable_value(raw.get(str(key))) == value, f"item raw {key}"
    if contract.expect_user_attrs is not None:
        for key, value in contract.expect_user_attrs.items():
            assert _stable_value(getattr(result.user, str(key), None)) == value, f"user attr {key}"
    if contract.expect_target_attrs is not None:
        for key, value in contract.expect_target_attrs.items():
            assert _stable_value(getattr(result.target, str(key), None)) == value, f"target attr {key}"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_species_outcome(contract: SpeciesOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative species/form metadata contract."""

    result = run_species_outcome(
        species=contract.species,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    metadata = result.metadata.get("species", {})
    for key, value in contract.expect_metadata.items():
        assert metadata.get(str(key)) == value, f"species metadata {key}"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    return result


def assert_form_change_outcome(contract: FormChangeOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative form-change outcome contract."""

    result = run_form_change_outcome(
        trigger=contract.trigger,
        user=contract.user,
        target=contract.target,
        item=contract.item,
        event=contract.event,
        move=contract.move,
        battle_extra=contract.battle_extra,
        direct_forme=contract.direct_forme,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_result is not UNSET:
        assert result.metadata.get("form_change_result") == contract.expect_result, "form change result"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    assert_battle_expectation(result, contract.expect_battle)
    return result


def assert_ability_event_outcome(contract: AbilityEventOutcomeContract) -> OutcomeResult:
    """Run and assert a declarative direct ability-event contract."""

    result = run_ability_event_outcome(
        event=contract.event,
        user=contract.user,
        target=contract.target,
        owner=contract.owner,
        target_side=contract.target_side,
        source_side=contract.source_side,
        pokemon_side=contract.pokemon_side,
        target_is_ally=contract.target_is_ally,
        game_type=contract.game_type,
        move=contract.move,
        move_extra=contract.move_extra,
        item=contract.item,
        status=contract.status,
        boosts=contract.boosts,
        relay_value=contract.relay_value,
        effect_id=contract.effect_id,
        effect_type=contract.effect_type,
        seed=contract.seed,
        random_control=contract.random_control,
    )
    if contract.expect_result is not UNSET:
        assert result.metadata.get("ability_event_result") == contract.expect_result, "ability event result"
    if contract.expect_boosts is not None:
        actual = result.metadata.get("ability_event_boosts", {})
        for key, value in contract.expect_boosts.items():
            canonical = STAT_ALIASES.get(str(key), str(key))
            assert actual.get(canonical) == value, f"ability event boost {canonical}"
    assert_pokemon_expectation(result, "user", contract.expect_user)
    assert_pokemon_expectation(result, "target", contract.expect_target)
    return result
