"""Once-only native wild-battle ability items, limited to canonical owned party."""


class PostBattleItems:
    """Commit a roll and its owned-item writes with a battle-scoped receipt."""

    @classmethod
    def resolve(cls, session):
        """Run during normal end, never during PvP, aborted setup, or staff cleanup."""
        from pokemon.battle.engine import BattleType
        from pokemon.services.battle_rewards import BattleRewards

        battle = session.battle
        if (not battle or getattr(getattr(battle, "type", None), "value", None) != BattleType.WILD.value
                or not getattr(battle, "battle_over", False)
                or not BattleRewards.supports(session.captainA)):
            return
        from django.db import transaction
        from evennia.objects.models import ObjectDB

        room = session.room
        try:
            with transaction.atomic():
                ObjectDB.objects.select_for_update().get(pk=room.pk)
                room.attributes.reset_cache()
                # Cleanup removes both keys atomically. A stale end cannot roll
                # another award after the receipt has been cleaned away.
                if not session.storage.get("state") or session.storage.get("post_battle_items") is not None:
                    return
                cls._award(session)
        except Exception:
            # SQL rollback must finish before rewinding Evennia's identity and
            # Attribute caches, otherwise a retry can see an uncommitted item.
            room.attributes.reset_cache()
            from pokemon.models.core import OwnedPokemon
            from pokemon.services.pokemon_refs import parse_pokemon_ref

            ids = []
            for part in battle.participants:
                if part.player is session.captainA:
                    for mon in part.pokemons:
                        kind, identifier = parse_pokemon_ref(getattr(mon, "model_id", None))
                        if kind == "owned" and identifier:
                            ids.append(identifier)
            for mon in OwnedPokemon.objects.filter(pk__in=ids, trainer__user_id=session.captainA.pk):
                mon.flush_from_cache(force=True)
                mon.refresh_from_db()
                OwnedPokemon.cache_instance(mon)
            raise

    @staticmethod
    def _award(session):
        """Require the canonical party and current trainer for every item write."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from utils.fusion import get_battle_party_with_fusion

        battle, player = session.battle, session.captainA
        participant = next((part for part in battle.participants if part.player is player), None)
        if participant is None:
            return
        party = {str(mon.pk) for mon in get_battle_party_with_fusion(player)}
        previous = [(mon, mon.item) for mon in participant.pokemons]
        rng_state = battle.rng.getstate() if hasattr(battle.rng, "getstate") else None
        try:
            awards = battle.resolve_post_battle_abilities(
                caught=bool(getattr(battle, "capture_succeeded", False)),
                thrown_ball=getattr(battle, "failed_capture_ball", None), participant=participant)
            receipt = []
            for runtime, item in awards:
                kind, identifier = parse_pokemon_ref(runtime.model_id)
                if kind != "owned" or str(identifier) not in party:
                    raise ValueError("Post-battle item is outside the current owned party.")
                mon = OwnedPokemon.objects.select_for_update().get(pk=identifier, trainer__user_id=player.pk)
                # A different persisted held item must never be overwritten.
                # Consumed battle items are not generally persisted by this path.
                if mon.held_item:
                    runtime.item = next(old for poke, old in previous if poke is runtime)
                    continue
                mon.held_item = item
                mon.save(update_fields=["held_item"])
                receipt.append({"pokemon": str(mon.pk), "item": item})
            session.storage.set("post_battle_items", receipt)
        except Exception:
            for mon, item in previous:
                mon.item = item
            if rng_state is not None:
                battle.rng.setstate(rng_state)
            raise
