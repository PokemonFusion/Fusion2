"""Reviewed manual bag boosts on current owned actors and persistent turns."""

from types import SimpleNamespace

from pokemon.names import normalize_name
from .effect_context import EffectContext
from .owned_battle_actor import BattleOwnershipChanged, OwnedBattleActor


class BattleBoosters:
    """Keep the six named X effects separate from medicine/capture policy."""

    stats = {
        "xattack": ("X Attack", "atk", "attack"),
        "xdefense": ("X Defense", "def", "defense"),
        "xspatk": ("X Sp. Atk", "spa", "special_attack"),
        "xspdef": ("X Sp. Def", "spd", "special_defense"),
        "xspeed": ("X Speed", "spe", "speed"),
        "xaccuracy": ("X Accuracy", "accuracy", "accuracy"),
    }

    @classmethod
    def supports(cls, item):
        """Never infer effects from arbitrary catalog callbacks or prefixes."""
        return normalize_name(item) in cls.stats or normalize_name(item) in {"direhit", "guardspec"}

    @staticmethod
    def format(battle):
        """Limit new bag boosts to the reviewed two-participant formats."""
        if (
            getattr(getattr(battle, "type", None), "name", "") not in {"WILD", "TRAINER", "PVP"}
            or len(battle.participants) != 2
            or getattr(battle, "multi", False)
            or any(getattr(part, "max_active", 1) not in {1, 2} for part in battle.participants)
        ):
            raise ValueError(
                "Battle boosters support two-participant wild/trainer/PvP singles or doubles only."
            )

    @classmethod
    def useful(cls, item, pokemon):
        """Preview stage direction without executing stateful ability/event callbacks.

        Simple changes magnitude, while Contrary reverses direction. Other
        supported positive multipliers cannot change whether a stage is capped.
        Execution still uses the full shared ChangeBoost/TryBoost/AfterBoost path.
        """
        if normalize_name(item) == "direhit":
            return "focusenergy" not in (getattr(pokemon, "volatiles", {}) or {})
        if normalize_name(item) == "guardspec":
            side = getattr(pokemon, "side", None)
            return "mist" not in (getattr(side, "conditions", {}) or {}) and not (
                getattr(side, "screens", {}) or {}
            ).get("mist")
        _, short, full = cls.stats[normalize_name(item)]
        stages = getattr(pokemon, "boosts", {}) or {}
        if not isinstance(stages, dict):
            raise ValueError("Invalid saved boost stages need battle recovery.")
        current = stages.get(full, stages.get(short, 0))
        if type(current) is not int or not -6 <= current <= 6:
            raise ValueError("Invalid saved boost stages need battle recovery.")
        contrary = EffectContext.key(EffectContext.ability(pokemon)) == "contrary"
        return current > -6 if contrary else current < 6

    @staticmethod
    def target(pokemon):
        """Embargo is the selected new-route guard; held-item suppression is irrelevant."""
        if (getattr(pokemon, "volatiles", {}) or {}).get("embargo"):
            raise ValueError("Embargo prevents using a battle booster on that Pokemon.")

    @classmethod
    def declare(cls, choices, item, target, *, actor=None):
        """Persist one fresh owned actor/self-target choice under the room/owner locks."""
        from .actions import Action, ActionType
        from .active_slots import slot_for
        from .mechanic_choices import MechanicChoices
        from pokemon.helpers.party_helpers import resolve_battle_switch_choice
        from pokemon.models.trainer import Trainer

        cls.format(choices.battle)
        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon)
        if target is not None:
            if "/" in str(target):
                raise ValueError("Battle boosters do not accept a move selector.")
            try:
                _, chosen = resolve_battle_switch_choice(
                    choices.caller, choices.switch_choices(), str(target).strip()
                )
            except (ValueError, TypeError, KeyError):
                raise ValueError("Target the acting Pokemon's current owned party slot.") from None
            if chosen is not pokemon:
                raise ValueError("A battle booster must target its own conscious active actor.")
        choices._mechanic_actor = position, pokemon
        with MechanicChoices.locked(choices, preserve_state=True):
            with OwnedBattleActor.locked(choices.battle, choices.participant, pokemon) as row:
                cls.target(pokemon)
                trainer = Trainer.objects.select_for_update().get(pk=row["trainer_id"])
                reserved = sum(
                    normalize_name(entry.get("item", "")) == normalize_name(item)
                    and str(entry.get("trainer")) == str(choices.caller.id)
                    for entry in choices.session.state.declare.values()
                )
                if trainer.get_item_quantity(item) <= reserved:
                    raise ValueError("No unreserved copy remains for this battle action.")
                if not cls.useful(item, pokemon):
                    raise ValueError(
                        "That battle booster would have no effect. No action was queued."
                    )
                action = Action(
                    choices.participant,
                    ActionType.ITEM,
                    choices.participant,
                    item=item,
                    priority=6,
                    pokemon=pokemon,
                    target_pokemon=pokemon,
                    target_slot=slot_for(choices.participant, pokemon),
                )
                declaration = {
                    "item": item,
                    "target": position,
                    "item_target_ref": pokemon.model_id,
                    "item_move": None,
                    "booster_version": 1,
                }
                choices._store(
                    position,
                    pokemon,
                    action,
                    declaration,
                    lambda pos: pos.declareItem(item),
                    f"{position} ({pokemon.name}) prepares {item} on itself; abilities may modify the outcome.",
                    commit_aware=True,
                )

    @classmethod
    def pending(cls, battle):
        """Recognize restored ordinary actions without introducing a second paid ledger."""
        return any(
            cls.supports(getattr(action, "item", "") or "")
            for participant in battle.participants
            for action in (
                participant.pending_action
                if isinstance(participant.pending_action, list)
                else [participant.pending_action] if participant.pending_action else []
            )
        )

    @classmethod
    def tracked(cls, battle):
        """Keep later turns guarded while a paid temporary effect or side Mist remains."""
        return (
            cls.pending(battle)
            or any(
                (getattr(mon, "tempvals", {}) or {}).get("bag_boosters")
                for participant in battle.participants
                for mon in participant.pokemons
            )
            or any("mist" in participant.side.conditions for participant in battle.participants)
        )

    @classmethod
    def apply_effect(cls, battle, item, pokemon):
        """Use normal boost events with the bag item as effect and actor as source."""
        from pokemon.utils.boosts import apply_boost

        if normalize_name(item) in {"direhit", "guardspec"}:
            failures = len(getattr(battle, "_callback_failures", []))
            if normalize_name(item) == "direhit":
                changed = bool(
                    battle.apply_volatile_status(
                        pokemon, "focusenergy", source=pokemon, effect="item:direhit"
                    )
                )
            else:
                changed = bool(
                    battle.add_side_condition(
                        battle.participant_for(pokemon),
                        "mist",
                        {
                            "id": "mist",
                            "duration": 5,
                            "source": pokemon,
                            "sourceEffect": "item:guardspec",
                        },
                        source=pokemon,
                    )
                )
            if len(getattr(battle, "_callback_failures", [])) != failures:
                raise BattleOwnershipChanged("The booster condition failed; no turn was committed.")
            return changed
        name, short, full = cls.stats[normalize_name(item)]
        before = dict(getattr(pokemon, "boosts", {}) or {})
        failures = len(getattr(battle, "_callback_failures", []))
        effect = SimpleNamespace(id=normalize_name(item), name=name, effectType="Item", raw={})
        apply_boost(pokemon, {short: 2}, source=pokemon, effect=effect)
        if len(getattr(battle, "_callback_failures", [])) != failures:
            raise BattleOwnershipChanged("The booster effect failed; no turn was committed.")
        current = getattr(pokemon, "boosts", {}) or {}
        changed = current.get(full, current.get(short, 0)) != before.get(full, before.get(short, 0))
        if changed:
            pokemon.tempvals["bag_boosters"] = True
        return changed

    @classmethod
    def execute(cls, battle, action):
        """Commit useful effect/debit with the existing complete-turn checkpoint boundary."""
        from pokemon.models.trainer import Trainer

        cls.format(battle)
        pokemon = action.pokemon
        if (
            action.target is not action.actor
            or action.target_pokemon is not pokemon
            or action.item_move is not None
        ):
            raise BattleOwnershipChanged("The saved booster target changed; no turn was committed.")
        with OwnedBattleActor.locked(battle, action.actor, pokemon, active=False) as row:
            if not any(mon is pokemon for mon in action.actor.active) or pokemon.hp <= 0:
                return False
            cls.target(pokemon)
            if not cls.useful(action.item, pokemon):
                return False
            trainer = Trainer.objects.select_for_update().get(pk=row["trainer_id"])
            if trainer.get_item_quantity(action.item) < 1:
                raise BattleOwnershipChanged(
                    "The queued booster copy is unavailable; no turn was committed."
                )
            if not cls.apply_effect(battle, action.item, pokemon):
                return False
            if not trainer.remove_item(action.item):
                raise BattleOwnershipChanged("The booster debit failed; no turn was committed.")
            pokemon.tempvals["bag_boosters"] = True
            return True

    @classmethod
    def notice(cls, item, pokemon):
        """Report the actual ability-modified result, rather than promising an unmodified +2."""
        key = normalize_name(item)
        if key == "direhit":
            return f"{pokemon.name} gained Focus Energy (+2 critical-hit stages)."
        if key == "guardspec":
            return f"{pokemon.name}'s side gained Mist for five turns."
        stat = cls.stats[key][2]
        return f"{pokemon.name}'s {stat.replace('_', ' ')} stage is now {pokemon.boosts[stat]:+d} after {item}."

    @staticmethod
    def cleanup(battle):
        """End paid temporary boosts/Focus Energy without writing owned base stats."""
        for participant in battle.participants:
            battle.remove_side_condition(participant, "mist")
            for pokemon in participant.pokemons:
                battle.remove_volatile(pokemon, "focusenergy")
                if (getattr(pokemon, "tempvals", {}) or {}).pop("bag_boosters", False):
                    battle.reset_stat_changes(pokemon)

    @staticmethod
    def freeze(battle):
        """Checkpoint only the reviewed Mist duration/source, never a legacy boolean."""
        from .terastallization import Terastallization

        saved = {}
        for participant in battle.participants:
            state = participant.side.conditions.get("mist")
            if state is None:
                continue
            source = state.get("source") if isinstance(state, dict) else None
            if (
                not isinstance(state, dict)
                or type(state.get("duration")) is not int
                or not 1 <= state["duration"] <= 5
                or source is None
                or battle.participant_for(source) is None
                or not battle._allied(participant, battle.participant_for(source))
                or state.get("sourceEffect") not in {"move:mist", "item:guardspec"}
            ):
                raise ValueError("Mist source/duration needs battle recovery before checkpointing.")
            side = Terastallization.side(battle, participant)
            saved[side] = {
                "duration": state["duration"],
                "source": Terastallization.identifier(source),
                "effect": state["sourceEffect"],
            }
        return {"version": 1, "mist": saved} if saved else {}

    @staticmethod
    def recover(battle, saved):
        """Bind the same side/source once without replaying Start or extending the timer."""
        from .terastallization import Terastallization
        from ._shared import snapshot_battle_value

        saved = snapshot_battle_value(saved)
        if saved == {}:
            return
        if (
            type(saved) is not dict
            or set(saved) != {"version", "mist"}
            or type(saved["version"]) is not int
            or saved["version"] != 1
            or type(saved["mist"]) is not dict
            or set(saved["mist"]) - {"A", "B"}
        ):
            raise ValueError("Unknown or corrupt booster condition checkpoint.")
        for side, state in saved["mist"].items():
            if (
                type(state) is not dict
                or set(state) != {"duration", "source", "effect"}
                or type(state["duration"]) is not int
                or not 1 <= state["duration"] <= 5
                or not isinstance(state["source"], str)
                or state["effect"] not in {"move:mist", "item:guardspec"}
            ):
                raise ValueError("Corrupt Mist source/duration checkpoint.")
            participants = [
                part for part in battle.participants if Terastallization.side(battle, part) == side
            ]
            matches = [
                mon
                for part in participants
                for mon in part.pokemons
                if Terastallization.identifier(mon) == state["source"]
            ]
            if len(matches) != 1:
                raise ValueError("The saved Mist source is no longer on its battle side.")
            for participant in participants:
                participant.side.conditions["mist"] = {
                    "id": "mist",
                    "duration": state["duration"],
                    "source": matches[0],
                    "sourceEffect": state["effect"],
                }
                participant.side.screens["mist"] = True
