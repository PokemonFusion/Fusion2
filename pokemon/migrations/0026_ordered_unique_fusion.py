from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ("pokemon", "0025_sync_ownedpokemon_levels"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="pokemonfusion",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="pokemonfusion",
            constraint=models.UniqueConstraint(
                fields=["parent_a", "parent_b"],
                name="unique_fusion_parents",
            ),
        ),
        migrations.AddConstraint(
            model_name="pokemonfusion",
            constraint=models.CheckConstraint(
                check=Q(parent_a__lt=F("parent_b")),
                name="ordered_fusion_parents",
            ),
        ),
    ]
