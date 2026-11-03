"""Use canonical stat events and durable randomness for held stat items."""

import random
from collections.abc import MutableSequence

from pokemon.utils.boosts import STAT_KEY_MAP, apply_boost

from .effect_context import EffectContext
from .item_consumption import ReactiveItemConsumption


class HeldItemBoosts:
    """Keep item identity, consumption and stage effects on shared boundaries."""

    STATS = ("atk", "def", "spa", "spd", "spe")

    @staticmethod
    def berry(pokemon, boosts):
        """Eating owns consumption; its effect uses the berry as the cause."""
        if pokemon is not None:
            apply_boost(pokemon, boosts, source=pokemon, effect=EffectContext.item(pokemon))

    @staticmethod
    def use(pokemon, boosts, *, source=None, effect=None):
        """Consume once even at a cap, retaining the item's boost context."""
        item = EffectContext.item(pokemon)
        if not ReactiveItemConsumption.use(pokemon, source=source, effect=effect):
            return False
        apply_boost(pokemon, boosts, source=source or pokemon, effect=item)
        return True

    @staticmethod
    def pinch(pokemon):
        """Respect low HP, effective Gluttony, suppression and eating gates."""
        if pokemon is None:
            return
        denominator = 2 if EffectContext.key(EffectContext.ability(pokemon)) == "gluttony" else 4
        if 0 < pokemon.hp <= pokemon.max_hp // denominator:
            ReactiveItemConsumption.eat(pokemon, source=pokemon)

    @classmethod
    def starf(cls, pokemon):
        """Choose uniformly among the reference's five stats below +6."""
        if pokemon is None:
            return
        stages = {STAT_KEY_MAP.get(key, key): value for key, value in pokemon.boosts.items()}
        eligible = [key for key in cls.STATS if stages.get(STAT_KEY_MAP[key], 0) < 6]
        if eligible:
            rng = ItemRandomState.own(pokemon.battle)
            cls.berry(pokemon, {rng.choice(eligible): 2})


class ItemRandomState:
    """Checkpoint the battle RNG when a Starf Berry can make a random choice."""

    @staticmethod
    def own(battle):
        """Detach the legacy module RNG without advancing global randomness."""
        if battle.rng is random:
            battle.rng = random.Random()
            battle.rng.setstate(random.getstate())
        battle._item_random_tracked = True
        return battle.rng

    @classmethod
    def freeze(cls, battle):
        """Save future choices as well as already applied stages and history."""
        present = any(EffectContext.key(getattr(mon, "item", None)) == "starfberry"
                      for part in battle.participants
                      for mon in (getattr(part, "pokemons", None) or getattr(part, "active", [])))
        if not present and not getattr(battle, "_item_random_tracked", False):
            return None
        version, state, gaussian = cls.own(battle).getstate()
        return [version, list(state), gaussian]

    @classmethod
    def restore(cls, battle, payload):
        """Accept JSON round trips without ever modifying the global RNG."""
        if payload is None:
            return
        sequences = (list, tuple, MutableSequence)
        if (not isinstance(payload, sequences) or len(payload) != 3
                or type(payload[0]) is not int or payload[0] != 3
                or not isinstance(payload[1], sequences)
                or len(payload[1]) != 625 or any(type(n) is not int for n in payload[1])
                or (payload[2] is not None and type(payload[2]) not in (int, float))):
            raise ValueError("Invalid held-item random state requires battle recovery.")
        rng = random.Random()
        try:
            rng.setstate((payload[0], tuple(payload[1]), payload[2]))
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Invalid held-item random state requires battle recovery.") from error
        battle.rng = rng
        battle._item_random_tracked = True
