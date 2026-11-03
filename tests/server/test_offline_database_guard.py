"""The offline test process must never reach the running game database."""

from types import SimpleNamespace

import pytest
from django.db.backends.base.base import BaseDatabaseWrapper


@pytest.mark.parametrize("already_connected", [False, True])
def test_offline_guard_refuses_new_and_cached_connections(already_connected):
    """Importing real models cannot bypass isolation through a cached handle."""
    calls = []
    wrapper = SimpleNamespace(
        connection=object() if already_connected else None,
        connect=lambda: calls.append("unexpected real connection"),
    )
    with pytest.raises(RuntimeError, match="Offline pytest cannot access"):
        BaseDatabaseWrapper.ensure_connection(wrapper)
    assert calls == []
