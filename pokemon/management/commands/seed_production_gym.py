"""Install the production Tempo strategy gym after an approved schema update."""

from django.core.management.base import BaseCommand

from pokemon.services.production_gym_seed import GYM_KEY, seed_production_gym_content


class Command(BaseCommand):
    """Create/update one owned gym without resetting progression or victories."""

    help = "Install or update the production Tempo Gym, preserving existing badges and reward receipts."

    def handle(self, *args, **options):
        """Publish stable content identifiers and the ordinary-player entry point."""
        result = seed_production_gym_content()
        self.stdout.write(self.style.SUCCESS(f"Tempo Gym content version {result.version} installed."))
        self.stdout.write(f"Profile: {result.profile.pk}; player command: +gym challenge {GYM_KEY}")
