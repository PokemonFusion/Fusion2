"""Apply explicitly typed indirect damage through the holder's guards."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndirectEffect:
    """Keep recoil and contact causes distinct from the attacking move."""

    id: str
    effectType: str = "Ability"
    move_id: str = ""


def apply_indirect_damage(pokemon, amount, *, battle=None, source=None, effect=None):
    """Return actual HP loss after the recipient's Damage event."""
    if pokemon is None or getattr(pokemon, "hp", 0) <= 0:
        return 0
    amount = max(0, int(amount))
    if amount <= 0:
        return 0
    battle = battle or getattr(pokemon, "battle", None)
    run_event = getattr(battle, "runEvent", None)
    if callable(run_event):
        modified = run_event("Damage", pokemon, source, effect, amount)
        if modified is False:
            return 0
        if isinstance(modified, (int, float)) and not isinstance(modified, bool):
            amount = max(0, int(modified))
    actual = min(pokemon.hp, amount)
    pokemon.hp -= actual
    if pokemon.hp == 0:
        getattr(pokemon, "tempvals", {}).pop("faint_cause", None)
    return actual


def apply_recoil_damage(pokemon, amount, move, *, battle=None, source=None):
    """Apply a recoil cause without granting protection against direct moves."""
    move_id = str(getattr(move, "id", None) or getattr(move, "name", "")).replace(" ", "").lower()
    return apply_indirect_damage(pokemon, amount, battle=battle, source=source,
                                 effect=IndirectEffect("recoil", "Recoil", move_id))
