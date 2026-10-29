"""Once-only, nonstacking held-item qualification for standard NPC trainer prizes."""

from collections.abc import Mapping
from copy import deepcopy
from uuid import UUID

from pokemon.names import normalize_name


class NPCPrizeItems:
    """Retain participation evidence instead of looking at equipment at payout time."""

    items = frozenset({"amuletcoin", "luckincense"})

    @staticmethod
    def enabled(battle):
        """Keep scripted/gym/Adventure, PvP, Multi and wild economies outside this batch."""
        return (getattr(getattr(battle, "type", None), "name", "") == "TRAINER"
                and len(getattr(battle, "participants", ())) == 2
                and not getattr(battle, "multi", False)
                and getattr(battle, "prize_source_type", None) in {"static", "random"}
                and bool(getattr(battle, "award_prizes", True)))

    @classmethod
    def tracked(cls, battle):
        """Serialize prize-bearing turns, including a later transfer from an NPC holder."""
        if not cls.enabled(battle):
            return False
        from .owned_battle_actor import OwnedBattleActor

        return bool(cls.freeze(battle)) or any(OwnedBattleActor.item_key(mon) in cls.items
            for participant in battle.participants for mon in participant.pokemons)

    @classmethod
    def validate(cls, battle, raw):
        """Fail closed on corrupt/outcome-foreign evidence while accepting empty legacy state."""
        if not isinstance(raw, Mapping):
            raise ValueError("NPC prize qualification needs recovery.")
        result = {}
        for owner, record in raw.items():
            try:
                if (not isinstance(owner, str) or not owner.isascii() or not owner.isdigit()
                        or str(int(owner)) != owner or int(owner) <= 0
                        or not isinstance(record, Mapping)
                        or set(record) != {"owner", "pokemon", "item", "phase", "turn", "reward"}
                        or record["owner"] != owner or record["item"] not in cls.items
                        or record["phase"] not in {"entry", "action"}
                        or type(record["turn"]) is not int or record["turn"] < 0
                        or record["turn"] > getattr(battle, "mechanic_turn", 0)
                        or record["reward"] != str(getattr(battle, "mechanic_battle_id", None))
                        or not str(record["pokemon"]).startswith("owned:")
                        or str(getattr(battle, "mechanic_controllers", {}).get(record["pokemon"])) != owner):
                    raise ValueError
                UUID(record["reward"])
                UUID(record["pokemon"].partition(":")[2])
            except (KeyError, ValueError, TypeError, AttributeError) as error:
                raise ValueError("NPC prize participation evidence needs recovery.") from error
            result[owner] = dict(record)
        return result

    @classmethod
    def restore(cls, battle, raw):
        """Restore saved evidence without granting new participation from current gear."""
        battle.npc_prize_qualifications = cls.validate(battle, raw)

    @classmethod
    def freeze(cls, battle):
        """Checkpoint detached primitive evidence with the same turn/outcome identity."""
        return deepcopy(cls.validate(battle, getattr(battle, "npc_prize_qualifications", {})))

    @classmethod
    def capture(cls, battle, participant, pokemon, *, phase, initial=False):
        """Validate actual owned active participation independently of battle-effect suppression."""
        from .owned_battle_actor import OwnedBattleActor

        if (not cls.enabled(battle) or pokemon is None or participant is None
                or getattr(participant, "is_ai", True)
                or OwnedBattleActor.item_key(pokemon) not in cls.items):
            return None
        from pokemon.services.battle_rewards import BattleRewards

        if not BattleRewards.supports(getattr(participant, "player", None)):
            return None
        with OwnedBattleActor.locked(battle, participant, pokemon) as saved:
            if initial and normalize_name(saved["held_item"]) != OwnedBattleActor.item_key(pokemon):
                raise ValueError("Initial NPC prize item ownership changed; battle recovery is required.")
            owner = str(BattleRewards.character(participant.player).pk)
            record = {"owner": owner, "pokemon": str(pokemon.model_id),
                      "item": OwnedBattleActor.item_key(pokemon), "phase": phase,
                      "turn": getattr(battle, "mechanic_turn", 0),
                      "reward": str(battle.mechanic_battle_id)}
            cls.validate(battle, {owner: record})
            return record

    @classmethod
    def record(cls, battle, proof):
        """Keep the first valid qualification for an owner, with a maximum multiplier of two."""
        if proof is None:
            return
        current = cls.freeze(battle)
        cls.validate(battle, {proof["owner"]: proof})
        current.setdefault(proof["owner"], dict(proof))
        battle.npc_prize_qualifications = current

    @classmethod
    def entry(cls, battle, pokemon):
        """Qualify a real active entry before hazards can faint the holder."""
        if cls.enabled(battle):
            cls.record(battle, cls.capture(battle, battle.participant_for(pokemon), pokemon, phase="entry"))

    @classmethod
    def initial(cls, battle):
        """Record initial active entries only on a new session, never during restoration."""
        if cls.enabled(battle):
            for participant in battle.participants:
                for pokemon in participant.active:
                    cls.record(battle, cls.capture(battle, participant, pokemon, phase="entry", initial=True))

    @classmethod
    def action(cls, battle, action):
        """Bind physical ownership before this ordinary move, so a new Trick item waits."""
        if not cls.enabled(battle):
            return None
        pokemon = action.pokemon or (action.actor.active[0] if action.actor.active else None)
        return cls.capture(battle, action.actor, pokemon, phase="action")

    @classmethod
    def move_attempted(cls, battle, pokemon):
        """DeductPP is reached after action prevention; zero-cost/Struggle attempts also count.

        The ordinary-action proof was captured before execution. Recursive/called
        moves cannot obtain a later item and retroactively qualify that action.
        This mutation is inside the persistent turn transaction and rolls back
        with its checkpoint if the action or its eventual writes fail.
        """
        proof = getattr(battle, "_npc_prize_action", None)
        if proof is not None and proof["pokemon"] == str(getattr(pokemon, "model_id", "")):
            cls.record(battle, proof)

    @classmethod
    def payload(cls, battle, winner, base):
        """Seal base and one earned bonus without rechecking final held equipment."""
        from pokemon.services.battle_rewards import BattleRewards
        from .owned_battle_actor import OwnedBattleActor

        payload = {"money": base}
        if not cls.enabled(battle) or not BattleRewards.supports(getattr(winner, "player", None)):
            return payload
        owner = str(BattleRewards.character(winner.player).pk)
        proof = cls.freeze(battle).get(owner)
        if proof is None:
            payload["npc_prize"] = {"base": base, "multiplier": 1, "qualification": None}
            return payload
        pokemon = next((mon for mon in winner.pokemons if str(mon.model_id) == proof["pokemon"]), None)
        if pokemon is None:
            raise ValueError("The earned NPC prize holder needs ownership recovery.")
        with OwnedBattleActor.locked(battle, winner, pokemon, active=False):
            payload.update(money=base * 2,
                npc_prize={"base": base, "multiplier": 2, "qualification": dict(proof)})
        return payload
