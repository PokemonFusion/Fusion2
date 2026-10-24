"""Read-only native association/count hints on ordinary party/storage surfaces."""


def native_pair_summary(actor):
    """Show retained companions without adding actionable party/box entries."""
    from pokemon.services.battle_rewards import BattleRewards

    if not BattleRewards.supports(actor):
        return ""
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.necrozma import NecrozmaCombination

    character = BattleRewards.character(actor)
    pairs = list(NecrozmaCombination.objects.filter(storage__user_id=character.pk).values(
        "host_id", "host__species", "companion_id", "companion__species"))
    if not pairs:
        return ""
    count = OwnedPokemon.objects.filter(trainer__user_id=character.pk).count()
    lines = [f"Owned Pokemon: {count}, including {len(pairs)} reserved native companion(s)."]
    for pair in pairs:
        lines.append(f"Native pair: {pair['host__species']} ({pair['host_id']}) + "
            f"{pair['companion__species']} ({pair['companion_id']}, reserved). "
            f"Inspect: +necrozma inspect {pair['companion_id']}")
    return "\n".join(lines)
