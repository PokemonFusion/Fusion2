"""Read current character authority and resources without creation properties."""

def persistent_character(character):
    """Resolve real ObjectDB actors while leaving pure display adapters alone."""
    actor = getattr(character, "character", character)
    meta = getattr(actor, "_meta", None)
    if meta and meta.concrete_model._meta.label_lower == "objects.objectdb" and actor.pk:
        return actor
    return None


def owned_characters(account):
    """Read the saved playable roster rather than an old handler cache."""
    meta = getattr(account, "_meta", None)
    if meta and meta.concrete_model._meta.label_lower == "accounts.accountdb":
        from pokemon.services.battle_rewards import BattleRewards
        return [char for char in BattleRewards.stored_attribute(account, "_playable_characters", default=[]) or []
                if persistent_character(char)]
    roster = getattr(account, "characters", [])
    return list(roster.all() if hasattr(roster, "all") else roster)


def existing_trainer(character):
    """Fetch an existing wallet/inventory owner without granting a trainer."""
    actor = persistent_character(character)
    if actor:
        from pokemon.models.trainer import Trainer
        return Trainer.objects.filter(user_id=actor.pk).first()
    return getattr(character, "trainer", None)


def existing_storage(character):
    """Fetch canonical storage without creating storage or starter boxes."""
    actor = persistent_character(character)
    if actor:
        from pokemon.models.storage import UserStorage
        return UserStorage.objects.filter(user_id=actor.pk).first()
    return getattr(character, "storage", None)


def refresh_character_reads(character):
    """Discard Attribute read caches; never grant, repair or persist state."""
    actor = persistent_character(character)
    if actor:
        actor.attributes.reset_cache()


def canonical_roster(character):
    """Return current owned rows and placements, retaining explicit integrity errors.

    Placement is authoritative. Unplaced rows and mismatched custody never become
    inferred party/box entries. Reserved members remain visibly separate.
    """
    from django.core.exceptions import ValidationError
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.storage import PokemonPlacement
    from pokemon.models.ownership import PokemonReservation
    from pokemon.services.ownership import fresh_owned

    trainer, storage = existing_trainer(character), existing_storage(character)
    rows = [fresh_owned(pk) for pk in OwnedPokemon.objects.filter(trainer=trainer).values_list("pk", flat=True)] if trainer else []
    placements = {row.pokemon_id: row for row in PokemonPlacement.objects.filter(pokemon_id__in=[mon.pk for mon in rows]).select_related("box")}
    claims = {row["pokemon_id"]: row["kind"] for row in PokemonReservation.objects.filter(pokemon_id__in=[mon.pk for mon in rows]).values("pokemon_id", "kind")}
    warnings, party, boxed, reserved, unplaced = [], [], [], [], []
    if trainer is None:
        warnings.append("Trainer setup is incomplete; no data was created.")
    if storage is None:
        warnings.append("Storage setup is incomplete; no data was created.")
    for mon in rows:
        placement = placements.get(mon.pk)
        label = mon.nickname or mon.species
        if not placement or not storage or placement.storage_id != storage.pk:
            warnings.append(f"{label}: missing or conflicting placement; ask staff to inspect it.")
            unplaced.append(mon)
            continue
        try:
            placement.clean()
        except ValidationError:
            warnings.append(f"{label}: invalid placement; ask staff to inspect it.")
            unplaced.append(mon)
            continue
        actual = (set(mon.active_slots.values_list('storage_id', 'slot')),
                  set(mon.stored_users.values_list('pk', flat=True)), set(mon.boxes.values_list('pk', flat=True)))
        expected = (set(), set(), set())
        if placement.location_type == 'party':
            expected = ({(storage.pk, placement.slot)}, set(), set())
        elif placement.location_type == 'box':
            expected = (set(), {storage.pk}, {placement.box_id})
        if actual != expected:
            warnings.append(f"{label}: conflicting storage membership; ask staff to inspect it.")
            unplaced.append(mon)
            continue
        mon.sheet_reservation = claims.get(mon.pk, "")
        if placement.location_type == "party":
            party.append((placement.slot, mon))
        elif placement.location_type == "box":
            boxed.append((placement.box_id, placement.box_position, mon))
        else:
            reserved.append({"pokemon": mon, "location": placement.get_location_type_display(),
                             "activity": claims.get(mon.pk, "")})
    party.sort(key=lambda pair: pair[0])
    boxed.sort(key=lambda triple: triple[:2])
    return {"trainer": trainer, "storage": storage, "pokemon": rows, "party_slots": party,
            "party": [mon for _, mon in party], "boxed": [mon for _, _, mon in boxed],
            "reserved": reserved, "unplaced": unplaced, "warnings": warnings}


def read_party_slots(character):
    """Read six canonical positions and refuse integrity errors without repairs."""
    snapshot = canonical_roster(character)
    if snapshot['trainer'] is None or snapshot['storage'] is None:
        from pokemon.services.placement import PlacementError
        raise PlacementError("Trainer or storage setup is incomplete; no data was created.")
    if snapshot["unplaced"]:
        from pokemon.services.placement import PlacementError
        raise PlacementError("Party data needs staff inspection; no data was changed.")
    slots = [None] * 6
    for slot, mon in snapshot["party_slots"]:
        slots[slot - 1] = mon
    return slots
