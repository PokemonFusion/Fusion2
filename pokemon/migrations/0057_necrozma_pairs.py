"""Native pair foundation; stop ambiguous legacy data before any schema writes."""

import django.db.models.deletion
import uuid
from django.db import migrations, models


def preflight(apps, schema_editor):
    """Lock the old owned/move tables and audit without modifying player assets."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("LOCK TABLE pokemon_ownedpokemon, pokemon_pokemonlearnedmove, "
            "pokemon_activemoveslot, pokemon_movesetslot IN SHARE ROW EXCLUSIVE MODE")
    from pokemon.services.necrozma_audit import require_necrozma_baseline

    require_necrozma_baseline(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('pokemon', '0056_onboarding_completion'),
    ]

    operations = [
        migrations.RunPython(preflight, migrations.RunPython.noop),
        migrations.CreateModel(
            name='NecrozmaCombination',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('base_species', models.CharField(default='Necrozma', max_length=50)),
                ('target_species', models.CharField(max_length=50)),
                ('policy_version', models.PositiveSmallIntegerField(default=1)),
                ('move_slot', models.PositiveSmallIntegerField()),
                ('displaced_pp', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('return_type', models.CharField(max_length=10)),
                ('return_slot', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='NecrozmaOperation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=10)),
                ('terms', models.JSONField()),
                ('state', models.CharField(default='pending', max_length=10)),
                ('expires_at', models.DateTimeField()),
                ('result', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='NecrozmaResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(max_length=50)),
                ('current_pp', models.PositiveSmallIntegerField()),
                ('policy_version', models.PositiveSmallIntegerField(default=1)),
            ],
        ),
        migrations.RemoveConstraint(
            model_name='pokemonplacement',
            name='pokemon_placement_shape',
        ),
        migrations.AlterField(
            model_name='pokemonplacement',
            name='location_type',
            field=models.CharField(choices=[('party', 'Party'), ('box', 'Box'), ('fusion', 'Fusion reservation'), ('daycare', 'Daycare reservation'), ('combined', 'Necrozma companion reservation')], db_index=True, max_length=10),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='companion',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='necrozma_companion_pair', to='pokemon.ownedpokemon'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='displaced_move',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pokemon.move'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='host',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='necrozma_host_pair', to='pokemon.ownedpokemon'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='moveset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pokemon.moveset'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='return_box',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pokemon.storagebox'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='necrozma_pairs', to='pokemon.userstorage'),
        ),
        migrations.AddField(
            model_name='pokemonplacement',
            name='combination',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='companion_placement', to='pokemon.necrozmacombination'),
        ),
        migrations.AddConstraint(
            model_name='pokemonplacement',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('box__isnull', True), ('box_position__isnull', True), ('combination__isnull', True), ('location_type', 'party'), ('slot__gte', 1), ('slot__isnull', False), ('slot__lte', 6)), models.Q(('box__isnull', False), ('box_position__gte', 1), ('box_position__isnull', False), ('combination__isnull', True), ('location_type', 'box'), ('slot__isnull', True)), models.Q(('box__isnull', True), ('box_position__isnull', True), ('combination__isnull', True), ('location_type__in', ('fusion', 'daycare')), ('slot__isnull', True)), models.Q(('box__isnull', True), ('box_position__isnull', True), ('combination__isnull', False), ('location_type', 'combined'), ('slot__isnull', True)), _connector='OR'), name='pokemon_placement_shape'),
        ),
        migrations.AddField(
            model_name='necrozmaoperation',
            name='storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='necrozma_operations', to='pokemon.userstorage'),
        ),
        migrations.AddField(
            model_name='necrozmaresource',
            name='host',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='necrozma_resources', to='pokemon.ownedpokemon'),
        ),
        migrations.AddField(
            model_name='necrozmacombination',
            name='resource',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='active_pair', to='pokemon.necrozmaresource'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaoperation',
            constraint=models.CheckConstraint(condition=models.Q(('action__in', ('combine', 'separate'))), name='necrozma_operation_action'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaoperation',
            constraint=models.CheckConstraint(condition=models.Q(('state__in', ('pending', 'completed', 'cancelled', 'expired'))), name='necrozma_operation_state'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaoperation',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('completed_at__isnull', False), ('state', 'completed')), models.Q(models.Q(('state', 'completed'), _negated=True), ('completed_at__isnull', True)), _connector='OR'), name='necrozma_completion_shape'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaresource',
            constraint=models.UniqueConstraint(fields=('host', 'source'), name='necrozma_host_source_unique'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaresource',
            constraint=models.CheckConstraint(condition=models.Q(('source__in', ('Sunsteel Strike', 'Moongeist Beam'))), name='necrozma_resource_source'),
        ),
        migrations.AddConstraint(
            model_name='necrozmaresource',
            constraint=models.CheckConstraint(condition=models.Q(('current_pp__lte', 8), ('policy_version', 1)), name='necrozma_resource_shape'),
        ),
        migrations.AddConstraint(
            model_name='necrozmacombination',
            constraint=models.CheckConstraint(condition=models.Q(('host', models.F('companion')), _negated=True), name='necrozma_distinct_sources'),
        ),
        migrations.AddConstraint(
            model_name='necrozmacombination',
            constraint=models.CheckConstraint(condition=models.Q(('base_species', 'Necrozma'), ('move_slot__gte', 1), ('move_slot__lte', 4), ('policy_version', 1), ('target_species__in', ('Necrozma-Dusk-Mane', 'Necrozma-Dawn-Wings'))), name='necrozma_pair_shape'),
        ),
        migrations.AddConstraint(
            model_name='necrozmacombination',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('displaced_move__isnull', True), ('displaced_pp__isnull', True)), models.Q(('displaced_move__isnull', False), ('displaced_pp__isnull', False)), _connector='OR'), name='necrozma_displaced_shape'),
        ),
        migrations.AddConstraint(
            model_name='necrozmacombination',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('return_box__isnull', True), ('return_slot__gte', 1), ('return_slot__isnull', False), ('return_slot__lte', 6), ('return_type', 'party')), models.Q(('return_slot__isnull', True), ('return_type', 'box')), _connector='OR'), name='necrozma_return_shape'),
        ),
    ]
