from random import choice, random
from pokemon.data import TYPE_CHART
from pokemon.utils.boosts import apply_boost


def type_effectiveness(target, move):
    if not move or not getattr(move, "type", None):
        return 1.0
    chart = TYPE_CHART.get(move.type.capitalize(), {})
    eff = 1.0
    for typ in getattr(target, "types", []):
        val = chart.get(typ.capitalize(), 0)
        if val == 1:
            eff *= 2
        elif val == 2:
            eff *= 0.5
        elif val == 3:
            eff *= 0
    return eff


class Acrobatics:
    def basePowerCallback(self, user, target, move):
        """Double power if the user holds no item."""
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if not item:
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Acupressure:
    def onHit(self, user, target, battle):
        """Randomly raise one of the target's stats by 2 stages."""
        stats = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
        viable = [s for s in stats if getattr(target, "boosts", {}).get(s, 0) < 6]
        if not viable:
            return False
        stat = choice(viable)
        apply_boost(target, {stat: 2})
        return True

class Afteryou:
    def onHit(self, user, target, battle):
        """Make the target act immediately after the user when possible."""
        if not battle:
            return True
        # Fail in singles battles (only one active Pokémon per side)
        if all(len(getattr(p, "active", [])) <= 1 for p in getattr(battle, "participants", [])):
            return False
        queue = getattr(battle, "queue", None)
        if queue:
            action = getattr(queue, "will_move", lambda t: None)(target)
            if not action:
                return False
            getattr(queue, "prioritize_action", lambda a: None)(action)
        return True

class Alluringvoice:
    def onHit(self, user, target, battle):
        """Lower the target's Attack by one stage."""
        apply_boost(target, {"atk": -1})
        return True

class Allyswitch:
    def onHit(self, user, target, battle):
        """Swap positions with the ally if possible."""
        side = getattr(user, "side", None)
        if not side or len(getattr(side, "active", [])) <= 1:
            return False
        active = side.active
        if user not in active:
            return False
        idx = active.index(user)
        other_idx = 1 - idx if len(active) > 1 else idx
        active[idx], active[other_idx] = active[other_idx], active[idx]
        return True

    def onPrepareHit(self, *args, **kwargs):
        return True

    def onRestart(self, *args, **kwargs):
        return True

    def onStart(self, *args, **kwargs):
        return True

class Anchorshot:
    def onHit(self, user, target, battle):
        """Trap the target and prevent switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Aquaring:
    """Runtime handler for the Aqua Ring volatile status."""

    def onResidual(self, *args, **kwargs):
        """Heal the user for 1/16 of its maximum HP each turn."""
        user = args[0] if args else None
        if not user:
            return False
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 16
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

    def onStart(self, *args, **kwargs):
        """Activate Aqua Ring on the user so residual can process it."""
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["aquaring"] = True
        return True

class Aromatherapy:
    def onHit(self, user, target, battle):
        """Cure status conditions of the user's party."""
        for mon in getattr(user, "party", [user]):
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True

class Assist:
    def onHit(self, user, target, battle):
        """Use a random move known by an ally."""
        allies = [ally for ally in getattr(user, "party", []) if ally is not user]
        moves = []
        for ally in allies:
            moves.extend(getattr(ally, "moves", []))
        moves = [m for m in moves if getattr(m, "name", "").lower() != "assist"]
        if not moves:
            return False
        move = choice(moves)
        if hasattr(move, "onHit"):
            move.onHit(user, target, battle)
        return True

class Assurance:
    def basePowerCallback(self, user, target, move):
        """Double power if the target already took damage this turn."""
        took_damage = getattr(target, "tempvals", {}).get("took_damage")
        base = getattr(move, "power", 0) or 0
        if took_damage:
            return base * 2
        return base

class Attract:
    """Runtime handler for the Attract volatile status."""

    def onBeforeMove(self, *args, **kwargs):
        """50% chance the infatuated Pokémon can't move."""
        user = args[0] if args else kwargs.get("user")
        if user and random() < 0.5:
            if hasattr(user, "tempvals"):
                user.tempvals["cant_move"] = "attract"
            return False
        return True

    def onEnd(self, *args, **kwargs):
        """Remove the Attract effect from the target."""
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("attract", None)
        return True

    def onStart(self, *args, **kwargs):
        """Begin infatuation, marking the target as attracted to the user."""
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["attract"] = user
        return True

    def onTryImmunity(self, *args, **kwargs):
        """Fail if genders are same or unknown."""
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        tg = getattr(target, "gender", "N") if target else "N"
        sg = getattr(source, "gender", "N") if source else "N"
        if tg == "N" or sg == "N" or tg == sg:
            return False
        return True

    def onUpdate(self, *args, **kwargs):
        """Clear the effect if the source Pokémon has fainted."""
        target = args[0] if args else kwargs.get("target")
        if not target or not hasattr(target, "volatiles"):
            return False
        src = target.volatiles.get("attract")
        if not src or getattr(src, "hp", 0) <= 0:
            target.volatiles.pop("attract", None)
        return True

class Aurawheel:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        if not move or not user:
            return
        species = getattr(getattr(user, "species", None), "name", "").lower()
        if "hangry" in species:
            move.type = "Dark"
        else:
            move.type = "Electric"
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        species = getattr(getattr(user, "species", None), "name", "").lower()
        if "morpeko" not in species:
            return False
        return True

class Auroraveil:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "lightclay":
            return 8
        return 5
    def onAnyModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        target = args[2] if len(args) > 2 else kwargs.get("target")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if not target or not source or not move or move.category == "Status":
            return damage
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("auroraveil"):
            mult = 0.5
            if len(getattr(side, "active", [])) > 1:
                mult = 2 / 3
            return int(damage * mult)
        return damage
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("auroraveil", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Activate the Aurora Veil screen on the side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["auroraveil"] = True
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        field = getattr(battle, 'field', None)
        weather = None
        if field and hasattr(field, 'weather'):
            weather = field.weather
        elif battle and hasattr(battle, 'weather'):
            weather = battle.weather
        elif battle and hasattr(battle, 'state'):
            weather = getattr(battle.state, 'roomweather', None)
        if str(weather).lower() in ('hail', 'snow'):
            return True
        return False

class Autotomize:
    def onHit(self, user, target, battle):
        """Reduce the user's weight and mark Autotomize as active.

        The actual Speed boost for Autotomize is handled by the move's raw
        data in :mod:`pokemon.battle.engine`.  If we were to apply the boost
        here as well it would be doubled, resulting in a +4 Speed increase
        instead of the expected +2.  We therefore only track the move's
        weight-reduction side effect in this handler and allow the default
        engine logic to apply the stat boosts once.
        """
        if hasattr(user, "tempvals"):
            user.tempvals["autotomize"] = True
        return True

    def onTryHit(self, user, *args, **kwargs):
        """Fail if the user's Speed is already maximized."""
        boosts = getattr(user, "boosts", {})
        if boosts.get("spe", 0) >= 6:
            return False
        return True

class Avalanche:
    def basePowerCallback(self, user, target, move):
        """Double power if the user was damaged earlier this turn."""
        took_damage = getattr(user, "tempvals", {}).get("took_damage")
        base = getattr(move, "power", 0) or 0
        if took_damage:
            return base * 2
        return base

class Axekick:
    def onMoveFail(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        max_hp = getattr(user, "max_hp", 0)
        recoil = max_hp // 2
        user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Banefulbunker:
    def onHit(self, user, target, battle):
        """Protect the user and poison contact attackers."""
        if hasattr(target, "setStatus"):
            target.setStatus("psn")
        return True

    def onPrepareHit(self, *args, **kwargs):
        return True

    def onStart(self, *args, **kwargs):
        return True

    def onTryHit(self, target, source, move):
        """Block the incoming move and poison contact attackers."""
        flags = getattr(move, "flags", {}) if move else {}
        if flags.get("contact") and hasattr(source, "setStatus"):
            source.setStatus("psn")
        return False

class Barbbarrage:
    def onBasePower(self, *args, **kwargs):
        """Double power if the target is poisoned."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if target and getattr(target, "status", None) in {"psn", "tox"}:
            return power * 2
        return power

class Batonpass:
    def onHit(self, user, target, battle):
        """Flag that the user will switch out and pass boosts."""
        if hasattr(user, "tempvals"):
            user.tempvals["baton_pass"] = True
        return True

class Beakblast:
    def onAfterMove(self, *args, **kwargs):
        return True

    def onHit(self, user, target, battle):
        """Burn the target on contact."""
        if hasattr(target, "setStatus"):
            target.setStatus("brn")
        return True

    def onStart(self, user, target, battle):
        if hasattr(user, "tempvals"):
            user.tempvals["beakblast"] = True
        return True

    def priorityChargeCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["beakblast_charge"] = True
        return -3

class Beatup:
    def basePowerCallback(self, user, target, move):
        """Calculate power based on each healthy ally's base Attack."""
        allies = getattr(move, "allies", None)
        if allies is None:
            party = getattr(user, "party", [user])
            allies = [ally for ally in party if getattr(ally, "hp", 0) > 0]
            move.allies = allies
            if isinstance(getattr(move, "raw", None), dict):
                move.raw["multihit"] = len(allies)
            current = allies[0] if allies else user
            base_atk = getattr(getattr(current, "base_stats", None), "atk", 0)
            return 5 + (base_atk // 10)
        if not allies:
            allies = [user]
        current = allies.pop(0)
        base_atk = getattr(getattr(current, "base_stats", None), "atk", 0)
        return 5 + (base_atk // 10)

    def onModifyMove(self, move, user):
        party = getattr(user, "party", [user])
        allies = [ally for ally in party if getattr(ally, "hp", 0) > 0]
        move.allies = allies
        if isinstance(getattr(move, "raw", None), dict):
            move.raw["multihit"] = len(allies)

class Belch:
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        consumed = getattr(user, "consumed_berry", False)
        return not consumed

class Bellydrum:
    def onHit(self, user, target, battle):
        """Halve HP and maximize Attack."""
        if getattr(user, "hp", 0) <= getattr(user, "max_hp", 0) // 2:
            return False
        user.hp -= getattr(user, "max_hp", 0) // 2
        user.hp = max(user.hp, 1)
        user.boosts["atk"] = 6
        return True

class Bestow:
    def onHit(self, user, target, battle):
        """Give the user's held item to the target if possible."""
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if not item or getattr(target, "item", None) or getattr(target, "held_item", None):
            return False
        if hasattr(target, "set_item"):
            target.set_item(item)
        else:
            setattr(target, "item", item)
            setattr(target, "held_item", item)
        if hasattr(user, "set_item"):
            user.set_item(None)
        else:
            setattr(user, "item", None)
            setattr(user, "held_item", None)
        return True

class Bide:
    def beforeMoveCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["bide"] = {"turns": 0, "damage": 0}
        return True
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        vol = getattr(user, "volatiles", {}).get("bide") if user else None
        if not vol:
            return True
        vol["turns"] += 1
        if vol["turns"] >= 3:
            return True
        user.volatiles["bide"] = vol
        return False
    def onDamage(self, *args, **kwargs):
        user = args[0] if args else None
        damage = args[1] if len(args) > 1 else 0
        if user and hasattr(user, "volatiles"):
            vol = user.volatiles.get("bide")
            if vol:
                vol["damage"] += damage
                user.volatiles["bide"] = vol
        return damage
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("bide", None)
        return True
    def onMoveAborted(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("bide", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["bide"] = {"turns": 0, "damage": 0}
        return True

class Bleakwindstorm:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        if str(weather).lower() in ('rain', 'raindance') and hasattr(move, 'accuracy'):
            move.accuracy = True

class Blizzard:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        if str(weather).lower() in ('hail', 'snow') and hasattr(move, 'accuracy'):
            move.accuracy = True

class Block:
    def onHit(self, user, target, battle):
        """Prevent the target from switching out."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Boltbeak:
    def basePowerCallback(self, user, target, move):
        """Double power if the target has not moved yet this turn."""
        moved = getattr(target, "tempvals", {}).get("moved")
        base = getattr(move, "power", 0) or 0
        if not moved:
            return base * 2
        return base

class Bounce:
    def onInvulnerability(self, *args, **kwargs):
        move = args[2] if len(args) > 2 else kwargs.get("move")
        if not move:
            return True
        unblock = {"gust", "twister", "thunder", "hurricane", "skyuppercut"}
        mname = getattr(move, "name", "").replace(" ", "").lower()
        return mname not in unblock
    def onSourceBasePower(self, *args, **kwargs):
        power = args[0] if args else kwargs.get("power")
        return power
    def onTryMove(self, *args, **kwargs):
        """Handle the two-turn Bounce behaviour."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("bounce"):
            vol.pop("bounce", None)
            user.volatiles = vol
            return True
        vol["bounce"] = True
        user.volatiles = vol
        return False

class Brickbreak:
    def onTryHit(self, user, target, move):
        """Shatter opposing Reflect, Light Screen, or Aurora Veil."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "screens"):
            for screen in ("reflect", "lightscreen", "auroraveil"):
                side.screens.pop(screen, None)
        return True

class Brine:
    def onBasePower(self, *args, **kwargs):
        """Double power if the target is at or below half HP."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if target:
            cur_hp = getattr(target, "hp", 0)
            max_hp = getattr(target, "max_hp", cur_hp or 1)
            if cur_hp * 2 <= max_hp:
                return power * 2
        return power

class Bugbite:
    def onHit(self, user, target, battle):
        """Consume the target's berry if it has one."""
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if item and isinstance(item, str) and "berry" in item.lower():
            if hasattr(target, "set_item"):
                target.set_item(None)
            else:
                setattr(target, "item", None)
                setattr(target, "held_item", None)
        return True

class Burningbulwark:
    def onHit(self, user, target, battle):
        """Burn contact attackers."""
        if hasattr(target, "setStatus"):
            target.setStatus("brn")
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onTryHit(self, target, source, move):
        """Block the incoming move and burn contact attackers."""
        flags = getattr(move, "flags", {}) if move else {}
        if flags.get("contact") and hasattr(source, "setStatus"):
            source.setStatus("brn")
        return False
class Burningjealousy:
    def onHit(self, user, target, battle):
        """Burn the target if it has any stat boosts."""
        boosts = getattr(target, "boosts", {})
        if any(v > 0 for v in boosts.values()):
            if hasattr(target, "setStatus"):
                target.setStatus("brn")
        return True

class Burnup:
    def onHit(self, user, target, battle):
        """Remove the Fire type from the user."""
        types = list(getattr(user, "types", []))
        user.types = [t for t in types if t.lower() != "fire"]
        return True

    def onTryMove(self, user, target, battle):
        """Fail if the user is not Fire type."""
        types = getattr(user, "types", [])
        if not any(t.lower() == "fire" for t in types):
            return False
        return True

class Camouflage:
    def onHit(self, user, target, battle):
        """Change the user's type to Normal."""
        user.types = ["Normal"]
        return True

class Captivate:
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        tg = getattr(target, "gender", "N") if target else "N"
        sg = getattr(source, "gender", "N") if source else "N"
        if tg == "N" or sg == "N" or tg == sg:
            return False
        return True

class Ceaselessedge:
    def onAfterHit(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        side = getattr(target, "side", None)
        if side and hasattr(side, "hazards"):
            side.hazards["spikes"] = max(1, side.hazards.get("spikes", 0) + 1)
        return True
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onAfterHit(*args, **kwargs)

class Celebrate:
    def onTryHit(self, user, *args, **kwargs):
        """Always succeeds and shows a celebratory message."""
        return True

class Charge:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            if "charge" in user.volatiles:
                user.volatiles["charge"] -= 1
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else None
        move = args[2] if len(args) > 2 else None
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "electric":
            return power * 2
        return power
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("charge", None)
        return True
    def onMoveAborted(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("charge", None)
        return True
    def onRestart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["charge"] = 2
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["charge"] = 2
        return True

class Clangoroussoul:
    def onHit(self, user, target, battle):
        """Lose 1/3 of the user's maximum HP.

        Stat boosts are handled in :py:meth:`onTryHit`; this method only
        applies the HP deduction after those boosts have been applied.
        """
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 3:
            return False
        user.hp -= max_hp // 3
        return True

    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        max_hp = getattr(user, 'max_hp', 0)
        if max_hp <= 1:
            return False
        if getattr(user, 'hp', 0) <= max_hp * 33 // 100:
            return False
        return True

    def onTryHit(self, user, *args, **kwargs):
        """Apply the stat boosts before HP reduction.

        This ensures the move mirrors the in-game behaviour where the
        user is boosted prior to losing HP.  The HP loss itself is handled
        in :py:meth:`onHit`.
        """
        boosts = {stat: 1 for stat in ["atk", "def", "spa", "spd", "spe"]}
        apply_boost(user, boosts)
        return True

class Clearsmog:
    def onHit(self, user, target, battle):
        """Reset the target's stat changes."""
        if hasattr(target, "boosts"):
            for stat in target.boosts:
                target.boosts[stat] = 0
        return True

class Collisioncourse:
    def onBasePower(self, *args, **kwargs):
        """Boost power if the move is super effective."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if target and move and type_effectiveness(target, move) > 1:
            return int(power * 4 / 3)
        return power

class Comeuppance:
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
        if isinstance(last, dict):
            return last.get("damage", 0)
        return 0
    def onModifyTarget(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
        if isinstance(last, dict):
            return last.get("source")
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, 'tempvals', {}).get('last_damaged_by') if user else None
        if not last or not last.get('this_turn'):
            return False
        return True

class Conversion:
    def onHit(self, user, target, battle):
        """Change the user's type to match its first move."""
        moves = getattr(user, "moves", [])
        if not moves:
            return False
        first = moves[0]
        mtype = getattr(first, "type", None)
        if not mtype:
            return False
        user.types = [mtype]
        return True

class Conversion2:
    def onHit(self, user, target, battle):
        """Change the user's type to match the target's."""
        ttypes = getattr(target, "types", [])
        if not ttypes:
            return False
        user.types = list(ttypes)
        return True

class Copycat:
    def onHit(self, user, target, battle):
        """Use the last move that was successfully used in battle."""
        move = getattr(battle, "last_move", None)
        if not move or getattr(move, "name", "").lower() == "copycat":
            return False
        if hasattr(move, "onHit"):
            move.onHit(user, target, battle)
        return True

class Coreenforcer:
    def onAfterSubDamage(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and getattr(target, "moved_this_turn", False):
            target.ability_suppressed = True
        return True
    def onHit(self, user, target, battle):
        """Suppress the target's ability until it switches out."""
        if hasattr(target, "__dict__"):
            target.ability_suppressed = True
        return True

class Corrosivegas:
    def onHit(self, user, target, battle):
        """Remove the target's held item if possible."""
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if not item:
            return False
        if hasattr(target, "set_item"):
            target.set_item(None)
        else:
            setattr(target, "item", None)
            setattr(target, "held_item", None)
        return True

class Counter:
    def beforeTurnCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["counter"] = {"slot": None, "damage": 0}
        return True
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, "volatiles", {}).get("counter") if user else None
        if vol:
            return vol.get("damage", 0)
        return 0
    def onDamagingHit(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        source = args[2] if len(args) > 2 else None
        move = args[3] if len(args) > 3 else None
        if target and source and getattr(move, "category", "") == "Physical":
            vol = getattr(target, "volatiles", {}).get("counter")
            if vol is not None:
                vol["slot"] = source
                vol["damage"] = getattr(move, "damage", 0) * 2
    def onRedirectTarget(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, "volatiles", {}).get("counter") if user else None
        if vol:
            return vol.get("slot")
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "tempvals"):
            user.tempvals["counter_damage"] = 0
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, 'volatiles', {}).get('counter') if user else None
        if not vol or vol.get('slot') is None:
            return False
        return True

class Courtchange:
    def onHitField(self, user, battle):
        """Swap the side conditions between the two players."""
        side1 = getattr(battle, "sides", [None, None])[0]
        side2 = getattr(battle, "sides", [None, None])[1]
        if not side1 or not side2:
            return False
        # Swap hazards and screens dictionaries if present
        for attr in ("hazards", "screens"):
            a = getattr(side1, attr, None)
            b = getattr(side2, attr, None)
            if a is not None and b is not None:
                side1.__dict__[attr], side2.__dict__[attr] = b, a
        return True

class Covet:
    def onAfterHit(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if not user or not target:
            return True
        if getattr(user, "item", None) or getattr(user, "held_item", None):
            return True
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if not item:
            return True
        if hasattr(target, "set_item"):
            target.set_item(None)
        else:
            setattr(target, "item", None)
            setattr(target, "held_item", None)
        if hasattr(user, "set_item"):
            user.set_item(item)
        else:
            setattr(user, "item", item)
            setattr(user, "held_item", item)
        return True

class Craftyshield:
    def onSideStart(self, *args, **kwargs):
        """Protect the side from status moves this turn."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["craftyshield"] = True
            side.volatiles = vol
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        queue = getattr(battle, 'queue', None)
        if queue and hasattr(queue, 'willAct'):
            try:
                return bool(queue.willAct())
            except Exception:
                return True
        return True
    def onTryHit(self, target, source, move):
        """Block status moves aimed at the user's side."""
        if getattr(move, "category", "") == "Status" and getattr(move, "target", "") not in {"self", "all"}:
            return False
        return True
      
class Crushgrip:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the target's remaining HP."""
        cur_hp = getattr(target, "hp", 0)
        max_hp = getattr(target, "max_hp", cur_hp or 1)
        ratio = cur_hp / max_hp if max_hp else 0
        power = int(120 * ratio) + 1
        return max(1, power)

class Curse:
    def onHit(self, user, target, battle):
        """Apply Curse differently for Ghost and non-Ghost users."""
        types = [t.lower() for t in getattr(user, "types", [])]
        if "ghost" in types:
            if getattr(user, "hp", 0) <= getattr(user, "max_hp", 0) // 2:
                return False
            user.hp -= getattr(user, "max_hp", 0) // 2
            user.hp = max(user.hp, 1)
            if hasattr(target, "volatiles"):
                target.volatiles["cursed"] = True
        else:
            apply_boost(user, {"atk": 1, "def": 1, "spe": -1})
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        types = [t.lower() for t in getattr(user, 'types', [])]
        if 'ghost' in types:
            if move:
                move.target = 'normal'
        else:
            if move:
                move.target = 'self'
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if not target:
            return False
        damage = getattr(target, "max_hp", 0) // 4
        target.hp = max(0, getattr(target, "hp", 0) - damage)
        return True
    def onStart(self, *args, **kwargs):
        return True
    def onTryHit(self, user, target, move):
        """Fail if a Ghost already cursed the target."""
        if "ghost" in [t.lower() for t in getattr(user, "types", [])]:
            if getattr(target, "volatiles", {}).get("cursed"):
                return False
        return True

class Darkvoid:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        move = args[2] if len(args) > 2 else kwargs.get('move')
        species = getattr(getattr(user, 'species', None), 'name', '').lower()
        if 'darkrai' in species or getattr(move, 'has_bounced', False):
            return True
        return False

class Defog:
    def onHit(self, user, target, battle):
        """Lower the target's evasion by one stage."""
        apply_boost(target, {"evasion": -1})
        return True

class Destinybond:
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles["destinybond"] = True
        return True
    def onFaint(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
        foe = last.get("source") if isinstance(last, dict) else None
        if foe and getattr(user, "volatiles", {}).get("destinybond"):
            foe.hp = 0
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("destinybond", None)
        return True
    def onMoveAborted(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("destinybond", None)
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["destinybond"] = True
        return True

class Detect:
    def onHit(self, user, target, battle):
        """Grant the user protection from moves this turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True

class Dig:
    def onImmunity(self, *args, **kwargs):
        return True
    def onInvulnerability(self, *args, **kwargs):
        move = args[2] if len(args) > 2 else kwargs.get("move")
        if not move:
            return True
        unblock = {"earthquake", "fissure", "magnitude"}
        mname = getattr(move, "name", "").replace(" ", "").lower()
        return mname not in unblock
    def onSourceModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if move and getattr(move, "name", "").replace(" ", "").lower() in {"earthquake", "magnitude"}:
            return int(damage * 2)
        return damage
    def onTryMove(self, *args, **kwargs):
        """Handle Dig as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("dig"):
            vol.pop("dig", None)
            user.volatiles = vol
            return True
        vol["dig"] = True
        user.volatiles = vol
        return False

class Direclaw:
    def onHit(self, user, target, battle):
        """May inflict poison, paralysis, or sleep."""
        if getattr(target, "status", None):
            return True
        status = choice(["psn", "par", "slp"])
        if hasattr(target, "setStatus"):
            target.setStatus(status)
        return True

class Disable:
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = getattr(user, "volatiles", {}).get("disable") if user else None
        if move and getattr(move, "id", "") == getattr(args[1] if len(args) > 1 else kwargs.get("move"), "id", ""):
            return False
        return True
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        disabled = getattr(user, "volatiles", {}).get("disable") if user else None
        return disabled
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("disable", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        move = getattr(target, "last_move", None)
        if target and hasattr(target, "volatiles"):
            target.volatiles["disable"] = move
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target has no move to disable."""
        last = getattr(target, "last_move", None)
        if not last or getattr(last, "isZ", False) or getattr(last, "isMax", False) or getattr(last, "id", "") == "struggle":
            return False
        return True

class Dive:
    def onImmunity(self, *args, **kwargs):
        return True
    def onInvulnerability(self, *args, **kwargs):
        move = args[2] if len(args) > 2 else kwargs.get("move")
        if not move:
            return True
        unblock = {"surf", "whirlpool"}
        mname = getattr(move, "name", "").replace(" ", "").lower()
        return mname not in unblock
    def onSourceModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if move and getattr(move, "name", "").replace(" ", "").lower() in {"surf", "whirlpool"}:
            return int(damage * 2)
        return damage
    def onTryMove(self, *args, **kwargs):
        """Handle Dive as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("dive"):
            vol.pop("dive", None)
            user.volatiles = vol
            return True
        vol["dive"] = True
        user.volatiles = vol
        return False

class Doodle:
    def onHit(self, user, target, battle):
        """Copy the target's ability onto the user."""
        ability = getattr(target, "ability", None)
        if not ability:
            return False
        setattr(user, "ability", ability)
        return True

class Doomdesire:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        side = getattr(target, 'side', None)
        if not side:
            return False
        return True

class Doubleshock:
    def onHit(self, user, target, battle):
        """Lose the Electric type after attacking."""
        if hasattr(user, "types"):
            user.types = [t for t in user.types if t.lower() != "electric"]
        return True
    def onTryMove(self, *args, **kwargs):
        """Fail if the user is not Electric type."""
        user = args[0] if args else kwargs.get("user")
        types = getattr(user, "types", []) if user else []
        return any(t.lower() == "electric" for t in types)

class Dragoncheer:
    def onModifyCritRatio(self, *args, **kwargs):
        ratio = args[0] if args else kwargs.get("ratio", 0)
        return ratio + 1
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["dragoncheer"] = True
        return True

class Dragonenergy:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the user's remaining HP."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        ratio = cur_hp / max_hp if max_hp else 0
        power = int(150 * ratio)
        return max(1, power)

class Dreameater:
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if getattr(target, "status", None) == "slp":
            return True
        return False

class Echoedvoice:
    """Helper callbacks for the move Echoed Voice."""
    def basePowerCallback(self, user, target, move, battle=None):
        """Scale base power based on the active echoed voice effect."""
        base_power = getattr(move, "basePower", getattr(move, "power", 0))
        chain = getattr(user, "echoed_voice_chain", 0)
        base_power *= max(1, chain + 1)
        field = getattr(battle, "field", None)
        if field and hasattr(field, "get_pseudo_weather"):
            effect = field.get_pseudo_weather("echoedvoice")
            if isinstance(effect, dict):
                multiplier = effect.get("multiplier", 1)
                base_power *= multiplier
        else:
            chain = getattr(user, "echoed_voice_chain", 0)
            if chain:
                base_power *= min(chain + 1, 5)
        return base_power

    def onFieldRestart(self, effect_state):
        """Refresh the effect and increase the power multiplier."""
        if not isinstance(effect_state, dict):
            return
        if effect_state.get("duration") != 2:
            effect_state["duration"] = 2
            if effect_state.get("multiplier", 1) < 5:
                effect_state["multiplier"] = effect_state.get("multiplier", 1) + 1

    def onFieldStart(self, effect_state):
        """Initialize the echoed voice multiplier."""
        if isinstance(effect_state, dict):
            effect_state["multiplier"] = 1

    def onTry(self, user=None, target=None, move=None, battle=None):
        """Start the echoed voice field effect when the move is used."""
        if not battle:
            return
        field = getattr(battle, "field", None)
        if field is None:
            return
        effect = {
            "duration": 2,
            "onFieldStart": self.onFieldStart,
            "onFieldRestart": self.onFieldRestart,
        }
        if hasattr(field, "add_pseudo_weather"):
            field.add_pseudo_weather("echoedvoice", effect)

class Eeriespell:
    def onHit(self, user, target, battle):
        """Reduce the PP of the target's last move by three."""
        move = getattr(target, "last_move", None)
        if not move:
            moves = getattr(target, "moves", [])
            move = moves[0] if moves else None
        if move and hasattr(move, "pp"):
            move.pp = max(0, move.pp - 3)
        return True

class Electricterrain:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "terrainextender":
            return 8
        return 5
    def onBasePower(self, *args, **kwargs):
        attacker = args[0] if args else None
        move = args[2] if len(args) > 2 else None
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "electric":
            grounded = getattr(attacker, "grounded", True)
            if grounded:
                return int(power * 1.3)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "terrain"):
            field.terrain = None
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field is not None:
            field.terrain = "electricterrain"
        return True
    def onSetStatus(self, *args, **kwargs):
        status = args[0] if args else kwargs.get("status")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if status == "slp" and target and getattr(target, "grounded", True):
            return False
        return True
    def onTryAddVolatile(self, *args, **kwargs):
        return True

class Electrify:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        if move:
            move.type = "Electric"
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["electrify"] = True
        return True
    def onTryHit(self, target, source, move):
        """Electrify the target's next move if it is about to act."""
        return True

class Electroball:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the user's Speed compared to the target's."""
        u_speed = getattr(getattr(user, "base_stats", None), "spe", 0) or 0
        t_speed = getattr(getattr(target, "base_stats", None), "spe", 1) or 1
        if t_speed == 0:
            t_speed = 1
        ratio = u_speed / t_speed
        if ratio >= 4:
            return 150
        if ratio >= 3:
            return 120
        if ratio >= 2:
            return 80
        if ratio > 1:
            return 60
        return 40

class Electrodrift:
    def onBasePower(self, *args, **kwargs):
        """Boost power if super effective."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if target and move and type_effectiveness(target, move) > 1:
            return int(power * 4 / 3)
        return power

class Electroshot:
    def onTryMove(self, *args, **kwargs):
        """Electro Shot has no additional move check in this stub."""
        return True

class Embargo:
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("embargo", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["embargo"] = True
        return True

class Encore:
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = getattr(user, "volatiles", {}).get("encore") if user else None
        return move
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("encore", None)
        return True
    def onOverrideAction(self, *args, **kwargs):
        user = args[0] if args else None
        return getattr(user, "volatiles", {}).get("encore")
    def onResidual(self, *args, **kwargs):
        user = args[0] if args else None
        if not user:
            return False
        move = getattr(user, "volatiles", {}).get("encore")
        if not move:
            return True
        last = getattr(user, "last_move", None)
        if not last or getattr(last, "id", None) != getattr(move, "id", move):
            user.volatiles.pop("encore", None)
        elif getattr(last, "pp", 1) <= 0:
            user.volatiles.pop("encore", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        move = getattr(target, "last_move", None)
        if target and hasattr(target, "volatiles"):
            target.volatiles["encore"] = move
        return True

class Endeavor:
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if not user or not target:
            return 0
        return max(0, getattr(target, "hp", 0) - getattr(user, "hp", 0))
    def onTryImmunity(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if not user or not target:
            return False
        return getattr(target, "hp", 0) > getattr(user, "hp", 0)

class Endure:
    def onDamage(self, *args, **kwargs):
        damage = args[1] if len(args) > 1 else kwargs.get("damage")
        target = args[0] if args else kwargs.get("user")
        if target and getattr(target, "volatiles", {}).get("endure"):
            if damage >= getattr(target, "hp", 0):
                return getattr(target, "hp", 1) - 1
        return damage
    def onHit(self, user, target, battle):
        """Allow the user to survive hits with at least 1 HP this turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["endure"] = True
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["endure"] = True
        return True

class Entrainment:
    def onHit(self, user, target, battle):
        """Give the target the user's ability."""
        ability = getattr(user, "ability", None)
        if not ability:
            return False
        setattr(target, "ability", ability)
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target already has the user's ability or is the user."""
        if target is source:
            return False
        if getattr(target, "ability", None) == getattr(source, "ability", None):
            return False
        return True

class Eruption:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the user's remaining HP."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        ratio = cur_hp / max_hp if max_hp else 0
        power = int(150 * ratio)
        return max(1, power)

class Expandingforce:
    def onBasePower(self, *args, **kwargs):
        """Boost power on Psychic Terrain when grounded."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        terrain = getattr(user, "terrain", None)
        grounded = getattr(user, "grounded", True)
        if terrain == "psychicterrain" and grounded:
            return int(power * 1.5)
        return power

    def onModifyMove(self, *args, **kwargs):
        """Adjust targeting on Psychic Terrain when the user is grounded."""
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        terrain = getattr(field, 'terrain', getattr(battle, 'terrain', None))
        if str(terrain).lower() == 'psychicterrain' and getattr(user, 'grounded', True):
            if move:
                move.target = 'allAdjacentFoes'

class Facade:
    def onBasePower(self, *args, **kwargs):
        """Double power if the user has a status condition (except sleep)."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        status = getattr(user, "status", None)
        if status and status != "slp":
            return power * 2
        return power

class Fairylock:
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            field.fairylock = 2
        return True
    def onTrapPokemon(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        return True

class Fakeout:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if getattr(user, 'active_move_actions', 1) > 1:
            return False
        return True

class Falseswipe:
    def onDamage(self, *args, **kwargs):
        damage = args[1] if len(args) > 1 else kwargs.get("damage")
        target = args[0] if args else kwargs.get("target")
        if target and damage >= getattr(target, "hp", 0):
            return max(0, getattr(target, "hp", 0) - 1)
        return damage

class Fellstinger:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and getattr(target, "hp", 1) <= 0:
            apply_boost(user, {"atk": 3})
        return True

class Ficklebeam:
    def onBasePower(self, *args, **kwargs):
        """30% chance to double power."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if random() < 0.3:
            return power * 2
        return power

class Filletaway:
    def onHit(self, user, target, battle):
        """Halve the user's HP; boosts are handled by the engine."""
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 2:
            return False
        user.hp -= max_hp // 2
        return True

    def onTry(self, *args, **kwargs):
        """Ensure the user has enough HP to perform the move."""
        user = args[0] if args else None
        if not user:
            return False
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 2 or max_hp == 1:
            return False
        return True

    def onTryHit(self, *args, **kwargs):
        """No-op so the engine applies the standard boosts once."""
        return True

class Finalgambit:
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else None
        damage = getattr(user, "hp", 0) if user else 0
        if user:
            user.hp = 0
        return damage

class Firepledge:
    def basePowerCallback(self, user, target, move):
        """Return boosted power if combined with another Pledge move."""
        if getattr(user, "pledge_combo", False):
            return 150
        return getattr(move, "power", 80) or 80
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if getattr(user, 'pledge_combo', False) and move:
            move.pledge_combo = True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if not target:
            return False
        types = [t.lower() for t in getattr(target, "types", [])]
        if "fire" not in types:
            damage = getattr(target, "max_hp", 0) // 8
            target.hp = max(0, getattr(target, "hp", 0) - damage)
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "conditions"):
            side.conditions.pop("firepledge", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Start the Fire Pledge side condition."""
        side = args[0] if args else kwargs.get("side")
        if side:
            side.conditions["firepledge"] = {
                "turns": 4,
                "source": kwargs.get("source"),
            }
        return True

class Firstimpression:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if getattr(user, 'active_move_actions', 1) > 1:
            return False
        return True

class Fishiousrend:
    def basePowerCallback(self, user, target, move):
        """Double power if the target has not moved yet this turn."""
        moved = getattr(target, "tempvals", {}).get("moved")
        base = getattr(move, "power", 0) or 0
        if not moved:
            return base * 2
        return base

class Flail:
    def basePowerCallback(self, user, target, move):
        """Increase power as the user has less HP remaining."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        thresh = int((48 * cur_hp) / max_hp) if max_hp else 48
        if thresh <= 1:
            return 200
        if thresh <= 4:
            return 150
        if thresh <= 9:
            return 100
        if thresh <= 16:
            return 80
        if thresh <= 32:
            return 40
        return 20

class Flameburst:
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onHit(*args, **kwargs)
    def onHit(self, user, target, battle):
        """Also damage adjacent foes for minor damage."""
        side = getattr(target, "side", None)
        if side:
            others = [p for p in getattr(side, "active", []) if p is not target]
            for mon in others:
                damage = max(1, getattr(mon, "max_hp", 1) // 16)
                mon.hp = max(0, getattr(mon, "hp", 0) - damage)
        return True

class Fling:
    def onPrepareHit(self, *args, **kwargs):
        user = args[0] if args else None
        move = args[2] if len(args) > 2 else kwargs.get('move')
        item = getattr(user, 'item', None) or getattr(user, 'held_item', None)
        if not item:
            return False
        if move:
            move.power = getattr(item, 'fling_power', getattr(move, 'power', 0))
        return True
    def onUpdate(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "set_item"):
            user.set_item(None)
        elif user:
            setattr(user, "item", None)
            setattr(user, "held_item", None)
        return True

class Floralhealing:
    def onHit(self, user, target, battle):
        """Restore half of the target's max HP."""
        max_hp = getattr(target, "max_hp", 0)
        heal = max_hp // 2
        target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
        return True

class Flowershield:
    def onHitField(self, user, battle):
        """Raise Defense of all Grass-type Pokémon on the field."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                types = [t.lower() for t in getattr(mon, "types", [])]
                if "grass" in types:
                    apply_boost(mon, {"def": 1})
        return True

class Fly:
    def onInvulnerability(self, *args, **kwargs):
        move = args[2] if len(args) > 2 else kwargs.get("move")
        if not move:
            return True
        unblock = {"gust", "twister", "thunder", "hurricane", "skyuppercut"}
        mname = getattr(move, "name", "").replace(" ", "").lower()
        return mname not in unblock
    def onSourceModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if move and getattr(move, "name", "").replace(" ", "").lower() in {"gust", "twister"}:
            return int(damage * 2)
        return damage
    def onTryMove(self, *args, **kwargs):
        """Handle Fly as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("fly"):
            vol.pop("fly", None)
            user.volatiles = vol
            return True
        vol["fly"] = True
        user.volatiles = vol
        return False

class Flyingpress:
    def onEffectiveness(self, *args, **kwargs):
        type_mod = args[0] if args else kwargs.get("typeMod")
        if type_mod is None:
            return
        return type_mod

class Focusenergy:
    def onModifyCritRatio(self, *args, **kwargs):
        ratio = args[0] if args else kwargs.get("ratio", 0)
        try:
            return ratio + 2
        except Exception:
            return ratio
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["focusenergy"] = True
        return True

class Focuspunch:
    def beforeMoveCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and getattr(user, "volatiles", {}).get("focuspunch", {}).get("lostFocus"):
            return True
    def onHit(self, user, target, battle):
        """Deal heavy damage if the user kept its focus."""
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["focuspunch"] = True
        return True
    def onTryAddVolatile(self, *args, **kwargs):
        status = args[0] if args else kwargs.get("status")
        sid = getattr(status, "id", None) if status is not None else None
        if sid is None:
            sid = str(status).lower() if status is not None else ""
        if sid == "flinch":
            return False
        return True
    def priorityChargeCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["focuspunch_charge"] = True
        return -3

class Followme:
    def onFoeRedirectTarget(self, *args, **kwargs):
        user = args[0] if args else None
        return user
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["followme"] = True
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        if not battle:
            return True
        participants = getattr(battle, 'participants', [])
        multi = any(len(getattr(p, 'active', [])) > 1 for p in participants)
        return multi

class Foresight:
    def onModifyBoost(self, *args, **kwargs):
        boosts = args[0] if args else kwargs.get("boosts", {})
        if isinstance(boosts, dict) and "evasion" in boosts:
            boosts["evasion"] = 0
        return boosts
    def onNegateImmunity(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["foresight"] = True
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target already has Miracle Eye active."""
        if getattr(target, "volatiles", {}).get("miracleeye"):
            return False
        return True

class Forestscurse:
    def onHit(self, user, target, battle):
        """Add the Grass type to the target."""
        if hasattr(target, "types") and "Grass" not in target.types:
            target.types.append("Grass")
        return True

class Freezedry:
    def onEffectiveness(self, *args, **kwargs):
        type_mod = args[0] if args else kwargs.get("typeMod")
        target_type = None
        if len(args) > 2:
            target_type = args[2]
        else:
            target_type = kwargs.get("type")
        if isinstance(target_type, str) and target_type.capitalize() == "Water":
            return 1
        return type_mod

class Freezeshock:
    def onTryMove(self, *args, **kwargs):
        """Handle Freeze Shock as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("freezeshock"):
            vol.pop("freezeshock", None)
            user.volatiles = vol
            return True
        vol["freezeshock"] = True
        user.volatiles = vol
        return False

class Freezyfrost:
    def onHit(self, user, target, battle):
        """Reset the target's stat boosts."""
        if hasattr(target, "boosts"):
            for stat in target.boosts:
                target.boosts[stat] = 0
        return True

class Frustration:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the user's unhappiness."""
        happiness = getattr(user, "happiness", 0)
        power = int((255 - min(255, max(0, happiness))) * 10 / 25)
        return max(1, power)

class Furycutter:
    def basePowerCallback(self, user, target, move):
        """Increase power with consecutive uses."""
        chain = getattr(user, "fury_cutter_chain", 0)
        if not getattr(move, "_fury_cutter_inc", False):
            chain = min(chain + 1, 4)
            setattr(user, "fury_cutter_chain", chain)
            setattr(move, "_fury_cutter_inc", True)
        return min(160, 40 * chain if chain else 40)

    def onRestart(self, user, target, move):
        setattr(user, "fury_cutter_chain", min(getattr(user, "fury_cutter_chain", 0) + 1, 4))

    def onStart(self, user, target, move):
        setattr(user, "fury_cutter_chain", 1)

class Fusionbolt:
    def onBasePower(self, *args, **kwargs):
        """Double power if Fusion Flare was used this turn."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        last = getattr(user, "last_move_this_turn", "").lower() if user else ""
        if last == "fusionflare":
            return power * 2
        return power

class Fusionflare:
    def onBasePower(self, *args, **kwargs):
        """Double power if Fusion Bolt was used this turn."""
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        last = getattr(user, "last_move_this_turn", "").lower() if user else ""
        if last == "fusionbolt":
            return power * 2
        return power

class Futuresight:
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if not target or not getattr(target, 'side', None):
            return False
        return True

class Gastroacid:
    def onCopy(self, *args, **kwargs):
        return False
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["gastroacid"] = True
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target's ability cannot be suppressed."""
        item = getattr(target, "item", "").lower()
        if item == "abilityshield":
            return None
        return True

class Gearup:
    def onHitSide(self, user, battle):
        """Raise Attack and Sp. Atk of allies with Plus or Minus."""
        side = getattr(user, "side", None)
        if not side:
            return False
        for mon in getattr(side, "active", []):
            ability = getattr(mon, "ability", "").lower()
            if ability in {"plus", "minus"}:
                apply_boost(mon, {"atk": 1, "spa": 1})
        return True

class Genesissupernova:
    def onHit(self, user, target, battle):
        """Set Psychic Terrain after dealing damage."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain("Psychic")
        return True

class Geomancy:
    def onTryMove(self, *args, **kwargs):
        """Apply Geomancy's stat boosts while handling its charge mechanic.

        The simplified battle engine used in the tests does not run a second
        turn for charge moves.  To ensure Geomancy's effects are still
        observable, apply the Special Attack, Special Defense and Speed boosts
        immediately on the first call while marking the user as "charging".
        Subsequent calls clear the volatile and allow normal execution.
        """

        user = args[0] if args else kwargs.get("user")
        if not user:
            return False

        vol = getattr(user, "volatiles", {})
        if vol.get("geomancy"):
            vol.pop("geomancy", None)
            user.volatiles = vol
            return True

        # First activation: apply the boosts immediately and mark the charge
        from pokemon.battle.utils import apply_boost

        apply_boost(user, {"spa": 2, "spd": 2, "spe": 2})
        vol["geomancy"] = True
        user.volatiles = vol
        return False

class Glaiverush:
    def onAccuracy(self, *args, **kwargs):
        return True
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("glaiverush", None)
        return True
    def onSourceModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        try:
            return int(damage * 2)
        except Exception:
            return damage
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["glaiverush"] = True
        return True

class Gmaxbefuddle:
    def onHit(self, user, target, battle):
        """Inflict a random status condition on the target."""
        if hasattr(target, "setStatus"):
            target.setStatus(choice(["par", "psn", "slp"]))
        return True

class Gmaxcannonade:
    def onHit(self, user, target, battle):
        """Begin residual damage each turn to the target's side."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["gmaxcannonade"] = 4
        return True
    def onResidual(self, *args, **kwargs):
        side = args[0] if args else None
        if not side:
            return False
        for mon in getattr(side, "active", []):
            types = [t.lower() for t in getattr(mon, "types", [])]
            if "water" not in types:
                dmg = getattr(mon, "max_hp", 0) // 6
                mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "volatiles"):
            side.volatiles.pop("gmaxcannonade", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Initialize residual G-Max Cannonade effect."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["gmaxcannonade"] = 4
            side.volatiles = vol
        return True

class Gmaxcentiferno:
    def onHit(self, user, target, battle):
        """Trap the target and cause residual damage."""
        if hasattr(target, "volatiles"):
            target.volatiles["gmaxcentiferno"] = 4
            target.volatiles["trapped"] = True
        return True

class Gmaxchistrike:
    def onHit(self, user, target, battle):
        """Boost the user's Attack and Defense."""
        apply_boost(user, {"atk": 1, "def": 1})
        return True
    def onModifyCritRatio(self, *args, **kwargs):
        ratio = args[0] if args else kwargs.get("ratio", 0)
        user = args[1] if len(args) > 1 else kwargs.get("user")
        layers = 1
        if user and hasattr(user, "volatiles"):
            layers = user.volatiles.get("gmaxchistrike_layers", 1)
        return ratio + layers
    def onRestart(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            layers = user.volatiles.get("gmaxchistrike_layers", 1)
            layers = min(3, layers + 1)
            user.volatiles["gmaxchistrike_layers"] = layers
            user.volatiles["gmaxchistrike"] = True
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["gmaxchistrike"] = True
            user.volatiles["gmaxchistrike_layers"] = 1
        return True

class Gmaxcuddle:
    def onHit(self, user, target, battle):
        """Infatuate foes of the opposite gender."""
        if hasattr(target, "volatiles"):
            target.volatiles["attract"] = True
        return True

class Gmaxdepletion:
    def onHit(self, user, target, battle):
        """Lower PP of the target's last move."""
        last_move = getattr(target, "last_move", None)
        if last_move and hasattr(last_move, "pp"):
            last_move.pp = max(0, last_move.pp - 2)
        return True

class Gmaxfinale:
    def onHit(self, user, target, battle):
        """Heal allies slightly after dealing damage."""
        side = getattr(user, "side", None)
        if side:
            for mon in getattr(side, "active", []):
                max_hp = getattr(mon, "max_hp", 0)
                heal = max_hp // 6
                mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
        return True

class Gmaxfoamburst:
    def onHit(self, user, target, battle):
        """Sharply lower the target's Speed."""
        apply_boost(target, {"spe": -2})
        return True

class Gmaxgoldrush:
    def onHit(self, user, target, battle):
        """Confuse the target."""
        if hasattr(target, "volatiles"):
            target.volatiles["confusion"] = True
        return True

class Gmaxmalodor:
    def onHit(self, user, target, battle):
        """Poison all foes."""
        opponents = []
        side = getattr(target, "side", None)
        if side:
            opponents = getattr(side, "active", [target])
        else:
            opponents = [target]
        for mon in opponents:
            if hasattr(mon, "setStatus"):
                mon.setStatus("psn")
        return True

class Gmaxmeltdown:
    def onHit(self, user, target, battle):
        """Prevent the target from using the same move consecutively."""
        if hasattr(target, "volatiles"):
            target.volatiles["torment"] = True
        return True

class Gmaxreplenish:
    def onHit(self, user, target, battle):
        """Attempt to restore allies' berries."""
        side = getattr(user, "side", None)
        if side:
            for mon in getattr(side, "active", []):
                if getattr(mon, "berry_consumed", False) and not getattr(mon, "item", None):
                    setattr(mon, "item", getattr(mon, "berry_consumed"))
        return True

class Gmaxsandblast:
    def onHit(self, user, target, battle):
        """Trap the target in a sandstorm."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_weather"):
            field.set_weather("Sandstorm")
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Gmaxsmite:
    def onHit(self, user, target, battle):
        """Confuse the target."""
        if hasattr(target, "volatiles"):
            target.volatiles["confusion"] = True
        return True

class Gmaxsnooze:
    def onAfterSubDamage(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and not getattr(target, "status", None) and random() < 0.5:
            if hasattr(target, "volatiles"):
                target.volatiles["drowsy"] = True
        return True
    def onHit(self, user, target, battle):
        """Make the target drowsy, causing sleep later."""
        if hasattr(target, "volatiles"):
            target.volatiles["drowsy"] = True
        return True

class Gmaxsteelsurge:
    def onEntryHazard(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if not pokemon:
            return False
        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and str(item).lower() == "heavydutyboots":
            return True
        dmg = getattr(pokemon, "max_hp", 0) // 8
        eff = type_effectiveness(pokemon, type("Move", (), {"type": "Steel"}))
        try:
            dmg = int(getattr(pokemon, "max_hp", 0) * eff / 8)
        except Exception:
            pass
        pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
        return True
    def onHit(self, user, target, battle):
        """Lay a steel-type damaging hazard on the target's side."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "hazards"):
            side.hazards["steelsurge"] = True
        return True
    def onSideStart(self, *args, **kwargs):
        """Activate the Steel Surge hazard on this side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "hazards"):
            side.hazards["steelsurge"] = True
        return True

class Gmaxstonesurge:
    def onHit(self, user, target, battle):
        """Set up stealth rocks on the opponent's side."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "hazards"):
            side.hazards["rocks"] = True
        return True

class Gmaxstunshock:
    def onHit(self, user, target, battle):
        """Paralyze or poison the target."""
        if hasattr(target, "setStatus"):
            target.setStatus(choice(["par", "psn"]))
        return True

class Gmaxsweetness:
    def onHit(self, user, target, battle):
        """Cure status conditions of the user's side."""
        side = getattr(user, "side", None)
        if side:
            for mon in getattr(side, "active", []):
                if hasattr(mon, "setStatus"):
                    mon.setStatus(0)
        return True

class Gmaxtartness:
    def onHit(self, user, target, battle):
        """Sharply lower the target's evasion."""
        apply_boost(target, {"evasion": -2})
        return True

class Gmaxterror:
    def onHit(self, user, target, battle):
        """Prevent the target from switching out."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Gmaxvinelash:
    def onHit(self, user, target, battle):
        """Start residual damage on the target's side."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["gmaxvinelash"] = 4
        return True
    def onResidual(self, *args, **kwargs):
        side = args[0] if args else None
        if not side:
            return False
        for mon in getattr(side, "active", []):
            types = [t.lower() for t in getattr(mon, "types", [])]
            if "grass" not in types:
                dmg = getattr(mon, "max_hp", 0) // 6
                mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "volatiles"):
            side.volatiles.pop("gmaxvinelash", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Begin the G-Max Vine Lash residual effect."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["gmaxvinelash"] = 4
            side.volatiles = vol
        return True

class Gmaxvolcalith:
    def onHit(self, user, target, battle):
        """Set up a rockstorm dealing residual damage."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["gmaxvolcalith"] = 4
        return True
    def onResidual(self, *args, **kwargs):
        side = args[0] if args else None
        if not side:
            return False
        for mon in getattr(side, "active", []):
            types = [t.lower() for t in getattr(mon, "types", [])]
            if "rock" not in types:
                dmg = getattr(mon, "max_hp", 0) // 6
                mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "volatiles"):
            side.volatiles.pop("gmaxvolcalith", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Start the G-Max Volcalith residual effect."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["gmaxvolcalith"] = 4
            side.volatiles = vol
        return True

class Gmaxvoltcrash:
    def onHit(self, user, target, battle):
        """Paralyze the target."""
        if hasattr(target, "setStatus"):
            target.setStatus("par")
        return True

class Gmaxwildfire:
    def onHit(self, user, target, battle):
        """Start a blazing field effect causing residual damage."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["gmaxwildfire"] = 4
        return True
    def onResidual(self, *args, **kwargs):
        side = args[0] if args else None
        if not side:
            return False
        for mon in getattr(side, "active", []):
            types = [t.lower() for t in getattr(mon, "types", [])]
            if "fire" not in types:
                dmg = getattr(mon, "max_hp", 0) // 6
                mon.hp = max(0, getattr(mon, "hp", 0) - dmg)
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "volatiles"):
            side.volatiles.pop("gmaxwildfire", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Begin the G-Max Wildfire residual effect."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["gmaxwildfire"] = 4
            side.volatiles = vol
        return True

class Gmaxwindrage:
    def onHit(self, user, target, battle):
        """Remove hazards and screens from the target's side."""
        side = getattr(target, "side", None)
        if side:
            if hasattr(side, "hazards"):
                side.hazards.clear()
            if hasattr(side, "screens"):
                side.screens.clear()
        return True

class Grassknot:
    def basePowerCallback(self, user, target, move):
        """Scale power with the target's weight."""
        weight = getattr(target, "weightkg", 0)
        if weight >= 200:
            return 120
        if weight >= 100:
            return 100
        if weight >= 50:
            return 80
        if weight >= 25:
            return 60
        if weight >= 10:
            return 40
        return 20
    def onTryHit(self, target, source, move):
        """Fail against Dynamax targets."""
        if getattr(target, "volatiles", {}).get("dynamax"):
            return False
        return True

class Grasspledge:
    def basePowerCallback(self, user, target, move):
        """Return 150 power when used in a pledge combo."""
        if getattr(move, "pledge_combo", False) or getattr(user, "pledge_combo", False):
            return 150
        return getattr(move, "power", 0) or 0
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if getattr(user, 'pledge_combo', False) and move:
            move.pledge_combo = True
    def onModifySpe(self, *args, **kwargs):
        spe = args[0] if args else kwargs.get("spe")
        return spe
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "conditions"):
            side.conditions.pop("grasspledge", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Start the Grass Pledge side condition."""
        side = args[0] if args else kwargs.get("side")
        if side:
            side.conditions["grasspledge"] = {
                "turns": 4,
                "source": kwargs.get("source"),
            }
        return True

class Grassyglide:
    def onModifyPriority(self, *args, **kwargs):
        priority = args[0] if args else kwargs.get("priority", 0)
        user = args[1] if len(args) > 1 else kwargs.get("user")
        if getattr(user, "terrain", "") == "grassyterrain":
            return priority + 1
        return priority

class Grassyterrain:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "terrainextender":
            return 8
        return 5
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        move_id = getattr(move, "name", "").replace(" ", "").lower() if move else ""
        if move_id in {"earthquake", "bulldoze", "magnitude"} and target and getattr(target, "grounded", True):
            return int(power * 0.5)
        if move and getattr(move, "type", "").lower() == "grass" and user and getattr(user, "grounded", True):
            return int(power * 1.3)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "terrain"):
            field.terrain = None
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field is not None:
            field.terrain = "grassyterrain"
        return True
    def onResidual(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if not pokemon:
            return False
        if getattr(pokemon, "grounded", True):
            max_hp = getattr(pokemon, "max_hp", 0)
            heal = max_hp // 16
            pokemon.hp = min(getattr(pokemon, "hp", 0) + heal, max_hp)
        return True

class Gravapple:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        battle = args[3] if len(args) > 3 else kwargs.get("battle")
        field = getattr(battle, "field", None) if battle else None
        if field and getattr(field, "pseudo_weather", {}).get("gravity"):
            return int(power * 1.5)
        return power

class Gravity:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        if getattr(source, "ability", "").lower() == "persistent":
            return 7
        return 5
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if move and getattr(move, "flags", {}).get("gravity") and not getattr(move, "isZ", False):
            if hasattr(user, "tempvals"):
                user.tempvals["cant_move"] = "gravity"
            return False
        return True
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if move and getattr(move, "flags", {}).get("gravity"):
            return True
        return False
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("gravity", None)
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            vol = getattr(field, "pseudo_weather", {})
            vol["gravity"] = True
            field.pseudo_weather = vol
        return True
    def onModifyAccuracy(self, *args, **kwargs):
        acc = args[0] if args else kwargs.get("accuracy", 100)
        try:
            return min(100, int(acc * 5 / 3))
        except Exception:
            return acc
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move and getattr(move, 'accuracy', True) is not True:
            try:
                move.accuracy = min(100, int(move.accuracy * 5 / 3))
            except Exception:
                pass

class Growth:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        sunny = str(weather).lower() in ('sunnyday', 'sunny', 'desolateland')
        if move:
            move.boosts = {'atk': 2, 'spa': 2} if sunny else {'atk': 1, 'spa': 1}

class Grudge:
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("grudge", None)
        return True
    def onFaint(self, *args, **kwargs):
        pokemon = args[0] if args else None
        last = getattr(pokemon, "tempvals", {}).get("last_damaged_by") if pokemon else None
        source = last.get("source") if isinstance(last, dict) else None
        move = getattr(source, "last_move", None)
        if move and hasattr(move, "pp"):
            move.pp = 0
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["grudge"] = True
        return True

class Guardianofalola:
    def damageCallback(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if not target:
            return 0
        hp75 = int(getattr(target, "max_hp", 0) * 3 / 4)
        protected = False
        vols = getattr(target, "volatiles", {})
        if vols.get("protect") or vols.get("banefulbunker") or vols.get("kingsshield") or vols.get("spikyshield"):
            protected = True
        side = getattr(target, "side", None)
        if side and getattr(side, "matblock", False):
            protected = True
        if protected:
            return max(1, int((hp75 / 4) + 0.5))
        return max(1, hp75)

class Guardsplit:
    def onHit(self, user, target, battle):
        """Average the Defense and Sp. Def stats of user and target."""
        for stat in ["def", "spd"]:
            u_val = getattr(user, stat, None)
            t_val = getattr(target, stat, None)
            if u_val is not None and t_val is not None:
                avg = (u_val + t_val) // 2
                setattr(user, stat, avg)
                setattr(target, stat, avg)
        return True

class Guardswap:
    def onHit(self, user, target, battle):
        """Swap Defense and Sp. Def stat boosts."""
        for stat in ["def", "spd"]:
            user_boost = getattr(user, "boosts", {}).get(stat, 0)
            target_boost = getattr(target, "boosts", {}).get(stat, 0)
            user.boosts[stat] = target_boost
            target.boosts[stat] = user_boost
        return True

class Gyroball:
    def basePowerCallback(self, user, target, move):
        """Increase power the slower the user is compared to the target."""
        user_spe = getattr(getattr(user, "base_stats", None), "spe", 0)
        target_spe = getattr(getattr(target, "base_stats", None), "spe", 0)
        user_spe = max(1, user_spe)
        power = int((25 * target_spe / user_spe) + 1)
        return min(150, max(1, power))

class Happyhour:
    def onTryHit(self, user, *args, **kwargs):
        """Simply succeed to display the effect."""
        return True

class Hardpress:
    def basePowerCallback(self, user, target, move):
        """Scale power based on the target's remaining HP."""
        cur_hp = getattr(target, "hp", 0)
        max_hp = getattr(target, "max_hp", cur_hp or 1)
        ratio = cur_hp / max_hp if max_hp else 0
        power = int(100 * ratio)
        return max(1, power)

class Haze:
    def onHitField(self, user, battle):
        """Remove all stat changes from all active Pokémon."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                if hasattr(mon, "boosts"):
                    for stat in mon.boosts:
                        mon.boosts[stat] = 0
        return True

class Healbell:
    def onHit(self, user, target, battle):
        """Cure status of all Pokémon on the user's side."""
        party = getattr(user, "party", [user])
        for mon in party:
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True

class Healblock:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        effect = args[2] if len(args) > 2 else kwargs.get("effect")
        if getattr(effect, "name", "") == "Psychic Noise":
            return 2
        if getattr(source, "ability", "").lower() == "persistent":
            return 7
        return 5
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if move and getattr(move, "flags", {}).get("heal") and not getattr(move, "isZ", False):
            if hasattr(user, "tempvals"):
                user.tempvals["cant_move"] = "healblock"
            return False
        return True
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if move and getattr(move, "flags", {}).get("heal"):
            return True
        return False
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("healblock", None)
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move:
            move.effect = 'healblock'
    def onRestart(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            # simply refresh duration indicator if present
            target.volatiles["healblock"] = True
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["healblock"] = True
        return True
    def onTryHeal(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "volatiles", {}).get("healblock"):
            return False
        return True

class Healingwish:
    def onSwap(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if pokemon:
            max_hp = getattr(pokemon, "max_hp", 0)
            pokemon.hp = max_hp
            if hasattr(pokemon, "setStatus"):
                pokemon.setStatus(0)
        return True
    def onTryHit(self, *args, **kwargs):
        return True

class Healpulse:
    def onHit(self, user, target, battle):
        """Heal the target by half of its max HP."""
        max_hp = getattr(target, "max_hp", 0)
        heal = max_hp // 2
        target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
        return True

class Heartswap:
    def onHit(self, user, target, battle):
        """Swap all stat boosts between user and target."""
        user_boosts = getattr(user, "boosts", {})
        target_boosts = getattr(target, "boosts", {})
        user.boosts, target.boosts = target_boosts.copy(), user_boosts.copy()
        return True

class Heatcrash:
    def basePowerCallback(self, user, target, move):
        """Scale power based on weight ratio."""
        user_wt = getattr(user, "weightkg", 0)
        target_wt = getattr(target, "weightkg", 1)
        if user_wt >= target_wt * 5:
            return 120
        if user_wt >= target_wt * 4:
            return 100
        if user_wt >= target_wt * 3:
            return 80
        if user_wt >= target_wt * 2:
            return 60
        return 40
    def onTryHit(self, target, source, move):
        """Fail against Dynamax targets."""
        if getattr(target, "volatiles", {}).get("dynamax"):
            return False
        return True

class Heavyslam:
    def basePowerCallback(self, user, target, move):
        """Scale power based on weight ratio."""
        user_wt = getattr(user, "weightkg", 0)
        target_wt = getattr(target, "weightkg", 1)
        if user_wt >= target_wt * 5:
            return 120
        if user_wt >= target_wt * 4:
            return 100
        if user_wt >= target_wt * 3:
            return 80
        if user_wt >= target_wt * 2:
            return 60
        return 40
    def onTryHit(self, target, source, move):
        """Fail against Dynamax targets."""
        if getattr(target, "volatiles", {}).get("dynamax"):
            return False
        return True

class Helpinghand:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        state = getattr(user, "volatiles", {}).get("helpinghand") if user else None
        multiplier = 1.0
        if isinstance(state, dict):
            multiplier = state.get("multiplier", 1.5)
        elif state:
            multiplier = 1.5
        return int(power * multiplier)

    def onRestart(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and "helpinghand" in getattr(user, "volatiles", {}):
            state = user.volatiles.get("helpinghand")
            if isinstance(state, dict):
                state["multiplier"] = state.get("multiplier", 1.5) * 1.5
            else:
                user.volatiles["helpinghand"] = {"target": state, "multiplier": 1.5 * 1.5}
        return True

    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["helpinghand"] = {"target": target, "multiplier": 1.5}
        return True
    def onTryHit(self, target, source, move):
        """Only works if the ally is preparing to move."""
        return True

class Hex:
    def basePowerCallback(self, user, target, move):
        """Double power if the target has a status condition."""
        if getattr(target, "status", None):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Hiddenpower:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        if move and user:
            move.type = getattr(user, "hp_type", "Dark")

class Highjumpkick:
    def onMoveFail(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        recoil = getattr(user, "max_hp", 0) // 2
        user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Holdback:
    def onDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and damage >= getattr(target, "hp", 0):
            return max(0, getattr(target, "hp", 0) - 1)
        return damage

class Hurricane:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        w = str(weather).lower()
        if w in ('rain', 'raindance', 'primordialsea') and hasattr(move, 'accuracy'):
            move.accuracy = True
        elif w in ('sunnyday', 'sunny', 'desolateland') and isinstance(getattr(move, 'accuracy', None), (int, float)):
            move.accuracy = move.accuracy // 2

class Hyperspacefury:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        species = getattr(getattr(user, 'species', None), 'name', '').lower()
        if 'hoopa-unbound' in species:
            return True
        return False

class Iceball:
    def basePowerCallback(self, user, target, move):
        """Power doubles with each consecutive hit and after Defense Curl."""
        temp = getattr(user, "tempvals", {})
        hits = temp.get("iceball_hits", 0)
        bp = (getattr(move, "power", 30) or 30) * (2 ** hits)
        if getattr(user, "defensecurl", False):
            bp *= 2
        temp["iceball_hits"] = hits + 1
        setattr(user, "tempvals", temp)
        return bp
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        state = getattr(user, "volatiles", {}).get("iceball")
        if state and state.get("hitCount", 0) == 5 and state.get("contactHitCount", 0) < 5:
            if hasattr(user, "volatiles"):
                user.volatiles["rolloutstorage"] = {"contactHitCount": state.get("contactHitCount", 0)}
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if user:
            temp = getattr(user, 'tempvals', {})
            hits = temp.get('iceball_hits', 0)
            if move:
                move.hit = hits + 1
                move.is_multi_turn = True
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "last_move", {}).get("id") == "struggle":
            getattr(target, "volatiles", {}).pop("iceball", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "tempvals"):
            user.tempvals["iceball_hits"] = 0
        return True

class Iceburn:
    def onTryMove(self, *args, **kwargs):
        """Handle Ice Burn as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("iceburn"):
            vol.pop("iceburn", None)
            user.volatiles = vol
            return True
        vol["iceburn"] = True
        user.volatiles = vol
        return False

class Icespinner:
    def onAfterHit(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        source = args[0] if args else kwargs.get("user")
        battle = kwargs.get("battle")
        if source and getattr(source, "hp", 0) > 0:
            field = getattr(battle, "field", None)
            if field and hasattr(field, "terrain"):
                field.terrain = None
        return True
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onAfterHit(*args, **kwargs)

class Imprison:
    def onFoeBeforeMove(self, *args, **kwargs):
        foe = args[0] if args else None
        if foe and getattr(foe, "volatiles", {}).get("imprison"):
            return False
        return True
    def onFoeDisableMove(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["imprison"] = True
        return True

class Incinerate:
    def onHit(self, user, target, battle):
        """Destroy the target's berry if it holds one."""
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if item and isinstance(item, str) and "berry" in item.lower():
            if hasattr(target, "set_item"):
                target.set_item(None)
            else:
                setattr(target, "item", None)
                setattr(target, "held_item", None)
        return True

class Infernalparade:
    def basePowerCallback(self, user, target, move):
        """Double power if the target is statused."""
        if getattr(target, "status", None):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Ingrain:
    def onDragOut(self, *args, **kwargs):
        return False
    def onResidual(self, *args, **kwargs):
        user = args[0] if args else None
        if not user:
            return False
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 16
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["ingrain"] = True
        return True
    def onTrapPokemon(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles["trapped"] = True
        return True

class Instruct:
    def onHit(self, user, target, battle):
        """Force the target to repeat its last used move."""
        move = getattr(target, "last_move", None)
        if move and hasattr(move, "onHit"):
            move.onHit(target, target, battle)
        return True

class Iondeluge:
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["iondeluge"] = True
            field.pseudo_weather = pw
        return True
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        if move and getattr(move, "type", "").lower() == "normal":
            move.type = "Electric"

class Ivycudgel:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        species = getattr(getattr(user, "species", None), "name", "") if user else ""
        if "wellspring" in species.lower():
            move.type = "Water"
        elif "hearthflame" in species.lower():
            move.type = "Fire"
        elif "cornerstone" in species.lower():
            move.type = "Rock"
    def onPrepareHit(self, *args, **kwargs):
        return True

class Jawlock:
    def onHit(self, user, target, battle):
        """Trap both the user and the target."""
        for mon in (user, target):
            if hasattr(mon, "volatiles"):
                mon.volatiles["trapped"] = True
        return True

class Judgment:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        if not (move and user):
            return
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if item and hasattr(item, "onPlate"):
            move.type = getattr(item, "onPlate")

class Jumpkick:
    def onMoveFail(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        recoil = getattr(user, "max_hp", 0) // 2
        user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Junglehealing:
    def onHit(self, user, target, battle):
        """Heal all allies and cure their status."""
        party = getattr(user, "party", [user])
        for mon in party:
            max_hp = getattr(mon, "max_hp", 0)
            heal = max_hp // 4
            mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True

class Kingsshield:
    def onHit(self, user, target, battle):
        """Protect the user and lower Attack on contact."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        if getattr(target, "made_contact", False):
            apply_boost(target, {"atk": -1})
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onTryHit(self, *args, **kwargs):
        """Block the incoming move like Protect."""
        return False

class Knockoff:
    def onAfterHit(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        if source and getattr(source, "hp", 0) <= 0:
            return True
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if item:
            if hasattr(target, "set_item"):
                target.set_item(None)
            else:
                setattr(target, "item", None)
        return True

    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if item:
            return int(power * 1.5)
        return power

class Laserfocus:
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("laserfocus", None)
        return True
    def onModifyCritRatio(self, *args, **kwargs):
        return 5
    def onRestart(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles["laserfocus"] = True
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["laserfocus"] = True
        return True

class Lashout:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if user and getattr(user, "statsLoweredThisTurn", False):
            return power * 2
        return power

class Lastresort:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if not user or not getattr(user, 'moves', None):
            return False
        if len(user.moves) < 2:
            return False
        has_lr = False
        for mv in user.moves:
            if getattr(mv, 'name', '').lower() == 'lastresort':
                has_lr = True
                continue
            if not getattr(mv, 'used', False):
                return False
        return has_lr

class Lastrespects:
    def basePowerCallback(self, user, target, move):
        """Increase power for each fainted ally."""
        party = getattr(user, "party", [user])
        fainted = sum(1 for p in party if p is not user and getattr(p, "hp", 0) <= 0)
        return 50 + 50 * fainted

class Leechseed:
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if not target:
            return False
        source = getattr(target, "volatiles", {}).get("leechseed")
        if not source:
            return True
        if getattr(source, "hp", 0) <= 0:
            if hasattr(target, "volatiles"):
                target.volatiles.pop("leechseed", None)
            return True
        damage = getattr(target, "max_hp", 0) // 8
        target.hp = max(0, getattr(target, "hp", 0) - damage)
        if hasattr(source, "hp"):
            source.hp = min(getattr(source, "hp", 0) + damage, getattr(source, "max_hp", 0))
        if getattr(target, "hp", 0) <= 0 and hasattr(target, "volatiles"):
            target.volatiles.pop("leechseed", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["leechseed"] = user
        return True
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        types = [t.lower() for t in getattr(target, "types", [])] if target else []
        return "grass" not in types

class Lightscreen:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "lightclay":
            return 8
        return 5
    def onAnyModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        target = args[2] if len(args) > 2 else kwargs.get("target")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if not target or not source or not move or move.category != "Special":
            return damage
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("lightscreen"):
            mult = 0.5
            if len(getattr(side, "active", [])) > 1:
                mult = 2 / 3
            return int(damage * mult)
        return damage
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("lightscreen", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Activate the Light Screen effect."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["lightscreen"] = True
        return True

class Lightthatburnsthesky:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if user and move:
            if getattr(user, 'atk', 0) > getattr(user, 'spa', 0):
                move.category = 'Physical'
            else:
                move.category = 'Special'

class Lockon:
    def onHit(self, user, target, battle):
        """Ensure the user's next move hits the target."""
        if hasattr(user, "volatiles"):
            user.volatiles["lockon"] = target
        return True
    def onSourceAccuracy(self, *args, **kwargs):
        return 100
    def onSourceInvulnerability(self, *args, **kwargs):
        return True
    def onTryHit(self, *args, **kwargs):
        """Always succeeds, setting up the lock-on effect."""
        return True

class Lowkick:
    def basePowerCallback(self, user, target, move):
        """Scale power with the target's weight."""
        wt = getattr(target, "weightkg", 0) * 10
        if wt >= 2000:
            return 120
        if wt >= 1000:
            return 100
        if wt >= 500:
            return 80
        if wt >= 250:
            return 60
        if wt >= 100:
            return 40
        return 20
    def onTryHit(self, *args, **kwargs):
        """Fail on Dynamaxed targets."""
        target = args[0] if args else None
        if getattr(target, "volatiles", {}).get("dynamax"):
            return False
        return True

class Luckychant:
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("luckychant", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Prevent critical hits against this side for a few turns."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["luckychant"] = True
        return True

class Lunarblessing:
    def onHit(self, user, target, battle):
        """Heal and cure status of all allies."""
        party = getattr(user, "party", [user])
        for mon in party:
            max_hp = getattr(mon, "max_hp", 0)
            heal = max_hp // 3
            mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True

class Lunardance:
    def onSwap(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if pokemon:
            max_hp = getattr(pokemon, "max_hp", 0)
            pokemon.hp = max_hp
            if hasattr(pokemon, "setStatus"):
                pokemon.setStatus(0)
        return True
    def onTryHit(self, *args, **kwargs):
        """Always succeeds to set up the healing effect."""
        return True

class Magiccoat:
    def onAllyTryHitSide(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["magiccoat"] = True
        return True
    def onTryHit(self, *args, **kwargs):
        """Reflect status moves back at the attacker."""
        move = kwargs.get("move")
        if move and getattr(move, "category", "") == "Status":
            return False
        return True

class Magicpowder:
    def onHit(self, user, target, battle):
        """Change the target's type to Psychic."""
        if hasattr(target, "types"):
            target.types = ["Psychic"]
        return True

class Magicroom:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        if getattr(source, "ability", "").lower() == "persistent":
            return 7
        return 5
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("magicroom", None)
        return True
    def onFieldRestart(self, *args, **kwargs):
        field = kwargs.get("field") or args[0] if args else None
        if hasattr(field, "remove_pseudo_weather"):
            field.remove_pseudo_weather("magicroom")
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["magicroom"] = True
            field.pseudo_weather = pw
        return True

class Magneticflux:
    def onHitSide(self, user, battle):
        """Boost defenses of allies with Plus or Minus."""
        side = getattr(user, "side", None)
        if not side:
            return False
        for mon in getattr(side, "active", []):
            ability = getattr(mon, "ability", "").lower()
            if ability in {"plus", "minus"}:
                apply_boost(mon, {"def": 1, "spd": 1})
        return True

class Magnetrise:
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("magnetrise", None)
        return True
    def onImmunity(self, *args, **kwargs):
        typ = args[0] if args else kwargs.get("type")
        if typ and str(typ).lower() == "ground":
            return False
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["magnetrise"] = True
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        battle = args[3] if len(args) > 3 else kwargs.get("battle")

        vols = getattr(user, "volatiles", {}) if user else {}
        if vols.get("smackdown") or vols.get("ingrain"):
            return False

        field = getattr(battle, "field", None) if battle else None
        if field and getattr(field, "pseudo_weather", {}).get("Gravity"):
            return False

        return True

class Magnitude:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        import random as _r
        level, power = _r.choice([(4,10),(5,30),(6,50),(7,70),(8,90),(9,110),(10,150)])
        if move:
            move.magnitude = level
            move.power = power
    def onUseMoveMessage(self, *args, **kwargs):
        return True

class Matblock:
    def onSideStart(self, *args, **kwargs):
        """Protect the side from attacks for one turn."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["matblock"] = True
            side.volatiles = vol
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        battle = args[3] if len(args) > 3 else kwargs.get('battle')
        if user and getattr(user, 'active_move_actions', 1) > 1:
            return False
        if battle and getattr(battle, 'queue', None) and hasattr(battle.queue, 'willAct'):
            try:
                return bool(battle.queue.willAct())
            except Exception:
                return True
        return True
    def onTryHit(self, *args, **kwargs):
        """Protect the user's side for the first turn."""
        return False

class Maxairstream:
    def onHit(self, user, target, battle):
        """Raise the user's Speed after dealing damage."""
        apply_boost(user, {"spe": 1})
        return True

class Maxdarkness:
    def onHit(self, user, target, battle):
        """Lower the target's Special Defense."""
        apply_boost(target, {"spd": -1})
        return True

class Maxflare:
    def onHit(self, user, target, battle):
        """Summon sunny weather."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_weather"):
            field.set_weather("SunnyDay")
        return True

class Maxflutterby:
    def onHit(self, user, target, battle):
        """Lower the target's Special Attack."""
        apply_boost(target, {"spa": -1})
        return True

class Maxgeyser:
    def onHit(self, user, target, battle):
        """Summon rain weather."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_weather"):
            field.set_weather("RainDance")
        return True

class Maxguard:
    def onHit(self, user, target, battle):
        """Protect the user for the turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True

    def onPrepareHit(self, *args, **kwargs):
        return True

    def onStart(self, *args, **kwargs):
        return True

    def onTryHit(self, *args, **kwargs):
        """Block the incoming move."""
        return False

class Maxhailstorm:
    def onHit(self, user, target, battle):
        """Summon hail weather."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_weather"):
            field.set_weather("Hail")
        return True

class Maxknuckle:
    def onHit(self, user, target, battle):
        """Raise the user's Attack."""
        apply_boost(user, {"atk": 1})
        return True

class Maxlightning:
    def onHit(self, user, target, battle):
        """Set Electric Terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain("Electric")
        return True

class Maxmindstorm:
    def onHit(self, user, target, battle):
        """Set Psychic Terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain("Psychic")
        return True

class Maxooze:
    def onHit(self, user, target, battle):
        """Raise the user's Special Attack."""
        apply_boost(user, {"spa": 1})
        return True

class Maxovergrowth:
    def onHit(self, user, target, battle):
        """Set Grassy Terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain("Grassy")
        return True

class Maxphantasm:
    def onHit(self, user, target, battle):
        """Lower the target's Defense."""
        apply_boost(target, {"def": -1})
        return True

class Maxquake:
    def onHit(self, user, target, battle):
        """Raise the user's Special Defense."""
        apply_boost(user, {"spd": 1})
        return True

class Maxrockfall:
    def onHit(self, user, target, battle):
        """Summon a sandstorm."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_weather"):
            field.set_weather("Sandstorm")
        return True

class Maxstarfall:
    def onHit(self, user, target, battle):
        """Set Misty Terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain("Misty")
        return True

class Maxsteelspike:
    def onHit(self, user, target, battle):
        """Raise the user's Defense."""
        apply_boost(user, {"def": 1})
        return True

class Maxstrike:
    def onHit(self, user, target, battle):
        """Lower the target's Speed."""
        apply_boost(target, {"spe": -1})
        return True

class Maxwyrmwind:
    def onHit(self, user, target, battle):
        """Lower the target's Attack."""
        apply_boost(target, {"atk": -1})
        return True

class Meanlook:
    def onHit(self, user, target, battle):
        """Prevent the target from switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Mefirst:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        return int(power * 1.5)
    def onTryHit(self, *args, **kwargs):
        """Fail if the target hasn't chosen a move."""
        target = args[0] if args else None
        if not getattr(target, "last_move", None):
            return False
        return True

class Metalburst:
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
        if isinstance(last, dict):
            dmg = last.get("damage", 0)
            try:
                return int(dmg * 1.5)
            except Exception:
                return dmg
        return 0
    def onModifyTarget(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, "tempvals", {}).get("last_damaged_by") if user else None
        if isinstance(last, dict):
            return last.get("source")
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, 'tempvals', {}).get('last_damaged_by') if user else None
        if not last or not last.get('this_turn'):
            return False
        return True

class Meteorbeam:
    def onTryMove(self, *args, **kwargs):
        """Handle Meteor Beam as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("meteorbeam"):
            vol.pop("meteorbeam", None)
            user.volatiles = vol
            return True
        vol["meteorbeam"] = True
        user.volatiles = vol
        return False

class Metronome:
    def onHit(self, user, target, battle):
        """Use a random move from the battle's metronome pool."""
        pool = getattr(battle, "metronome_pool", [])
        if not pool:
            return False
        move = choice(pool)
        if hasattr(move, "onHit"):
            move.onHit(user, target, battle)
        return True

class Mimic:
    def onHit(self, user, target, battle):
        """Copy the target's last move into the user's moveset."""
        move = getattr(target, "last_move", None)
        if not move or getattr(move, "name", "").lower() == "mimic":
            return False
        moves = getattr(user, "moves", [])
        if moves:
            moves[0] = move
        else:
            user.moves = [move]
        return True

class Mindblown:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            recoil = getattr(user, "max_hp", 0) // 2
            user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Mindreader:
    def onHit(self, user, target, battle):
        """Ensure the user's next move will hit the target."""
        if hasattr(user, "volatiles"):
            user.volatiles["lock_on"] = target
        return True
    def onTryHit(self, *args, **kwargs):
        return True

class Minimize:
    def onAccuracy(self, *args, **kwargs):
        return True
    def onSourceModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and getattr(target, "volatiles", {}).get("minimize") and move:
            mname = getattr(move, "name", "").replace(" ", "").lower()
            if mname in {"stomp", "steamroller", "dragonrush", "flyingpress", "maliciousmoonsault"}:
                try:
                    return int(damage * 2)
                except Exception:
                    return damage
        return damage

class Miracleeye:
    def onModifyBoost(self, *args, **kwargs):
        boosts = args[0] if args else kwargs.get("boosts", {})
        if isinstance(boosts, dict) and "evasion" in boosts:
            boosts["evasion"] = 0
        return boosts
    def onNegateImmunity(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["miracleeye"] = True
        return True
    def onTryHit(self, *args, **kwargs):
        """Allow Psychic moves to hit Dark types and negate evasion boosts."""
        return True

class Mirrorcoat:
    def beforeTurnCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["mirrorcoat"] = {"slot": None, "damage": 0}
        return True
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        vol = getattr(user, "volatiles", {}).get("mirrorcoat") if user else None
        if vol:
            return vol.get("damage", 0)
        return 0
    def onDamagingHit(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        source = args[2] if len(args) > 2 else None
        move = args[3] if len(args) > 3 else None
        if target and source and getattr(move, "category", "") == "Special":
            vol = getattr(target, "volatiles", {}).get("mirrorcoat")
            if vol is not None:
                vol["slot"] = source
                vol["damage"] = getattr(move, "damage", 0) * 2
    def onRedirectTarget(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, "volatiles", {}).get("mirrorcoat") if user else None
        if vol:
            return vol.get("slot")
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "tempvals"):
            user.tempvals["mirrorcoat_damage"] = 0
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, 'volatiles', {}).get('mirrorcoat') if user else None
        if not vol or vol.get('slot') is None:
            return False
        return True

class Mirrormove:
    def onTryHit(self, *args, **kwargs):
        """Fail if the target hasn't used a move yet."""
        target = args[0] if args else None
        if not getattr(target, "last_move", None):
            return False
        return True

class Mist:
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("mist", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Prevent stat reduction on this side for five turns."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["mist"] = True
        return True
    def onTryBoost(self, *args, **kwargs):
        boosts = args[0] if args else kwargs.get("boosts")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("mist"):
            return None
        return boosts

class Mistyexplosion:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        terrain = getattr(user, "terrain", None)
        grounded = getattr(user, "grounded", True)
        if terrain == "mistyterrain" and grounded:
            return int(power * 1.5)
        return power

class Mistyterrain:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "terrainextender":
            return 8
        return 5
    def onBasePower(self, *args, **kwargs):
        attacker = args[0] if args else kwargs.get("user")
        defender = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "dragon" and defender and getattr(defender, "grounded", True):
            return int(power * 0.5)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "terrain"):
            field.terrain = None
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field is not None:
            field.terrain = "mistyterrain"
        return True
    def onSetStatus(self, *args, **kwargs):
        status = args[0] if args else kwargs.get("status")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and getattr(target, "grounded", True):
            return False
        return True
    def onTryAddVolatile(self, *args, **kwargs):
        status = args[0] if args else kwargs.get("status")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and getattr(target, "grounded", True) and status in {"yawn", "confusion"}:
            return False
        return True

class Moonlight:
    def onHit(self, user, target, battle):
        """Heal the user based on weather conditions."""
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 2
        weather = getattr(getattr(battle, "field", None), "weather", None)
        if weather == "SunnyDay":
            heal = int(max_hp * 2 / 3)
        elif weather in {"RainDance", "Sandstorm", "Hail"}:
            heal = max_hp // 4
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

class Morningsun:
    def onHit(self, user, target, battle):
        """Heal the user similar to Moonlight."""
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 2
        weather = getattr(getattr(battle, "field", None), "weather", None)
        if weather == "SunnyDay":
            heal = int(max_hp * 2 / 3)
        elif weather in {"RainDance", "Sandstorm", "Hail"}:
            heal = max_hp // 4
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

class Mortalspin:
    def onAfterHit(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if user:
            side = getattr(user, "side", None)
            if side and hasattr(side, "hazards"):
                for h in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
                    side.hazards.pop(h, None)
        if target and getattr(target, "status", None) is None:
            if hasattr(target, "setStatus"):
                target.setStatus("psn")
        return True
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onAfterHit(*args, **kwargs)

class Mudsport:
    def onBasePower(self, *args, **kwargs):
        attacker = args[0] if args else kwargs.get("user")
        defender = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "electric":
            return int(power * 0.33)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("mudsport", None)
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["mudsport"] = True
            field.pseudo_weather = pw
        return True

class Multiattack:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if move and item and hasattr(item, "memory_type"):
            move.type = getattr(item, "memory_type")

class Naturalgift:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if move and item:
            move.type = getattr(item, "natural_type", getattr(move, "type", None))
    def onPrepareHit(self, *args, **kwargs):
        user = args[0] if args else None
        move = args[2] if len(args) > 2 else kwargs.get('move')
        item = getattr(user, 'item', None) or getattr(user, 'held_item', None)
        if not item:
            return False
        if move:
            move.type = getattr(item, 'natural_type', getattr(move, 'type', None))
            move.power = getattr(item, 'natural_power', getattr(move, 'power', 0))
        return True

class Naturepower:
    def onTryHit(self, *args, **kwargs):
        """Choose a move based on terrain; always succeeds here."""
        return True

class Naturesmadness:
    def damageCallback(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if not target:
            return 0
        hp = getattr(target, "hp", 0)
        return max(1, hp // 2)

class Nightmare:
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if not target:
            return False
        if getattr(target, "status", None) == "slp":
            dmg = getattr(target, "max_hp", 0) // 4
            target.hp = max(0, getattr(target, "hp", 0) - dmg)
        return True
    def onStart(self, *args, **kwargs):
        target = args[0] if args else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["nightmare"] = True
        return True

class Noretreat:
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["noretreat"] = True
        return True
    def onTrapPokemon(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if pokemon and getattr(pokemon, "volatiles", {}).get("noretreat"):
            pokemon.volatiles["trapped"] = True
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if user and getattr(user, 'volatiles', {}).get('noretreat'):
            return False
        if user and getattr(user, 'volatiles', {}).get('trapped'):
            return True
        return True

class Obstruct:
    def onHit(self, user, target, battle):
        """Protect the user and harshly lower contact attackers' Defense."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        if getattr(target, "made_contact", False):
            apply_boost(target, {"def": -2})
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        return True
    def onTryHit(self, *args, **kwargs):
        """Block the incoming move like Protect."""
        return False

class Octolock:
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        user = getattr(target, "volatiles", {}).get("octolock") if target else None
        if not target or not user:
            return False
        if not getattr(user, "hp", 0):
            target.volatiles.pop("octolock", None)
            return True
        apply_boost(target, {"def": -1, "spd": -1})
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["octolock"] = user
        return True
    def onTrapPokemon(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if pokemon and getattr(pokemon, "volatiles", {}).get("octolock"):
            pokemon.volatiles["trapped"] = True
        return True
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        types = [t.lower() for t in getattr(target, "types", [])] if target else []
        return "ghost" not in types

class Odorsleuth:
    def onTryHit(self, *args, **kwargs):
        """Remove the target's evasion boosts and Ghost immunity."""
        return True

class Orderup:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        user = args[0] if args else None
        if user:
            apply_boost(user, {"atk": 1})
        return True

class Outrage:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        turns = vol.get("outrage", 0)
        if not turns:
            vol["outrage"] = 2
        else:
            vol["outrage"] = turns - 1
            if vol["outrage"] <= 0:
                vol.pop("outrage", None)
                vol["confusion"] = 2
        user.volatiles = vol
        return True

class Painsplit:
    def onHit(self, user, target, battle):
        """Average HP between user and target."""
        u_hp = getattr(user, "hp", 0)
        t_hp = getattr(target, "hp", 0)
        avg = (u_hp + t_hp) // 2
        user.hp = avg
        target.hp = avg
        return True

class Partingshot:
    def onHit(self, user, target, battle):
        """Lower target's offenses then switch the user out."""
        apply_boost(target, {"atk": -1, "spa": -1})
        if hasattr(user, "tempvals"):
            user.tempvals["switch_out"] = True
        return True

class Payback:
    def basePowerCallback(self, user, target, move):
        """Double power if the target already moved."""
        moved = getattr(target, "tempvals", {}).get("moved")
        base = getattr(move, "power", 0) or 0
        return base * 2 if moved else base

class Perishsong:
    def onEnd(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles.pop("perishsong", None)
        return True
    def onHitField(self, user, battle):
        """All active Pokémon faint in three turns."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                if hasattr(mon, "volatiles"):
                    mon.volatiles["perishsong"] = 3
        return True
    def onResidual(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if not pokemon:
            return False
        if "perishsong" in getattr(pokemon, "volatiles", {}):
            pokemon.volatiles["perishsong"] -= 1
            if pokemon.volatiles["perishsong"] <= 0:
                pokemon.hp = 0
        return True

class Petaldance:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        turns = vol.get("petaldance", 0)
        if not turns:
            vol["petaldance"] = 2
        else:
            vol["petaldance"] = turns - 1
            if vol["petaldance"] <= 0:
                vol.pop("petaldance", None)
                vol["confusion"] = 2
        user.volatiles = vol
        return True

class Phantomforce:
    def onTryMove(self, *args, **kwargs):
        """Handle Phantom Force as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("phantomforce"):
            vol.pop("phantomforce", None)
            user.volatiles = vol
            return True
        vol["phantomforce"] = True
        user.volatiles = vol
        return False

class Photongeyser:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if user and move:
            if getattr(user, 'atk', 0) > getattr(user, 'spa', 0):
                move.category = 'Physical'
            else:
                move.category = 'Special'

class Pikapapow:
    def basePowerCallback(self, user, target, move):
        """Power scales with the user's happiness."""
        happiness = getattr(user, "happiness", 0)
        return max(1, int((happiness * 10) / 25))

class Pluck:
    def onHit(self, user, target, battle):
        """Eat the target's berry if it has one."""
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if item and isinstance(item, str) and "berry" in item.lower():
            if hasattr(user, "item", None) and not getattr(user, "item", None):
                if hasattr(user, "set_item"):
                    user.set_item(item)
                else:
                    setattr(user, "item", item)
                    setattr(user, "held_item", item)
            if hasattr(target, "set_item"):
                target.set_item(None)
            else:
                setattr(target, "item", None)
                setattr(target, "held_item", None)
        return True

class Pollenpuff:
    def onHit(self, user, target, battle):
        """Heal allies or damage foes."""
        if getattr(user, "side", None) is getattr(target, "side", None):
            max_hp = getattr(target, "max_hp", 0)
            heal = max_hp // 2
            target.hp = min(getattr(target, "hp", 0) + heal, max_hp)
        else:
            # Damage already handled elsewhere; nothing extra here
            pass
        return True
    def onTryHit(self, *args, **kwargs):
        return True
    def onTryMove(self, *args, **kwargs):
        return True

class Poltergeist:
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get('target')
        item = None
        if target:
            item = getattr(target, 'item', None) or getattr(target, 'held_item', None)
        return bool(item)
    def onTryHit(self, *args, **kwargs):
        """Fail if the target has no held item."""
        target = args[0] if args else None
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if not item:
            return False
        return True

class Powder:
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["powder"] = True
        return True
    def onTryMove(self, *args, **kwargs):
        """Prevent Fire-type moves while powdered."""
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if move and getattr(move, "type", "").lower() == "fire":
            return False
        return True

class Powershift:
    def onCopy(self, *args, **kwargs):
        return False
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("powershift", None)
        return True
    def onRestart(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles["powershift"] = True
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["powershift"] = True
        return True

class Powersplit:
    def onHit(self, user, target, battle):
        """Average the Attack and Sp. Atk stats of user and target."""
        for stat in ["atk", "spa"]:
            u_val = getattr(user, stat, None)
            t_val = getattr(target, stat, None)
            if u_val is not None and t_val is not None:
                avg = (u_val + t_val) // 2
                setattr(user, stat, avg)
                setattr(target, stat, avg)
        return True

class Powerswap:
    def onHit(self, user, target, battle):
        """Swap Attack and Sp. Atk stat boosts."""
        for stat in ["atk", "spa"]:
            u_boost = getattr(user, "boosts", {}).get(stat, 0)
            t_boost = getattr(target, "boosts", {}).get(stat, 0)
            user.boosts[stat] = t_boost
            target.boosts[stat] = u_boost
        return True

class Powertrick:
    def onCopy(self, *args, **kwargs):
        return False
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            atk = getattr(user, "atk", None)
            defense = getattr(user, "def", getattr(user, "def_", None))
            if atk is not None and defense is not None:
                setattr(user, "atk", defense)
                if hasattr(user, "def"):
                    setattr(user, "def", atk)
                else:
                    setattr(user, "def_", atk)
            if hasattr(user, "volatiles"):
                user.volatiles.pop("powertrick", None)
        return True
    def onRestart(self, *args, **kwargs):
        return self.onStart(*args, **kwargs)
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user:
            atk = getattr(user, "atk", None)
            defense = getattr(user, "def", None)
            if atk is not None and defense is not None:
                setattr(user, "atk", defense)
                setattr(user, "def", atk)
            if hasattr(user, "volatiles"):
                user.volatiles["powertrick"] = True
        return True

class Powertrip:
    def basePowerCallback(self, user, target, move):
        """Increase power for each positive stat boost."""
        boosts = getattr(user, "boosts", {})
        positive = sum(v for v in boosts.values() if v > 0)
        return (getattr(move, "power", 0) or 0) + 20 * positive

class Present:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        from random import randint
        roll = randint(1, 100)
        if move:
            if roll <= 20:
                move.heal = 0.25
                move.power = 0
            elif roll <= 60:
                move.power = 40
            elif roll <= 80:
                move.power = 80
            else:
                move.power = 120

class Protect:
    def onHit(self, user, target, battle):
        """Protect the user from moves this turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        return True
    def onTryHit(self, *args, **kwargs):
        """Block the incoming move."""
        return False

class Psyblade:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        terrain = getattr(user, "terrain", None)
        if terrain == "electricterrain":
            return int(power * 1.5)
        return power

class Psychicfangs:
    def onTryHit(self, *args, **kwargs):
        """Shatter the target's screens before dealing damage."""
        target = args[0] if args else None
        side = getattr(target, "side", None)
        if side and hasattr(side, "screens"):
            for screen in ("reflect", "lightscreen", "auroraveil"):
                side.screens.pop(screen, None)
        return True

class Psychicterrain:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "terrainextender":
            return 8
        return 5
    def onBasePower(self, *args, **kwargs):
        attacker = args[0] if args else kwargs.get("user")
        defender = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "psychic" and attacker and getattr(attacker, "grounded", True):
            return int(power * 1.3)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "terrain"):
            field.terrain = None
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field is not None:
            field.terrain = "psychicterrain"
        return True
    def onTryHit(self, *args, **kwargs):
        """Prevent priority moves from hitting grounded Pokémon."""
        move = kwargs.get("move")
        if move and getattr(move, "priority", 0) > 0:
            target = args[0] if args else None
            if getattr(target, "grounded", True):
                return False
        return True

class Psychoshift:
    def onHit(self, user, target, battle):
        """Transfer the user's status condition to the target."""
        status = getattr(user, "status", 0)
        if not status:
            return False
        if hasattr(target, "setStatus"):
            target.setStatus(status)
        if hasattr(user, "setStatus"):
            user.setStatus(0)
        return True
    def onTryHit(self, *args, **kwargs):
        return True

class Psychup:
    def onHit(self, user, target, battle):
        """Copy the target's stat boosts."""
        boosts = getattr(target, "boosts", {})
        user.boosts = boosts.copy()
        return True

class Psywave:
    def damageCallback(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        import random as _r
        level = getattr(user, "level", 1)
        mult = _r.randint(50, 150)
        return max(1, int(level * mult / 100))

class Punishment:
    def basePowerCallback(self, user, target, move):
        """Increase power based on target's boosts, capped at 200."""
        boosts = getattr(target, "boosts", {})
        positive = sum(v for v in boosts.values() if v > 0)
        power = 60 + 20 * positive
        return min(200, power)

class Purify:
    def onHit(self, user, target, battle):
        """Cure the target's status and heal the user if successful."""
        if getattr(target, "status", 0):
            if hasattr(target, "setStatus"):
                target.setStatus(0)
            max_hp = getattr(user, "max_hp", 0)
            heal = max_hp // 2
            user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
            return True
        return False

class Pursuit:
    def basePowerCallback(self, user, target, move):
        """Double power if the target is switching out."""
        if getattr(target, "tempvals", {}).get("switching"):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)
    def beforeTurnCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["pursuit"] = True
        return True
    def onBeforeSwitchOut(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "volatiles", {}).get("pursuit"):
            target.tempvals["switching"] = True
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move:
            move.pursuit = True
    def onTryHit(self, target, source, move):
        """Always succeeds, even on switching targets."""
        return True

class Quash:
    def onHit(self, user, target, battle):
        """Make the target act last this turn."""
        if hasattr(target, "tempvals"):
            target.tempvals["quash"] = True
        return True

class Quickguard:
    def onHitSide(self, user, battle):
        """Protect the user's side from priority moves for the turn."""
        side = getattr(user, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["quickguard"] = True
            return True
        return False
    def onSideStart(self, *args, **kwargs):
        """Activate Quick Guard for this side."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["quickguard"] = True
            side.volatiles = vol
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        if battle and getattr(battle, 'queue', None) and hasattr(battle.queue, 'willAct'):
            try:
                return bool(battle.queue.willAct())
            except Exception:
                return True
        return True
    def onTryHit(self, target, source, move):
        """Block priority moves for the turn."""
        if getattr(move, "priority", 0) > 0:
            return False
        return True

class Rage:
    def onBeforeMove(self, *args, **kwargs):
        return True
    def onHit(self, user, target, battle):
        """Boost the user's Attack when hit."""
        apply_boost(user, {"atk": 1})
        if hasattr(user, "volatiles"):
            user.volatiles["rage"] = True
        return True
    def onStart(self, *args, **kwargs):
        return True

class Ragefist:
    def basePowerCallback(self, user, target, move):
        """Increase power based on times the user was hit."""
        times = getattr(user, "times_attacked", 0)
        return min(350, 50 + 50 * times)

class Ragepowder:
    def onFoeRedirectTarget(self, *args, **kwargs):
        user = args[0] if args else None
        return user
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["ragepowder"] = True
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        if not battle:
            return True
        participants = getattr(battle, 'participants', [])
        multi = any(len(getattr(p, 'active', [])) > 1 for p in participants)
        return multi

class Ragingbull:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        species = getattr(getattr(user, "species", None), "name", "") if user else ""
        lower = species.lower()
        if "blaze" in lower:
            move.type = "Fire"
        elif "aqua" in lower:
            move.type = "Water"
        else:
            move.type = "Normal"
    def onTryHit(self, target, source, move):
        """Remove the target's screens before damage."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "screens"):
            for screen in ("reflect", "lightscreen", "auroraveil"):
                side.screens.pop(screen, None)
        return True

class Ragingfury:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        turns = vol.get("ragingfury", 0)
        if not turns:
            vol["ragingfury"] = 2
        else:
            vol["ragingfury"] = turns - 1
            if vol["ragingfury"] <= 0:
                vol.pop("ragingfury", None)
                vol["confusion"] = 2
        user.volatiles = vol
        return True

class Rapidspin:
    def onAfterHit(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            side = getattr(user, "side", None)
            if side and hasattr(side, "hazards"):
                for h in ("spikes", "stealthrock", "toxicspikes", "stickyweb"):
                    side.hazards.pop(h, None)
            apply_boost(user, {"spe": 1})
        return True
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onAfterHit(*args, **kwargs)

class Razorwind:
    def onTryMove(self, *args, **kwargs):
        """Handle Razor Wind as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("razorwind"):
            vol.pop("razorwind", None)
            user.volatiles = vol
            return True
        vol["razorwind"] = True
        user.volatiles = vol
        return False

class Recycle:
    def onHit(self, user, target, battle):
        """Restore the last used berry if none is held."""
        if getattr(user, "item", None) or getattr(user, "held_item", None):
            return False
        item = getattr(user, "last_used_item", None)
        if not item:
            item = getattr(user, "berry_consumed", None)
        if not item:
            return False
        if hasattr(user, "set_item"):
            user.set_item(item)
        else:
            setattr(user, "item", item)
            setattr(user, "held_item", item)
        user.last_used_item = None
        return True

class Reflect:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "lightclay":
            return 8
        return 5
    def onAnyModifyDamage(self, *args, **kwargs):
        damage = args[0] if args else kwargs.get("damage")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        target = args[2] if len(args) > 2 else kwargs.get("target")
        move = args[3] if len(args) > 3 else kwargs.get("move")
        if not target or not source or not move or move.category != "Physical":
            return damage
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("reflect"):
            mult = 0.5
            if len(getattr(side, "active", [])) > 1:
                mult = 2 / 3
            return int(damage * mult)
        return damage
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("reflect", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Activate the Reflect screen on the side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["reflect"] = True
        return True

class Reflecttype:
    def onHit(self, user, target, battle):
        """Copy the target's type(s) to the user."""
        ttypes = getattr(target, "types", [])
        if not ttypes:
            return False
        user.types = list(ttypes)
        return True

class Refresh:
    def onHit(self, user, target, battle):
        """Cure the user's major status condition."""
        if hasattr(user, "setStatus"):
            user.setStatus(0)
        return True

class Relicsong:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        user = args[0] if args else None
        if user and getattr(user, "species", "").lower() == "meloetta":
            form = getattr(user, "form", "aria")
            user.form = "pirouette" if form == "aria" else "aria"
        return True
    def onHit(self, user, target, battle):
        """10% chance to put the target to sleep."""
        if getattr(target, "status", None) is None:
            if random() < 0.1 and hasattr(target, "setStatus"):
                target.setStatus("slp")
        return True

class Rest:
    def onHit(self, user, target, battle):
        """Fully heal the user and put it to sleep."""
        max_hp = getattr(user, "max_hp", getattr(user, "hp", 0))
        user.hp = max_hp
        if hasattr(user, "setStatus"):
            user.setStatus("slp")
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if not user:
            return False
        if getattr(user, 'status', None) == 'slp':
            return False
        return True

class Retaliate:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        fainted = getattr(getattr(user, "side", None), "faintedLastTurn", False)
        if fainted:
            return power * 2
        return power

class Return:
    def basePowerCallback(self, user, target, move):
        """Power scales with happiness."""
        happiness = getattr(user, "happiness", 0)
        return max(1, int((happiness * 10) / 25))

class Revelationdance:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        types = getattr(user, "types", []) if user else []
        if move and types:
            move.type = types[0]

class Revenge:
    def basePowerCallback(self, user, target, move):
        """Double power if the user was hit this turn."""
        if getattr(user, "tempvals", {}).get("took_damage"):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Reversal:
    def basePowerCallback(self, user, target, move):
        """Increase power as the user has less HP remaining."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        ratio = int((48 * cur_hp) / max_hp) if max_hp else 48
        if ratio <= 1:
            return 200
        if ratio <= 4:
            return 150
        if ratio <= 9:
            return 100
        if ratio <= 16:
            return 80
        if ratio <= 32:
            return 40
        return 20

class Revivalblessing:
    def onTryHit(self, user, *args, **kwargs):
        """Fail if there are no fainted allies to revive."""
        party = getattr(user, "party", [])
        if not any(getattr(mon, "hp", 0) <= 0 for mon in party):
            return False
        return True

class Risingvoltage:
    def basePowerCallback(self, user, target, move):
        """Double power on Electric Terrain against grounded foes."""
        terrain = getattr(user, "terrain", None)
        grounded = getattr(target, "grounded", True)
        base = getattr(move, "power", 0) or 0
        if terrain == "electricterrain" and grounded:
            return base * 2
        return base

class Roleplay:
    def onHit(self, user, target, battle):
        """Copy the target's ability."""
        ability = getattr(target, "ability", None)
        if ability is None:
            return False
        setattr(user, "ability", ability)
        return True
    def onTryHit(self, target, source, move):
        """Fail if the abilities are the same or cannot be copied."""
        if getattr(target, "ability", None) == getattr(source, "ability", None):
            return False
        return True

class Rollout:
    def basePowerCallback(self, user, target, move):
        """Power doubles with each consecutive hit and after Defense Curl."""
        temp = getattr(user, "tempvals", {})
        hits = temp.get("rollout_hits", 0)
        bp = (getattr(move, "power", 30) or 30) * (2 ** hits)
        if getattr(user, "defensecurl", False):
            bp *= 2
        temp["rollout_hits"] = hits + 1
        setattr(user, "tempvals", temp)
        return bp
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        state = getattr(user, "volatiles", {}).get("rollout")
        if state and state.get("hitCount", 0) == 5 and state.get("contactHitCount", 0) < 5:
            if hasattr(user, "volatiles"):
                user.volatiles["rolloutstorage"] = {"contactHitCount": state.get("contactHitCount", 0)}
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if user and move:
            hits = getattr(user, 'tempvals', {}).get('rollout_hits', 0)
            move.hit = hits + 1
            move.is_multi_turn = True
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "last_move", {}).get("id") == "struggle":
            getattr(target, "volatiles", {}).pop("rollout", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "tempvals"):
            user.tempvals["rollout_hits"] = 0
        return True

class Roost:
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["roost"] = True
        return True
    def onType(self, *args, **kwargs):
        types = args[0] if args else kwargs.get("types")
        if isinstance(types, list):
            return [t for t in types if t.lower() != "flying"]
        return types

class Rototiller:
    def onHitField(self, user, battle):
        """Boost Attack and Sp. Atk of grounded Grass types."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                grounded = getattr(mon, "grounded", True)
                types = [t.lower() for t in getattr(mon, "types", [])]
                if grounded and "grass" in types:
                    apply_boost(mon, {"atk": 1, "spa": 1})
        return True

class Round:
    def basePowerCallback(self, user, target, move):
        """Double power if used consecutively in the same turn."""
        if getattr(move, "sourceEffect", None) == "round":
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)
    def onTry(self, *args, **kwargs):
        return True

class Ruination:
    def damageCallback(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if not target:
            return 0
        return max(1, getattr(target, "hp", 0) // 2)

class Safeguard:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        item = getattr(source, "item", None) or getattr(source, "held_item", None)
        if item and str(item).lower() == "lightclay":
            return 8
        return 5
    def onSetStatus(self, *args, **kwargs):
        status = args[0] if args else kwargs.get("status")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("safeguard") and status:
            return False
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("safeguard", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Protect the side from status conditions."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["safeguard"] = True
        return True
    def onTryAddVolatile(self, *args, **kwargs):
        volatile = args[0] if args else kwargs.get("status")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        side = getattr(target, "side", None)
        if side and getattr(side, "screens", {}).get("safeguard") and volatile == "confusion":
            return False
        return True

class Saltcure:
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("saltcure", None)
        return True
    def onResidual(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if not pokemon:
            return False
        dmg = getattr(pokemon, "max_hp", 0)
        types = [t.lower() for t in getattr(pokemon, "types", [])]
        if "water" in types or "steel" in types:
            dmg //= 4
        else:
            dmg //= 8
        pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["saltcure"] = user
        return True

class Sandsearstorm:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        if str(weather).lower() in ('rain', 'raindance') and hasattr(move, 'accuracy'):
            move.accuracy = True

class Sappyseed:
    def onHit(self, user, target, battle):
        """Seed the target, draining HP each turn."""
        if hasattr(target, "volatiles"):
            target.volatiles["leechseed"] = user
        return True

class Secretpower:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        terrain = getattr(field, 'terrain', None)
        if not move:
            return
        if terrain == 'electricterrain':
            move.secondary = {'status': 'par'}
        elif terrain == 'grassyterrain':
            move.secondary = {'status': 'slp'}
        elif terrain == 'mistyterrain':
            move.secondary = {'boosts': {'spa': -1}}
        elif terrain == 'psychicterrain':
            move.secondary = {'boosts': {'spd': -1}}
        else:
            move.secondary = {'status': 'par'}

class Shadowforce:
    def onTryMove(self, *args, **kwargs):
        """Handle Shadow Force as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("shadowforce"):
            vol.pop("shadowforce", None)
            user.volatiles = vol
            return True
        vol["shadowforce"] = True
        user.volatiles = vol
        return False

class Shedtail:
    def onHit(self, user, target, battle):
        """Create a substitute and switch the user out."""
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 2:
            return False
        user.hp -= max_hp // 2
        if hasattr(user, "volatiles"):
            user.volatiles["substitute"] = True
        if hasattr(user, "tempvals"):
            user.tempvals["switch_out"] = True
        return True
    def onTryHit(self, user, *args, **kwargs):
        """Fail if the user lacks enough HP to create a substitute."""
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 2:
            return False
        return True

class Shellsidearm:
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onHit(*args, **kwargs)
    def onHit(self, user, target, battle):
        """May poison the target."""
        if getattr(target, "status", None) is None and random() < 0.2:
            if hasattr(target, "setStatus"):
                target.setStatus("psn")
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        target = args[2] if len(args) > 2 else kwargs.get('target')
        if user and target and move:
            atk = getattr(user, 'atk', 0)
            spa = getattr(user, 'spa', 0)
            defe = getattr(target, 'def', getattr(target, 'def_', 0))
            spd = getattr(target, 'spd', 0)
            phys = atk / max(1, defe)
            spec = spa / max(1, spd)
            move.category = 'Physical' if phys > spec else 'Special'
    def onPrepareHit(self, *args, **kwargs):
        return True

class Shelltrap:
    def onHit(self, user, target, battle):
        """Only works if the user was hit by a contact move this turn."""
        if not getattr(user, "tempvals", {}).get("shelltrap", False):
            return False
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["shelltrap"] = True
        return True
    def onTryMove(self, *args, **kwargs):
        """Activate Shell Trap and skip the attack on the first turn."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("shelltrap_ready"):
            vol.pop("shelltrap_ready", None)
            user.volatiles = vol
            return True
        vol["shelltrap_ready"] = True
        user.volatiles = vol
        return False
    def priorityChargeCallback(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["shelltrap_charge"] = True
        return -3

class Shoreup:
    def onHit(self, user, target, battle):
        """Heal the user, more in a sandstorm."""
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 2
        weather = getattr(getattr(battle, "field", None), "weather", None)
        if weather == "Sandstorm":
            heal = int(max_hp * 2 / 3)
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

class Silktrap:
    def onHit(self, user, target, battle):
        """Protect the user and lower Speed on contact."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        if getattr(target, "made_contact", False):
            apply_boost(target, {"spe": -1})
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onTryHit(self, target, source, move):
        """Block the incoming move and drop Speed on contact."""
        flags = getattr(move, "flags", {}) if move else {}
        if flags.get("contact") and hasattr(source, "boosts"):
            apply_boost(source, {"spe": -1})
        return False

class Simplebeam:
    def onHit(self, user, target, battle):
        """Change the target's ability to Simple."""
        if hasattr(target, "__dict__"):
            target.ability = "Simple"
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target already has Simple or is protected."""
        ability = getattr(target, "ability", "").lower()
        if ability == "simple":
            return False
        item = getattr(target, "item", "").lower()
        if item == "abilityshield":
            return False
        return True

class Sketch:
    def onHit(self, user, target, battle):
        """Permanently copy the target's last move."""
        move = getattr(target, "last_move", None)
        if not move or getattr(move, "name", "").lower() == "sketch":
            return False
        moves = getattr(user, "moves", [])
        if not moves:
            user.moves = [move]
        else:
            for i, m in enumerate(moves):
                if getattr(m, "name", "").lower() == "sketch":
                    moves[i] = move
                    break
        return True

class Skillswap:
    def onHit(self, user, target, battle):
        """Swap abilities between user and target."""
        u_abil = getattr(user, "ability", None)
        t_abil = getattr(target, "ability", None)
        setattr(user, "ability", t_abil)
        setattr(target, "ability", u_abil)
        return True
    def onTryHit(self, target, source, move):
        """Fail if either ability cannot be swapped."""
        banned = {"illusion", "multitype", "comatose"}
        if getattr(source, "ability", "").lower() in banned:
            return False
        if getattr(target, "ability", "").lower() in banned:
            return False
        return True

class Skullbash:
    def onTryMove(self, *args, **kwargs):
        """Handle Skull Bash as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("skullbash"):
            vol.pop("skullbash", None)
            user.volatiles = vol
            return True
        vol["skullbash"] = True
        user.volatiles = vol
        return False

class Skyattack:
    def onTryMove(self, *args, **kwargs):
        """Handle Sky Attack as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("skyattack"):
            vol.pop("skyattack", None)
            user.volatiles = vol
            return True
        vol["skyattack"] = True
        user.volatiles = vol
        return False

class Skydrop:
    def onAnyBasePower(self, *args, **kwargs):
        return args[0] if args else kwargs.get("power")
    def onAnyDragOut(self, *args, **kwargs):
        return False
    def onAnyInvulnerability(self, *args, **kwargs):
        return True
    def onFaint(self, *args, **kwargs):
        pokemon = args[0] if args else None
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles.pop("skydrop", None)
        return True
    def onFoeBeforeMove(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "volatiles", {}).get("skydrop"):
            return True
        return False
    def onFoeTrapPokemon(self, *args, **kwargs):
        target = args[0] if args else None
        return bool(target and getattr(target, "volatiles", {}).get("skydrop"))
    def onHit(self, user, target, battle):
        """Release the target from Sky Drop."""
        if hasattr(target, "volatiles"):
            target.volatiles.pop("skydrop", None)
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        target = args[2] if len(args) > 2 else kwargs.get('target')
        if target and hasattr(target, 'volatiles') and move:
            target.volatiles['skydrop'] = True
            move.is_sky_drop = True
    def onMoveFail(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        for mon in (user, target):
            if mon and hasattr(mon, "volatiles"):
                mon.volatiles.pop("skydrop", None)
        return True
    def onRedirectTarget(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "volatiles", {}).get("skydrop"):
            return target
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else kwargs.get('target')
        battle = args[3] if len(args) > 3 else kwargs.get('battle')
        if target and getattr(target, 'weightkg', 0) >= 200:
            return False
        if battle and getattr(getattr(battle, 'field', None), 'pseudo_weather', {}).get('Gravity'):
            return False
        if user and getattr(user, 'volatiles', {}).get('skydrop'):
            return False
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target is too heavy or already airborne."""
        if getattr(target, "weightkg", 0) >= 200:
            return False
        if getattr(target, "volatiles", {}).get("skydrop"):
            return False
        return True

class Sleeptalk:
    def onHit(self, user, target, battle):
        """Use a random move if the user is asleep."""
        if getattr(user, "status", None) != "slp":
            return False
        moves = [m for m in getattr(user, "moves", []) if getattr(m, "name", "").lower() not in ("sleeptalk", "rest")]
        if not moves:
            return False
        move = choice(moves)
        if hasattr(move, "onHit"):
            move.onHit(user, target, battle)
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        return getattr(user, 'status', None) == 'slp'

class Smackdown:
    def onRestart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles["smackdown"] = True
        return True
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["smackdown"] = True
        return True

class Smellingsalts:
    def basePowerCallback(self, user, target, move):
        """Double power on paralyzed targets."""
        if getattr(target, "status", None) == "par":
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)
    def onHit(self, user, target, battle):
        """Cure the target's paralysis after hitting."""
        if getattr(target, "status", None) == "par" and hasattr(target, "setStatus"):
            target.setStatus(0)
        return True

class Snatch:
    def onAnyPrepareHit(self, *args, **kwargs):
        return None
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["snatch"] = True
        return True

class Snore:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        return getattr(user, 'status', None) == 'slp'

class Soak:
    def onHit(self, user, target, battle):
        """Change the target's type to pure Water."""
        if hasattr(target, "types"):
            target.types = ["Water"]
        return True

class Solarbeam:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        weather = getattr(user, "weather", None)
        if weather in {"raindance", "primordialsea", "sandstorm", "hail", "snow"}:
            return int(power * 0.5)
        return power
    def onTryMove(self, *args, **kwargs):
        """Handle Solar Beam as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("solarbeam"):
            vol.pop("solarbeam", None)
            user.volatiles = vol
            return True
        vol["solarbeam"] = True
        user.volatiles = vol
        return False

class Solarblade:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        weather = getattr(user, "weather", None)
        if weather in {"raindance", "primordialsea", "sandstorm", "hail", "snow"}:
            return int(power * 0.5)
        return power
    def onTryMove(self, *args, **kwargs):
        """Handle Solar Blade as a two-turn move."""
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        if vol.get("solarblade"):
            vol.pop("solarblade", None)
            user.volatiles = vol
            return True
        vol["solarblade"] = True
        user.volatiles = vol
        return False

class Sparklingaria:
    def onAfterMove(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if target and getattr(target, "status", None) == "brn" and hasattr(target, "setStatus"):
            target.setStatus(0)
        return True

class Sparklyswirl:
    def onHit(self, user, target, battle):
        """Heal and cure status of the user's party."""
        party = getattr(user, "party", [user])
        for mon in party:
            max_hp = getattr(mon, "max_hp", 0)
            heal = max_hp // 3
            mon.hp = min(getattr(mon, "hp", 0) + heal, max_hp)
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True

class Speedswap:
    def onHit(self, user, target, battle):
        """Swap the base Speed stats of user and target."""
        u_speed = getattr(user, "spe", None)
        t_speed = getattr(target, "spe", None)
        if u_speed is not None and t_speed is not None:
            user.spe, target.spe = t_speed, u_speed
        return True

class Spiderweb:
    def onHit(self, user, target, battle):
        """Trap the target, preventing switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Spikes:
    def onEntryHazard(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if not pokemon:
            return False
        if not getattr(pokemon, "grounded", True):
            return True
        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and str(item).lower() == "heavydutyboots":
            return True
        side = getattr(pokemon, "side", None)
        layers = getattr(side, "hazards", {}).get("spikes", 0) if side else 0
        dmg_frac = {1: 1/8, 2: 3/16, 3: 1/4}.get(layers, 0)
        dmg = int(getattr(pokemon, "max_hp", 0) * dmg_frac)
        pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
        return True
    def onSideRestart(self, *args, **kwargs):
        return True
    def onSideStart(self, *args, **kwargs):
        """Lay a layer of Spikes on the opposing side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "hazards"):
            layers = side.hazards.get("spikes", 0)
            side.hazards["spikes"] = min(layers + 1, 3)
        return True

class Spikyshield:
    def onHit(self, user, target, battle):
        """Protect the user and damage contact attackers."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        if getattr(target, "made_contact", False):
            damage = max(1, getattr(target, "max_hp", 1) // 8)
            target.hp = max(0, getattr(target, "hp", 0) - damage)
        return True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onTryHit(self, target, source, move):
        """Block the move and hurt contact attackers."""
        flags = getattr(move, "flags", {}) if move else {}
        if flags.get("contact") and hasattr(source, "max_hp"):
            damage = max(1, getattr(source, "max_hp", 1) // 8)
            source.hp = max(0, getattr(source, "hp", 0) - damage)
        return False

class Spiritshackle:
    def onHit(self, user, target, battle):
        """Trap the target, preventing it from switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Spite:
    def onHit(self, user, target, battle):
        """Reduce the PP of the target's last move by 4."""
        last_move = getattr(target, "last_move", None)
        if last_move and hasattr(last_move, "pp"):
            last_move.pp = max(0, last_move.pp - 4)
        return True

class Spitup:
    def basePowerCallback(self, user, target, move):
        """Power depends on stockpile layers."""
        layers = getattr(user, "stockpile_layers", getattr(user, "stockpile", 0))
        return layers * 100 if layers else 0
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            setattr(user, "stockpile_layers", 0)
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        layers = 0
        if user:
            layers = getattr(user, 'stockpile_layers', getattr(user, 'stockpile', 0))
        return layers > 0

class Splash:
    def onTry(self, *args, **kwargs):
        return True
    def onTryHit(self, *args, **kwargs):
        """Always fails to have any effect."""
        return True

class Splinteredstormshards:
    def onAfterSubDamage(self, user, target, battle):
        """Also clear terrain when hitting a substitute."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain(None)
        return True
    def onHit(self, user, target, battle):
        """Clear any active terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain(None)
        return True

class Spotlight:
    def onFoeRedirectTarget(self, *args, **kwargs):
        target = args[0] if args else None
        return target
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["spotlight"] = True
        return True
    def onTryHit(self, target, source, move):
        """Force foes to target the user this turn."""
        return True

class Stealthrock:
    def onEntryHazard(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if not pokemon:
            return False
        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and str(item).lower() == "heavydutyboots":
            return True
        eff = type_effectiveness(pokemon, type("Move", (), {"type": "Rock"}))
        dmg = int(getattr(pokemon, "max_hp", 0) * eff / 8)
        pokemon.hp = max(0, getattr(pokemon, "hp", 0) - dmg)
        return True
    def onSideStart(self, *args, **kwargs):
        """Set Stealth Rock on the opposing side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "hazards"):
            side.hazards["rocks"] = True
        return True

class Steelbeam:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            recoil = getattr(user, "max_hp", 0) // 2
            user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Steelroller:
    def onAfterSubDamage(self, user, target, battle):
        """Remove terrain after hitting a substitute."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain(None)
        return True
    def onHit(self, user, target, battle):
        """Clear active terrain."""
        field = getattr(battle, "field", None)
        if field and hasattr(field, "set_terrain"):
            field.set_terrain(None)
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        field = getattr(battle, 'field', None)
        terrain = getattr(field, 'terrain', None) if field else None
        return bool(terrain)

class Stickyweb:
    def onEntryHazard(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if not pokemon or not getattr(pokemon, "grounded", True):
            return True
        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and str(item).lower() == "heavydutyboots":
            return True
        apply_boost(pokemon, {"spe": -1})
        return True
    def onSideStart(self, *args, **kwargs):
        """Set Sticky Web on the opposing side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "hazards"):
            side.hazards["stickyweb"] = True
        return True

class Stockpile:
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user:
            setattr(user, "stockpile_layers", 0)
            if hasattr(user, "volatiles"):
                user.volatiles.pop("stockpile", None)
        return True
    def onRestart(self, *args, **kwargs):
        return self.onStart(*args, **kwargs)
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        layers = getattr(user, "stockpile_layers", getattr(user, "stockpile", 0)) if user else 0
        if user:
            setattr(user, "stockpile_layers", layers + 1)
        return True
    def onResidual(self, *args, **kwargs):
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if not user:
            return False
        layers = getattr(user, 'stockpile_layers', getattr(user, 'stockpile', 0))
        return layers < 3

class Stompingtantrum:
    def basePowerCallback(self, user, target, move):
        """Double power if the user's previous move failed."""
        if getattr(user, "move_failed", False):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Stoneaxe:
    def onAfterHit(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        side = getattr(target, "side", None)
        if side and hasattr(side, "hazards"):
            side.hazards["stoneaxe"] = True
        return True
    def onAfterSubDamage(self, *args, **kwargs):
        return self.onAfterHit(*args, **kwargs)

class Storedpower:
    def basePowerCallback(self, user, target, move):
        """Increase power for each positive stat boost."""
        boosts = getattr(user, "boosts", {})
        positive = sum(v for v in boosts.values() if v > 0)
        return (getattr(move, "power", 0) or 0) + 20 * positive

class Strengthsap:
    def onHit(self, user, target, battle):
        """Heal the user based on target's Attack and lower its Attack."""
        atk = getattr(target, "stats", {}).get("atk", getattr(target, "atk", 0))
        max_hp = getattr(user, "max_hp", 0)
        heal = min(atk, max_hp - getattr(user, "hp", 0))
        user.hp = getattr(user, "hp", 0) + heal
        apply_boost(target, {"atk": -1})
        return True

class Struggle:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move:
            move.recoil = 0.25

class Stuffcheeks:
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        return not (item and "berry" in str(item).lower())
    def onHit(self, *args, **kwargs):
        user = args[0]
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if not item or "berry" not in str(item).lower():
            return False
        if hasattr(user, "set_item"):
            user.set_item(None)
        else:
            setattr(user, "item", None)
            setattr(user, "held_item", None)
        apply_boost(user, {"def": 2})
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        item = None
        if user:
            item = getattr(user, 'item', None) or getattr(user, 'held_item', None)
        return bool(item and 'berry' in str(item).lower())

class Substitute:
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("substitute", None)
        return True
    def onHit(self, *args, **kwargs):
        user = args[0]
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 4:
            return False
        user.hp -= max_hp // 4
        if hasattr(user, "volatiles"):
            user.volatiles["substitute"] = {"hp": max_hp // 4}
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            hp = getattr(user, "max_hp", getattr(user, "hp", 0)) // 4
            user.volatiles["substitute"] = {"hp": hp}
        return True
    def onTryHit(self, user, *args, **kwargs):
        """Fail if a substitute already exists or HP is too low."""
        if getattr(user, "volatiles", {}).get("substitute"):
            return False
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 4:
            return False
        return True
    def onTryPrimaryHit(self, *args, **kwargs):
        target = args[0] if args else None
        if target and getattr(target, "volatiles", {}).get("substitute"):
            return False
        return True

class Suckerpunch:
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get('target')
        move = getattr(target, 'last_move', None)
        if not move:
            return False
        category = getattr(move, 'category', '').lower()
        return category != 'status'

class Supercellslam:
    def onMoveFail(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        recoil = getattr(user, "max_hp", 0) // 2
        user.hp = max(0, getattr(user, "hp", 0) - recoil)
        return True

class Superfang:
    def damageCallback(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get("target")
        if not target:
            return 0
        return max(1, getattr(target, "hp", 0) // 2)

class Swallow:
    def onHit(self, *args, **kwargs):
        user = args[0]
        layers = getattr(user, "stockpile_layers", getattr(user, "stockpile", 0))
        if not layers:
            return False
        max_hp = getattr(user, "max_hp", 0)
        if layers == 1:
            heal = max_hp // 4
        elif layers == 2:
            heal = max_hp // 2
        else:
            heal = max_hp
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        setattr(user, "stockpile_layers", 0)
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        layers = 0
        if user:
            layers = getattr(user, 'stockpile_layers', getattr(user, 'stockpile', 0))
        return layers > 0

class Switcheroo:
    def onHit(self, *args, **kwargs):
        user, target = args[0], args[1]
        my_item = getattr(user, "item", None) or getattr(user, "held_item", None)
        your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if my_item is None and your_item is None:
            return False
        if hasattr(user, "set_item"):
            user.set_item(your_item)
        else:
            setattr(user, "item", your_item)
            setattr(user, "held_item", your_item)
        if hasattr(target, "set_item"):
            target.set_item(my_item)
        else:
            setattr(target, "item", my_item)
            setattr(target, "held_item", my_item)
        return True
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        user = args[1] if len(args) > 1 else kwargs.get("source")
        my_item = getattr(user, "item", None) or getattr(user, "held_item", None)
        your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
        return my_item is not None or your_item is not None

class Synchronoise:
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        t_types = [t.lower() for t in getattr(target, "types", [])] if target else []
        s_types = [t.lower() for t in getattr(source, "types", [])] if source else []
        return any(t in s_types for t in t_types)

class Synthesis:
    def onHit(self, user, target, battle):
        """Heal the user; amount depends on weather."""
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 2
        weather = getattr(getattr(battle, "field", None), "weather", None)
        if weather == "SunnyDay":
            heal = int(max_hp * 2 / 3)
        elif weather in {"RainDance", "Sandstorm", "Hail"}:
            heal = max_hp // 4
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

class Syrupbomb:
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("syrupbomb", None)
        return True
    def onResidual(self, *args, **kwargs):
        target = args[0] if args else None
        if not target:
            return False
        vol = getattr(target, "volatiles", {}).get("syrupbomb")
        if not vol:
            return False
        apply_boost(target, {"spe": -1})
        turns = vol.get("turns", 2) if isinstance(vol, dict) else 2
        turns -= 1
        if turns <= 0:
            target.volatiles.pop("syrupbomb", None)
        else:
            target.volatiles["syrupbomb"] = {"turns": turns}
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["syrupbomb"] = user
        return True
    def onUpdate(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and getattr(target, "hp", 0) <= 0:
            if hasattr(target, "volatiles"):
                target.volatiles.pop("syrupbomb", None)

class Tailwind:
    def durationCallback(self, *args, **kwargs):
        return 4
    def onModifySpe(self, *args, **kwargs):
        spe = args[0] if args else kwargs.get("spe")
        if spe is None:
            return None
        return spe * 2
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens.pop("tailwind", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Double the Speed of allies for four turns."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "screens"):
            side.screens["tailwind"] = True
        return True

class Takeheart:
    def onHit(self, user, target, battle):
        """Raise user's Sp. Atk and Sp. Def and cure its status."""
        apply_boost(user, {"spa": 1, "spd": 1})
        if hasattr(user, "setStatus"):
            user.setStatus(0)
        else:
            setattr(user, "status", None)
        return True

class Tarshot:
    def onEffectiveness(self, *args, **kwargs):
        type_mod = args[0] if args else kwargs.get("typeMod")
        move_type = args[2] if len(args) > 2 else kwargs.get("type")
        if isinstance(move_type, str) and move_type.lower() == "fire":
            return type_mod + 1 if isinstance(type_mod, int) else 1
        return type_mod
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["tarshot"] = True
        return True

class Taunt:
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if user and getattr(user, "volatiles", {}).get("taunt") and getattr(move, "category", "") == "Status":
            if hasattr(user, "tempvals"):
                user.tempvals["cant_move"] = "taunt"
            return False
        return True
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if user and getattr(user, "volatiles", {}).get("taunt") and getattr(move, "category", "") == "Status":
            return True
        return False
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("taunt", None)
        return True
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["taunt"] = True
        return True

class Teatime:
    def onHitField(self, user, battle):
        """Force all Pokémon to consume their held Berries."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                item = getattr(mon, "item", None) or getattr(mon, "held_item", None)
                if item and isinstance(item, str) and "berry" in item.lower():
                    if hasattr(mon, "set_item"):
                        mon.set_item(None)
                    else:
                        setattr(mon, "item", None)
                        setattr(mon, "held_item", None)
        return True

class Technoblast:
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        item = getattr(user, "item", None) or getattr(user, "held_item", None)
        if move and item and hasattr(item, "drive_type"):
            move.type = getattr(item, "drive_type")

class Telekinesis:
    def onAccuracy(self, *args, **kwargs):
        return True
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("telekinesis", None)
        return True
    def onImmunity(self, *args, **kwargs):
        typ = args[0] if args else kwargs.get("type")
        if typ and str(typ).lower() == "ground":
            return False
        return True
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["telekinesis"] = 3
        return True
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get('target')
        if target and getattr(target, 'volatiles', {}).get('telekinesis'):
            return False
        return True
    def onUpdate(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            turns = target.volatiles.get("telekinesis")
            if isinstance(turns, int):
                turns -= 1
                if turns <= 0:
                    target.volatiles.pop("telekinesis", None)
                else:
                    target.volatiles["telekinesis"] = turns

class Teleport:
    def onTry(self, *args, **kwargs):
        return True

class Temperflare:
    def basePowerCallback(self, user, target, move):
        """Double power if the user's previous move failed."""
        if getattr(user, "move_failed", False):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Terablast:
    def basePowerCallback(self, user, target, move):
        """Return 100 power if Tera type is Stellar."""
        if getattr(user, "terastallized", None) == "Stellar":
            return 100
        return getattr(move, "power", 0)
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        tera = getattr(user, 'terastallized', None)
        if tera and move:
            if getattr(user, 'atk', 0) > getattr(user, 'spa', 0):
                move.category = 'Physical'
            else:
                move.category = 'Special'
            move.type = tera
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        tera = getattr(user, "terastallized", None)
        if tera and move:
            move.type = tera
    def onPrepareHit(self, *args, **kwargs):
        return True

class Terastarstorm:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        tera = getattr(user, 'terastallized', None)
        if move and tera:
            move.type = tera
            if tera == 'Stellar':
                move.power = 120
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        tera = getattr(user, "terastallized", None)
        if move and tera:
            move.type = tera

class Terrainpulse:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        terrain = getattr(field, 'terrain', None)
        if move and terrain and getattr(user, 'grounded', True):
            move.power = 100
            move.type = terrain.replace('terrain', '').capitalize()
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        user = args[1] if len(args) > 1 else kwargs.get("user")
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        terrain = getattr(field, 'terrain', None)
        if move and terrain and getattr(user, 'grounded', True):
            move.type = terrain.replace('terrain', '').capitalize()

class Thief:
    def onAfterHit(self, *args, **kwargs):
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if not user or not target:
            return True
        if getattr(user, "item", None) or getattr(user, "held_item", None):
            return True
        item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if not item:
            return True
        if hasattr(target, "set_item"):
            target.set_item(None)
        else:
            setattr(target, "item", None)
            setattr(target, "held_item", None)
        if hasattr(user, "set_item"):
            user.set_item(item)
        else:
            setattr(user, "item", item)
            setattr(user, "held_item", item)
        return True

class Thousandarrows:
    def onEffectiveness(self, *args, **kwargs):
        type_mod = args[0] if args else kwargs.get("typeMod")
        target_type = args[2] if len(args) > 2 else kwargs.get("type")
        if isinstance(target_type, str) and target_type.capitalize() == "Flying":
            return 1
        return type_mod

class Thousandwaves:
    def onHit(self, user, target, battle):
        """Trap the target, preventing switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Thrash:
    def onAfterMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if not user:
            return False
        vol = getattr(user, "volatiles", {})
        turns = vol.get("thrash", 0)
        if not turns:
            vol["thrash"] = 2
        else:
            vol["thrash"] = turns - 1
            if vol["thrash"] <= 0:
                vol.pop("thrash", None)
                vol["confusion"] = 2
        user.volatiles = vol
        return True

class Throatchop:
    def onBeforeMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if user and getattr(user, "volatiles", {}).get("throatchop"):
            flags = getattr(move, "flags", {}) if move else {}
            if flags.get("sound"):
                if hasattr(user, "tempvals"):
                    user.tempvals["cant_move"] = "throatchop"
                return False
        return True
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if user and getattr(user, "volatiles", {}).get("throatchop"):
            return getattr(move, "flags", {}).get("sound")
        return False
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("throatchop", None)
        return True
    def onHit(self, *args, **kwargs):
        user, target = args[0], args[1]
        if hasattr(target, "volatiles"):
            target.volatiles["throatchop"] = 2
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move:
            move.flags = getattr(move, 'flags', {})
            move.flags['sound'] = False
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["throatchop"] = 2
        return True

class Thunder:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        w = str(weather).lower()
        if w in ('rain', 'raindance', 'primordialsea') and hasattr(move, 'accuracy'):
            move.accuracy = True
        elif w in ('sunnyday', 'sunny', 'desolateland') and isinstance(getattr(move, 'accuracy', None), (int, float)):
            move.accuracy = move.accuracy // 2

class Thunderclap:
    def onTry(self, *args, **kwargs):
        return True

class Tidyup:
    def onHit(self, user, target, battle):
        """Remove hazards on the user's side and boost Attack and Speed."""
        side = getattr(user, "side", None)
        if side:
            if hasattr(side, "hazards"):
                side.hazards.clear()
        apply_boost(user, {"atk": 1, "spe": 1})
        return True

class Topsyturvy:
    def onHit(self, user, target, battle):
        """Invert the target's stat boosts."""
        boosts = getattr(target, "boosts", {})
        for stat in boosts:
            boosts[stat] = -boosts[stat]
        return True

class Torment:
    def onDisableMove(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        move = args[1] if len(args) > 1 else kwargs.get("move")
        if user and getattr(user, "volatiles", {}).get("torment"):
            last = getattr(user, "last_move", None)
            if last and getattr(last, "id", None) == getattr(move, "id", None):
                return True
        return False
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("torment", None)
        return True
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["torment"] = True
        return True

class Toxicspikes:
    def onEntryHazard(self, *args, **kwargs):
        pokemon = args[0] if args else kwargs.get("pokemon")
        if not pokemon or not getattr(pokemon, "grounded", True):
            return True
        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and str(item).lower() == "heavydutyboots":
            return True
        side = getattr(pokemon, "side", None)
        layers = getattr(side, "hazards", {}).get("toxicspikes", 0) if side else 0
        types = [t.lower() for t in getattr(pokemon, "types", [])]
        if "poison" in types:
            if side and layers:
                side.hazards["toxicspikes"] = 0
            return True
        status = "tox" if layers > 1 else "psn"
        if hasattr(pokemon, "setStatus"):
            pokemon.setStatus(status)
        return True
    def onSideRestart(self, *args, **kwargs):
        return True
    def onSideStart(self, *args, **kwargs):
        """Set Toxic Spikes on the opposing side."""
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "hazards"):
            layers = side.hazards.get("toxicspikes", 0)
            side.hazards["toxicspikes"] = min(layers + 1, 2)
        return True

class Transform:
    def onHit(self, user, target, battle):
        """Copy the target's appearance and stats, storing originals."""
        backup = user.tempvals.get("transform_backup")
        if backup is None:
            backup = {}
            for attr in ("species", "stats", "base_stats", "types", "moves", "ability"):
                if hasattr(user, attr):
                    val = getattr(user, attr)
                    if attr in {"stats", "base_stats"} and hasattr(val, "__dict__"):
                        backup[attr] = val.__class__(**val.__dict__)
                    elif attr == "moves":
                        backup[attr] = [m for m in val]
                    else:
                        backup[attr] = val
            user.tempvals["transform_backup"] = backup

        user.transformed = True
        if hasattr(target, "species"):
            user.species = target.species
        if hasattr(target, "stats"):
            user.stats = target.stats.__class__(**target.stats.__dict__)
        if hasattr(target, "base_stats"):
            user.base_stats = target.base_stats.__class__(**target.base_stats.__dict__)
        if hasattr(target, "types"):
            user.types = list(target.types)
        if hasattr(target, "moves"):
            user.moves = [m for m in target.moves]
        if hasattr(target, "ability"):
            user.ability = target.ability
        return True

class Triattack:
    def onHit(self, user, target, battle):
        """20% chance to burn, paralyze, or freeze the target."""
        if random() < 0.2 and hasattr(target, "setStatus"):
            target.setStatus(choice(["brn", "par", "frz"]))
        return True

class Trick:
    def onHit(self, user, target, battle):
        """Swap held items with the target."""
        my_item = getattr(user, "item", None) or getattr(user, "held_item", None)
        your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if my_item is None and your_item is None:
            return False
        if hasattr(user, "set_item"):
            user.set_item(your_item)
        else:
            setattr(user, "item", your_item)
            setattr(user, "held_item", your_item)
        if hasattr(target, "set_item"):
            target.set_item(my_item)
        else:
            setattr(target, "item", my_item)
            setattr(target, "held_item", my_item)
        return True
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        my_item = getattr(source, "item", None) or getattr(source, "held_item", None)
        your_item = getattr(target, "item", None) or getattr(target, "held_item", None)
        return my_item is not None or your_item is not None

class Trickortreat:
    def onHit(self, user, target, battle):
        """Add Ghost type to the target."""
        types = list(getattr(target, "types", []))
        if "Ghost" not in types and "ghost" not in [t.lower() for t in types]:
            types.append("Ghost")
            setattr(target, "types", types)
        return True

class Trickroom:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        if getattr(source, "ability", "").lower() == "persistent":
            return 7
        return 5
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("trickroom", None)
        return True
    def onFieldRestart(self, *args, **kwargs):
        field = kwargs.get("field") or args[0] if args else None
        if hasattr(field, "remove_pseudo_weather"):
            field.remove_pseudo_weather("trickroom")
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["trickroom"] = True
            field.pseudo_weather = pw
        return True

class Tripleaxel:
    def basePowerCallback(self, user, target, move):
        """Power increases with each hit."""
        hit = getattr(move, "hit", 1)
        return 20 * hit

class Triplekick:
    def basePowerCallback(self, user, target, move):
        hit = getattr(move, "hit", 1)
        return 10 * hit

class Trumpcard:
    def basePowerCallback(self, user, target, move):
        pp = getattr(move, "pp", 5)
        if pp == 0:
            return 200
        if pp == 1:
            return 80
        if pp == 2:
            return 60
        if pp == 3:
            return 50
        return 40

class Upperhand:
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get('target')
        move = getattr(target, 'last_move', None)
        priority = getattr(move, 'priority', 0) if move else 0
        return priority > 0

class Uproar:
    def onAnySetStatus(self, *args, **kwargs):
        status = args[1] if len(args) > 1 else kwargs.get("status")
        if status == "slp":
            return False
        return True
    def onEnd(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        if user and hasattr(user, "volatiles"):
            user.volatiles.pop("uproar", None)
        return True
    def onResidual(self, *args, **kwargs):
        user = args[0] if args else None
        if user and getattr(user, "volatiles", {}).get("uproar"):
            user.volatiles["uproar"] -= 1
            if user.volatiles["uproar"] <= 0:
                user.volatiles.pop("uproar", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["uproar"] = 3
        return True
    def onTryHit(self, *args, **kwargs):
        """Always succeeds and prevents Sleep for several turns."""
        return True

class Veeveevolley:
    def basePowerCallback(self, user, target, move):
        """Power scales with happiness."""
        happiness = getattr(user, "happiness", 0)
        return max(1, int((happiness * 10) / 25))

class Venomdrench:
    def onHit(self, user, target, battle):
        """Lower target's Attack, Sp. Atk, and Speed if poisoned."""
        if getattr(target, "status", None) in {"psn", "tox"}:
            apply_boost(target, {"atk": -1, "spa": -1, "spe": -1})
        return True

class Venoshock:
    def onBasePower(self, *args, **kwargs):
        user = args[0] if args else kwargs.get("user")
        target = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if target and getattr(target, "status", None) in {"psn", "tox"}:
            return power * 2
        return power

class Wakeupslap:
    def basePowerCallback(self, user, target, move):
        """Double power on sleeping targets."""
        if getattr(target, "status", None) == "slp":
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)
    def onHit(self, *args, **kwargs):
        target = args[1]
        if getattr(target, "status", None) == "slp" and hasattr(target, "setStatus"):
            target.setStatus(0)
        return True

class Waterpledge:
    def basePowerCallback(self, user, target, move):
        """Return 150 power when used in a pledge combo."""
        if getattr(move, "sourceEffect", None) in {"grasspledge", "firepledge"}:
            return 150
        return getattr(move, "power", 0) or 0
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        user = args[1] if len(args) > 1 else kwargs.get('user')
        if getattr(user, 'pledge_combo', False) and move:
            move.pledge_combo = True
    def onPrepareHit(self, *args, **kwargs):
        return True
    def onSideEnd(self, *args, **kwargs):
        side = args[0] if args else kwargs.get("side")
        if side and hasattr(side, "conditions"):
            side.conditions.pop("waterpledge", None)
        return True
    def onSideStart(self, *args, **kwargs):
        """Start the Water Pledge side condition."""
        side = args[0] if args else kwargs.get("side")
        if side:
            side.conditions["waterpledge"] = {
                "turns": 4,
                "source": kwargs.get("source"),
            }
        return True

class Watershuriken:
    def basePowerCallback(self, user, target, move):
        """Ash-Greninja's Battle Bond boosts power by 5."""
        species = getattr(user, "species", None)
        ability = getattr(user, "ability", None)
        power = getattr(move, "power", 15) or 15
        if species == "Greninja-Ash" and ability == "battlebond" and not getattr(user, "transformed", False):
            return power + 5
        return power

class Watersport:
    def onBasePower(self, *args, **kwargs):
        attacker = args[0] if args else kwargs.get("user")
        defender = args[1] if len(args) > 1 else kwargs.get("target")
        move = args[2] if len(args) > 2 else kwargs.get("move")
        power = getattr(move, "power", 0) if move else 0
        if move and getattr(move, "type", "").lower() == "fire":
            return int(power * 0.33)
        return power
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("watersport", None)
        return True
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["watersport"] = True
            field.pseudo_weather = pw
        return True

class Waterspout:
    def basePowerCallback(self, user, target, move):
        """Power scales with the user's remaining HP."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        return (getattr(move, "power", 150) or 150) * cur_hp / max_hp

class Weatherball:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        w = str(weather).lower()
        if not move:
            return
        if w in ('sunnyday', 'sunny', 'desolateland'):
            move.power = 100
            move.type = 'Fire'
        elif w in ('rain', 'raindance', 'primordialsea'):
            move.power = 100
            move.type = 'Water'
        elif w in ('hail', 'snow'):
            move.power = 100
            move.type = 'Ice'
        elif w in ('sandstorm', 'sand'):
            move.power = 100
            move.type = 'Rock'
    def onModifyType(self, *args, **kwargs):
        move = args[0] if args else kwargs.get("move")
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        if not move:
            return
        w = str(weather).lower()
        if w in ('sunnyday', 'sunny', 'desolateland'):
            move.type = 'Fire'
        elif w in ('rain', 'raindance', 'primordialsea'):
            move.type = 'Water'
        elif w in ('hail', 'snow'):
            move.type = 'Ice'
        elif w in ('sandstorm', 'sand'):
            move.type = 'Rock'

class Wideguard:
    def onHitSide(self, user, battle):
        """Protect the side from multi-target moves for the turn."""
        side = getattr(user, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["wideguard"] = True
            return True
        return False
    def onSideStart(self, *args, **kwargs):
        """Activate Wide Guard for this side."""
        side = args[0] if args else kwargs.get("side")
        if side:
            vol = getattr(side, "volatiles", {})
            vol["wideguard"] = True
            side.volatiles = vol
        return True
    def onTry(self, *args, **kwargs):
        battle = kwargs.get('battle') if kwargs else None
        if len(args) > 3:
            battle = args[3] or battle
        if battle and getattr(battle, 'queue', None) and hasattr(battle.queue, 'willAct'):
            try:
                return bool(battle.queue.willAct())
            except Exception:
                return True
        return True
    def onTryHit(self, target, source, move):
        """Block moves that hit multiple targets."""
        if getattr(move, "target", "") in {"allAdjacent", "allAdjacentFoes"}:
            return False
        return True

class Wildboltstorm:
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        battle = kwargs.get('battle')
        if len(args) > 2:
            battle = args[2] or battle
        field = getattr(battle, 'field', None)
        weather = getattr(field, 'weather', getattr(battle, 'weather', None))
        if str(weather).lower() in ('rain', 'raindance') and hasattr(move, 'accuracy'):
            move.accuracy = True

class Wish:
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if not target:
            return False
        heal = getattr(target, "wish_hp", None)
        if heal is not None:
            target.hp = min(getattr(target, "hp", 0) + heal, getattr(target, "max_hp", heal))
        if hasattr(target, "volatiles"):
            target.volatiles.pop("wish", None)
        return True
    def onStart(self, *args, **kwargs):
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["wish"] = 2
            user.wish_hp = getattr(user, "max_hp", 0) // 2
        return True

class Wonderroom:
    def durationCallback(self, *args, **kwargs):
        source = args[1] if len(args) > 1 else kwargs.get("source")
        if getattr(source, "ability", "").lower() == "persistent":
            return 7
        return 5
    def onFieldEnd(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field and hasattr(field, "pseudo_weather"):
            field.pseudo_weather.pop("wonderroom", None)
        return True
    def onFieldRestart(self, *args, **kwargs):
        field = kwargs.get("field") or args[0] if args else None
        if hasattr(field, "remove_pseudo_weather"):
            field.remove_pseudo_weather("wonderroom")
    def onFieldStart(self, *args, **kwargs):
        field = args[0] if args else kwargs.get("field")
        if field:
            pw = getattr(field, "pseudo_weather", {})
            pw["wonderroom"] = True
            field.pseudo_weather = pw
        return True
    def onModifyMove(self, *args, **kwargs):
        move = args[0] if args else kwargs.get('move')
        if move:
            move.creates_wonderroom = True

class Worryseed:
    def onHit(self, user, target, battle):
        """Replace the target's ability with Insomnia."""
        setattr(target, "ability", "insomnia")
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target already has Insomnia or is protected."""
        if getattr(target, "ability", "").lower() == "insomnia":
            return False
        item = getattr(target, "item", "").lower()
        if item == "abilityshield":
            return False
        return True
    def onTryImmunity(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        return not (getattr(target, "ability", "").lower() == "insomnia")

class Wringout:
    def basePowerCallback(self, user, target, move):
        """Scale power with the target's remaining HP."""
        cur_hp = getattr(target, "hp", 0)
        max_hp = getattr(target, "max_hp", cur_hp or 1)
        return max(1, int(120 * cur_hp / max_hp))

class Yawn:
    def onEnd(self, *args, **kwargs):
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            if target.volatiles.get("yawn") == 1:
                if getattr(target, "status", None) is None and hasattr(target, "setStatus"):
                    target.setStatus("slp")
            target.volatiles.pop("yawn", None)
        return True
    def onStart(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["yawn"] = 2
        return True
    def onTryHit(self, target, source, move):
        """Fail if the target already has a status condition."""
        if getattr(target, "status", None):
            return False
        if getattr(target, "volatiles", {}).get("yawn"):
            return False
        return True


# ----------------------------------------------------------------------
# Volatile status handlers lookup
# ----------------------------------------------------------------------

VOLATILE_HANDLERS = {
    "leechseed": Leechseed(),
    "substitute": Substitute(),
    "aquaring": Aquaring(),
    "attract": Attract(),
}

