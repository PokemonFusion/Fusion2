from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0002_pokemon_trainer"),
    ]

    operations = [
        migrations.CreateModel(
            name="GymBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("region", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name="trainer",
            name="badge_count",
        ),
        migrations.AddField(
            model_name="trainer",
            name="badges",
            field=models.ManyToManyField(blank=True, related_name="trainers", to="pokemon.gymbadge"),
        ),
    ]
