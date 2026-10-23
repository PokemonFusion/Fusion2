"""Bounded paid Z status bonuses and selected durable side/slot effects."""

from copy import deepcopy

from .active_slots import slot_for
from .terastallization import Terastallization


class ZEffects:
    """Apply one reviewed bonus before the unchanged ordinary source effect."""

    @staticmethod
    def hit(battle, user, move, damage):
        """Only reviewed signatures change terrain after actual HP/sub damage."""
        profile = getattr(move, "_z_profile", None)
        if not getattr(move, "_z_paid", False) or not profile or damage <= 0:
            return
        if profile.intrinsic == "psychicterrain":
            battle.setTerrain("psychicterrain", source=user)
        elif profile.intrinsic == "clearterrain":
            battle.clearTerrain()

    @staticmethod
    def start(battle, user, profile, move):
        """Only the eight explicitly reviewed status sources receive bonuses."""
        if profile.kind != "status":
            return
        from pokemon.utils.boosts import apply_boost

        before = dict(user.boosts)
        effect = profile.intrinsic
        if effect == "boost":
            apply_boost(user, dict(profile.bonus), source=user, effect=move)
        elif effect == "clearnegative":
            for key, value in user.boosts.items():
                if value < 0:
                    user.boosts[key] = 0
        elif effect == "heal" or effect == "curse" and "Ghost" in user.types:
            healed = battle.heal(user, user.max_hp, source=user, effect=move)
            battle.log_action(f"{user.name}'s Z power restored {healed} HP.")
        elif effect == "curse":
            apply_boost(user, {"atk": 1}, source=user, effect=move)
        elif effect == "crit2":
            battle.apply_volatile_status(user, "focusenergy", source=user, effect=move)
            battle.log_action(f"{user.name}'s Z power raised its critical-hit stage by two.")
        elif effect == "redirect":
            battle.apply_volatile_status(user, "followme", source=user, effect=move)
            state = user.volatiles.get("followme")
            if not isinstance(state, dict):
                state = user.volatiles["followme"] = {"id": "followme"}
            state["duration"] = 1
            state["z_turn"] = battle.mechanic_turn
        elif effect == "healreplacement":
            part = battle.participant_for(user)
            side = Terastallization.side(battle, part)
            pending = getattr(battle, "z_replacement", {})
            pending.setdefault(side, {})[str(slot_for(part, user))] = str(user.model_id)
            battle.z_replacement = pending
            battle.log_action(f"{user.name}'s Z power prepared a heal for its replacement slot.")
        battle.announce_stat_changes(user, before, user.boosts)

    @staticmethod
    def end_turn(battle):
        """Expire only this Z bonus's one-turn redirect after all actions/residuals."""
        for part in battle.participants:
            for mon in part.pokemons:
                state = mon.volatiles.get("followme")
                if isinstance(state, dict) and "z_turn" in state:
                    battle.remove_volatile(mon, "followme")

    @staticmethod
    def switch_in(battle, pokemon):
        """Heal one incoming conscious occupant of the exact slot, HP only."""
        part = battle.participant_for(pokemon)
        if part is None or pokemon.hp <= 0:
            return
        side = Terastallization.side(battle, part)
        pending = getattr(battle, "z_replacement", {}).get(side, {})
        key = str(slot_for(part, pokemon))
        if key in pending:
            pending.pop(key)
            healed = battle.heal(pokemon, pokemon.max_hp, source=pokemon)
            battle.log_action(f"{pokemon.name}'s replacement Z power restored {healed} HP.")

    @staticmethod
    def freeze(battle):
        """Save only selected replacement/Tailwind effects without replaying Start."""
        replacement = {
            side: dict(slots)
            for side, slots in getattr(battle, "z_replacement", {}).items()
            if slots
        }
        tailwind = {}
        has_tailwind_z = any(
            ((getattr(mon, "z_profile", None) or {}).get("request") or {}).get("source")
            == "Tailwind"
            for part in battle.participants
            for mon in part.pokemons
        )
        if has_tailwind_z:
            for part in battle.participants:
                state = part.side.conditions.get("tailwind")
                if state:
                    tailwind[Terastallization.side(battle, part)] = state.get("duration")
        return (
            {"version": 1, "replacement": replacement, "tailwind": tailwind}
            if replacement or tailwind
            else {}
        )

    @staticmethod
    def recover(battle, saved):
        """Validate each selected effect against an actual activated source."""
        battle.z_replacement = {}
        from ._shared import snapshot_battle_value

        saved = snapshot_battle_value(saved)
        if saved == {}:
            return
        if (
            not isinstance(saved, dict)
            or set(saved) != {"version", "replacement", "tailwind"}
            or type(saved["version"]) is not int
            or saved["version"] != 1
            or not isinstance(saved["replacement"], dict)
            or not isinstance(saved["tailwind"], dict)
        ):
            raise ValueError("Unknown or corrupt selected Z effect checkpoint.")
        proofs = {}
        for part in battle.participants:
            for mon in part.pokemons:
                if getattr(mon, "z_activated", False):
                    proofs[str(mon.model_id)] = (
                        Terastallization.side(battle, part),
                        mon.z_profile["request"]["source"],
                    )
        for side, slots in saved["replacement"].items():
            if side not in {"A", "B"} or not isinstance(slots, dict):
                raise ValueError("Invalid Z replacement side/slot checkpoint.")
            for slot, source in slots.items():
                if slot not in {"0", "1"} or proofs.get(source) != (side, "Memento"):
                    raise ValueError("Unbound Z replacement source checkpoint.")
        if saved["tailwind"] and not any(source == "Tailwind" for side, source in proofs.values()):
            raise ValueError("Unbound selected Z Tailwind checkpoint.")
        for side, duration in saved["tailwind"].items():
            if side not in {"A", "B"} or type(duration) is not int or not 1 <= duration <= 6:
                raise ValueError("Invalid selected Z Tailwind duration checkpoint.")
            part = next(
                part for part in battle.participants if Terastallization.side(battle, part) == side
            )
            part.side.add_side_condition("tailwind", {"id": "tailwind", "duration": duration})
            part.side.screens["tailwind"] = True
        battle.z_replacement = deepcopy(saved["replacement"])
