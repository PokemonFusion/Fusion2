"""Database models for Pokémon ownership."""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

from evennia.objects.models import ObjectDB
from evennia.utils.idmapper.models import SharedMemoryModel
from django.db import models
import uuid

# ------------------------------------------------------------------
# Data schema for trainer-owned Pokémon
# ------------------------------------------------------------------

STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]


@dataclass
class PokemonData:
    """Serializable container mirroring Pokemon Showdown's structure."""

    # Identity
    species: str
    nickname: str = ""
    gender: str = ""
    level: int = 100
    shiny: bool = False
    pokeball: Optional[str] = None
    original_trainer_id: str = ""

    # Battle stats
    nature: str = "Hardy"
    ability: str = ""
    item: str = ""
    evs: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in STAT_KEYS})
    ivs: Dict[str, int] = field(default_factory=lambda: {k: 31 for k in STAT_KEYS})
    moves: List[str] = field(default_factory=list)
    learned_moves: List[str] = field(default_factory=list)
    tera_type: Optional[str] = None

    # RPG extensions
    current_hp: int = 0
    max_hp: int = 0
    status: str = ""
    fainted: bool = False
    exp: int = 0
    experience_to_level_up: int = 0
    trainer_id: str = ""

    def to_dict(self) -> Dict:
        """Return a JSON-serialisable representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PokemonData":
        """Create from a JSON dictionary, applying defaults."""
        return cls(
            species=data.get("species", "Unknown"),
            nickname=data.get("nickname", data.get("species", "Unknown")),
            gender=data.get("gender", ""),
            level=data.get("level", 100),
            shiny=data.get("shiny", False),
            pokeball=data.get("pokeball"),
            original_trainer_id=data.get("original_trainer_id", ""),
            nature=data.get("nature", "Hardy"),
            ability=data.get("ability", ""),
            item=data.get("item", ""),
            evs=data.get("evs", {k: 0 for k in STAT_KEYS}),
            ivs=data.get("ivs", {k: 31 for k in STAT_KEYS}),
            moves=list(data.get("moves", [])),
            learned_moves=list(data.get("learned_moves", [])),
            tera_type=data.get("tera_type"),
            current_hp=data.get("current_hp", 0),
            max_hp=data.get("max_hp", 0),
            status=data.get("status", ""),
            fainted=data.get("fainted", False),
            exp=data.get("exp", 0),
            experience_to_level_up=data.get("experience_to_level_up", 0),
            trainer_id=data.get("trainer_id", ""),
        )


class Pokemon(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField()
    type_ = models.CharField(max_length=255)
    ability = models.CharField(max_length=50, blank=True)
    held_item = models.CharField(max_length=50, blank=True)
    data = models.JSONField(default=dict, blank=True)
    trainer = models.ForeignKey(
        "Trainer",
        on_delete=models.CASCADE,
        related_name="owned_pokemon",
        null=True,
        blank=True,
    )

    def __str__(self):
        owner = f" owned by {self.trainer.user.key}" if self.trainer else ""
        return (
            f"{self.id}: {self.name} (Level {self.level}, Type: {self.type_}, "
            f"Ability: {self.ability})" + owner
        )

    # ------------------------------------------------------------------
    # Convenience properties for JSON data fields
    # ------------------------------------------------------------------

    def _get_data(self):
        return self.data or {}

    def _set_data(self, key, value):
        d = self.data or {}
        d[key] = value
        self.data = d

    @property
    def current_hp(self):
        return self._get_data().get("current_hp", 0)

    @current_hp.setter
    def current_hp(self, value):
        self._set_data("current_hp", value)

    @property
    def status(self):
        return self._get_data().get("status", "")

    @status.setter
    def status(self, value):
        self._set_data("status", value)

    @property
    def gender(self):
        return self._get_data().get("gender")

    @gender.setter
    def gender(self, value):
        self._set_data("gender", value)

    @property
    def nature(self):
        return self._get_data().get("nature")

    @nature.setter
    def nature(self, value):
        self._set_data("nature", value)

    @property
    def ivs(self):
        return self._get_data().get("ivs", {})

    @ivs.setter
    def ivs(self, value):
        self._set_data("ivs", value)

    @property
    def evs(self):
        return self._get_data().get("evs", {})

    @evs.setter
    def evs(self, value):
        self._set_data("evs", value)

    # Additional identity fields
    @property
    def nickname(self) -> str:
        return self._get_data().get("nickname", self.name)

    @nickname.setter
    def nickname(self, value: str) -> None:
        self._set_data("nickname", value)

    @property
    def shiny(self) -> bool:
        return self._get_data().get("shiny", False)

    @shiny.setter
    def shiny(self, value: bool) -> None:
        self._set_data("shiny", value)

    @property
    def pokeball(self) -> Optional[str]:
        return self._get_data().get("pokeball")

    @pokeball.setter
    def pokeball(self, value: Optional[str]) -> None:
        self._set_data("pokeball", value)

    @property
    def original_trainer_id(self) -> str:
        return self._get_data().get("original_trainer_id", "")

    @original_trainer_id.setter
    def original_trainer_id(self, value: str) -> None:
        self._set_data("original_trainer_id", value)

    # Battle related data
    @property
    def moves(self) -> List[str]:
        return self._get_data().get("moves", [])

    @moves.setter
    def moves(self, value: List[str]) -> None:
        self._set_data("moves", list(value))

    @property
    def learned_moves(self) -> List[str]:
        return self._get_data().get("learned_moves", [])

    @learned_moves.setter
    def learned_moves(self, value: List[str]) -> None:
        self._set_data("learned_moves", list(value))

    @property
    def tera_type(self) -> Optional[str]:
        return self._get_data().get("tera_type")

    @tera_type.setter
    def tera_type(self, value: Optional[str]) -> None:
        self._set_data("tera_type", value)

    @property
    def max_hp(self) -> int:
        return self._get_data().get("max_hp", 0)

    @max_hp.setter
    def max_hp(self, value: int) -> None:
        self._set_data("max_hp", value)

    @property
    def fainted(self) -> bool:
        return self._get_data().get("fainted", False)

    @fainted.setter
    def fainted(self, value: bool) -> None:
        self._set_data("fainted", value)

    @property
    def exp(self) -> int:
        return self._get_data().get("exp", 0)

    @exp.setter
    def exp(self, value: int) -> None:
        self._set_data("exp", value)

    @property
    def experience_to_level_up(self) -> int:
        return self._get_data().get("experience_to_level_up", 0)

    @experience_to_level_up.setter
    def experience_to_level_up(self, value: int) -> None:
        self._set_data("experience_to_level_up", value)

    @property
    def trainer_owner_id(self) -> str:
        return self._get_data().get("trainer_id", "")

    @trainer_owner_id.setter
    def trainer_owner_id(self, value: str) -> None:
        self._set_data("trainer_id", value)


class UserStorage(models.Model):
    user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE)
    active_pokemon = models.ManyToManyField(
        Pokemon, related_name="active_users"
    )
    stored_pokemon = models.ManyToManyField(
        Pokemon, related_name="stored_users", blank=True
    )


class StorageBox(models.Model):
    """A box of Pokémon stored for a particular user."""

    storage = models.ForeignKey(
        UserStorage, on_delete=models.CASCADE, related_name="boxes"
    )
    name = models.CharField(max_length=255)
    pokemon = models.ManyToManyField(Pokemon, related_name="boxes", blank=True)

    def __str__(self):
        return f"{self.name} (Owner: {self.storage.user.key})"


class OwnedPokemon(SharedMemoryModel):
    """Persistent data for a player's Pokémon."""

    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Species & identity
    species = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True)
    nature = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    shiny = models.BooleanField(default=False)
    level = models.IntegerField(default=1)
    experience = models.IntegerField(default=0)

    # Ownership & trainers
    original_trainer = models.ForeignKey(
        ObjectDB,
        related_name="original_pokemon",
        on_delete=models.CASCADE,
    )
    current_trainer = models.ForeignKey(
        ObjectDB,
        related_name="owned_pokemon",
        on_delete=models.CASCADE,
    )

    # Stats
    happiness = models.IntegerField(default=0)
    bond = models.IntegerField(default=0)
    ivs = models.JSONField(default=dict)
    evs = models.JSONField(default=dict)

    # Status
    current_hp = models.IntegerField(default=0)
    max_hp = models.IntegerField(default=0)
    status_condition = models.CharField(max_length=20, blank=True)
    walked_steps = models.IntegerField(default=0)

    # Battle context
    battle_id = models.IntegerField(null=True, blank=True)
    battle_team = models.CharField(max_length=1, blank=True)

    # Items & ability
    held_item = models.CharField(max_length=50, blank=True)
    ability = models.CharField(max_length=50)

    # Known moves and PP data
    known_moves = models.JSONField(default=list, blank=True)
    moveset = models.JSONField(default=list, blank=True)
    data = models.JSONField(default=dict, blank=True)


class ActiveMoveset(SharedMemoryModel):
    """Mapping of active move slots for a Pokémon."""

    pokemon = models.OneToOneField(
        OwnedPokemon,
        related_name="active_moveset",
        on_delete=models.CASCADE,
    )
    moves = models.JSONField(default=list, blank=True)


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
        ObjectDB, on_delete=models.CASCADE, related_name="trainer"
    )
    trainer_number = models.PositiveIntegerField(unique=True)
    money = models.PositiveIntegerField(default=0)
    seen_pokemon = models.ManyToManyField(
        Pokemon, related_name="seen_by_trainers", blank=True
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

    def log_seen_pokemon(self, pokemon: Pokemon) -> None:
        self.seen_pokemon.add(pokemon)
