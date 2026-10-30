"""Player-facing menu selections must retain canonical party positions."""

from types import SimpleNamespace

import pytest

from menus import moveset_manager, pokestore


def gapped_player():
    """Return a small party with only canonical slots two and six occupied."""
    mons = [SimpleNamespace(unique_id=name, nickname=name, species="Squirtle",
                            movesets=SimpleNamespace(order_by=lambda field: []), active_moveset=None)
            for name in ("Second", "Sixth")]
    messages = []
    player = SimpleNamespace(
        storage=SimpleNamespace(get_party_slots=lambda: [None, mons[0], None, None, None, mons[1]]),
        location=SimpleNamespace(db=SimpleNamespace(is_pokemon_center=True)),
        ndb=SimpleNamespace(), msg=messages.append,
    )
    return player, mons, messages


def test_storage_deposit_prompt_and_selection_use_canonical_slot(monkeypatch):
    """Choosing six deposits the member displayed as six, despite intervening gaps."""
    player, mons, _ = gapped_player()
    text, _ = pokestore.node_deposit(player)
    assert "2. Second" in text and "6. Sixth" in text
    monkeypatch.setattr(pokestore, "node_choose_box", lambda caller, **kw: (kw["poke_id"], None))
    assert pokestore.node_deposit(player, "6")[0] == mons[1].unique_id


@pytest.mark.parametrize("selection", ["0", "1", "3", "7", "-1"])
def test_moveset_prompt_rejects_empty_and_invalid_slots(selection):
    """An invalid index must not open a different member's moveset editor."""
    player, _, messages = gapped_player()
    text, _ = moveset_manager.node_start(player, selection)
    assert "Invalid choice." in messages
    assert "2. Second" in text and "6. Sixth" in text
    assert not hasattr(player.ndb, "ms_pokemon")


def test_moveset_selection_uses_canonical_slot():
    """The sixth party member remains choice six in the editor."""
    player, mons, _ = gapped_player()
    moveset_manager.node_start(player, "6")
    assert player.ndb.ms_pokemon is mons[1]


def test_storage_swap_rejects_a_now_empty_slot(monkeypatch):
    """A stale swap prompt must not turn a gap into an unintended withdrawal."""
    player, _, messages = gapped_player()
    player.swap_pokemon = lambda *args: pytest.fail("An empty slot cannot be swapped")
    pokestore.node_choose_party_slot(player, "1", poke_id="boxed")
    assert "Invalid choice." in messages
