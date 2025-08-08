"""Database models for player-owned Pokémon and trainers."""

from evennia import DefaultObject
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.objects.models import ObjectDB
from django.db import models

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from .stats import EV_LIMIT, STAT_EV_LIMIT
import uuid
import math

# Maximum multiplier to calculate PP when fully boosted (e.g. PP Max or 3 PP Ups)
MAX_PP_MULTIPLIER = 1.6


def validate_ivs(value):
    """Validate that IV list has six integers between 0 and 31."""
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("IVs must contain six integers.")
    for v in value:
        if not isinstance(v, int) or v < 0 or v > 31:
            raise ValidationError("IV values must be between 0 and 31.")


def validate_evs(value):
    """Validate that EV list has six integers in allowed ranges."""
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("EVs must contain six integers.")
    for v in value:
        if not isinstance(v, int) or v < 0 or v > STAT_EV_LIMIT:
            raise ValidationError(
                f"EV values must be between 0 and {STAT_EV_LIMIT}."
            )
    if sum(value) > EV_LIMIT:
        raise ValidationError(f"Total EVs cannot exceed {EV_LIMIT}.")


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
    ivs = ArrayField(
        models.PositiveSmallIntegerField(),
        size=6,
        default=list,
        validators=[validate_ivs],
    )
    evs = ArrayField(
        models.PositiveSmallIntegerField(),
        size=6,
        default=list,
        validators=[validate_evs],
    )
    held_item = models.CharField(max_length=50, blank=True)

    def clean(self):
        super().clean()
        validate_ivs(self.ivs)
        validate_evs(self.evs)

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # Type helpers
    # ------------------------------------------------------------------
    def _lookup_species_types(self) -> list[str]:
        """Return a list of types for this Pokémon's species.

        This method is a thin wrapper around whatever Pokédex data source the
        project provides.  It is defined on the model so that subclasses can
        easily override the lookup behaviour if they need to.
        """

        species_name = self.species
        try:  # pragma: no cover - data source may be unavailable in tests
            # Example if you have a POKEDEX dict somewhere:
            # from pokemon.dex import POKEDEX
            # entry = POKEDEX.get(species_name.lower())
            # return [t.title() for t in entry.get("types", [])] if entry else []
            pass
        except Exception:
            pass
        return []

    @property
    def types(self) -> list[str]:
        """Return this Pokémon's type or types as a list of names."""

        override = getattr(self, "_types_override", None)
        if override is not None:
            return override

        ts = self._lookup_species_types()
        if ts:
            return ts

        data = getattr(self, "data", {}) or {}
        t_from_json = data.get("type") or data.get("types")
        if isinstance(t_from_json, str):
            return [
                p.strip().title()
                for p in t_from_json.replace(",", "/").split("/")
                if p.strip()
            ]
        if isinstance(t_from_json, (list, tuple)):
            return [str(p).title() for p in t_from_json if p]

        return []

    @types.setter
    def types(self, value: list[str]) -> None:
        """Allow manually overriding the computed types."""

        self._types_override = value

    @property
    def primary_type(self) -> str | None:
        """Return the first type if available."""

        return self.types[0] if self.types else None

    @property
    def secondary_type(self) -> str | None:
        """Return the second type if present."""

        return self.types[1] if len(self.types) > 1 else None


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


def ensure_boxes(storage: UserStorage, count: int = 8) -> UserStorage:
    """Ensure that a storage container has at least ``count`` boxes.

    Parameters
    ----------
    storage
        The storage instance to populate.
    count
        Number of boxes to ensure. Defaults to eight.

    Returns
    -------
    UserStorage
        The storage instance, populated with boxes if necessary.
    """
    existing = storage.boxes.count()
    for i in range(existing + 1, count + 1):
        StorageBox.objects.create(storage=storage, name=f"Box {i}")
    return storage


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
    learned_moves = models.ManyToManyField(
        Move,
        related_name="owners",
        through="PokemonLearnedMove",
    )
    active_moveset = models.ForeignKey(
        "Moveset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_for",
    )

    def __str__(self):
        return f"{self.nickname or self.species} ({self.unique_id})"

    @property
    def name(self) -> str:
        """Return nickname if set, otherwise the species."""
        return self.nickname or self.species

    @property
    def computed_level(self) -> int:
        """Return the Pokémon's level derived from its stored experience."""
        from .stats import level_for_exp

        return level_for_exp(self.total_exp)

    @property
    def active_moves(self):
        """Return active moves ordered by slot."""
        return [s.move for s in self.activemoveslot_set.order_by("slot")]

    def set_level(self, level: int) -> None:
        """Set ``total_exp`` and persist the corresponding level."""
        from .stats import exp_for_level

        self.total_exp = exp_for_level(level)
        self.level = level
        try:
            from pokemon.utils.pokemon_helpers import refresh_stats

            refresh_stats(self)
        except Exception:  # pragma: no cover - helper may be unavailable in tests
            pass

    def delete_if_wild(self) -> None:
        """Delete this Pokémon if it is an uncaptured wild encounter."""
        if self.is_wild and self.trainer is None and self.ai_trainer is None:
            self.delete()

    # ------------------------------------------------------------------
    # Move management helpers
    # ------------------------------------------------------------------
    def learn_level_up_moves(self, *, caller=None, prompt: bool = False) -> None:
        """Learn all level-up moves up to the current level.

        If ``caller`` is provided and ``prompt`` is True, the caller will be
        asked about replacing moves for any newly learned techniques.
        """
        from .generation import get_valid_moves
        from pokemon.utils.move_learning import learn_move

        moves = get_valid_moves(self.species, self.computed_level)
        known = {m.name.lower() for m in self.learned_moves.all()}
        for mv in moves:
            if mv.lower() not in known:
                learn_move(self, mv, caller=caller, prompt=prompt)
                known.add(mv.lower())

        if not self.movesets.exists():
            ms = self.movesets.create(index=0)
            for i, mv in enumerate(moves[:4], 1):
                move_obj, _ = Move.objects.get_or_create(name=mv.capitalize())
                ms.slots.create(move=move_obj, slot=i)
            self.active_moveset = ms
            self.save()
            self.apply_active_moveset()

    def apply_active_moveset(self) -> None:
        """Replace active move slots with the currently selected moveset."""
        ms = self.active_moveset
        if not ms:
            return
        slots = list(ms.slots.order_by("slot"))
        self.activemoveslot_set.all().delete()
        for slot_obj in slots[:4]:
            mv = slot_obj.move
            slot = self.activemoveslot_set.create(move=mv, slot=slot_obj.slot)
            try:
                from .dex import MOVEDEX
            except Exception:  # pragma: no cover - MOVEDEX may be missing in tests
                MOVEDEX = {}
            base_pp = MOVEDEX.get(mv.name.lower(), {}).get("pp")
            boost_obj = self.pp_boosts.filter(move=mv).first()
            bonus = boost_obj.bonus_pp if boost_obj else 0
            if base_pp is not None:
                slot.current_pp = base_pp + bonus
                slot.save()

    def swap_moveset(self, index: int) -> None:
        """Switch to the moveset at ``index`` (0-based)."""
        ms = self.movesets.filter(index=index).first()
        if not ms:
            return
        self.active_moveset = ms
        self.save()
        self.apply_active_moveset()

    def get_max_pp(self, move_name: str) -> int | None:
        """Return the maximum PP for ``move_name`` accounting for boosts."""
        try:
            from .dex import MOVEDEX
        except Exception:  # pragma: no cover - fallback for tests
            MOVEDEX = {}
        base_pp = MOVEDEX.get(move_name.lower(), {}).get("pp")
        if base_pp is None:
            return None
        boost = self.pp_boosts.filter(move__name__iexact=move_name).first()
        bonus = boost.bonus_pp if boost else 0
        return base_pp + bonus

    # ------------------------------------------------------------------
    # PP boosting helpers
    # ------------------------------------------------------------------
    def _apply_pp_boost(self, move_name: str, full: bool = False) -> bool:
        """Apply a PP Up or PP Max boost to ``move_name``."""
        try:
            from .dex import MOVEDEX
        except Exception:  # pragma: no cover - fallback for tests
            MOVEDEX = {}
        base_pp = MOVEDEX.get(move_name.lower(), {}).get("pp")
        if base_pp is None:
            return False
        move = Move.objects.filter(name__iexact=move_name).first()
        if not move:
            return False
        boost_obj, _ = self.pp_boosts.get_or_create(move=move, defaults={"bonus_pp": 0})
        max_bonus = math.floor(base_pp * MAX_PP_MULTIPLIER) - base_pp
        current = boost_obj.bonus_pp
        if current >= max_bonus:
            return False
        if full:
            new_bonus = max_bonus
        else:
            step = max(1, base_pp // 5)
            new_bonus = min(current + step, max_bonus)
        delta = new_bonus - current
        boost_obj.bonus_pp = new_bonus
        boost_obj.save()
        for slot in self.activemoveslot_set.filter(move=move):
            if slot.current_pp is not None:
                slot.current_pp = min(slot.current_pp + delta, base_pp + new_bonus)
                slot.save()
        return True

    def apply_pp_up(self, move_name: str) -> bool:
        """Apply a PP Up to ``move_name`` and return success."""
        return self._apply_pp_boost(move_name, full=False)

    def apply_pp_max(self, move_name: str) -> bool:
        """Apply a PP Max to ``move_name`` and return success."""
        return self._apply_pp_boost(move_name, full=True)

    def heal(self) -> None:
        """Fully restore HP, clear status, and reset PP."""
        from pokemon.utils.pokemon_helpers import get_max_hp

        max_hp = get_max_hp(self)
        if hasattr(self, "current_hp"):
            self.current_hp = max_hp
        if hasattr(self, "status"):
            self.status = ""
        try:
            from pokemon.dex import MOVEDEX
        except Exception:  # pragma: no cover - tests may not provide dex
            MOVEDEX = {}

        bonuses = {}
        manager = getattr(self, "pp_boosts", None)
        if manager is not None:
            try:
                iterable = manager.all()
            except Exception:  # pragma: no cover
                iterable = manager
            for b in iterable:
                bonuses[getattr(b.move, "name", "").lower()] = getattr(b, "bonus_pp", 0)

        slots = getattr(self, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:  # pragma: no cover
                slot_iter = slots
        else:
            slot_iter = []

        updated = []
        for slot in slot_iter:
            base = MOVEDEX.get(slot.move.name.lower(), {}).get("pp")
            bonus = bonuses.get(slot.move.name.lower(), 0)
            if base is not None:
                slot.current_pp = base + bonus
                updated.append(slot)

        if updated:
            try:
                slots.bulk_update(updated, ["current_pp"])
            except Exception:  # pragma: no cover - fallback for stubs
                for slot in updated:
                    try:
                        slot.save()
                    except Exception:
                        pass

        try:
            self.save()
        except Exception:
            pass


class PokemonLearnedMove(models.Model):
    """Through table linking a Pokémon to a learned move."""

    pokemon = models.ForeignKey(
        "OwnedPokemon",
        on_delete=models.CASCADE,
        db_index=True,
    )
    move = models.ForeignKey(Move, on_delete=models.CASCADE, db_index=True)

    class Meta:
        unique_together = ("pokemon", "move")
        indexes = [
            models.Index(
                fields=["pokemon"], name="pokemonlearnedmove_pokemon_idx"
            ),
            models.Index(fields=["move"], name="pokemonlearnedmove_move_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.pokemon} knows {self.move}"


class Moveset(models.Model):
    """A set of up to four moves belonging to a Pokémon."""

    pokemon = models.ForeignKey(
        "OwnedPokemon", on_delete=models.CASCADE, related_name="movesets"
    )
    index = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pokemon", "index"],
                name="unique_moveset_index",
            ),
            models.CheckConstraint(
                check=models.Q(index__gte=0, index__lte=3),
                name="moveset_index_range",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.pokemon} set {self.index}"

    def clean(self):
        """Validate moveset count per Pokémon."""
        super().clean()
        if self.pokemon and self.pokemon.movesets.exclude(pk=self.pk).count() >= 4:
            raise ValidationError("A Pokémon may only have four movesets.")


class MovesetSlot(models.Model):
    """A single move within a moveset."""

    moveset = models.ForeignKey(
        Moveset, on_delete=models.CASCADE, related_name="slots"
    )
    move = models.ForeignKey(Move, on_delete=models.CASCADE)
    slot = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["moveset", "slot"],
                name="unique_moveset_slot",
            ),
            models.CheckConstraint(
                check=models.Q(slot__gte=1, slot__lte=4),
                name="movesetslot_slot_range",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.moveset} [{self.slot}] -> {self.move}"


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

    # ------------------------------------------------------------------
    # Inventory helpers
    # ------------------------------------------------------------------
    def add_item(self, item_name: str, amount: int = 1) -> None:
        """Add ``amount`` of ``item_name`` to this trainer's inventory."""
        item_name = item_name.lower()
        entry, _ = InventoryEntry.objects.get_or_create(
            owner=self, item_name=item_name, defaults={"quantity": 0}
        )
        entry.quantity += amount
        entry.save()

    def remove_item(self, item_name: str, amount: int = 1) -> bool:
        """Remove ``amount`` of ``item_name`` and return success."""
        item_name = item_name.lower()
        try:
            entry = InventoryEntry.objects.get(owner=self, item_name=item_name)
        except InventoryEntry.DoesNotExist:
            return False
        if entry.quantity < amount:
            return False
        entry.quantity -= amount
        if entry.quantity <= 0:
            entry.delete()
        else:
            entry.save()
        return True

    def list_inventory(self):
        """Return ``InventoryEntry`` objects owned by this trainer."""
        return InventoryEntry.objects.filter(owner=self).order_by("item_name")


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
    """Record a fusion between a trainer and a Pokémon."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name="pokemon_fusions",
        null=True,
        blank=True,
    )
    pokemon = models.ForeignKey(
        OwnedPokemon,
        on_delete=models.CASCADE,
        related_name="trainer_fusions",
        null=True,
        blank=True,
    )
    result = models.OneToOneField(
        OwnedPokemon,
        on_delete=models.CASCADE,
        related_name="fusion_result",
    )
    permanent = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trainer", "pokemon"],
                name="unique_trainer_pokemon_fusion",
            )
        ]

    def __str__(self) -> str:
        return f"Fusion of {self.trainer} + {self.pokemon} -> {self.result}"


class MovePPBoost(models.Model):
    """Store extra PP added to a move for a specific Pokémon."""

    pokemon = models.ForeignKey(
        OwnedPokemon, on_delete=models.CASCADE, related_name="pp_boosts"
    )
    move = models.ForeignKey(Move, on_delete=models.CASCADE)
    bonus_pp = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("pokemon", "move")

    def __str__(self) -> str:
        return f"{self.pokemon} {self.move} +{self.bonus_pp} PP"
