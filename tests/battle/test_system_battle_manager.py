from __future__ import annotations

import sys
import types


def test_system_start_uses_canonical_battle_handler(monkeypatch):
	"""Startup should expose the canonical handler through battle_manager."""

	from pokemon.battle.handler import battle_handler
	from world import system_init

	holder = types.SimpleNamespace()
	heartbeat = types.ModuleType("world.heartbeat")
	heartbeat.ensure_heartbeat_script = lambda: None
	hygiene = types.ModuleType("utils.db_connection_hygiene")
	hygiene.install_command_connection_hygiene = lambda: None

	monkeypatch.setattr(system_init, "get_system", lambda: holder)
	monkeypatch.setitem(sys.modules, "world.heartbeat", heartbeat)
	monkeypatch.setitem(sys.modules, "utils.db_connection_hygiene", hygiene)

	system_init.at_server_start()

	assert holder.battle_manager is battle_handler
