"""Bound owned Z inputs, strict source PP and one reusable activation per side."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from types import SimpleNamespace

from pokemon.names import normalize_name, resolve_dex_entry

from .owned_battle_actor import BattleOwnershipChanged, OwnedBattleActor
from .terastallization import Terastallization
from .z_profiles import ZProfiles


class ZMoves:
    """Only explicitly accepted crystal/source profiles can become paid Z actions."""

    version = 1

    @staticmethod
    def has_z_history(pokemon):
        """Treat a saved paid name/marker as evidence, never infer from a held item."""
        move = getattr(pokemon, "last_move", None)
        return bool(getattr(move, "_z_paid", False) or getattr(move, "isZ", False)
                    or (getattr(move, "raw", {}) or {}).get("isZ")
                    or str(getattr(move, "name", "")).startswith("Z-"))

    @classmethod
    def validate_request(cls, request):
        """Reject malformed or partial proof before any resource mutation."""
        keys = {
            "version",
            "battle",
            "turn",
            "team",
            "controller",
            "pokemon",
            "slot",
            "crystal",
            "native",
            "source_slot",
            "source_id",
            "source",
            "pp",
            "target",
            "target_ref",
            "profile",
        }
        if (
            not isinstance(request, dict)
            or set(request) != keys
            or type(request["version"]) is not int
            or request["version"] != cls.version
            or any(
                type(request[key]) is not int for key in ("turn", "source_slot", "source_id", "pp")
            )
            or request["turn"] < 0
            or request["source_slot"] not in range(1, 5)
            or request["source_id"] <= 0
            or request["pp"] <= 0
            or any(
                not isinstance(request[key], str) or not request[key]
                for key in keys - {"version", "turn", "source_slot", "source_id", "pp"}
            )
            or request["team"] not in {"A", "B"}
            or request["slot"] not in {"0", "1"}
            or request["target"] not in {"A1", "A2", "B1", "B2"}
        ):
            raise ValueError("Incomplete or corrupt Z request requires recovery.")

    @staticmethod
    def fingerprint(profile):
        """Bind the exact reviewed descriptor across input and reconstruction."""
        return hashlib.sha256(json.dumps(asdict(profile), sort_keys=True).encode()).hexdigest()

    @staticmethod
    def native(profile, pokemon, row):
        """A crystal cannot grant a native form, species or transformation."""
        from pokemon.dex import POKEDEX

        entry = resolve_dex_entry(POKEDEX, row["species"])
        raw = getattr(entry, "raw", {}) or {}
        from .necrozma import NativeNecrozmaBattle

        combined = NativeNecrozmaBattle.signature_allowed(profile, pokemon, row)
        disguise = (getattr(pokemon, "native_origin", {}) or {}).get("disguise_busted")
        busted = (row["species"] in {"Mimikyu", "Mimikyu-Totem"}
                  and disguise == {"ref": str(pokemon.model_id), "species": row["species"],
                                  "form": str(pokemon.species)}
                  and str(pokemon.species) == ("Mimikyu-Busted-Totem" if row["species"] == "Mimikyu-Totem" else "Mimikyu-Busted"))
        if (
            not raw
            or raw.get("num", 0) <= 0
            or raw.get("battleOnly")
            or raw.get("changesFrom") and not combined
            or raw.get("requiredItem")
            or raw.get("requiredItems")
            or str(raw.get("forme", "")).lower().startswith(("mega", "primal", "ultra"))
            or str(pokemon.species) != row["species"] and not busted
            or getattr(pokemon, "transformed", False)
        ):
            raise ValueError(
                "Z-Moves require a supported current native form, without Transform or a form shortcut."
            )
        if profile.native and row["species"] not in profile.native and not combined:
            raise ValueError("That signature needs its exact native holder.")

    @staticmethod
    def sources(pokemon, row):
        """Read canonical gapped active slots, learned identity, capacity and current PP."""
        from pokemon.models.moves import (
            ActiveMoveslot,
            MovePPBoost,
            MovesetSlot,
            PokemonLearnedMove,
        )
        from pokemon.services.pp_capacity import PPCapacity
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        _, identifier = parse_pokemon_ref(pokemon.model_id)
        slots = list(
            ActiveMoveslot.objects.select_for_update()
            .filter(pokemon_id=identifier)
            .select_related("move")
            .order_by("slot")
        )
        canonical = dict(
            MovesetSlot.objects.filter(moveset_id=row["active_moveset_id"]).values_list(
                "slot", "move_id"
            )
        )
        learned = set(
            PokemonLearnedMove.objects.filter(pokemon_id=identifier).values_list(
                "move_id", flat=True
            )
        )
        bonuses = dict(
            MovePPBoost.objects.select_for_update()
            .filter(pokemon_id=identifier)
            .values_list("move_id", "bonus_pp")
        )
        if not slots or len({normalize_name(s.move.name) for s in slots}) != len(slots):
            raise ValueError(
                "The active move slots are missing or ambiguous; recover them before choosing Z."
            )
        result = []
        for slot in slots:
            if (
                slot.slot not in range(1, 5)
                or canonical.get(slot.slot) != slot.move_id
                or slot.move_id not in learned
            ):
                raise ValueError(
                    "The saved active/learned move identity changed; choose again after recovery."
                )
            policy = PPCapacity.for_move(slot.move.name)
            bonus = bonuses.get(slot.move_id, 0)
            if policy.base <= 0 or type(bonus) is not int or not 0 <= bonus <= policy.stages[-1]:
                raise ValueError("Invalid source PP capacity; no Z input was queued.")
            maximum = policy.base + bonus
            current = maximum if slot.current_pp is None else slot.current_pp
            if type(current) is not int or not 0 <= current <= maximum:
                raise ValueError("Invalid current source PP; no Z input was queued.")
            runtime = [
                move
                for move in pokemon.moves
                if normalize_name(move.name) == normalize_name(slot.move.name)
            ]
            if len(runtime) != 1:
                raise ValueError("The current battle move identity changed; refresh your choices.")
            result.append((slot, current, maximum, runtime[0]))
        return result

    @classmethod
    def source(cls, pokemon, row, selector, *, require_pp=True):
        """Require the actual slot number or complete normalized active move name."""
        selector = str(selector).strip()
        sources = cls.sources(pokemon, row)
        matches = [
            s
            for s in sources
            if (
                s[0].slot == int(selector)
                if selector.isdigit()
                else normalize_name(s[0].move.name) == normalize_name(selector)
            )
        ]
        if len(matches) != 1:
            raise ValueError("Choose an actual active move slot or its full name.")
        slot, current, maximum, runtime = matches[0]
        if require_pp and current <= 0:
            raise ValueError("That active source move has no PP remaining.")
        return slot, current, maximum, runtime

    @staticmethod
    def targets(battle, participant, pokemon, profile):
        """Use the reviewed target class, including signatures whose source differs."""
        from .legal_actions import LegalActions

        if profile.target in {"self", "all", "allySide", "allyTeam"} or (
            profile.intrinsic == "curse" and "Ghost" not in pokemon.types
        ):
            return [pokemon]
        if profile.intrinsic == "curse":
            return LegalActions(battle, participant, pokemon).targets(SimpleNamespace(raw={"target": "adjacentFoe"}))
        return LegalActions(battle, participant, pokemon).targets(
            SimpleNamespace(raw={"target": profile.target})
        )

    @classmethod
    def binding(cls, battle, participant, pokemon, selector, target):
        """Create a fully bound native/source/target request under owned locks."""
        from .legal_actions import LegalActions

        side = Terastallization.side(battle, participant)
        if side in getattr(battle, "z_used", set()):
            raise ValueError("Your side has already used its Z-Move this battle.")
        if OwnedBattleActor.incompatible(battle, participant, pokemon, mechanic="z"):
            raise ValueError(
                "Z-Moves cannot stack with that actor's other battle mechanic or transformation."
            )
        crystal = OwnedBattleActor.item_key(pokemon)
        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            if normalize_name(row["held_item"]) != crystal:
                raise BattleOwnershipChanged(
                    "The saved held crystal changed; recover the battle before using Z."
                )
            slot, current, maximum, runtime = cls.source(pokemon, row, selector)
            profile = ZProfiles.get(crystal, slot.move.name)
            if profile is None:
                raise ValueError(
                    "That crystal/source pair is deferred. Use +zmove to list accepted active sources."
                )
            cls.native(profile, pokemon, row)
            legality = LegalActions(battle, participant, pokemon)
            source_move = legality._move(runtime)
            source_move.pp = current
            if not legality._move_allowed(runtime, source_move):
                raise ValueError(
                    "That source move is not legal now (PP, Disable, Taunt and move locks still apply)."
                )
            targets = cls.targets(battle, participant, pokemon, profile)
            if not any(mon is target for mon in targets):
                raise ValueError("Choose a current legal target for that Z-Move.")
            target_part = battle.participant_for(target)
            target_side = Terastallization.side(battle, target_part)
            request = {
                "version": cls.version,
                "battle": str(battle.mechanic_battle_id),
                "turn": battle.mechanic_turn,
                "team": side,
                "controller": str(OwnedBattleActor.controller(participant).pk),
                "pokemon": Terastallization.identifier(pokemon),
                "slot": str(Terastallization.slot(participant, pokemon)),
                "crystal": crystal,
                "native": row["species"],
                "source_slot": slot.slot,
                "source_id": slot.move_id,
                "source": slot.move.name,
                "pp": current,
                "target": target_side + str(Terastallization.slot(target_part, target) + 1),
                "target_ref": str(getattr(target, "model_id", "") or ""),
                "profile": cls.fingerprint(profile),
            }
        return request, source_move, profile

    @classmethod
    def queue(cls, choices, selector, target=None, *, actor=None):
        """Reserve one side and persist one ordinary MOVE action after all checks."""
        from django.db import transaction
        from .actions import Action, ActionType
        from .active_slots import slot_for
        from .mechanic_choices import MechanicChoices

        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon)
        choices._mechanic_actor = position, pokemon
        battle, participant = choices.battle, choices.participant
        with MechanicChoices.locked(choices):
            side = Terastallization.side(battle, participant)
            if side in battle.z_pending:
                raise ValueError("Your side already has a Z-Move queued this turn.")
            with OwnedBattleActor.locked(battle, participant, pokemon) as row:
                slot, current, maximum, runtime = cls.source(pokemon, row, selector)
                profile = ZProfiles.get(OwnedBattleActor.item_key(pokemon), slot.move.name)
                if profile is None:
                    raise ValueError(
                        "That crystal/source pair is deferred. Use +zmove to list accepted active sources."
                    )
                labels = choices.target_labels(cls.targets(battle, participant, pokemon, profile))
                if target is None and (
                    len(labels) == 1 or profile.target in {"self", "allAdjacentFoes", "allAdjacent"}
                ):
                    target = next(iter(labels), None)
                target = str(target or "").upper()
                if target not in labels:
                    raise ValueError("Choose a legal current target: " + ", ".join(labels))
                request, source_move, profile = cls.binding(
                    battle, participant, pokemon, selector, labels[target]
                )
            action = Action(
                participant,
                ActionType.MOVE,
                battle.participant_for(labels[target]),
                move=source_move,
                pokemon=pokemon,
                target_pokemon=labels[target],
                target_slot=slot_for(battle.participant_for(labels[target]), labels[target]),
                z_request=deepcopy(request),
            )
            battle.z_pending[side] = deepcopy(request)
            choices._store(
                position,
                pokemon,
                action,
                {
                    "move": normalize_name(request["source"]),
                    "target": target,
                    "target_ref": request["target_ref"],
                    "z": deepcopy(request),
                },
                lambda pos: pos.declareAttack(target, normalize_name(request["source"])),
                f"{position} ({pokemon.name}) prepares {profile.name} from {request['source']} → {target}.",
                commit_aware=True,
            )

    @classmethod
    def discover(cls, choices, *, actor=None):
        """Read fresh active slots without queueing, deduction or side mutation."""
        position, pokemon = choices.actor(actor)
        lines = []
        with OwnedBattleActor.locked(choices.battle, choices.participant, pokemon) as row:
            for slot, current, maximum, runtime in cls.sources(pokemon, row):
                profile = ZProfiles.get(OwnedBattleActor.item_key(pokemon), slot.move.name)
                if profile is None:
                    continue
                cls.native(profile, pokemon, row)
                lines.append(
                    f"{slot.slot}: {slot.move.name} ({current}/{maximum} PP), {profile.crystal} → {profile.name}, {profile.move_type} {profile.category} {profile.power}."
                )
        side = Terastallization.side(choices.battle, choices.participant)
        budget = (
            "spent"
            if side in choices.battle.z_used
            else "queued" if side in choices.battle.z_pending else "available"
        )
        return f"{position} ({pokemon.name}) Z choices; side use {budget}:\n" + (
            "\n".join(lines) if lines else "No accepted crystal/source pair is active."
        )

    @classmethod
    def validate_roster(cls, battle):
        """Reject contradictory owned sources before any complete-turn/end writes."""
        pending = {r.get("pokemon"): r for r in getattr(battle, "z_pending", {}).values()}
        for participant in getattr(battle, "participants", []):
            for pokemon in participant.pokemons:
                request = pending.get(Terastallization.identifier(pokemon))
                guard = getattr(pokemon, "z_guard_crystal", None) or (request or {}).get("crystal")
                if not guard:
                    continue
                with OwnedBattleActor.locked(battle, participant, pokemon, active=False) as row:
                    if (
                        normalize_name(row["held_item"]) != guard
                        or OwnedBattleActor.item_key(pokemon) != guard
                    ):
                        raise BattleOwnershipChanged(
                            "Z crystal ownership changed; battle recovery is required."
                        )
                    if request:
                        slot, current, maximum, runtime = cls.source(
                            pokemon, row, request["source_slot"]
                        )
                        if slot.move_id != request["source_id"] or normalize_name(
                            slot.move.name
                        ) != normalize_name(request["source"]):
                            raise BattleOwnershipChanged(
                                "The queued Z source changed; no turn was committed."
                            )

    @classmethod
    def refresh(cls, battle, action):
        """Refresh an explicit Z source without silently becoming an ordinary move."""
        request = action.z_request
        cls.validate_request(request)
        from .active_slots import active_at

        target = action.target_pokemon
        locked = getattr(action, "z_locked", False)
        profile = ZProfiles.get(request["crystal"], request["source"])
        dynamic_target = bool(profile and (profile.intrinsic == "curse" or profile.target in {"self", "all", "allySide", "allyTeam"}))
        if locked:
            # Legal earlier actions (Spite, Disable, Encore or Taunt) may
            # prevent this actor after the whole roster passed preflight.
            # They consume the turn without turning into an ownership fault.
            from .legal_actions import LegalActions

            with OwnedBattleActor.locked(battle, action.actor, action.pokemon) as row:
                slot, current, maximum, runtime = cls.source(
                    action.pokemon, row, request["source_slot"], require_pp=False
                )
                if (
                    slot.move_id != request["source_id"]
                    or normalize_name(row["held_item"]) != request["crystal"]
                ):
                    raise BattleOwnershipChanged("The locked Z source changed identity.")
                legality = LegalActions(battle, action.actor, action.pokemon)
                candidate = legality._move(runtime)
                candidate.pp = current
                if current == 0 or not legality._move_allowed(runtime, candidate):
                    battle.log_action(
                        f"{action.pokemon.name} cannot use {request['source']} for its Z-Move now!"
                    )
                    return None
            target = active_at(action.target, action.target_slot or 0)
            if dynamic_target:
                options = cls.targets(battle, action.actor, action.pokemon, profile)
                if target not in options:
                    target = (options[0] if len(options) == 1 else battle.rng.choice(options)) if options else None
                if target is not None:
                    from .active_slots import slot_for

                    action.target = battle.participant_for(target)
                    action.target_slot = slot_for(action.target, target)
            if target is None or target.hp <= 0:
                return action
        fresh, source, profile = cls.binding(
            battle, action.actor, action.pokemon, request["source_slot"], target
        )
        ignored = {"pp", "target_ref", "slot"} if locked else {"pp"}
        if locked and dynamic_target:
            ignored.add("target")
        if any(fresh.get(key) != value for key, value in request.items() if key not in ignored):
            raise BattleOwnershipChanged(
                "The bound Z action changed; refresh/recovery is required."
            )
        if getattr(battle, "z_pending", {}).get(request["team"]) != request:
            raise BattleOwnershipChanged("The Z reservation does not match this action.")
        action.move = source
        action.target_pokemon = target
        return action

    @classmethod
    def lock(cls, battle):
        """Validate both sides before switches, marking actual Z MOVE inputs."""
        from .legal_actions import LegalActions

        for participant in battle.participants:
            actions = participant.pending_action
            actions = actions if isinstance(actions, list) else [actions] if actions else []
            for action in actions:
                if getattr(action, "z_request", None) is not None:
                    if LegalActions.for_action(battle, action).is_active():
                        cls.refresh(battle, action)
                        action.z_locked = True

    @classmethod
    def begin(cls, battle, action):
        """After ordinary prevention, atomically pay exactly one fresh source PP."""
        request, pokemon, participant = action.z_request, action.pokemon, action.actor
        cls.validate_request(request)
        side = Terastallization.side(battle, participant)
        if side in battle.z_used or battle.z_pending.get(side) != request:
            raise BattleOwnershipChanged("This Z input has no current unused side reservation.")
        profile = ZProfiles.get(request["crystal"], request["source"])
        if profile is None or cls.fingerprint(profile) != request["profile"]:
            raise BattleOwnershipChanged("The reviewed Z profile changed; recovery is required.")
        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            if (
                normalize_name(row["held_item"]) != request["crystal"]
                or OwnedBattleActor.item_key(pokemon) != request["crystal"]
            ):
                raise BattleOwnershipChanged("The held Z source changed before activation.")
            cls.native(profile, pokemon, row)
            slot, current, maximum, runtime = cls.source(pokemon, row, request["source_slot"])
            if slot.move_id != request["source_id"]:
                raise BattleOwnershipChanged("The active Z source was replaced.")
            slot.current_pp = current - 1
            slot.save(update_fields=["current_pp"])
            runtime.pp = slot.current_pp
            action.move.pp = slot.current_pp
            # Keep all live SQL-slot mirrors coherent, including rebuilt adapters.
            manager = getattr(pokemon, "activemoveslot_set", None)
            if manager is not None:
                for mirror in manager.all():
                    if getattr(mirror, "slot", None) == slot.slot:
                        mirror.current_pp = slot.current_pp
            pokemon.z_profile = {"version": cls.version, "request": deepcopy(request)}
            pokemon.z_activated = True
            pokemon.z_guard_crystal = request["crystal"]
            battle.z_used.add(side)
            battle.z_pending.pop(side)
            history = pokemon.tempvals.setdefault("moves_used_since_entry", [])
            if normalize_name(request["source"]) not in history:
                history.append(normalize_name(request["source"]))
            action.move = profile.descriptor(action.move, pokemon)
            pokemon.last_move = action.move
            battle.log_action(f"{pokemon.name} unleashed {profile.name} with {request['source']}!")
            from .z_effects import ZEffects

            ZEffects.start(battle, pokemon, profile, action.move)
        return profile

    @classmethod
    def recover(cls, battle, declarations):
        """Validate ledgers/whole-roster evidence without replaying a move or PP debit."""
        if (
            not battle.z_used
            and not battle.z_pending
            and not any(
                getattr(mon, "z_profile", None)
                or getattr(mon, "z_activated", False)
                or getattr(mon, "z_guard_crystal", None)
            or cls.has_z_history(mon)
                for part in battle.participants
                for mon in part.pokemons
            )
        ):
            return
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from evennia.objects.models import ObjectDB

        sides = {Terastallization.side(battle, part) for part in battle.participants}
        if not battle.z_used <= sides or not set(battle.z_pending) <= sides:
            raise ValueError("Unknown side in Z checkpoint.")
        activated = set()
        pending_seen = set()
        for participant in battle.participants:
            side = Terastallization.side(battle, participant)
            for pokemon in participant.pokemons:
                profile = getattr(pokemon, "z_profile", None)
                marker = getattr(pokemon, "z_activated", False)
                pending = battle.z_pending.get(side)
                if pending and pending.get("pokemon") != Terastallization.identifier(pokemon):
                    pending = None
                if not profile and not marker and not pending:
                    if getattr(pokemon, "z_guard_crystal", None) or cls.has_z_history(pokemon):
                        raise ValueError("Unbound Z source guard requires recovery.")
                    continue
                if (
                    type(marker) is not bool
                    or bool(profile) != marker
                    or (profile and side not in battle.z_used)
                    or (
                        profile
                        and (
                            not isinstance(profile, dict)
                            or set(profile) != {"version", "request"}
                            or type(profile["version"]) is not int
                            or profile["version"] != cls.version
                        )
                    )
                ):
                    raise ValueError("Z activation/profile and side ledger disagree.")
                request = profile.get("request") if profile else pending
                cls.validate_request(request)
                if request["turn"] > battle.mechanic_turn or (
                    getattr(pokemon, "z_guard_crystal", None)
                    and pokemon.z_guard_crystal != request["crystal"]
                ):
                    raise ValueError("Contradictory Z turn/source proof requires recovery.")
                kind, identifier = parse_pokemon_ref(pokemon.model_id)
                row = (
                    OwnedPokemon.objects.filter(pk=identifier)
                    .values(
                        "species", "held_item", "is_egg", "trainer__user_id", "active_moveset_id"
                    )
                    .first()
                    if kind == "owned"
                    else None
                )
                controller = battle.mechanic_controllers.get(str(pokemon.model_id))
                placement = (
                    PokemonPlacement.objects.filter(pokemon_id=identifier)
                    .values("location_type", "storage__user_id")
                    .first()
                    if row
                    else None
                )
                if (
                    not row
                    or row["is_egg"]
                    or not placement
                    or placement["location_type"] not in {"party", "fusion"}
                    or str(row["trainer__user_id"]) != str(controller).lstrip("#")
                    or placement["storage__user_id"] != row["trainer__user_id"]
                    or request.get("battle") != str(battle.mechanic_battle_id)
                    or request.get("team") != side
                    or request.get("controller") != str(controller).lstrip("#")
                    or request.get("pokemon") != Terastallization.identifier(pokemon)
                    or request.get("native") != row["species"]
                    or (getattr(pokemon, "native_origin", None) or {}).get("ref")
                    != str(pokemon.model_id)
                    or (getattr(pokemon, "native_origin", None) or {}).get("species")
                    != row["species"]
                    or request.get("crystal") != normalize_name(row["held_item"])
                    or request.get("crystal") != OwnedBattleActor.item_key(pokemon)
                ):
                    raise ValueError("Invalid owned Z checkpoint provenance/source.")
                if placement["location_type"] == "fusion":
                    character = ObjectDB.objects.get(pk=placement["storage__user_id"])
                    if str(
                        BattleRewards.stored_attribute(character, "fusion_id", default="")
                    ) != str(identifier):
                        raise ValueError("Z checkpoint has an inactive Fusion reservation.")
                accepted = ZProfiles.get(request["crystal"], request["source"])
                if accepted is None or cls.fingerprint(accepted) != request.get("profile"):
                    raise ValueError("Z checkpoint uses an unsupported or changed profile.")
                if profile:
                    if side in activated:
                        raise ValueError("Multiple Z activations on one side require recovery.")
                    activated.add(side)
                    pokemon.z_guard_crystal = request["crystal"]
                    history = getattr(pokemon, "last_move", None)
                    matches = normalize_name(getattr(history, "name", "")) == normalize_name(accepted.name)
                    if cls.has_z_history(pokemon) and not matches:
                        raise ValueError("Paid Z history conflicts with its activated source.")
                    if matches:
                        # Older explicit move references may predate the two
                        # source fields. Only this validated name/profile pair
                        # can supply them; absent history remains absent.
                        history._pp_move_name = accepted.source
                        history._z_profile = accepted
                        history._z_paid = history.isZ = True
                if pending:
                    slot_label = side + str(Terastallization.slot(participant, pokemon) + 1)
                    declaration = declarations.get(slot_label, {})
                    if (
                        side in battle.z_used
                        or pending.get("turn") != battle.mechanic_turn
                        or declaration.get("z") != pending
                        or normalize_name(declaration.get("move"))
                        != normalize_name(pending.get("source"))
                    ):
                        raise ValueError("Unbound or stale queued Z checkpoint.")
                    pending_seen.add(side)
        if activated != battle.z_used or pending_seen != set(battle.z_pending):
            raise ValueError("Z checkpoint ledger has no matching actor evidence.")

    @staticmethod
    def cleanup(battle):
        """Clear session markers before ending sync while retaining the source guard."""
        for participant in getattr(battle, "participants", []):
            for pokemon in participant.pokemons:
                pokemon.z_profile = None
                pokemon.z_activated = False
        battle.z_pending = {}
        battle.z_replacement = {}

    @staticmethod
    def protected(target, move, battle):
        """Personal protection and relevant side shields quarter a paid damaging Z."""
        from .protection import MoveProtection

        if not getattr(move, "_z_paid", False) or move.category == "Status":
            return False
        if any(
            getattr(target, "volatiles", {}).get(key) for key in (*MoveProtection.named, "protect")
        ):
            return True
        side = getattr(battle.participant_for(target), "side", None) if battle else None
        conditions = getattr(side, "conditions", {}) or {}
        return bool(
            "matblock" in conditions
            or (
                "wideguard" in conditions
                and move.raw.get("target") in {"allAdjacent", "allAdjacentFoes"}
            )
        )
