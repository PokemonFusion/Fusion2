from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0017_add_template_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_name", models.CharField(max_length=100)),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory",
                        to="pokemon.trainer",
                    ),
                ),
            ],
            options={
                "unique_together": {("owner", "item_name")},
            },
        ),
    ]
