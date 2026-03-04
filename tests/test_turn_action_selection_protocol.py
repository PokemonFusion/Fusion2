"""Regression tests for protocol-based action collection in turn processing."""

from pokemon.battle.actions import Action, ActionType
from pokemon.battle.turns import TurnProcessor


class _ParticipantWithSingleChooseActions:
    """Participant double returning a single Action from choose_actions."""

    def __init__(self, name: str):
        self.name = name
        self.has_lost = False
        self.team = name
        self.active = [object()]

    def choose_actions(self, battle):
        return Action(actor=self, action_type=ActionType.RUN)


class _DummyBattle(TurnProcessor):
    """Minimal battle object exposing collaborators needed by select_actions."""

    def __init__(self, participants):
        self.participants = participants

    def opponents_of(self, participant):
        return [part for part in self.participants if part is not participant]


def test_select_actions_accepts_single_action_from_choose_actions():
    """select_actions should normalize single choose_actions results."""

    player = _ParticipantWithSingleChooseActions("Player")
    foe = _ParticipantWithSingleChooseActions("Foe")
    battle = _DummyBattle([player, foe])

    actions = battle.select_actions()

    assert len(actions) == 2
    assert all(isinstance(action, Action) for action in actions)
    assert actions[0].target is foe
    assert actions[1].target is player
