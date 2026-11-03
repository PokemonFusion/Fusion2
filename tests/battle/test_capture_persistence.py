"""Capture result/tracking tests; real persistence is covered by lifecycle_database."""

from types import SimpleNamespace
from uuid import uuid4

from pokemon.services.capture import _receipt_result, _update_temp_tracking


def test_capture_receipt_retry_preserves_identity_and_suppresses_prompt():
    receipt = SimpleNamespace(owned_id=uuid4(), location="party", party_slot=3, box_name=None)
    original = _receipt_result(receipt)
    retry = _receipt_result(receipt, retry=True)
    assert retry.owned_pokemon_id == original.owned_pokemon_id
    assert retry.party_slot == 3
    assert original.should_prompt_nickname
    assert not retry.should_prompt_nickname


def test_capture_tracking_removes_only_captured_encounter():
    writes = []
    session = SimpleNamespace(temp_pokemon_ids=["encounter:a", "encounter:b"],
                              storage=SimpleNamespace(set=lambda key, value: writes.append((key, value))))
    player = SimpleNamespace(ndb=SimpleNamespace(battle_instance=session))
    _update_temp_tracking(player=player, model_id="encounter:a")
    _update_temp_tracking(player=player, model_id="encounter:a")
    assert session.temp_pokemon_ids == ["encounter:b"]
    assert writes == [("temp_pokemon_ids", ["encounter:b"])]


def test_capture_tracking_uses_battle_context_without_player_session():
    session = SimpleNamespace(temp_pokemon_ids=["encounter:a"], storage=None)
    _update_temp_tracking(battle_context=session, model_id="encounter:a")
    assert session.temp_pokemon_ids == []
