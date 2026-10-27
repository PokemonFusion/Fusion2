"""Persist one initial character grant independently of later creature custody."""
import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Keep legacy progress unchanged; new completions receive durable receipts."""

    dependencies = [
        ('pokemon', '0055_gym_content'),
        ('objects', '0013_defaultobject_alter_objectdb_id_defaultcharacter_and_more'),
    ]
    operations = [migrations.CreateModel(name='OnboardingCompletion', fields=[
        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ('origin_character_id', models.BigIntegerField(unique=True)),
        ('pokemon_uuid', models.UUIDField(unique=True)),
        ('kind', models.CharField(choices=[('human', 'Human'), ('fusion', 'Fusion')], max_length=10)),
        ('choices', models.JSONField(default=dict)), ('receipt', models.JSONField(default=dict)),
        ('completed_at', models.DateTimeField(auto_now_add=True)),
        ('character', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='onboarding_completion', to='objects.objectdb')),
        ('pokemon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='onboarding_grants', to='pokemon.ownedpokemon')),
    ])]
