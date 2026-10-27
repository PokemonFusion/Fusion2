"""Reproduce native entry and ordinary post-battle item integration boundaries."""

import random
import sys
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace

import pytest

from .helpers import build_battle, load_modules


def test_tera_shift_uses_calculated_stats_retains_damage_and_survives_checkpoint():
    from pokemon.battle.native_forms import NativeBattleForm
    from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

    battle, user, _ = build_battle(attacker_ability="Tera Shift")
    user.name = user.species = user.base_species = "Terapagos"
    user.level = 50
    user.max_hp = get_max_hp(user)
    user.hp = user.max_hp - 13
    old_maximum = user.max_hp
    battle.start_turn()
    assert str(user.species) == "Terapagos-Terastal"
    assert str(getattr(user.ability, "name", user.ability)).lower().replace(" ", "") == "terashell"
    assert user.max_hp == get_max_hp(user) > old_maximum
    assert user.max_hp - user.hp == 13
    assert user.base_stats.special_attack == get_stats(user)["special_attack"]
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    battle.start_turn()
    assert NativeBattleForm.restore(restored)
    assert restored.species == "Terapagos" and restored.max_hp == old_maximum
    assert restored.hp == old_maximum - 13


def test_tera_shift_rejects_non_native_holder_and_transformed_identity():
    from pokemon.battle.native_forms import NativeBattleForm

    _, user, _ = build_battle(attacker_ability="Tera Shift")
    user.species = user.base_species = "Eevee"
    assert not NativeBattleForm.tera_shift(user)
    user.species = user.base_species = "Terapagos"
    user.transformed = True
    assert not NativeBattleForm.tera_shift(user)


@pytest.mark.parametrize("caught,ball,held,expected", [
    (False, "Poke Ball", None, "Poke Ball"),
    (True, "Poke Ball", None, None),
    (False, None, None, None),
    (False, "Poke Ball", "Leftovers", "Leftovers"),
])
def test_postbattle_fetch_qualifies_real_failed_throw_and_does_not_overwrite(caught, ball, held, expected):
    battle, user, _ = build_battle(attacker_ability="Ball Fetch")
    user.item = battle._coerce_item(held) if held else None
    battle.resolve_post_battle_abilities(caught=caught, thrown_ball=ball,
                                       participant=battle.participants[0])
    assert str(getattr(user.item, "name", user.item) or "").lower().replace(" ", "") == (expected or "").lower().replace(" ", "")


def test_postbattle_award_persists_only_canonical_owned_party_and_receipts_empty_roll(monkeypatch):
    from pokemon.services.post_battle_items import PostBattleItems
    import utils.fusion

    battle, user, _ = build_battle(attacker_ability="Honey Gather")
    user.level, user.model_id = 100, "owned:00000000-0000-0000-0000-000000000001"
    player = SimpleNamespace(pk=132)
    battle.participants[0].player = player
    saved, receipt = [], {}
    owned = SimpleNamespace(pk=user.model_id.split(":")[1], held_item="",
                            save=lambda **kw: saved.append(kw))
    class Manager:
        def select_for_update(self):
            return self

        def get(self, **filters):
            assert filters == {"pk": owned.pk, "trainer__user_id": player.pk}
            return owned

    monkeypatch.setitem(sys.modules, "pokemon.models.core", SimpleNamespace(OwnedPokemon=SimpleNamespace(objects=Manager())))
    monkeypatch.setattr(utils.fusion, "get_battle_party_with_fusion", lambda owner: [owned] if owner is player else [])
    session = SimpleNamespace(battle=battle, captainA=player,
                              storage=SimpleNamespace(set=lambda key, value: receipt.update({key: value})))
    battle.rng = random.Random(1)
    PostBattleItems._award(session)
    assert owned.held_item == "Honey" and saved == [{"update_fields": ["held_item"]}]
    assert receipt["post_battle_items"] == [{"pokemon": owned.pk, "item": "Honey"}]


def test_postbattle_foreign_reference_rejected_and_runtime_rng_rolled_back(monkeypatch):
    from pokemon.services.post_battle_items import PostBattleItems
    import utils.fusion

    battle, user, _ = build_battle(attacker_ability="Honey Gather")
    user.level, user.model_id = 100, "owned:00000000-0000-0000-0000-000000000001"
    player = SimpleNamespace(pk=132)
    battle.participants[0].player = player
    monkeypatch.setattr(utils.fusion, "get_battle_party_with_fusion", lambda owner: [])
    monkeypatch.setitem(sys.modules, "pokemon.models.core", SimpleNamespace(OwnedPokemon=SimpleNamespace()))
    battle.rng = random.Random(1)
    old_state = battle.rng.getstate()
    session = SimpleNamespace(battle=battle, captainA=player)
    with pytest.raises(ValueError, match="outside"):
        PostBattleItems._award(session)
    assert user.item is None and battle.rng.getstate() == old_state


def test_normal_wild_end_receipt_prevents_reroll_and_stale_end_after_cleanup(monkeypatch):
    from django.db import transaction
    from pokemon.services.battle_rewards import BattleRewards
    from pokemon.services.post_battle_items import PostBattleItems

    battle, _, _ = build_battle()
    battle.battle_over = True
    values = {"state": {"ending": True}}
    session = SimpleNamespace(battle=battle, captainA=object(),
                              room=SimpleNamespace(pk=131, attributes=SimpleNamespace(reset_cache=lambda: None)),
                              storage=SimpleNamespace(get=lambda key: values.get(key)))
    monkeypatch.setattr(BattleRewards, "supports", lambda player: True)
    monkeypatch.setattr(transaction, "atomic", nullcontext)
    manager = SimpleNamespace(select_for_update=lambda: SimpleNamespace(get=lambda **kw: session.room))
    monkeypatch.setitem(sys.modules, "evennia.objects.models", SimpleNamespace(ObjectDB=SimpleNamespace(objects=manager)))
    calls = []
    def award(current):
        calls.append(current)
        values["post_battle_items"] = []  # A failed chance roll is also final.
    monkeypatch.setattr(PostBattleItems, "_award", award)
    PostBattleItems.resolve(session)
    PostBattleItems.resolve(session)
    assert calls == [session]
    values.clear()  # Atomic normal battle cleanup.
    PostBattleItems.resolve(session)
    assert calls == [session]
    values["state"] = {"ending": True}
    battle.type = load_modules()["BattleType"].PVP
    PostBattleItems.resolve(session)
    assert calls == [session]


def test_failed_postbattle_receipt_rewinds_identity_and_attribute_caches_after_sql_rollback(monkeypatch):
    from django.db import transaction
    from pokemon.services.battle_rewards import BattleRewards
    from pokemon.services.post_battle_items import PostBattleItems
    import utils.fusion

    battle, user, _ = build_battle(attacker_ability="Honey Gather")
    user.level, user.model_id = 100, "owned:00000000-0000-0000-0000-000000000001"
    battle.battle_over = True
    battle.rng = random.Random(1)
    rng_before = battle.rng.getstate()
    player = SimpleNamespace(pk=132)
    battle.participants[0].player = player
    events, cache = [], {}
    sql = {"held_item": ""}
    owned = SimpleNamespace(pk=user.model_id.split(":")[1], held_item="")
    owned.save = lambda **kw: sql.update(held_item=owned.held_item)
    def refresh():
        events.append("owned_refresh")
        owned.held_item = sql["held_item"]
    owned.refresh_from_db = refresh
    owned.flush_from_cache = lambda **kw: events.append("owned_flush")
    class Manager:
        def select_for_update(self):
            return self

        def get(self, **kw):
            return owned

        def filter(self, **kw):
            return [owned]
    fake_model = SimpleNamespace(objects=Manager(), cache_instance=lambda mon: None)
    monkeypatch.setitem(sys.modules, "pokemon.models.core", SimpleNamespace(OwnedPokemon=fake_model))
    monkeypatch.setattr(utils.fusion, "get_battle_party_with_fusion", lambda owner: [owned])
    monkeypatch.setattr(BattleRewards, "supports", lambda owner: True)
    def clear():
        events.append("room_refresh")
        cache.clear()
    room = SimpleNamespace(pk=131, attributes=SimpleNamespace(reset_cache=clear))
    object_manager = SimpleNamespace(select_for_update=lambda: SimpleNamespace(get=lambda **kw: room))
    monkeypatch.setitem(sys.modules, "evennia.objects.models", SimpleNamespace(ObjectDB=SimpleNamespace(objects=object_manager)))
    @contextmanager
    def atomic():
        try:
            yield
        except Exception:
            events.append("sql_rollback")
            sql["held_item"] = ""
            raise
    monkeypatch.setattr(transaction, "atomic", atomic)
    def fail_receipt(key, value):
        cache[key] = value  # An autosaving Attribute can retain its failed SQL value.
        raise RuntimeError("receipt write failed")
    storage = SimpleNamespace(get=lambda key: cache.get(key, {"ending": True} if key == "state" else None),
                              set=fail_receipt)
    session = SimpleNamespace(battle=battle, captainA=player, room=room, storage=storage)
    with pytest.raises(RuntimeError, match="receipt write failed"):
        PostBattleItems.resolve(session)
    assert user.item is None and battle.rng.getstate() == rng_before
    assert owned.held_item == "" and storage.get("post_battle_items") is None
    assert events.index("sql_rollback") < events.index("owned_refresh")
