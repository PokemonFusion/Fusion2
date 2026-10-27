"""Trainer related models such as ``Trainer`` and inventory."""

from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from evennia.objects.models import ObjectDB

from pokemon.names import normalize_name

from .core import SpeciesEntry
from .validators import validate_evs, validate_ivs


def _resolve_species_entry(species: str | int) -> "SpeciesEntry | None":
        """Return the :class:`SpeciesEntry` instance matching ``species`` if possible."""

        if isinstance(species, int):
                return SpeciesEntry.objects.filter(pk=species).first()
        from pokemon.dex import POKEDEX
        from pokemon.names import find_named, resolve_dex_entry

        exact = SpeciesEntry.objects.filter(name__iexact=str(species)).first()
        if exact:
                return exact
        entry = resolve_dex_entry(POKEDEX, species)
        if entry:
                display = entry.get("name") if isinstance(entry, dict) else entry.name
                exact = SpeciesEntry.objects.filter(name__iexact=display).first()
                if exact:
                        return exact
        return find_named(SpeciesEntry.objects.all(), species)


class GymBadge(models.Model):
        """A gym badge rewarded for defeating a particular gym."""

        name = models.CharField(max_length=255)
        region = models.CharField(max_length=255)
        description = models.TextField(blank=True)

        def __str__(self):  # pragma: no cover - simple repr
                return f"{self.name} ({self.region})"


class Trainer(models.Model):
        """Model storing trainer specific stats for a Character."""

        user = models.OneToOneField(ObjectDB, on_delete=models.CASCADE, related_name="trainer", db_index=True)
        trainer_number = models.PositiveIntegerField(unique=True)
        money = models.PositiveIntegerField(default=0)
        seen_pokemon = models.ManyToManyField("SpeciesEntry", related_name="seen_by_trainers", blank=True)
        badges = models.ManyToManyField("GymBadge", related_name="trainers", blank=True)

        def __str__(self):  # pragma: no cover - simple repr
                return f"Trainer {self.trainer_number} for {self.user.key}"

        def add_badge(self, badge: GymBadge) -> None:
                self.badges.add(badge)

        def _change_money(self, amount: int, *, debit: bool) -> bool:
                """Serialize every existing wallet writer against marketplace settlement."""
                if type(amount) is not int or amount < 0:
                        raise ValueError("Money changes require a nonnegative whole amount.")
                with transaction.atomic():
                        balance = type(self).objects.select_for_update().values_list("money", flat=True).get(pk=self.pk)
                        if debit and balance < amount:
                                self.money = balance
                                return False
                        if not debit and balance > 2_147_483_647 - amount:
                                raise ValueError("Trainer wallet cannot receive this payment.")
                        self.money = balance - amount if debit else balance + amount
                        type(self).objects.filter(pk=self.pk).update(money=self.money)
                        return True

        def add_money(self, amount: int) -> None:
                """Credit the current saved wallet without overwriting concurrent payments."""
                self._change_money(amount, debit=False)

        def spend_money(self, amount: int) -> bool:
                """Debit only available current money, including after stale object reads."""
                return self._change_money(amount, debit=True)

        def log_seen_pokemon(self, species: str | int) -> None:
                """Record that the trainer has seen the given species."""
                entry = _resolve_species_entry(species)
                if entry:
                        self.seen_pokemon.add(entry)

        def log_caught_pokemon(self, species: str | int) -> None:
                """Record that the trainer has caught the given species."""

                entry = _resolve_species_entry(species)
                if not entry:
                        return

                self.seen_pokemon.add(entry)

                # Mirror progress onto the underlying Evennia typeclass when available
                user = getattr(self, "user", None)
                target_name = entry.name
                for source in (user, getattr(user, "typeclass", None)):
                        if not source:
                                continue
                        for method in ("mark_seen", "mark_owned", "mark_caught"):
                                func = getattr(source, method, None)
                                if callable(func):
                                        try:
                                                func(target_name)
                                        except Exception:
                                                continue

        def _sync_character_inventory(self) -> None:
                """Update the attached character's cached inventory if possible."""

                user = getattr(self, "user", None)
                if not user:
                        return
                character = getattr(user, "typeclass", None) or user
                if not character:
                        return
                updater = getattr(character, "_update_inventory_cache_from_trainer", None)
                if callable(updater):
                        try:
                                updater()
                        except Exception:
                                pass

        def _inventory_entries(self, item_name: str, *, lock: bool = False):
                """Match canonical and legacy spellings without rewriting inventory."""
                key = normalize_name(item_name)
                entries = InventoryEntry.objects.filter(owner=self).order_by("pk")
                if lock:
                        entries = entries.select_for_update()
                return [entry for entry in entries if normalize_name(entry.item_name) == key]

        def get_item_quantity(self, item_name: str) -> int:
                """Count the item across equivalent stored name spellings."""
                return sum(entry.quantity for entry in self._inventory_entries(item_name))

        def has_item(self, item_name: str, amount: int = 1) -> bool:
                """Return ``True`` if at least ``amount`` of ``item_name`` is owned."""

                return self.get_item_quantity(item_name) >= amount

        def add_item(self, item_name: str, amount: int = 1) -> None:
                """Reuse legacy aliases and store new items under normalized names."""
                if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                        raise ValueError("Item amount must be a positive integer.")
                with transaction.atomic():
                        Trainer.objects.select_for_update().get(pk=self.pk)
                        entries = self._inventory_entries(item_name, lock=True)
                        if entries:
                                entry = entries[0]
                        else:
                                entry = InventoryEntry(owner=self, item_name=normalize_name(item_name), quantity=0)
                        entry.quantity += amount
                        entry.save()
                        transaction.on_commit(self._sync_character_inventory)

        def remove_item(self, item_name: str, amount: int = 1) -> bool:
                """Lock the inventory debit and refresh its cache only on commit."""
                if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                        raise ValueError("Item amount must be a positive integer.")
                with transaction.atomic():
                        Trainer.objects.select_for_update().get(pk=self.pk)
                        entries = self._inventory_entries(item_name, lock=True)
                        if sum(entry.quantity for entry in entries) < amount:
                                return False
                        remaining = amount
                        for entry in entries:
                                removed = min(entry.quantity, remaining)
                                entry.quantity -= removed
                                remaining -= removed
                                if entry.quantity <= 0:
                                        entry.delete()
                                else:
                                        entry.save(update_fields=["quantity"])
                                if remaining == 0:
                                        break
                        transaction.on_commit(self._sync_character_inventory)
                return True

        def list_inventory(self):
                """Return ``InventoryEntry`` objects owned by this trainer."""
                return InventoryEntry.objects.filter(owner=self).order_by("item_name")


class NPCTrainer(models.Model):
        """Static NPC trainer such as gym leaders."""

        name = models.CharField(max_length=255, unique=True)
        description = models.TextField(blank=True)

        def __str__(self):  # pragma: no cover - simple repr
                return self.name


class GymLeaderProfile(models.Model):
        """Gym-specific metadata for an otherwise reusable static NPC trainer."""

        npc_trainer = models.OneToOneField(
                "NPCTrainer",
                on_delete=models.CASCADE,
                related_name="gym_leader_profile",
        )
        badge = models.ForeignKey(
                "GymBadge",
                on_delete=models.PROTECT,
                related_name="gym_leader_profiles",
        )
        league_key = models.CharField(max_length=80, db_index=True)
        gym_key = models.CharField(max_length=80, db_index=True)
        # Transitional content key until GymBadge grows its own durable key field.
        badge_key = models.CharField(max_length=80, db_index=True)
        required_badge_count = models.PositiveSmallIntegerField(default=0)
        is_enabled = models.BooleanField(default=True, db_index=True)
        sort_order = models.PositiveSmallIntegerField(default=1, db_index=True)

        content_version = models.PositiveIntegerField(default=0)
        content_digest = models.CharField(max_length=64, blank=True, default="")
        content_definition = models.JSONField(default=dict, blank=True)

        battle_format = models.CharField(max_length=10, default="single", choices=(("single", "Singles"), ("double", "Doubles")))
        ai_profile = models.CharField(max_length=80, default="gym_leader")
        strategy_key = models.CharField(max_length=40, blank=True, default="", choices=(("", "None"), ("trick_room", "Trick Room")))
        content_stage = models.CharField(max_length=16, default="production", choices=(("production", "Production"), ("test", "Test")))
        intro_text = models.TextField(blank=True)
        victory_text = models.TextField(blank=True)
        defeat_text = models.TextField(blank=True)
        rules_text = models.TextField(blank=True)
        reward_policy = models.CharField(max_length=16, default="legacy", choices=(("legacy", "Legacy"), ("badge_only", "Badge only")))
        rematch_cooldown_seconds = models.PositiveIntegerField(default=0)

        class Meta:
                ordering = ("sort_order", "league_key", "gym_key")
                constraints = [
                        models.UniqueConstraint(
                                fields=("league_key", "gym_key"),
                                name="gymleaderprofile_unique_gym",
                        ),
                        models.UniqueConstraint(
                                fields=("league_key", "badge_key"),
                                name="gymleaderprofile_unique_badge_key",
                        ),
                ]

        def __str__(self):  # pragma: no cover - simple repr
                return f"{self.npc_trainer} ({self.league_key}:{self.gym_key})"


class NPCPokemonTemplate(models.Model):
        """Reusable template for NPC-owned battle Pokemon."""

        npc_trainer = models.ForeignKey(
                "NPCTrainer",
                on_delete=models.CASCADE,
                related_name="pokemon_templates",
        )
        template_key = models.CharField(max_length=100, blank=True)
        species = models.CharField(max_length=50)
        level = models.PositiveSmallIntegerField(default=1)
        ability = models.CharField(max_length=50, blank=True)
        nature = models.CharField(max_length=20, blank=True)
        gender = models.CharField(max_length=10, blank=True)
        ivs = ArrayField(models.PositiveSmallIntegerField(), size=6, default=list, validators=[validate_ivs])
        evs = ArrayField(models.PositiveSmallIntegerField(), size=6, default=list, validators=[validate_evs])
        held_item = models.CharField(max_length=50, blank=True)
        move_names = models.JSONField(default=list, blank=True)
        sort_order = models.PositiveSmallIntegerField(default=1, db_index=True)

        class Meta:
                ordering = ("sort_order", "id")

        def __str__(self):  # pragma: no cover - simple repr
                label = self.template_key or self.species
                return f"{self.npc_trainer}: {label}"


class InventoryEntry(models.Model):
        """A quantity of a particular item owned by a trainer."""

        owner = models.ForeignKey("Trainer", on_delete=models.CASCADE, related_name="inventory")
        item_name = models.CharField(max_length=100)
        quantity = models.PositiveIntegerField(default=1)

        class Meta:
                unique_together = ("owner", "item_name")

        def __str__(self) -> str:  # pragma: no cover - simple repr
                return f"{self.item_name} x{self.quantity}"
