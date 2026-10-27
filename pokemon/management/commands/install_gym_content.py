"""Validate or install a bounded authored gym through the shared installer."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from pokemon.services.gym_content import GymContent, install_gym_content


class Command(BaseCommand):
    """Keep author diagnostics explicit; dry validation never allocates content."""

    help = 'Validate or install one versioned gym JSON file without resetting earned badges or victory receipts.'

    def add_arguments(self, parser):
        """Require an exact content path and offer a read-only validation mode."""
        parser.add_argument('definition')
        parser.add_argument('--check', action='store_true', help='Validate only; no database changes.')

    def handle(self, *args, **options):
        """Report a stable identity/version/digest or a concrete author error."""
        try:
            path = Path(options['definition'])
            if path.stat().st_size > 262144:
                raise ValueError('Gym JSON must be at most 256 KiB.')
            content = GymContent.parse(json.loads(path.read_text(encoding='utf-8')))
            data = content.definition
            if not options['check']:
                profile = install_gym_content(data)
                self.stdout.write(f'Installed profile {profile.pk}. Player route: +gym check {profile.gym_key}')
            self.stdout.write(self.style.SUCCESS(f"Valid {data['league_key']}:{data['gym_key']} v{data['version']} sha256 {content.digest}"))
        except (OSError, ValueError, TypeError) as error:
            raise CommandError(f'Gym content rejected: {error}') from error
        except IntegrityError as error:
            raise CommandError('Gym identity conflicts with existing content. Review leader, gym and badge keys; nothing was installed.') from error
