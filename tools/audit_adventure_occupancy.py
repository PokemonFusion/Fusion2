"""Read-only preflight for the Adventure occupancy migration; never repairs data."""

import importlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")


def main():
    """Report exact claims/conflicts before any separately approved migration."""
    import django
    from django.conf import settings

    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise RuntimeError("Configure the intended PostgreSQL database before running this read-only audit.")
    django.setup()
    from django.apps import apps
    from django.db import connection, transaction

    migration = importlib.import_module("pokemon.migrations.0060_adventure_occupancy")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
        report = migration.inspect_legacy_occupancy(apps, "default")
    print(json.dumps(report, indent=2))
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
