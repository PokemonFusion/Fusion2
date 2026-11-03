"""Check project migrations against the deployed and local Evennia histories."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("profile", ("installed", "pf2-dev-6.0"))
def test_framework_migration_graph(profile):
    """Require no unavailable framework nodes when constructing the full graph."""
    root = Path(__file__).resolve().parents[2]
    script = r'''
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.settings'
import django
django.setup()
from django.db.migrations.loader import MigrationLoader

original = MigrationLoader.load_disk
def deployed_history(loader):
    """Model PF2-Dev's inspected ObjectDB migration files through 0013."""
    original(loader)
    for key in list(loader.disk_migrations):
        if key[0] == 'objects' and int(key[1].split('_', 1)[0]) > 13:
            del loader.disk_migrations[key]

if sys.argv[1] == 'pf2-dev-6.0':
    MigrationLoader.load_disk = deployed_history
loader = MigrationLoader(None)
target = [('pokemon', '0058_necrozma_integrity')]
state = loader.project_state(target)
for model, field in [('OwnershipTransfer', 'proposer'),
                     ('MarketListing', 'seller'),
                     ('OnboardingCompletion', 'character')]:
    relation = state.apps.get_model('pokemon', model)._meta.get_field(field)
    assert relation.remote_field.model._meta.label == 'objects.ObjectDB'
assert ('pokemon', '0058_necrozma_integrity') in loader.graph.nodes
print('FRAMEWORK_MIGRATION_GRAPH_OK', sys.argv[1])
'''
    environment = os.environ.copy()
    environment.pop("PF2_NO_EVENNIA", None)
    environment.pop("PF2_TEST_POSTGRES_DSN", None)
    environment.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-B", "-c", script, profile],
                            cwd=root, env=environment, capture_output=True,
                            text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
