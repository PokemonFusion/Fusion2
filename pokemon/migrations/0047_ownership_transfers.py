"""Add durable transfer consent and shared reservations; no ownership rewrites."""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """Keep the existing Evennia history and add only PF2-owned tables."""

    dependencies = [
        ('objects', '0016_delete_exit'),
        ('pokemon', '0046_berry_bed'),
    ]

    operations = [
        migrations.CreateModel(
            name='OwnershipTransfer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('terms', models.JSONField()),
                ('approvals', models.JSONField(default=list)),
                ('state', models.CharField(db_index=True, default='pending', max_length=12)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('result', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('proposer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proposed_pokemon_transfers', to='objects.objectdb')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_pokemon_transfers', to='objects.objectdb')),
            ],
        ),
        migrations.CreateModel(
            name='PokemonReservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(max_length=12)),
                ('token', models.UUIDField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pokemon', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='system_reservation', to='pokemon.ownedpokemon')),
                ('storage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pokemon_reservations', to='pokemon.userstorage')),
                ('transfer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reservations', to='pokemon.ownershiptransfer')),
            ],
        ),
        migrations.AddConstraint(
            model_name='ownershiptransfer',
            constraint=models.CheckConstraint(condition=models.Q(('proposer', models.F('recipient')), _negated=True), name='transfer_distinct_characters'),
        ),
        migrations.AddConstraint(
            model_name='ownershiptransfer',
            constraint=models.CheckConstraint(condition=models.Q(('state__in', ('pending', 'completed', 'cancelled', 'expired'))), name='transfer_known_state'),
        ),
        migrations.AddConstraint(
            model_name='ownershiptransfer',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('completed_at__isnull', False), ('state', 'completed')), models.Q(models.Q(('state', 'completed'), _negated=True), ('completed_at__isnull', True)), _connector='OR'), name='transfer_completion_shape'),
        ),
        migrations.AddConstraint(
            model_name='pokemonreservation',
            constraint=models.CheckConstraint(condition=models.Q(('kind__in', ('trade', 'market', 'daycare', 'breeding'))), name='reservation_known_kind'),
        ),
        migrations.AddConstraint(
            model_name='pokemonreservation',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'trade'), ('transfer__isnull', False)), models.Q(models.Q(('kind', 'trade'), _negated=True), ('transfer__isnull', True)), _connector='OR'), name='reservation_transfer_shape'),
        ),
    ]
