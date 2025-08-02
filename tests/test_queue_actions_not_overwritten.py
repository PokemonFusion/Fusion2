from tests.test_battle_rebuild import BattleSession, DummyRoom, DummyPlayer


def _setup_battle():
    """Create a simple two-player battle for testing."""
    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p2 = DummyPlayer(2, room)
    inst = BattleSession(p1, p2)
    inst.start_pvp()
    return inst, p1, p2


def test_queue_move_does_not_overwrite_existing_action():
    inst, p1, _ = _setup_battle()
    inst.queue_move("tackle", caller=p1)
    inst.queue_move("growl", caller=p1)
    assert inst.state.declare["A1"]["move"].lower() == "tackle"


def test_queue_switch_does_not_overwrite_existing_action():
    inst, p1, _ = _setup_battle()
    inst.queue_switch(2, caller=p1)
    inst.queue_switch(3, caller=p1)
    assert inst.state.declare["A1"]["switch"] == 2


def test_queue_item_does_not_overwrite_existing_action():
    inst, p1, _ = _setup_battle()
    inst.queue_item("potion", caller=p1)
    inst.queue_item("superpotion", caller=p1)
    assert inst.state.declare["A1"]["item"].lower() == "potion"


def test_queue_run_does_not_overwrite_existing_action():
    inst, p1, _ = _setup_battle()
    inst.queue_run(caller=p1)
    inst.queue_run(caller=p1)
    assert inst.state.declare["A1"]["run"] == "1"


def test_cannot_declare_new_action_if_already_declared():
    inst, p1, _ = _setup_battle()
    inst.queue_move("tackle", caller=p1)
    before = inst.state.declare["A1"].copy()
    inst.queue_switch(2, caller=p1)
    assert inst.state.declare["A1"] == before


def test_turn_runs_and_clears_declarations():
    """Battle runs once all actions are declared and clears declarations."""
    inst, p1, p2 = _setup_battle()
    inst.prompt_next_turn = lambda: None
    ran = {"flag": False}

    def fake_run_turn():
        ran["flag"] = True

    inst.battle.run_turn = fake_run_turn

    inst.queue_move("tackle", caller=p1)
    inst.queue_move("tackle", caller=p2)

    assert ran["flag"] is True
    assert inst.state.declare == {}

