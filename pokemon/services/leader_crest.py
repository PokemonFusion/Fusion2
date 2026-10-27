"""Bounded native Bisharp KO evidence on the existing battle receipt lifecycle."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from pokemon.names import normalize_name

CATEGORY = "kingambit_evolution"
EVENT = "kingambit_victory"
CREST = "leaderscrest"


def canonical_uuid(value):
    """Reject absent or malformed identities instead of using names/flags."""
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


@dataclass(frozen=True)
class LeaderQualification:
    """At most three real leader identities and their conservative level floor."""

    leaders: tuple[str, ...] = ()
    level_floor: int = 0

    def ready(self, level):
        """Require an actual stored level above the third-KO threshold."""
        return len(self.leaders) == 3 and type(level) is int and level > self.level_floor

    @classmethod
    def parse(cls, data, pokemon_id, trainer_id):
        """Validate private structured evidence; arbitrary completion flags do nothing."""
        if not isinstance(data, Mapping) or data.get("version") != 1:
            return None
        if data.get("pokemon") != str(pokemon_id) or data.get("trainer") != trainer_id:
            return None
        leaders, floor = data.get("leaders"), data.get("level_floor")
        if (not isinstance(leaders, Sequence) or isinstance(leaders, (str, bytes)) or not 1 <= len(leaders) <= 3
                or type(floor) is not int or not 1 <= floor <= 100):
            return None
        identities = tuple(canonical_uuid(value) for value in leaders)
        if None in identities or len(set(identities)) != len(identities):
            return None
        return cls(identities, floor)


class LeaderCrestProgress:
    """Seal real KOs at faint, then claim only a terminal committed victory."""

    @staticmethod
    def evidence(character, pokemon_id):
        """Bypass Attribute's identity cache, including after rolled-back updates."""
        from pokemon.services.battle_rewards import BattleRewards

        return BattleRewards.stored_attribute(character, str(pokemon_id), category=CATEGORY)

    @staticmethod
    def candidate(battle, defeated):
        """Read authoritative native identities and the direct lethal move ledger."""
        from pokemon.battle.engine import BattleType
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        if battle.type not in {BattleType.WILD, BattleType.TRAINER} or not battle.award_xp:
            return None
        cause = (getattr(defeated, "tempvals", {}) or {}).get("faint_cause", {})
        source, move = cause.get("source"), cause.get("effect")
        if source is None or getattr(move, "category", None) not in {"Physical", "Special"}:
            return None
        owner, foe = battle.participant_for(source), battle.participant_for(defeated)
        if (owner is None or foe not in battle.opponents_of(owner) or not foe.is_ai
                or not BattleRewards.supports(owner.player)
                or not any(mon is source for mon in owner.active)
                or not any(mon is source for mon in owner.pokemons)
                or not any(mon is defeated for mon in foe.pokemons)
                or getattr(source, "hp", 0) <= 0 or getattr(defeated, "hp", 1) != 0):
            return None
        if any(getattr(mon, "transformed", False) or normalize_name(getattr(mon, "species", "")) != "bisharp"
               or normalize_name(getattr(mon, "base_species", "")) != "bisharp" for mon in (source, defeated)):
            return None
        item = getattr(defeated, "item", None)
        if normalize_name(getattr(item, "name", item)) != CREST:
            return None
        ledger = (getattr(defeated, "tempvals", {}) or {}).get("last_damaged_by", {})
        before, damage = ledger.get("hp_before"), ledger.get("actual_damage")
        if (ledger.get("source") is not source or ledger.get("move") is not move
                or ledger.get("turn") != battle.turn_count
                or type(before) is not int or type(damage) is not int
                or before <= 0 or damage < before):
            return None
        source_kind, own_id = parse_pokemon_ref(getattr(source, "model_id", None))
        target_kind, encounter_id = parse_pokemon_ref(getattr(defeated, "model_id", None))
        if source_kind != "owned" or target_kind != "encounter":
            return None
        own_id, encounter_id = canonical_uuid(own_id), canonical_uuid(encounter_id)
        if not own_id or not encounter_id:
            return None
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        player = BattleRewards.character(owner.player)
        row = OwnedPokemon.objects.filter(pk=own_id, trainer__user_id=player.pk).values(
            "species", "level", "is_egg", "trainer_id",
        ).first()
        target = EncounterPokemon.objects.filter(pk=encounter_id).values("species", "held_item", "source_kind").first()
        if (not row or row["species"] != "Bisharp" or row["is_egg"] or not target
                or target["species"] != "Bisharp" or normalize_name(target["held_item"]) != CREST
                or target["source_kind"] != ("wild" if battle.type == BattleType.WILD else "npc")):
            return None
        if not PokemonPlacement.objects.filter(pokemon_id=own_id, storage__user_id=player.pk,
                                              location_type="party").exists():
            return None
        return {"pokemon": own_id, "leader": encounter_id, "level": row["level"]}

    @classmethod
    def record_result(cls, session):
        """Retain a victory effect before cleanup; failure must preserve the session."""
        from pokemon.battle.engine import BattleType
        from pokemon.services.battle_rewards import BattleRewards, CATEGORY as REWARDS_CATEGORY

        battle = session.battle
        delivery = getattr(battle, "reward_delivery", None)
        if (battle is None or delivery is None or not BattleRewards.supports(session.captainA)
                or battle.type not in {BattleType.WILD, BattleType.TRAINER}
                or not battle.award_xp or not battle.battle_over
                or getattr(battle, "capture_succeeded", False)
                or (getattr(battle, "_flee_result", {}) or {}).get("success")
                or len(battle.participants) != 2):
            return False
        own = next((part for part in battle.participants if part.player is session.captainA), None)
        foe = next((part for part in battle.participants if part is not own), None)
        if (own is None or foe is None or not foe.is_ai or own.has_lost or not foe.has_lost
                or not any(mon.hp > 0 for mon in own.pokemons)
                or not foe.pokemons or any(mon.hp > 0 for mon in foe.pokemons)):
            return False
        character = BattleRewards.character(session.captainA)
        character.attributes.reset_cache()
        candidates = []
        for mon in foe.pokemons:
            identity = getattr(mon, "model_id", None)
            if not identity:
                continue
            key = delivery.key(f"faint:{foe.team}:{identity}")
            receipt = BattleRewards.stored_attribute(character, key, category=REWARDS_CATEGORY)
            if receipt and receipt.get("battle_id") == delivery.battle_id and receipt.get("claimed"):
                candidate = receipt.get("payload", {}).get("kingambit_defeat")
                if candidate:
                    candidates.append(dict(candidate))
        if not candidates:
            return False
        delivery.record(session.captainA, EVENT, {"kingambit": candidates})
        return True

    @classmethod
    def apply(cls, character, trainer, candidates):
        """Run only inside BattleRewards' character/trainer claim transaction."""
        from pokemon.models.core import OwnedPokemon

        for candidate in candidates:
            own_id, leader = canonical_uuid(candidate.get("pokemon")), canonical_uuid(candidate.get("leader"))
            level = candidate.get("level")
            if not own_id or not leader or type(level) is not int or not 1 <= level <= 100:
                raise ValueError("Invalid sealed Kingambit evidence.")
            row = OwnedPokemon.objects.select_for_update().filter(pk=own_id, trainer=trainer).values("species").first()
            # Released/transferred/evolved Pokemon cannot gain this owner's progress.
            if not row or row["species"] != "Bisharp":
                continue
            prior = cls.evidence(character, own_id)
            progress = LeaderQualification.parse(prior, own_id, trainer.pk) if prior is not None else LeaderQualification()
            if progress is None:
                raise ValueError("Unrecognized Kingambit evidence; staff review is required.")
            if leader in progress.leaders or len(progress.leaders) == 3:
                continue
            character.attributes.add(own_id, {
                "version": 1, "pokemon": own_id, "trainer": trainer.pk,
                "leaders": [*progress.leaders, leader], "level_floor": max(progress.level_floor, level),
            }, category=CATEGORY)

    @staticmethod
    def read(player, pokemon):
        """Read fresh private owner/UUID evidence without locking in reverse order."""
        from pokemon.services.battle_rewards import BattleRewards

        if not BattleRewards.supports(player) or not getattr(pokemon, "trainer_id", None):
            return LeaderQualification()
        character = BattleRewards.character(player)
        character.attributes.reset_cache()
        data = LeaderCrestProgress.evidence(character, pokemon.pk)
        return LeaderQualification.parse(data, pokemon.pk, pokemon.trainer_id) or LeaderQualification()

    @classmethod
    def describe(cls, player, pokemon):
        """Show useful ordinary-player progress without exposing internal receipts."""
        if normalize_name(getattr(pokemon, "species", "")) != "bisharp":
            return None
        progress = cls.read(player, pokemon)
        count = len(progress.leaders)
        detail = ("ready for +evolve" if progress.ready(pokemon.level) else
                  "a further level is required; level 100 cannot qualify" if count == 3 and progress.level_floor == 100 else
                  f"reach level {progress.level_floor + 1}" if count == 3 else "then gain a level")
        return f"Kingambit: {count}/3 leader victories; {detail}."
