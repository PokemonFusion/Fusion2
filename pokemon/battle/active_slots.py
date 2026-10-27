"""Stable field positions while keeping the engine's active list compact."""

from __future__ import annotations


def active_slots(participant, *, update=True) -> dict:
    """Map stable slots, optionally without updating the participant's cache."""
    active = list(getattr(participant, "active", []))
    previous = getattr(participant, "_active_slots", {})
    slots = {slot: mon for slot, mon in previous.items()
             if any(candidate is mon for candidate in active)}
    for mon in active:
        if any(candidate is mon for candidate in slots.values()):
            continue
        slot = next((slot for slot in range(getattr(participant, "max_active", max(1, len(active)))) if slot not in slots), None)
        if slot is not None:
            slots[slot] = mon
    if update:
        participant._active_slots = slots
    return slots


def active_at(participant, slot):
    """Return the current occupant of a logical field position."""
    return active_slots(participant).get(slot)


def slot_for(participant, pokemon):
    """Find a battler's logical position using identity."""
    return next((slot for slot, mon in active_slots(participant).items() if mon is pokemon), None)


def assign_active(participant, slot, pokemon):
    """Replace one logical position, preserving every other occupant."""
    slots = active_slots(participant)
    if pokemon is None:
        slots.pop(slot, None)
    else:
        slots[slot] = pokemon
    participant._active_slots = slots
    participant.active[:] = [mon for _, mon in sorted(slots.items())]
    if getattr(participant, "side", None) is not None:
        participant.side.active = participant.active
