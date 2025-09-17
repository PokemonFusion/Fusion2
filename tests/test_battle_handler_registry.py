"""Ensure battle handler integration keeps the registry in sync."""

from __future__ import annotations

import importlib.util
import sys
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
