"""Database models for player-owned Pokémon and trainers."""

from evennia import DefaultObject
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.objects.models import ObjectDB
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
import uuid


class Gender(models.TextChoices):
    """Allowed Pokémon genders."""

    MALE = "M", "Male"
    FEMALE = "F", "Female"
    NONE = "N", "None"


class Nature(models.TextChoices):
    """Available Pokémon natures."""

    HARDY = "Hardy", "Hardy"
    LONELY = "Lonely", "Lonely"
    BRAVE = "Brave", "Brave"
    ADAMANT = "Adamant", "Adamant"
    NAUGHTY = "Naughty", "Naughty"
    BOLD = "Bold", "Bold"
    DOCILE = "Docile", "Docile"
    RELAXED = "Relaxed", "Relaxed"
    IMPISH = "Impish", "Impish"
    LAX = "Lax", "Lax"
    TIMID = "Timid", "Timid"
    HASTY = "Hasty", "Hasty"
    SERIOUS = "Serious", "Serious"
    JOLLY = "Jolly", "Jolly"
    NAIVE = "Naive", "Naive"
    MODEST = "Modest", "Modest"
    MILD = "Mild", "Mild"
    QUIET = "Quiet", "Quiet"
    BASHFUL = "Bashful", "Bashful"
    RASH = "Rash", "Rash"
    CALM = "Calm", "Calm"
    GENTLE = "Gentle", "Gentle"
    SASSY = "Sassy", "Sassy"
    CAREFUL = "Careful", "Careful"
    QUIRKY = "Quirky", "Quirky"


class Move(models.Model):
    """A normalized move entry."""

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class SpeciesEntry(models.Model):
    """Pokédex species entry."""

    name = models.CharField(max_length=50, unique=True)
    dex_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    def __str__(self) -> str:
        return self.name


class BasePokemon(models.Model):
    """Abstract base model for Pokémon."""

    species = models.CharField(max_length=50, default="")
    level = models.PositiveSmallIntegerField(default=1)
    ability = models.CharField(max_length=50, blank=True)
    nature = models.CharField(max_length=20, blank=True, choices=Nature.choices)
    gender = models.CharField(max_length=10, blank=True, choices=Gender.choices)
    ivs = ArrayField(models.PositiveSmallIntegerField(), size=6, default=list)
    evs = ArrayField(models.PositiveSmallIntegerField(), size=6, default=list)
    held_item = models.CharField(max_length=50, blank=True)

    class Meta:
        abstract = True


class Pokemon(BasePokemon):
    """Simple Pokémon instance used for starter and storage boxes."""

    type_ = models.CharField(max_length=255)
    data = models.JSONField(default=dict, blank=True)
    temporary = models.BooleanField(default=False, db_index=True)
    trainer = models.ForeignKey(
        "Trainer",
        on_delete=models.CASCADE,
        related_name="owned_pokemon",
        null=True,
        blank=True,
        db_index=True,
    )

    def __str__(self):
        owner = f" owned by {self.trainer.user.key}" if self.trainer else ""
        return (
            f"{self.id}: {self.species} (Level {self.level}, Type: {self.type_}, "
            f"Ability: {self.ability})" + owner
        )


class UserStorage(models.Model):
    user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE, db_index=True)
    active_pokemon = models.ManyToManyField(
        "OwnedPokemon",
        related_name="active_users",
        through="ActivePokemonSlot",
    )
    stored_pokemon = models.ManyToManyField(
        "OwnedPokemon", related_name="stored_users", blank=True
    )

    def add_active_pokemon(self, pokemon, slot: int | None = None) -> None:
        """Add a Pokémon to the active party in the given slot."""
        existing = set(self.active_slots.values_list("slot", flat=True))
        if len(existing) >= 6:
            raise ValueError("Party already has six Pokémon.")
        if slot is None:
            for i in range(1, 7):
                if i not in existing:
                    slot = i
                    break
        if slot is None:
            raise ValueError("No available slot for Pokémon.")
        ActivePokemonSlot.objects.create(storage=self, pokemon=pokemon, slot=slot)

    def remove_active_pokemon(self, pokemon) -> None:
        """Remove a Pokémon from the active party."""
        ActivePokemonSlot.objects.filter(storage=self, pokemon=pokemon).delete()

    def get_party(self):
        """Return active Pokémon ordered by slot."""
        qs = self.active_pokemon.all()
        if hasattr(qs, "order_by"):
            qs = qs.order_by("active_slots__slot")
        return list(qs)


class StorageBox(models.Model):
    """A box of Pokémon stored for a particular user."""

    storage = models.ForeignKey(
        UserStorage, on_delete=models.CASCADE, related_name="boxes", db_index=True
    )
    name = models.CharField(max_length=255)
    pokemon = models.ManyToManyField("OwnedPokemon", related_name="boxes", blank=True)

    def __str__(self):
        return f"{self.name} (Owner: {self.storage.user.key})"


class OwnedPokemon(SharedMemoryModel, BasePokemon):
    """Persistent data for a player's Pokémon."""

    unique_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    trainer = models.ForeignKey(
        "pokemon.Trainer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )
    is_wild = models.BooleanField(default=False, db_index=True)
    ai_trainer = models.ForeignKey(
        "NPCTrainer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="wild_or_ai_pokemon",
    )
    is_template = models.BooleanField(default=False, db_index=True)
    is_battle_instance = models.BooleanField(default=False, db_index=True)
    nickname = models.CharField(max_length=50, blank=True)
    is_shiny = models.BooleanField(default=False, db_index=True)
    met_location = models.CharField(max_length=100, blank=True)
    met_level = models.PositiveSmallIntegerField(null=True, blank=True)
    met_date = models.DateTimeField(null=True, blank=True)
    obtained_method = models.CharField(max_length=50, blank=True)
    original_trainer = models.ForeignKey(
        "Trainer",
        on_delete=models.SET_NULL,
        null=True,
        related_name="original_pokemon",
    )
    original_trainer_name = models.CharField(max_length=100, blank=True)
    is_egg = models.BooleanField(default=False)
    hatch_steps = models.PositiveIntegerField(null=True, blank=True)
    friendship = models.PositiveSmallIntegerField(default=70)
    flags = ArrayField(models.CharField(max_length=50), blank=True, default=list)
    tera_type = models.CharField(max_length=20, blank=True)
    current_hp = models.PositiveIntegerField(default=0)
    total_exp = models.BigIntegerField(default=0)
    learned_moves = models.ManyToManyField(Move, related_name="owners")
    active_moveset = models.ManyToManyField(
        Move,
        through="ActiveMoveslot",
        related_name="active_on",
    )
    movesets = models.JSONField(blank=True, default=list)
    active_moveset_index = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.nickname or self.species} ({self.unique_id})"

    @property
    def name(self) -> str:
        """Return nickname if set, otherwise the species."""
        return self.nickname or self.species

    @property
    def level(self) -> int:
        """Return the Pokémon's level derived from experience."""
        from .stats import level_for_exp

        return level_for_exp(self.total_exp)

    def set_level(self, level: int) -> None:
        """Set ``total_exp`` based on the desired level."""
        from .stats import exp_for_level

        self.total_exp = exp_for_level(level)

    def delete_if_wild(self) -> None:
        """Delete this Pokémon if it is an uncaptured wild encounter."""
        if self.is_wild and self.trainer is None and self.ai_trainer is None:
            self.delete()

    # ------------------------------------------------------------------
    # Move management helpers
    # ------------------------------------------------------------------
    def learn_level_up_moves(self) -> None:
        """Learn all level-up moves up to the current level."""
        from .generation import get_valid_moves

        moves = get_valid_moves(self.species, self.level)
        objs = [
            m
            for m in Move.objects.filter(name__in=moves)
        ]
        if objs:
            self.learned_moves.add(*objs)
        if not self.movesets:
            self.movesets = [moves[:4]]
            self.active_moveset_index = 0
        self.save()
        self.apply_active_moveset()

    def apply_active_moveset(self) -> None:
        """Replace active move slots with the currently selected moveset."""
        sets = self.movesets or []
        if not sets:
            return
        moves = sets[self.active_moveset_index] if self.active_moveset_index < len(sets) else []
        self.activemoveslot_set.all().delete()
        for idx, name in enumerate(moves[:4], 1):
            mv = Move.objects.filter(name__iexact=name).first()
            if mv:
                self.activemoveslot_set.create(move=mv, slot=idx)

    def swap_moveset(self, index: int) -> None:
        """Switch to the moveset at ``index`` (0-based)."""
        if self.movesets is None:
            self.movesets = []
        if index < 0 or index >= len(self.movesets):
            return
        self.active_moveset_index = index
        self.save()
        self.apply_active_moveset()


class ActiveMoveslot(models.Model):
    """Mapping of active move slots for a Pokémon."""

    pokemon = models.ForeignKey(OwnedPokemon, on_delete=models.CASCADE, db_index=True)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, db_index=True)
    slot = models.PositiveSmallIntegerField(db_index=True)
    current_pp = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pokemon", "slot")

    def __str__(self):
        return f"{self.pokemon} -> {self.move} [{self.slot}]"


class ActivePokemonSlot(models.Model):
    """Mapping of active Pokémon party slots."""

    storage = models.ForeignKey(
        "UserStorage", on_delete=models.CASCADE, related_name="active_slots", db_index=True
    )
    pokemon = models.ForeignKey(
        OwnedPokemon, on_delete=models.CASCADE, related_name="active_slots", db_index=True
    )
    slot = models.PositiveSmallIntegerField(db_index=True)

    class Meta:
        unique_together = (
            ("storage", "slot"),
            ("storage", "pokemon"),
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.slot < 1 or self.slot > 6:
            raise ValidationError("Slot must be between 1 and 6.")
        count = ActivePokemonSlot.objects.filter(storage=self.storage).exclude(pk=self.pk).count()
        if count >= 6 and not ActivePokemonSlot.objects.filter(pk=self.pk).exists():
            raise ValidationError("Party already has six Pokémon.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class BattleSlot(SharedMemoryModel):
    """Ephemeral per-battle state for a Pokémon."""

    pokemon = models.OneToOneField(
        OwnedPokemon, on_delete=models.CASCADE, primary_key=True
    )
    battle_id = models.PositiveIntegerField(db_index=True)
    battle_team = models.PositiveSmallIntegerField(db_index=True)
    current_hp = models.PositiveIntegerField()
    status = models.CharField(max_length=20)
    fainted = models.BooleanField(default=False)

    def __str__(self):
        return f"Battle {self.battle_id}: {self.pokemon}"


class GymBadge(models.Model):
    """A gym badge rewarded for defeating a particular gym."""

    name = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.region})"


class Trainer(models.Model):
    """Model storing trainer specific stats for a Character."""

    user = models.OneToOneField(
        ObjectDB, on_delete=models.CASCADE, related_name="trainer", db_index=True
    )
    trainer_number = models.PositiveIntegerField(unique=True)
    money = models.PositiveIntegerField(default=0)
    seen_pokemon = models.ManyToManyField(
        SpeciesEntry, related_name="seen_by_trainers", blank=True
    )
    badges = models.ManyToManyField(GymBadge, related_name="trainers", blank=True)

    def __str__(self):
        return f"Trainer {self.trainer_number} for {self.user.key}"

    # Helper methods
    def add_badge(self, badge: GymBadge) -> None:
        self.badges.add(badge)

    def add_money(self, amount: int) -> None:
        self.money += amount
        self.save()

    def spend_money(self, amount: int) -> bool:
        """Remove money if available and return success."""
        if self.money < amount:
            return False
        self.money -= amount
        self.save()
        return True

    def log_seen_pokemon(self, species: str | int) -> None:
        """Record that the trainer has seen the given species."""
        if isinstance(species, int):
            entry = SpeciesEntry.objects.filter(pk=species).first()
        else:
            entry = SpeciesEntry.objects.filter(name__iexact=str(species)).first()
        if entry:
            self.seen_pokemon.add(entry)


class NPCTrainer(models.Model):
    """Static NPC trainer such as gym leaders."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class InventoryEntry(models.Model):
    """A quantity of a particular item owned by a trainer."""

    owner = models.ForeignKey(
        "pokemon.Trainer", on_delete=models.CASCADE, related_name="inventory"
    )
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("owner", "item_name")

    def __str__(self) -> str:
        return f"{self.item_name} x{self.quantity}"


class PokemonFusion(models.Model):
    """Record a fusion between two Pokémon using their unique IDs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_a = models.ForeignKey(
        OwnedPokemon,
        on_delete=models.CASCADE,
        related_name="fusion_parent_a",
    )
    parent_b = models.ForeignKey(
        OwnedPokemon,
        on_delete=models.CASCADE,
        related_name="fusion_parent_b",
    )
    result = models.OneToOneField(
        OwnedPokemon,
        on_delete=models.CASCADE,
        related_name="fusion_result",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("parent_a", "parent_b")

    def __str__(self) -> str:
        return f"Fusion of {self.parent_a} + {self.parent_b} -> {self.result}"


