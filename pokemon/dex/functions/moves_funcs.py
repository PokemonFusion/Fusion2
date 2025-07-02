from random import choice, random

from pokemon.battle.utils import apply_boost


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
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass
    def onUpdate(self, *args, **kwargs):
        pass

class Aurawheel:
    def onModifyType(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        species = getattr(getattr(user, "species", None), "name", "").lower()
        if "morpeko" not in species:
            return False
        return True

class Auroraveil:
    def durationCallback(self, *args, **kwargs):
        pass
    def onAnyModifyDamage(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass
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
        """Boost Speed by two stages and reduce weight."""
        apply_boost(user, {"spe": 2})
        if hasattr(user, "tempvals"):
            user.tempvals["autotomize"] = True
        return True

    def onTryHit(self, *args, **kwargs):
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
        pass

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

    def onTryHit(self, *args, **kwargs):
        return True

class Barbbarrage:
    def onBasePower(self, *args, **kwargs):
        pass

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
        return True

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
        pass

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
        pass
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDamage(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onMoveAborted(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Bleakwindstorm:
    def onModifyMove(self, *args, **kwargs):
        pass

class Blizzard:
    def onModifyMove(self, *args, **kwargs):
        pass

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
        pass
    def onSourceBasePower(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Brickbreak:
    def onTryHit(self, *args, **kwargs):
        pass

class Brine:
    def onBasePower(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

class Ceaselessedge:
    def onAfterHit(self, *args, **kwargs):
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

class Celebrate:
    def onTryHit(self, *args, **kwargs):
        pass

class Charge:
    def onAfterMove(self, *args, **kwargs):
        pass
    def onBasePower(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onMoveAborted(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Clangoroussoul:
    def onHit(self, user, target, battle):
        """Lose 1/3 max HP and raise all stats by one stage."""
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 3:
            return False
        user.hp -= max_hp // 3
        boosts = {stat: 1 for stat in ["atk", "def", "spa", "spd", "spe"]}
        apply_boost(user, boosts)
        return True

    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        max_hp = getattr(user, 'max_hp', 0)
        if max_hp <= 1:
            return False
        if getattr(user, 'hp', 0) <= max_hp * 33 // 100:
            return False
        return True

    def onTryHit(self, *args, **kwargs):
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
        pass

class Comeuppance:
    def damageCallback(self, *args, **kwargs):
        pass
    def onModifyTarget(self, *args, **kwargs):
        pass
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
        pass
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
        pass
    def damageCallback(self, *args, **kwargs):
        pass
    def onDamagingHit(self, *args, **kwargs):
        pass
    def onRedirectTarget(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
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
        pass

class Craftyshield:
    def onSideStart(self, *args, **kwargs):
        pass
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
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onFaint(self, *args, **kwargs):
        pass
    def onMoveAborted(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Detect:
    def onHit(self, user, target, battle):
        """Grant the user protection from moves this turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["protect"] = True
        return True
    def onPrepareHit(self, *args, **kwargs):
        pass

class Dig:
    def onImmunity(self, *args, **kwargs):
        pass
    def onInvulnerability(self, *args, **kwargs):
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

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
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Dive:
    def onImmunity(self, *args, **kwargs):
        pass
    def onInvulnerability(self, *args, **kwargs):
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

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
        pass

class Dragoncheer:
    def onModifyCritRatio(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass

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
        pass
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onSetStatus(self, *args, **kwargs):
        pass
    def onTryAddVolatile(self, *args, **kwargs):
        pass

class Electrify:
    def onModifyType(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

class Electroshot:
    def onTryMove(self, *args, **kwargs):
        pass

class Embargo:
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Encore:
    def onDisableMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onOverrideAction(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Endeavor:
    def damageCallback(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Endure:
    def onDamage(self, *args, **kwargs):
        pass
    def onHit(self, user, target, battle):
        """Allow the user to survive hits with at least 1 HP this turn."""
        if hasattr(user, "volatiles"):
            user.volatiles["endure"] = True
        return True
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Entrainment:
    def onHit(self, user, target, battle):
        """Give the target the user's ability."""
        ability = getattr(user, "ability", None)
        if not ability:
            return False
        setattr(target, "ability", ability)
        return True
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onModifyMove(self, *args, **kwargs):
        pass

class Facade:
    def onBasePower(self, *args, **kwargs):
        pass

class Fairylock:
    def onFieldStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Fakeout:
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if getattr(user, 'active_move_actions', 1) > 1:
            return False
        return True

class Falseswipe:
    def onDamage(self, *args, **kwargs):
        pass

class Fellstinger:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        pass

class Ficklebeam:
    def onBasePower(self, *args, **kwargs):
        pass

class Filletaway:
    def onHit(self, user, target, battle):
        """Halve the user's HP to sharply boost offensive stats."""
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 2:
            return False
        user.hp -= max_hp // 2
        apply_boost(user, {"atk": 2, "spa": 2, "spe": 2})
        return True
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        if not user:
            return False
        max_hp = getattr(user, 'max_hp', 0)
        if getattr(user, 'hp', 0) <= max_hp // 2 or max_hp == 1:
            return False
        return True
    def onTryHit(self, *args, **kwargs):
        pass

class Finalgambit:
    def damageCallback(self, *args, **kwargs):
        pass

class Firepledge:
    def basePowerCallback(self, user, target, move):
        """Return boosted power if combined with another Pledge move."""
        if getattr(user, "pledge_combo", False):
            return 150
        return getattr(move, "power", 80) or 80
    def onModifyMove(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
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
        pass
    def onUpdate(self, *args, **kwargs):
        pass

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
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Flyingpress:
    def onEffectiveness(self, *args, **kwargs):
        pass

class Focusenergy:
    def onModifyCritRatio(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Focuspunch:
    def beforeMoveCallback(self, *args, **kwargs):
        pass
    def onHit(self, user, target, battle):
        """Deal heavy damage if the user kept its focus."""
        return True
    def onStart(self, *args, **kwargs):
        pass
    def onTryAddVolatile(self, *args, **kwargs):
        pass
    def priorityChargeCallback(self, *args, **kwargs):
        pass

class Followme:
    def onFoeRedirectTarget(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
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
        pass
    def onNegateImmunity(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Forestscurse:
    def onHit(self, user, target, battle):
        """Add the Grass type to the target."""
        if hasattr(target, "types") and "Grass" not in target.types:
            target.types.append("Grass")
        return True

class Freezedry:
    def onEffectiveness(self, *args, **kwargs):
        pass

class Freezeshock:
    def onTryMove(self, *args, **kwargs):
        pass

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
        pass

class Fusionflare:
    def onBasePower(self, *args, **kwargs):
        pass

class Futuresight:
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else None
        if not target or not getattr(target, 'side', None):
            return False
        return True

class Gastroacid:
    def onCopy(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

class Glaiverush:
    def onAccuracy(self, *args, **kwargs):
        pass
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onHit(self, user, target, battle):
        """Make the target drowsy, causing sleep later."""
        if hasattr(target, "volatiles"):
            target.volatiles["drowsy"] = True
        return True

class Gmaxsteelsurge:
    def onEntryHazard(self, *args, **kwargs):
        pass
    def onHit(self, user, target, battle):
        """Lay a steel-type damaging hazard on the target's side."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "hazards"):
            side.hazards["steelsurge"] = True
        return True
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxvolcalith:
    def onHit(self, user, target, battle):
        """Set up a rockstorm dealing residual damage."""
        side = getattr(target, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["gmaxvolcalith"] = 4
        return True
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

class Grasspledge:
    def basePowerCallback(self, user, target, move):
        """Return 150 power when used in a pledge combo."""
        if getattr(move, "pledge_combo", False) or getattr(user, "pledge_combo", False):
            return 150
        return getattr(move, "power", 0) or 0
    def onModifyMove(self, *args, **kwargs):
        pass
    def onModifySpe(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Grassyglide:
    def onModifyPriority(self, *args, **kwargs):
        pass

class Grassyterrain:
    def durationCallback(self, *args, **kwargs):
        pass
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass

class Gravapple:
    def onBasePower(self, *args, **kwargs):
        pass

class Gravity:
    def durationCallback(self, *args, **kwargs):
        pass
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onModifyAccuracy(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass

class Growth:
    def onModifyMove(self, *args, **kwargs):
        pass

class Grudge:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onFaint(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Guardianofalola:
    def damageCallback(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHeal(self, *args, **kwargs):
        pass

class Healingwish:
    def onSwap(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

class Helpinghand:
    def onBasePower(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Hex:
    def basePowerCallback(self, user, target, move):
        """Double power if the target has a status condition."""
        if getattr(target, "status", None):
            return (getattr(move, "power", 0) or 0) * 2
        return getattr(move, "power", 0)

class Hiddenpower:
    def onModifyType(self, *args, **kwargs):
        pass

class Highjumpkick:
    def onMoveFail(self, *args, **kwargs):
        pass

class Holdback:
    def onDamage(self, *args, **kwargs):
        pass

class Hurricane:
    def onModifyMove(self, *args, **kwargs):
        pass

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
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Iceburn:
    def onTryMove(self, *args, **kwargs):
        pass

class Icespinner:
    def onAfterHit(self, *args, **kwargs):
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

class Imprison:
    def onFoeBeforeMove(self, *args, **kwargs):
        pass
    def onFoeDisableMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Instruct:
    def onHit(self, user, target, battle):
        """Force the target to repeat its last used move."""
        move = getattr(target, "last_move", None)
        if move and hasattr(move, "onHit"):
            move.onHit(target, target, battle)
        return True

class Iondeluge:
    def onFieldStart(self, *args, **kwargs):
        pass
    def onModifyType(self, *args, **kwargs):
        pass

class Ivycudgel:
    def onModifyType(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass

class Jawlock:
    def onHit(self, user, target, battle):
        """Trap both the user and the target."""
        for mon in (user, target):
            if hasattr(mon, "volatiles"):
                mon.volatiles["trapped"] = True
        return True

class Judgment:
    def onModifyType(self, *args, **kwargs):
        pass

class Jumpkick:
    def onMoveFail(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Knockoff:
    def onAfterHit(self, *args, **kwargs):
        pass
    def onBasePower(self, *args, **kwargs):
        pass

class Laserfocus:
    def onEnd(self, *args, **kwargs):
        pass
    def onModifyCritRatio(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Lashout:
    def onBasePower(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Lightscreen:
    def durationCallback(self, *args, **kwargs):
        pass
    def onAnyModifyDamage(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Lightthatburnsthesky:
    def onModifyMove(self, *args, **kwargs):
        pass

class Lockon:
    def onHit(self, user, target, battle):
        """Ensure the user's next move hits the target."""
        if hasattr(user, "volatiles"):
            user.volatiles["lockon"] = target
        return True
    def onSourceAccuracy(self, *args, **kwargs):
        pass
    def onSourceInvulnerability(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

class Luckychant:
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Magiccoat:
    def onAllyTryHitSide(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Magicpowder:
    def onHit(self, user, target, battle):
        """Change the target's type to Psychic."""
        if hasattr(target, "types"):
            target.types = ["Psychic"]
        return True

class Magicroom:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldRestart(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

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
        pass
    def onImmunity(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        target = args[0] if args else None
        battle = args[3] if len(args) > 3 else kwargs.get('battle')
        if target and (target.volatiles.get('smackdown') or target.volatiles.get('ingrain')):
            return False
        if battle and getattr(getattr(battle, 'field', None), 'pseudo_weather', {}).get('Gravity'):
            return False
        return True

class Magnitude:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onUseMoveMessage(self, *args, **kwargs):
        pass

class Matblock:
    def onSideStart(self, *args, **kwargs):
        pass
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
        pass

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
        return True

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
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Metalburst:
    def damageCallback(self, *args, **kwargs):
        pass
    def onModifyTarget(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        last = getattr(user, 'tempvals', {}).get('last_damaged_by') if user else None
        if not last or not last.get('this_turn'):
            return False
        return True

class Meteorbeam:
    def onTryMove(self, *args, **kwargs):
        pass

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
        pass

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
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass

class Miracleeye:
    def onModifyBoost(self, *args, **kwargs):
        pass
    def onNegateImmunity(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Mirrorcoat:
    def beforeTurnCallback(self, *args, **kwargs):
        pass
    def damageCallback(self, *args, **kwargs):
        pass
    def onDamagingHit(self, *args, **kwargs):
        pass
    def onRedirectTarget(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        user = args[0] if args else None
        vol = getattr(user, 'volatiles', {}).get('mirrorcoat') if user else None
        if not vol or vol.get('slot') is None:
            return False
        return True

class Mirrormove:
    def onTryHit(self, *args, **kwargs):
        pass

class Mist:
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass
    def onTryBoost(self, *args, **kwargs):
        pass

class Mistyexplosion:
    def onBasePower(self, *args, **kwargs):
        pass

class Mistyterrain:
    def durationCallback(self, *args, **kwargs):
        pass
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onSetStatus(self, *args, **kwargs):
        pass
    def onTryAddVolatile(self, *args, **kwargs):
        pass

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
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

class Mudsport:
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

class Multiattack:
    def onModifyType(self, *args, **kwargs):
        pass

class Naturalgift:
    def onModifyType(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass

class Naturepower:
    def onTryHit(self, *args, **kwargs):
        pass

class Naturesmadness:
    def damageCallback(self, *args, **kwargs):
        pass

class Nightmare:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Noretreat:
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass
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
        return True

class Octolock:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Odorsleuth:
    def onTryHit(self, *args, **kwargs):
        pass

class Orderup:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        pass

class Outrage:
    def onAfterMove(self, *args, **kwargs):
        pass

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
        pass
    def onHitField(self, user, battle):
        """All active Pokémon faint in three turns."""
        for side in getattr(battle, "sides", []):
            for mon in getattr(side, "active", []):
                if hasattr(mon, "volatiles"):
                    mon.volatiles["perishsong"] = 3
        return True
    def onResidual(self, *args, **kwargs):
        pass

class Petaldance:
    def onAfterMove(self, *args, **kwargs):
        pass

class Phantomforce:
    def onTryMove(self, *args, **kwargs):
        pass

class Photongeyser:
    def onModifyMove(self, *args, **kwargs):
        pass

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
        pass

class Powder:
    def onStart(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Powershift:
    def onCopy(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Powertrip:
    def basePowerCallback(self, user, target, move):
        """Increase power for each positive stat boost."""
        boosts = getattr(user, "boosts", {})
        positive = sum(v for v in boosts.values() if v > 0)
        return (getattr(move, "power", 0) or 0) + 20 * positive

class Present:
    def onModifyMove(self, *args, **kwargs):
        pass

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
        return True

class Psyblade:
    def onBasePower(self, *args, **kwargs):
        pass

class Psychicfangs:
    def onTryHit(self, *args, **kwargs):
        pass

class Psychicterrain:
    def durationCallback(self, *args, **kwargs):
        pass
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

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
        pass
    def onBeforeSwitchOut(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
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
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
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
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Ragingfury:
    def onAfterMove(self, *args, **kwargs):
        pass

class Rapidspin:
    def onAfterHit(self, *args, **kwargs):
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

class Razorwind:
    def onTryMove(self, *args, **kwargs):
        pass

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
        pass
    def onAnyModifyDamage(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
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
        pass

class Return:
    def basePowerCallback(self, user, target, move):
        """Power scales with happiness."""
        happiness = getattr(user, "happiness", 0)
        return max(1, int((happiness * 10) / 25))

class Revelationdance:
    def onModifyType(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Roost:
    def onStart(self, *args, **kwargs):
        pass
    def onType(self, *args, **kwargs):
        pass

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
        pass

class Safeguard:
    def durationCallback(self, *args, **kwargs):
        pass
    def onSetStatus(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass
    def onTryAddVolatile(self, *args, **kwargs):
        pass

class Saltcure:
    def onEnd(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Sandsearstorm:
    def onModifyMove(self, *args, **kwargs):
        pass

class Sappyseed:
    def onHit(self, user, target, battle):
        """Seed the target, draining HP each turn."""
        if hasattr(target, "volatiles"):
            target.volatiles["leechseed"] = user
        return True

class Secretpower:
    def onModifyMove(self, *args, **kwargs):
        pass

class Shadowforce:
    def onTryMove(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

class Shellsidearm:
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, user, target, battle):
        """May poison the target."""
        if getattr(target, "status", None) is None and random() < 0.2:
            if hasattr(target, "setStatus"):
                target.setStatus("psn")
        return True
    def onModifyMove(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass

class Shelltrap:
    def onHit(self, user, target, battle):
        """Only works if the user was hit by a contact move this turn."""
        if not getattr(user, "tempvals", {}).get("shelltrap", False):
            return False
        return True
    def onStart(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass
    def priorityChargeCallback(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Simplebeam:
    def onHit(self, user, target, battle):
        """Change the target's ability to Simple."""
        if hasattr(target, "__dict__"):
            target.ability = "Simple"
        return True
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onTryHit(self, *args, **kwargs):
        pass

class Skullbash:
    def onTryMove(self, *args, **kwargs):
        pass

class Skyattack:
    def onTryMove(self, *args, **kwargs):
        pass

class Skydrop:
    def onAnyBasePower(self, *args, **kwargs):
        pass
    def onAnyDragOut(self, *args, **kwargs):
        pass
    def onAnyInvulnerability(self, *args, **kwargs):
        pass
    def onFaint(self, *args, **kwargs):
        pass
    def onFoeBeforeMove(self, *args, **kwargs):
        pass
    def onFoeTrapPokemon(self, *args, **kwargs):
        pass
    def onHit(self, user, target, battle):
        """Release the target from Sky Drop."""
        if hasattr(target, "volatiles"):
            target.volatiles.pop("skydrop", None)
        return True
    def onModifyMove(self, *args, **kwargs):
        pass
    def onMoveFail(self, *args, **kwargs):
        pass
    def onRedirectTarget(self, *args, **kwargs):
        pass
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
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Solarblade:
    def onBasePower(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Sparklingaria:
    def onAfterMove(self, *args, **kwargs):
        pass

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
        pass
    def onSideRestart(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass
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
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Stealthrock:
    def onEntryHazard(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Steelbeam:
    def onAfterMove(self, *args, **kwargs):
        pass

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
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Stockpile:
    def onEnd(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
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
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

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
        pass

class Stuffcheeks:
    def onDisableMove(self, *args, **kwargs):
        pass
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
        pass
    def onHit(self, *args, **kwargs):
        user = args[0]
        max_hp = getattr(user, "max_hp", 0)
        if getattr(user, "hp", 0) <= max_hp // 4:
            return False
        user.hp -= max_hp // 4
        if hasattr(user, "volatiles"):
            user.volatiles["substitute"] = True
        return True
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass
    def onTryPrimaryHit(self, *args, **kwargs):
        pass

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
        pass

class Superfang:
    def damageCallback(self, *args, **kwargs):
        pass

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
        pass

class Synchronoise:
    def onTryImmunity(self, *args, **kwargs):
        pass

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
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onUpdate(self, *args, **kwargs):
        pass

class Tailwind:
    def durationCallback(self, *args, **kwargs):
        pass
    def onModifySpe(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onStart(self, *args, **kwargs):
        pass

class Taunt:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

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
        pass

class Telekinesis:
    def onAccuracy(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onImmunity(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        target = args[1] if len(args) > 1 else kwargs.get('target')
        if target and getattr(target, 'volatiles', {}).get('telekinesis'):
            return False
        return True
    def onUpdate(self, *args, **kwargs):
        pass

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
        pass
    def onModifyType(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass

class Terastarstorm:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onModifyType(self, *args, **kwargs):
        pass

class Terrainpulse:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onModifyType(self, *args, **kwargs):
        pass

class Thief:
    def onAfterHit(self, *args, **kwargs):
        pass

class Thousandarrows:
    def onEffectiveness(self, *args, **kwargs):
        pass

class Thousandwaves:
    def onHit(self, user, target, battle):
        """Trap the target, preventing switching."""
        if hasattr(target, "volatiles"):
            target.volatiles["trapped"] = True
        return True

class Thrash:
    def onAfterMove(self, *args, **kwargs):
        pass

class Throatchop:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        user, target = args[0], args[1]
        if hasattr(target, "volatiles"):
            target.volatiles["throatchop"] = 2
        return True
    def onModifyMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Thunder:
    def onModifyMove(self, *args, **kwargs):
        pass

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
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Toxicspikes:
    def onEntryHazard(self, *args, **kwargs):
        pass
    def onSideRestart(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Transform:
    def onHit(self, user, target, battle):
        """Copy the target's appearance and stats."""
        user.transformed = True
        user.species = getattr(target, "species", user.species)
        user.stats = getattr(target, "stats", {}).copy()
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
        pass

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
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldRestart(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

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
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

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
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

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
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

class Waterspout:
    def basePowerCallback(self, user, target, move):
        """Power scales with the user's remaining HP."""
        cur_hp = getattr(user, "hp", 0)
        max_hp = getattr(user, "max_hp", cur_hp or 1)
        return (getattr(move, "power", 150) or 150) * cur_hp / max_hp

class Weatherball:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onModifyType(self, *args, **kwargs):
        pass

class Wideguard:
    def onHitSide(self, user, battle):
        """Protect the side from multi-target moves for the turn."""
        side = getattr(user, "side", None)
        if side and hasattr(side, "volatiles"):
            side.volatiles["wideguard"] = True
            return True
        return False
    def onSideStart(self, *args, **kwargs):
        pass
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
    def onTryHit(self, *args, **kwargs):
        pass

class Wildboltstorm:
    def onModifyMove(self, *args, **kwargs):
        pass

class Wish:
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Wonderroom:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldRestart(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass

class Worryseed:
    def onHit(self, user, target, battle):
        """Replace the target's ability with Insomnia."""
        setattr(target, "ability", "insomnia")
        return True
    def onTryHit(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Wringout:
    def basePowerCallback(self, user, target, move):
        """Scale power with the target's remaining HP."""
        cur_hp = getattr(target, "hp", 0)
        max_hp = getattr(target, "max_hp", cur_hp or 1)
        return max(1, int(120 * cur_hp / max_hp))

class Yawn:
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

