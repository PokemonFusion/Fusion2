"""Confine standalone integration checks to one disposable PostgreSQL schema."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class IsolatedPostgres:
    """Use an explicit test DSN and refuse ORM connections outside our schema."""

    def __init__(self):
        self.dsn = os.environ.get("PF2_TEST_POSTGRES_DSN")
        if not self.dsn:
            raise RuntimeError("Set PF2_TEST_POSTGRES_DSN explicitly; game database settings are never a fallback.")
        self.schema = "pf2_recovery_test_" + uuid4().hex
        self.options = f"-c search_path={self.schema} -c lock_timeout=10000 -c statement_timeout=30000"
        self.admin = None
        self.connection_guard = None

    def __enter__(self):
        """Create an empty schema and configure Django before loading game apps."""
        self.admin = psycopg2.connect(self.dsn, connect_timeout=5)
        self.admin.autocommit = True
        try:
            with self.admin.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
            self._configure_django()
        except BaseException:
            self.close()
            raise
        return self

    def _configure_django(self):
        """Override every Django database alias and check each new connection."""
        import django
        from django.conf import settings
        from django.db.backends.base.base import BaseDatabaseWrapper

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        params = parse_dsn(self.dsn)
        settings.DATABASES = {"default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": params.get("dbname", "postgres"),
            "USER": params.get("user", ""),
            "PASSWORD": params.get("password", ""),
            "HOST": params.get("host", ""),
            "PORT": params.get("port", ""),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"options": self.options, "connect_timeout": 5,
                        **({"sslmode": params["sslmode"]} if "sslmode" in params else {})},
        }}
        original_connect = BaseDatabaseWrapper.connect

        def connect_isolated(connection):
            """Reject accidental game connections, including worker threads."""
            if (connection.vendor != "postgresql"
                    or connection.settings_dict.get("OPTIONS", {}).get("options") != self.options):
                raise RuntimeError("Integration checks may only connect to their disposable PostgreSQL schema.")
            original_connect(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_schema()")
                if cursor.fetchone()[0] != self.schema:
                    connection.close()
                    raise RuntimeError("Disposable PostgreSQL schema was not selected.")

        self.connection_guard = patch.object(BaseDatabaseWrapper, "connect", connect_isolated)
        self.connection_guard.start()
        django.setup()

    def create_model_tables(self):
        """Build production model tables directly without applying migrations."""
        from django.apps import apps
        from django.db import connection

        with connection.schema_editor() as editor:
            for model in apps.get_models():
                editor.create_model(model)

    def close(self):
        """Close ORM connections and drop only this instance's generated schema."""
        from django.db import connections

        try:
            if self.connection_guard is not None:
                connections.close_all()
                self.connection_guard.stop()
                self.connection_guard = None
        finally:
            if self.admin is not None:
                try:
                    with self.admin.cursor() as cursor:
                        cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
                finally:
                    self.admin.close()
                    self.admin = None

    def __exit__(self, exc_type, exc_value, traceback):
        """Always remove the disposable schema, including after failed checks."""
        self.close()
