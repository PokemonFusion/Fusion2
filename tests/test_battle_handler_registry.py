"""Ensure battle handler integration keeps the registry in sync."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from pokemon.battle import registry as registry_mod


def test_battle_handler_updates_registry():
        """BattleHandler.register should expose sessions to the registry."""

        handler_name = "pokemon.battle.handler"
        handler_path = Path(__file__).resolve().parents[1] / "pokemon" / "battle" / "handler.py"

        original_module = sys.modules.get(handler_name)
        spec = importlib.util.spec_from_file_location(handler_name, handler_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[handler_name] = module
        spec.loader.exec_module(module)

        session = None
        existing_sessions = list(registry_mod.REGISTRY.all())
        try:
                handler = module.BattleHandler()

                for sess in existing_sessions:
                        registry_mod.REGISTRY.unregister(sess)

                class Stub:
                        pass

                player = Stub()
                opponent = Stub()
                watcher = Stub()
                room = Stub()
                room.id = 777
                session = Stub()
                session.battle_id = 321
                session.room = room
                session.teamA = [player]
                session.teamB = [opponent]
                session.observers = {watcher}

                handler.register(session)

                sessions = registry_mod.REGISTRY.all()
                assert session in sessions
                assert registry_mod.REGISTRY.sessions_for(player) == [session]
                assert registry_mod.REGISTRY.sessions_for(opponent) == [session]
                assert registry_mod.REGISTRY.sessions_for(watcher) == [session]

                handler.unregister(session)
                assert session not in registry_mod.REGISTRY.all()
        finally:
                if session is not None:
                        registry_mod.REGISTRY.unregister(session)
                for sess in existing_sessions:
                        registry_mod.REGISTRY.register(sess)
                if original_module is not None:
                        sys.modules[handler_name] = original_module
                else:
                        sys.modules.pop(handler_name, None)


def test_battle_handler_exposes_manager_compatibility_api():
        """BattleHandler should satisfy callers still using battle_manager APIs."""

        from pokemon.battle.handler import BattleHandler

        handler = BattleHandler()
        player = types.SimpleNamespace(id=12, db=types.SimpleNamespace(), ndb=types.SimpleNamespace())
        class Watcher:
                id = 44
                key = "Watcher"

        watcher = Watcher()

        class Session:
                battle_id = 55
                room = types.SimpleNamespace(id=777)
                teamA = [player]
                teamB = []
                trainers = [player]
                observers = set()

                def __init__(self):
                        self.added = []
                        self.removed = []
                        self.notices = []
                        self.ended = False

                def add_observer(self, obj):
                        self.added.append(obj)
                        self.observers.add(obj)

                def remove_observer(self, obj):
                        self.removed.append(obj)
                        self.observers.discard(obj)

                def notify(self, text):
                        self.notices.append(text)

                def end(self):
                        self.ended = True

        session = Session()
        player.db.battle_id = session.battle_id
        player.ndb.battle_instance = session

        handler.register(session)

        assert handler.ndb.instances is handler.instances
        assert handler.get(session.battle_id) is session
        assert handler.for_player(player) is session
        assert handler.watch(session.battle_id, watcher) is True
        assert watcher in session.added
        assert handler.unwatch(session.battle_id, watcher) is True
        assert watcher in session.removed
        assert handler.abort_request(session.battle_id, player) is True
        assert session.ended is True
        assert session.notices
