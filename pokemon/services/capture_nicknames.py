"""Durable, character-scoped nickname choices for newly captured Pokémon."""

from __future__ import annotations

from django.db import transaction

from pokemon.services.pokemon_refs import build_owned_ref, parse_pokemon_ref

QUEUE_ATTRIBUTE = "pending_capture_nicknames"


class CaptureNicknames:
    """Keep nickname prompts attached to a caught Pokémon's persistent ID."""

    def __init__(self, player):
        """Bind the ordinary character who owns the captured Pokémon."""
        self.player = player

    def pending(self):
        """Read serializable prompt data without consuming it on display."""
        attributes = getattr(self.player, "attributes", None)
        if attributes is not None:
            # Evennia caches Attributes; a rolled-back capture must not leave
            # a phantom nickname prompt in that process's cache.
            attributes.reset_cache()
            attribute = attributes.get(QUEUE_ATTRIBUTE, return_obj=True)
            if attribute is not None:
                try:
                    attribute.refresh_from_db(fields=["db_value"])
                except attribute.DoesNotExist:
                    attributes.reset_cache()
                    return []
                return list(attribute.value or [])
            return []
        return list(getattr(getattr(self.player, "db", None), QUEUE_ATTRIBUTE, None) or [])

    def queue(self, pokemon, *, species):
        """Record one prompt inside the capture's transaction, deduplicated by ID."""
        if getattr(self.player, "db", None) is None:
            return  # Non-character capture adapters have no interactive UI.
        reference = build_owned_ref(pokemon.pk)
        pending = self.pending()
        if any(entry.get("pokemon_id") == reference for entry in pending):
            return
        pending.append({"pokemon_id": reference, "species": str(species)})
        setattr(self.player.db, QUEUE_ATTRIBUTE, pending)

    def complete(self, reference, nickname=None):
        """Rename only the queued owned Pokémon, or retain its existing name."""
        from pokemon.models.core import OwnedPokemon

        kind, identifier = parse_pokemon_ref(reference)
        if kind != "owned" or not identifier:
            raise ValueError("That captured Pokémon is no longer available.")
        pending = self.pending()
        if not any(entry.get("pokemon_id") == reference for entry in pending):
            raise ValueError("That nickname choice has already been handled.")
        if nickname is not None:
            nickname = nickname.strip()
            maximum = OwnedPokemon._meta.get_field("nickname").max_length
            if not nickname or len(nickname) > maximum or "|" in nickname or not nickname.isprintable():
                raise ValueError(f"Enter a nickname of 1–{maximum} characters without color codes or line breaks.")

        with transaction.atomic():
            pokemon = OwnedPokemon.objects.select_for_update().filter(
                pk=identifier, trainer=getattr(self.player, "trainer", None),
            ).first()
            if pokemon is None:
                # Release or ownership changes must never rename a different catch.
                setattr(self.player.db, QUEUE_ATTRIBUTE, [entry for entry in pending if entry.get("pokemon_id") != reference])
                return None
            if nickname is not None:
                pokemon.refresh_from_db()
                pokemon.nickname = nickname
                pokemon.save(update_fields=["nickname"])
            setattr(self.player.db, QUEUE_ATTRIBUTE, [entry for entry in pending if entry.get("pokemon_id") != reference])
        return pokemon.name
