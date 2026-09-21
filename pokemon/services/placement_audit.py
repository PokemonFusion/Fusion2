"""Read-only lifecycle audit shared with migration 0040.

``audit_placements_v1`` is migration-stable: keep its historical model/field
contract intact. Future schema changes should add a versioned audit instead.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class PlacementProblem:
    """An actionable record identifier and reason for staff review."""

    pokemon_id: str
    code: str
    detail: str

    def __str__(self):
        return f"{self.pokemon_id}: {self.code}: {self.detail}"


def audit_placements_v1(apps, using="default"):
    """Yield ownership, placement shape, occupancy, and legacy mirror problems.

    This deliberately makes no repairs and does not infer ownership from mirrors.
    It uses historical-model-compatible field queries and the requested alias.
    """
    Owned = apps.get_model("pokemon", "OwnedPokemon")
    Placement = apps.get_model("pokemon", "PokemonPlacement")
    Storage = apps.get_model("pokemon", "UserStorage")
    Box = apps.get_model("pokemon", "StorageBox")
    Active = apps.get_model("pokemon", "ActivePokemonSlot")
    owners = dict(apps.get_model("pokemon", "Trainer").objects.using(using).values_list("pk", "user_id"))
    storages = dict(Storage.objects.using(using).values_list("pk", "user_id"))
    boxes = dict(Box.objects.using(using).values_list("pk", "storage_id"))
    placements = defaultdict(list)
    party_occupancy = Counter()
    box_occupancy = Counter()
    for row in Placement.objects.using(using).values():
        placements[row["pokemon_id"]].append(row)
        if row["location_type"] == "party":
            party_occupancy[(row["storage_id"], row["slot"])] += 1
        if row["location_type"] == "box":
            box_occupancy[(row["box_id"], row["box_position"])] += 1
    active = defaultdict(set)
    stored = defaultdict(set)
    boxed = defaultdict(set)
    for pid, sid, slot in Active.objects.using(using).values_list("pokemon_id", "storage_id", "slot"):
        active[pid].add((sid, slot))
    for pid, sid in Storage.stored_pokemon.through.objects.using(using).values_list("ownedpokemon_id", "userstorage_id"):
        stored[pid].add(sid)
    for pid, bid in Box.pokemon.through.objects.using(using).values_list("ownedpokemon_id", "storagebox_id"):
        boxed[pid].add(bid)

    for pid, trainer_id in Owned.objects.using(using).values_list("pk", "trainer_id").iterator():
        def problem(code, detail):
            return PlacementProblem(str(pid), code, detail)

        if trainer_id not in owners:
            yield problem("owner_missing", f"trainer={trainer_id}")
        rows = placements.get(pid, [])
        if len(rows) != 1:
            yield problem("placement_count", f"expected 1, found {len(rows)}; trainer={trainer_id}")
            if active[pid] or stored[pid] or boxed[pid]:
                yield problem("legacy_without_placement", f"party={active[pid]}, storage={stored[pid]}, boxes={boxed[pid]}")
            continue
        row = rows[0]
        sid, location = row["storage_id"], row["location_type"]
        slot, bid, position = row["slot"], row["box_id"], row["box_position"]
        if owners.get(trainer_id) != storages.get(sid):
            yield problem("owner_mismatch", f"trainer={trainer_id}, storage={sid}")
        valid = False
        expected_active, expected_stored, expected_boxed = set(), set(), set()
        if location == "party":
            valid = slot is not None and 1 <= slot <= 6 and bid is None and position is None
            expected_active = {(sid, slot)}
            if party_occupancy[(sid, slot)] > 1:
                yield problem("duplicate_party_slot", f"storage={sid}, slot={slot}")
        elif location == "box":
            valid = slot is None and bid is not None and position is not None and position >= 1
            expected_stored, expected_boxed = {sid}, {bid}
            if boxes.get(bid) != sid:
                yield problem("box_owner_mismatch", f"storage={sid}, box={bid}")
            if box_occupancy[(bid, position)] > 1:
                yield problem("duplicate_box_position", f"box={bid}, position={position}")
        elif location == "fusion":
            valid = slot is None and bid is None and position is None
        if not valid:
            yield problem("invalid_shape", f"location={location}, slot={slot}, box={bid}, position={position}")
        if (active[pid], stored[pid], boxed[pid]) != (expected_active, expected_stored, expected_boxed):
            yield problem("legacy_mismatch", f"party={active[pid]}, storage={stored[pid]}, boxes={boxed[pid]}")
