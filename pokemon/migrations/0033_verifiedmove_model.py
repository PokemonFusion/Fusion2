from django.db import migrations, models


class Migration(migrations.Migration):
    """Create table for tracking verified moves and drop old field."""

    dependencies = [
        ("pokemon", "0032_move_verified"),
    ]

    operations = [
        migrations.CreateModel(
            name="VerifiedMove",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=50, unique=True)),
                ("verified", models.BooleanField(default=False)),
            ],
        ),
        migrations.RemoveField(
            model_name="move",
            name="verified",
        ),
    ]

