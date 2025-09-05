import logging
from tests.test_interface_display import (
    iface,
    display_battle_interface,
    DummyMon,
    DummyTrainer,
    BattleState,
)


def test_invalid_viewer_team_logs_warning_and_shows_percent(caplog):
    mon_a = DummyMon("Pika", 15, 20)
    mon_b = DummyMon("Bulba", 30, 60)
    t_a = DummyTrainer("Ash", mon_a)
    t_b = DummyTrainer("Gary", mon_b)
    st = BattleState()

    caplog.set_level(logging.WARNING, logger=iface.__name__)
    out = display_battle_interface(t_a, t_b, st, viewer_team="X")

    assert "15/20" not in out and "30/60" not in out
    assert "75%" in out and "50%" in out
    assert any("viewer_team" in r.message for r in caplog.records)
