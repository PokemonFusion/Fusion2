"""Bound reusable Mega declarations and reversible native battle forms."""

from copy import deepcopy

from pokemon.names import normalize_name

from .owned_battle_actor import BattleOwnershipChanged, OwnedBattleActor
from .mega_pairs import MEGA_PAIRS
from .terastallization import Terastallization


class MegaEvolution:
    """Only explicitly accepted native stone pairs can activate through players."""

    version = 1
    pairs = MEGA_PAIRS

    @staticmethod
    def dex_profile(stone):
        """Validate checked-in canonical metadata; metadata alone grants no activation."""
        from pokemon.dex import ITEMDEX, POKEDEX
        from pokemon.names import resolve_dex_entry

        item = resolve_dex_entry(ITEMDEX, stone)
        raw = getattr(item, "raw", {}) or {}
        target = raw.get("megaStone")
        native = raw.get("megaEvolves")
        entry = resolve_dex_entry(POKEDEX, target or "")
        form = getattr(entry, "raw", {}) or {}
        if (
            not native
            or not target
            or not str(form.get("forme", "")).startswith("Mega")
            or form.get("baseSpecies") != native
            or form.get("num", 0) <= 0
            or not form.get("baseStats")
            or not form.get("types")
            or not form.get("abilities")
        ):
            raise ValueError("That held item is not a canonical supported Mega Stone.")
        return native, target, form

    @classmethod
    def declaration(cls, battle, participant, pokemon, *, pending=False):
        """Recheck fresh native placement and exact SQL/runtime held ownership."""
        side = Terastallization.side(battle, participant)
        if side in getattr(battle, "mega_used", set()):
            raise ValueError("Your side has already used Mega Evolution this battle.")
        if OwnedBattleActor.incompatible(battle, participant, pokemon, mechanic="mega"):
            raise ValueError(
                "Mega Evolution cannot stack with that actor's transformation or Z use."
            )
        stone = OwnedBattleActor.item_key(pokemon)
        pair = cls.pairs.get(stone)
        if pair is None:
            raise ValueError(
                "That stone pair is deferred or unsupported for player Mega Evolution."
            )
        native, target, _ = cls.dex_profile(stone)
        if pair != (native, target):
            raise ValueError("The reviewed Mega pair disagrees with the catalog.")
        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            if (
                normalize_name(row["held_item"]) != stone
                or row["species"] != native
                or str(pokemon.species) != native
                or str(pokemon.base_species) != native
            ):
                raise ValueError(
                    "Mega Evolution needs the native holder and matching equipped stone in saved and battle state."
                )
            request = {
                "version": cls.version,
                "battle": str(battle.mechanic_battle_id),
                "turn": battle.mechanic_turn,
                "team": side,
                "controller": str(OwnedBattleActor.controller(participant).pk),
                "pokemon": Terastallization.identifier(pokemon),
                "slot": str(Terastallization.slot(participant, pokemon)),
                "stone": stone,
                "target": target,
            }
        existing = getattr(battle, "mega_pending", {}).get(side)
        if not pending and existing and existing != request:
            raise ValueError(
                "Your side already has Mega Evolution reserved. Cancel that actor first."
            )
        return request

    @classmethod
    def reserve(cls, battle, participant, pokemon):
        """An identical request is idempotent and spends neither action nor use."""
        request = cls.declaration(battle, participant, pokemon)
        if not hasattr(battle, "mega_pending"):
            battle.mega_pending = {}
        battle.mega_pending[request["team"]] = request
        return request

    @staticmethod
    def validate_roster(battle):
        """Do not execute or end against transferred, boxed or inactive bound owners."""
        pending = {
            row.get("pokemon"): row.get("stone")
            for row in getattr(battle, "mega_pending", {}).values()
        }
        for participant in getattr(battle, "participants", []):
            for pokemon in getattr(participant, "pokemons", []):
                if (
                    getattr(pokemon, "mega_guard_stone", None)
                    or Terastallization.identifier(pokemon) in pending
                ):
                    with OwnedBattleActor.locked(battle, participant, pokemon, active=False) as row:
                        stone = (
                            getattr(pokemon, "mega_guard_stone", None)
                            or pending[Terastallization.identifier(pokemon)]
                        )
                        if (
                            normalize_name(row["held_item"]) != stone
                            or OwnedBattleActor.item_key(pokemon) != stone
                        ):
                            raise BattleOwnershipChanged(
                                "Mega held ownership changed; battle recovery is required."
                            )

    @staticmethod
    def species_stats(pokemon, *, species=None):
        """Calculate checked-in stats at the effective level, retaining the Fusion overlay."""
        from types import SimpleNamespace
        from pokemon.helpers.pokemon_helpers import get_stats

        scale = (getattr(pokemon, "native_origin", None) or {}).get("stat_scale", 100)
        if scale not in {100, 110}:
            raise ValueError("Invalid native battle stat overlay.")
        data = SimpleNamespace(
            species=species or str(pokemon.species),
            level=pokemon.level,
            ivs=pokemon.ivs,
            evs=pokemon.evs,
            nature=pokemon.nature,
            trained_stat_nature=getattr(pokemon, "trained_stat_nature", None),
            hyper_training=pokemon.hyper_training,
        )
        return {
            name: value if name == "hp" else value * scale // 100
            for name, value in get_stats(data).items()
        }

    @classmethod
    def restoration(cls, pokemon, *, ability=None):
        """Keep the native profile separate from mutable damage, PP and status."""
        entry = pokemon._lookup_species_entry(str(pokemon.species))
        raw = entry if isinstance(entry, dict) else getattr(entry, "raw", {}) or {}
        stats = cls.species_stats(pokemon)
        return {
            "species": str(pokemon.species),
            "base_species": str(pokemon.base_species),
            "name": str(pokemon.name),
            "types": list(raw.get("types", [])),
            "ability": str(
                ability
                if ability is not None
                else getattr(pokemon.ability, "name", pokemon.ability)
            ),
            "max_hp": stats["hp"],
            "level": pokemon.level,
            "stats": stats,
        }

    @classmethod
    def activate(cls, battle, participant, pokemon, request):
        """Transform under the whole-turn transaction; unexpected failure must propagate."""
        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            from .engine import _resolve_ability

            _, _, form = cls.dex_profile(request["stone"])
            ability = _resolve_ability(form["abilities"]["0"])
            if ability is None or not getattr(ability, "raw", None):
                raise RuntimeError("The reviewed Mega ability has no executable definition.")
            pokemon.mega_profile = {
                "version": cls.version,
                "native": row["species"],
                "target": request["target"],
                "stone": request["stone"],
                "restore": cls.restoration(pokemon, ability=row["ability"]),
            }
            display_name = row.get("nickname") or row["species"]
            pokemon.mega_profile["restore"]["name"] = display_name
            if not pokemon.formeChange(
                request["target"], battle=battle, source=pokemon, preserve_ability=True
            ):
                raise RuntimeError("Validated Mega Evolution failed to apply its form.")
            pokemon.name = display_name
            pokemon.setAbility(
                ability, battle=battle, source=pokemon, is_from_forme_change=True, run_start=False
            )
            pokemon.mega_evolved = True
            pokemon.mega_evolution_forme = request["target"]
            from pokemon.dex.entities import Stats

            pokemon.base_stats = Stats(**cls.species_stats(pokemon))
            pokemon.stats = pokemon._battle_stats()
            battle.register_handlers(pokemon)
            battle.start_owned_ability(pokemon)
            battle.mega_used.add(request["team"])
            battle.log_action(f"{display_name} Mega Evolved into {request['target']}!")

    @classmethod
    def prepare_entry(cls, pokemon):
        """Reset temporary changed/copied abilities before normal Mega reentry."""
        profile = getattr(pokemon, "mega_profile", None)
        if not profile or getattr(pokemon, "transformed", False):
            return
        from .engine import _resolve_ability

        _, target, form = cls.dex_profile(profile["stone"])
        if str(pokemon.species) != target:
            raise ValueError("Mega reentry profile does not match the current form.")
        pokemon.ability = _resolve_ability(form["abilities"]["0"])

    @classmethod
    def lock(cls, battle):
        """Bind actual legal MOVE inputs, then transform in pre-form speed order."""
        from .actions import ActionType
        from .legal_actions import LegalActions
        from .effect_context import EffectContext

        candidates = []
        for side, request in list(getattr(battle, "mega_pending", {}).items()):
            for participant in battle.participants:
                if Terastallization.side(battle, participant) != side:
                    continue
                actions = getattr(participant, "pending_action", None)
                actions = actions if isinstance(actions, list) else [actions] if actions else []
                for action in actions:
                    pokemon = action.pokemon
                    if (
                        action.action_type is not ActionType.MOVE
                        or not getattr(action, "player_selected", False)
                        or pokemon is None
                        or Terastallization.identifier(pokemon) != request.get("pokemon")
                    ):
                        continue
                    pokemon.mega_guard_stone = request.get("stone")
                    try:
                        fresh = cls.declaration(battle, participant, pokemon, pending=True)
                        if (
                            fresh != request
                            or LegalActions.for_action(battle, action).refresh(
                                action, fallback=False
                            )
                            is None
                        ):
                            raise ValueError("The bound Mega request or MOVE input changed.")
                    except BattleOwnershipChanged:
                        raise
                    except ValueError as error:
                        battle.log_action(f"Mega request discarded: {error}")
                        continue
                    candidates.append(
                        (
                            EffectContext.speed(pokemon),
                            battle.rng.random(),
                            participant,
                            pokemon,
                            deepcopy(request),
                        )
                    )
        # Both speeds are captured before either entry ability or form changes.
        for _, _, participant, pokemon, request in sorted(
            candidates, key=lambda value: (-value[0], value[1])
        ):
            cls.activate(battle, participant, pokemon, request)
        battle.mega_pending = {}

    @classmethod
    def recover(cls, battle):
        """Validate whole-roster form evidence without rerunning activation or entry."""
        from pokemon.dex.entities import Stats

        if not hasattr(battle, "mega_used"):
            battle.mega_used = set()
        sides = {Terastallization.side(battle, part) for part in battle.participants}
        if not battle.mega_used <= sides or not set(getattr(battle, "mega_pending", {})) <= sides:
            raise ValueError("Unknown side in the Mega checkpoint ledger.")
        for participant in battle.participants:
            side = Terastallization.side(battle, participant)
            activated = []
            for pokemon in participant.pokemons:
                pokemon.pending_mega = False
                profile = getattr(pokemon, "mega_profile", None)
                if profile and side not in battle.mega_used:
                    raise ValueError("Mega form and spent-side ledger disagree.")
                lookup = getattr(pokemon, "_lookup_species_entry", None)
                entry = lookup(str(getattr(pokemon, "species", ""))) if callable(lookup) else None
                raw = entry if isinstance(entry, dict) else getattr(entry, "raw", {}) or {}
                if not profile and not str(raw.get("forme", "")).startswith("Mega"):
                    if getattr(pokemon, "mega_evolved", False):
                        raise ValueError("Unconfirmed Mega flag requires battle recovery.")
                    continue
                from pokemon.models.core import OwnedPokemon
                from pokemon.services.pokemon_refs import parse_pokemon_ref

                kind, identifier = parse_pokemon_ref(getattr(pokemon, "model_id", None))
                row = (
                    OwnedPokemon.objects.filter(pk=identifier)
                    .values("species", "ability", "held_item", "nickname", "trainer__user_id")
                    .first()
                    if kind == "owned"
                    else None
                )
                controller = getattr(battle, "mechanic_controllers", {}).get(str(pokemon.model_id))
                if not row or str(row["trainer__user_id"]) != str(controller).lstrip("#"):
                    raise ValueError("Mega checkpoint has foreign or missing native ownership.")
                native, target, form = cls.dex_profile(normalize_name(row["held_item"]))
                if row["species"] != native:
                    raise ValueError("Mega checkpoint native provenance is inconsistent.")
                if not profile:
                    # Legacy dex-confirmed form: infer a spent side, never an
                    # activation permission for a deferred pair.
                    if str(pokemon.species) != target or normalize_name(
                        pokemon.base_species
                    ) not in {normalize_name(native), normalize_name(target)}:
                        raise ValueError("Legacy Mega checkpoint is ambiguous.")
                    current = pokemon.species
                    pokemon.species = native
                    restore = cls.restoration(pokemon, ability=row["ability"])
                    restore.update(
                        species=native,
                        base_species=native,
                        types=list(pokemon._lookup_species_types()),
                        stats=cls.species_stats(pokemon),
                    )
                    pokemon.species = current
                    profile = {
                        "version": cls.version,
                        "native": native,
                        "target": target,
                        "stone": normalize_name(row["held_item"]),
                        "restore": restore,
                    }
                    pokemon.mega_profile = profile
                restore = profile.get("restore", {})
                native_entry = pokemon._lookup_species_entry(native)
                native_data = (
                    native_entry
                    if isinstance(native_entry, dict)
                    else getattr(native_entry, "raw", {}) or {}
                )
                expected = cls.species_stats(pokemon, species=native)
                if (
                    profile.get("version") != cls.version
                    or profile.get("native") != native
                    or profile.get("target") != target
                    or profile.get("stone") != normalize_name(row["held_item"])
                    or restore.get("species") != native
                    or restore.get("base_species") != native
                    or restore.get("stats") != expected
                    or list(restore.get("types", [])) != list(native_data.get("types", []))
                    or normalize_name(restore.get("ability")) != normalize_name(row["ability"])
                    or restore.get("max_hp") != expected["hp"]
                    or not isinstance(restore.get("max_hp"), int)
                    or restore["max_hp"] <= 0
                    or (
                        str(pokemon.species) != target
                        and not getattr(pokemon, "transformed", False)
                    )
                ):
                    raise ValueError("Invalid Mega restoration profile; recovery is required.")
                if not getattr(pokemon, "transformed", False):
                    pokemon.base_stats = Stats(**cls.species_stats(pokemon))
                    pokemon.stats = pokemon._battle_stats()
                pokemon.base_species = native
                pokemon.mega_evolved = True
                pokemon.mega_evolution_forme = target
                pokemon.mega_guard_stone = normalize_name(row["held_item"])
                pokemon.native_origin = dict(
                    getattr(pokemon, "native_origin", None) or {},
                    ref=str(pokemon.model_id),
                    species=native,
                )
                battle.register_handlers(pokemon)
                activated.append(pokemon)
            if len(activated) > 1:
                raise ValueError("Conflicting Mega activations on one side require recovery.")
            if activated:
                battle.mega_used.add(side)

    @staticmethod
    def cleanup(battle):
        """Idempotently restore runtime identity before strict owned sync; retain used budget."""
        from pokemon.dex.entities import Stats

        for participant in battle.participants:
            for pokemon in participant.pokemons:
                profile = getattr(pokemon, "mega_profile", None)
                if not profile:
                    continue
                restore = profile["restore"]
                for name in ("species", "base_species", "name", "types", "ability", "max_hp"):
                    setattr(pokemon, name, deepcopy(restore[name]))
                pokemon.base_stats = Stats(**restore["stats"])
                pokemon.stats = pokemon._battle_stats()
                pokemon.mega_evolved = False
                pokemon.mega_evolution_forme = None
                pokemon.mega_profile = None
                pokemon.ability_state = {}
        battle.mega_pending = {}
