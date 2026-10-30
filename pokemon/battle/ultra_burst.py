"""One native Ultra declaration and a reversible, transaction-owned runtime form."""

from copy import deepcopy
from dataclasses import asdict

from pokemon.names import normalize_name

from .necrozma import NativeNecrozmaBattle
from .owned_battle_actor import BattleOwnershipChanged, OwnedBattleActor
from .terastallization import Terastallization
from .ultra_eligibility import UltraEligibility
from .ultra_profile import UltraProfile


class UltraBurst:
    """Keep the persistent pair unchanged and Ultra's budget independent of Z."""

    version = 1

    @staticmethod
    def tracked(battle):
        """Keep stale-turn and outer-commit guards after activation or fainting."""
        return bool(getattr(battle, "ultra_used", set()) or getattr(battle, "ultra_pending", {}))

    @classmethod
    def declaration(cls, battle, participant, pokemon, *, pending=False):
        """Capture exact current terms without reserving an action or paying PP."""
        side = Terastallization.side(battle, participant)
        if side in getattr(battle, "ultra_used", set()):
            raise ValueError("Your side has already used Ultra Burst this battle.")
        if getattr(pokemon, "ultra_profile", None):
            raise ValueError("That actor has already used Ultra Burst.")
        preparation = UltraEligibility.binding(battle, participant, pokemon)
        request = {
            "version": cls.version,
            "battle": str(battle.mechanic_battle_id),
            "turn": battle.mechanic_turn,
            "team": side,
            "controller": str(OwnedBattleActor.controller(participant).pk),
            "pokemon": Terastallization.identifier(pokemon),
            "slot": str(Terastallization.slot(participant, pokemon)),
            "crystal": normalize_name(UltraProfile.checked().crystal),
            "preparation": asdict(preparation),
        }
        existing = getattr(battle, "ultra_pending", {}).get(side)
        if not pending and existing and existing != request:
            raise ValueError("Your side already has an Ultra declaration. Cancel that actor first.")
        return request

    @classmethod
    def validate_request(cls, request):
        """Reject partial or loosely typed checkpoint terms before trusting identity."""
        keys = {
            "version",
            "battle",
            "turn",
            "team",
            "controller",
            "pokemon",
            "slot",
            "crystal",
            "preparation",
        }
        prep = request.get("preparation") if isinstance(request, dict) else None
        if (
            not isinstance(request, dict)
            or set(request) != keys
            or type(request["version"]) is not int
            or request["version"] != cls.version
            or type(request["turn"]) is not int
            or request["turn"] < 0
            or any(
                not isinstance(request[key], str) or not request[key]
                for key in keys - {"version", "turn", "preparation"}
            )
            or request["team"] not in {"A", "B"}
            or request["slot"] not in {"0", "1"}
            or request["crystal"] != normalize_name(UltraProfile.checked().crystal)
            or not isinstance(prep, dict)
            or set(prep)
            != {"profile", "native", "pair", "photon_slot", "photon_id", "current_pp", "capacity"}
            or prep["profile"] != UltraProfile.checked().fingerprint
            or prep["native"] not in UltraProfile.checked().native
            or not isinstance(prep["pair"], dict)
            or any(
                type(prep[key]) is not int
                for key in ("photon_slot", "photon_id", "current_pp", "capacity")
            )
            or prep["photon_slot"] not in range(1, 5)
            or prep["photon_id"] <= 0
            or not 0 <= prep["current_pp"] <= prep["capacity"]
            or prep["capacity"] <= 0
        ):
            raise BattleOwnershipChanged("Corrupt Ultra declaration requires battle recovery.")

    @staticmethod
    def same_terms(first, second, *, current_pp=True):
        """PP changes after confirmation are lawful; source identity remains exact."""
        first, second = deepcopy(first), deepcopy(second)
        if not current_pp:
            first["preparation"].pop("current_pp", None)
            second["preparation"].pop("current_pp", None)
        return first == second

    @classmethod
    def choose(cls, choices, *, actor=None, reviewed=None, cancel=False):
        """Preview/confirm under the existing room lock and outer-commit boundary."""
        from django.db import transaction
        from .mechanic_choices import MechanicChoices

        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon, allow_queued=cancel)
        choices._mechanic_actor = position, pokemon
        battle = choices.battle
        with MechanicChoices.locked(choices, allow_queued=cancel):
            side = Terastallization.side(battle, choices.participant)
            if cancel:
                request = battle.ultra_pending.get(side, {})
                if request.get("pokemon") != Terastallization.identifier(pokemon):
                    raise ValueError("That actor has no unspent Ultra declaration.")
                battle.ultra_pending.pop(side)
                message = f"{position}: Ultra Burst cancelled."
            else:
                request = cls.declaration(battle, choices.participant, pokemon)
                if reviewed is None:
                    return deepcopy(request)
                cls.validate_request(reviewed)
                if not cls.same_terms(request, reviewed):
                    raise ValueError("Ultra terms changed. Reopen +ultra and review them again.")
                battle.ultra_pending[side] = request
                message = f"{position} ({pokemon.name}): Ultra Burst reserved. Choose a normal attack with +attack."
            transaction.on_commit(lambda: choices.caller.msg(message), robust=True)

    @classmethod
    def lock(cls, battle):
        """Transform only a fresh bound ordinary MOVE; any mismatch aborts the turn."""
        from .actions import ActionType
        from .effect_context import EffectContext
        from .legal_actions import LegalActions

        candidates = []
        for side, request in getattr(battle, "ultra_pending", {}).items():
            cls.validate_request(request)
            matched = []
            for participant in battle.participants:
                if Terastallization.side(battle, participant) != side:
                    continue
                actions = participant.pending_action
                actions = actions if isinstance(actions, list) else [actions] if actions else []
                for action in actions:
                    pokemon = action.pokemon
                    if (
                        pokemon is None
                        or Terastallization.identifier(pokemon) != request["pokemon"]
                    ):
                        continue
                    if (
                        action.action_type is not ActionType.MOVE
                        or not getattr(action, "player_selected", False)
                        or getattr(action, "z_request", None) is not None
                        or LegalActions.for_action(battle, action).refresh(action, fallback=False)
                        is None
                    ):
                        raise BattleOwnershipChanged(
                            "Ultra Burst needs its bound legal ordinary attack."
                        )
                    fresh = cls.declaration(battle, participant, pokemon, pending=True)
                    if not cls.same_terms(request, fresh, current_pp=False):
                        raise BattleOwnershipChanged(
                            "Ultra identity or reviewed terms changed; no turn committed."
                        )
                    matched.append(
                        (
                            EffectContext.speed(pokemon),
                            battle.rng.random(),
                            participant,
                            pokemon,
                            request,
                        )
                    )
            if len(matched) != 1:
                raise BattleOwnershipChanged(
                    "Ultra declaration has no unique current ordinary action."
                )
            candidates.extend(matched)
        for _, _, participant, pokemon, request in sorted(
            candidates, key=lambda row: (-row[0], row[1])
        ):
            cls.activate(battle, participant, pokemon, request)
        battle.ultra_pending = {}

    @classmethod
    def activate(cls, battle, participant, pokemon, request):
        """Change runtime form/ability only; the complete turn owns rollback."""
        from .engine import _resolve_ability
        from .mega_evolution import MegaEvolution
        from pokemon.dex.entities import Stats

        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            profile = UltraProfile.checked()
            ability = _resolve_ability("Neuroforce")
            if not ability or not getattr(ability, "raw", None):
                raise RuntimeError("The reviewed Ultra ability has no executable definition.")
            pokemon.ultra_profile = {
                "version": cls.version,
                "request": deepcopy(request),
                "active": True,
                "restore": {
                    key: value
                    for key, value in MegaEvolution.restoration(
                        pokemon, ability=row["ability"]
                    ).items()
                    if key in {"species", "base_species", "name", "types", "ability"}
                },
            }
            pokemon.ultra_guard_crystal = request["crystal"]
            display_name = row.get("nickname") or row["species"]
            pokemon.ultra_profile["restore"]["name"] = display_name
            if not pokemon.formeChange(
                profile.target, battle=battle, source=pokemon, preserve_ability=True
            ):
                raise RuntimeError("Validated Ultra Burst failed to apply its form.")
            pokemon.name = display_name
            pokemon.base_species = row["species"]
            pokemon.setAbility(
                ability, battle=battle, source=pokemon, is_from_forme_change=True, run_start=False
            )
            pokemon.native_ability_provenance = "native"
            pokemon.base_stats = Stats(**MegaEvolution.species_stats(pokemon))
            pokemon.stats = pokemon._battle_stats()
            battle.register_handlers(pokemon)
            battle.start_owned_ability(pokemon)
            battle.ultra_used.add(request["team"])
            battle.log_action(f"{display_name} used Ultra Burst and became {profile.target}!")

    @classmethod
    def validate_active(cls, battle, participant, pokemon, row, *, signature=False):
        """Require the exact living native lifecycle; never trust an Ultra species string."""
        profile = getattr(pokemon, "ultra_profile", None)
        if (
            not isinstance(profile, dict)
            or set(profile) != {"version", "request", "active", "restore"}
            or type(profile["version"]) is not int
            or profile["version"] != cls.version
            or type(profile["active"]) is not bool
        ):
            raise BattleOwnershipChanged("Unbound Ultra form requires battle recovery.")
        request = profile["request"]
        cls.validate_request(request)
        side = Terastallization.side(battle, participant)
        pair = NativeNecrozmaBattle.validate_actor(battle, participant, pokemon, row=row)
        prep = request["preparation"]
        restore = profile["restore"]
        native_entry = pokemon._lookup_species_entry(prep["native"])
        native_raw = (
            native_entry
            if isinstance(native_entry, dict)
            else getattr(native_entry, "raw", {}) or {}
        )
        if (
            not pair
            or not NativeNecrozmaBattle.matches(prep["pair"], NativeNecrozmaBattle.proof(pair))
            or request["battle"] != str(battle.mechanic_battle_id)
            or request["team"] != side
            or request["controller"] != str(OwnedBattleActor.controller(participant).pk)
            or request["pokemon"] != Terastallization.identifier(pokemon)
            or side not in battle.ultra_used
            or request["turn"] > battle.mechanic_turn
            or row["species"] != prep["native"]
            or normalize_name(row["ability"]) != "prismarmor"
            or normalize_name(row["held_item"]) != request["crystal"]
            or OwnedBattleActor.item_key(pokemon) != request["crystal"]
            or getattr(pokemon, "ultra_guard_crystal", None) != request["crystal"]
            or not isinstance(restore, dict)
            or set(restore) != {"species", "base_species", "name", "types", "ability"}
            or not isinstance(restore["name"], str)
            or restore.get("species") != prep["native"]
            or restore.get("base_species") != prep["native"]
            or normalize_name(restore.get("ability")) != "prismarmor"
            or restore.get("types") != native_raw.get("types")
            or getattr(pokemon, "mega_evolved", False)
            or getattr(pokemon, "terastallized", None)
            or getattr(pokemon, "_pf2_active_fusion", False)
        ):
            raise BattleOwnershipChanged("Ultra lifecycle, ownership or restoration proof changed.")
        if str(pokemon.species) != (
            UltraProfile.checked().target if profile["active"] else prep["native"]
        ) and not getattr(pokemon, "transformed", False):
            raise BattleOwnershipChanged("Ultra form and activation proof disagree.")
        from .z_moves import ZMoves

        slot, _, capacity, _ = ZMoves.source(pokemon, row, prep["photon_slot"], require_pp=False)
        if (
            slot.move_id != prep["photon_id"]
            or normalize_name(slot.move.name) != "photongeyser"
            or capacity != prep["capacity"]
        ):
            raise BattleOwnershipChanged("The Ultra Photon source changed identity or capacity.")
        if signature and (
            not profile["active"]
            or getattr(pokemon, "transformed", False)
            or battle.mechanic_turn <= request["turn"]
        ):
            raise ValueError(
                "Use the Ultra signature on a later completed turn while still in native Ultra form."
            )
        return profile

    @classmethod
    def validate_roster(cls, battle):
        """Check reserves and fainted actors too, without requiring active Prism Armor."""
        for participant in battle.participants:
            for pokemon in participant.pokemons:
                if (
                    getattr(pokemon, "ultra_profile", None)
                    or getattr(pokemon, "ultra_guard_crystal", None)
                    or str(pokemon.species) == "Necrozma-Ultra"
                ):
                    with OwnedBattleActor.locked(battle, participant, pokemon, active=False) as row:
                        cls.validate_active(battle, participant, pokemon, row)

    @classmethod
    def recover(cls, battle):
        """Resolve saved controller IDs for validation before session transport attaches."""
        if not cls.tracked(battle) and not any(
            getattr(mon, "ultra_profile", None)
            or getattr(mon, "ultra_guard_crystal", None)
            or str(mon.species) == "Necrozma-Ultra"
            for part in battle.participants
            for mon in part.pokemons
        ):
            return
        from pokemon.services.battle_rewards import BattleRewards
        from evennia.objects.models import ObjectDB

        previous = []
        try:
            for participant in battle.participants:
                side = Terastallization.side(battle, participant)
                tracked = [
                    mon
                    for mon in participant.pokemons
                    if getattr(mon, "ultra_profile", None)
                    or getattr(mon, "ultra_guard_crystal", None)
                    or str(mon.species) == "Necrozma-Ultra"
                    or getattr(battle, "ultra_pending", {}).get(side, {}).get("pokemon")
                    == Terastallization.identifier(mon)
                ]
                if tracked and not BattleRewards.supports(getattr(participant, "player", None)):
                    controllers = {
                        str(battle.mechanic_controllers.get(str(mon.model_id), "")).lstrip("#")
                        for mon in tracked
                    }
                    if len(controllers) != 1 or not next(iter(controllers)).isdigit():
                        raise ValueError("Ultra checkpoint has no unique issued controller.")
                    previous.append((participant, participant.player))
                    participant.player = ObjectDB.objects.get(pk=int(next(iter(controllers))))
            cls._recover(battle)
        finally:
            for participant, player in previous:
                participant.player = player

    @classmethod
    def _recover(cls, battle):
        """Validate durable proof; do not replay ability Start, activation or PP writes."""
        from pokemon.dex.entities import Stats
        from .mega_evolution import MegaEvolution

        sides = {Terastallization.side(battle, part) for part in battle.participants}
        if not battle.ultra_used <= sides or not set(battle.ultra_pending) <= sides:
            raise ValueError("Unknown side in Ultra checkpoint.")
        counts = {}
        for participant in battle.participants:
            for pokemon in participant.pokemons:
                if (
                    getattr(pokemon, "ultra_profile", None)
                    or getattr(pokemon, "ultra_guard_crystal", None)
                    or str(pokemon.species) == "Necrozma-Ultra"
                ):
                    with OwnedBattleActor.locked(battle, participant, pokemon, active=False) as row:
                        cls.validate_active(battle, participant, pokemon, row)
                    side = Terastallization.side(battle, participant)
                    counts[side] = counts.get(side, 0) + 1
                    if counts[side] > 1:
                        raise ValueError("Multiple Ultra actors contradict the side budget.")
                    if not getattr(pokemon, "transformed", False):
                        stats = MegaEvolution.species_stats(pokemon)
                        damage, fainted = max(0, pokemon.max_hp - pokemon.hp), pokemon.hp <= 0
                        pokemon.max_hp = stats["hp"]
                        pokemon.hp = 0 if fainted else max(1, pokemon.max_hp - damage)
                        pokemon.base_stats = Stats(**stats)
                        pokemon.stats = pokemon._battle_stats()
        if set(counts) != battle.ultra_used:
            raise ValueError("Ultra spent ledger has no unique actor proof.")
        for side, request in battle.ultra_pending.items():
            cls.validate_request(request)
            matches = [
                (part, mon)
                for part in battle.participants
                for mon in part.active
                if Terastallization.side(battle, part) == side
                and Terastallization.identifier(mon) == request["pokemon"]
            ]
            if len(matches) != 1 or not cls.same_terms(
                request, cls.declaration(battle, *matches[0], pending=True), current_pp=False
            ):
                raise ValueError("Stale Ultra pending proof requires recovery.")

    @staticmethod
    def prepare_entry(pokemon):
        """Normal reentry restores the form's native ability; reconnect never calls this."""
        if not (getattr(pokemon, "native_origin", None) or {}).get("necrozma"):
            return
        from .engine import _resolve_ability

        active = (getattr(pokemon, "ultra_profile", None) or {}).get("active", False)
        pokemon.ability = _resolve_ability("Neuroforce" if active else "Prism Armor")
        pokemon.ability_suppressed = False
        pokemon.native_ability_provenance = "native"

    @staticmethod
    def revert(pokemon):
        """Return runtime to the paired form, retaining live resources and spent proof."""
        from pokemon.dex.entities import Stats
        from .engine import _resolve_ability
        from .mega_evolution import MegaEvolution

        profile = getattr(pokemon, "ultra_profile", None)
        if not profile:
            return
        restore = profile["restore"]
        deficit = max(0, pokemon.max_hp - pokemon.hp)
        fainted = pokemon.hp <= 0
        for name in ("species", "base_species", "name", "types"):
            setattr(pokemon, name, deepcopy(restore[name]))
        stats = MegaEvolution.species_stats(pokemon)
        pokemon.max_hp = stats["hp"]
        pokemon.hp = 0 if fainted else max(1, pokemon.max_hp - deficit)
        pokemon.ability = _resolve_ability(restore["ability"])
        pokemon.ability_state = {}
        pokemon.ability_suppressed = False
        pokemon.native_ability_provenance = "native"
        pokemon.base_stats = Stats(**stats)
        pokemon.stats = pokemon._battle_stats()
        profile["active"] = False

    @classmethod
    def cleanup(cls, battle):
        """End/abort clears unspent declarations without refunding an activated side."""
        for participant in battle.participants:
            for pokemon in participant.pokemons:
                cls.revert(pokemon)
        battle.ultra_pending = {}
