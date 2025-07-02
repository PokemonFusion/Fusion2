from random import choice

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
    def onHit(self, *args, **kwargs):
        pass

class Allyswitch:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Anchorshot:
    def onHit(self, *args, **kwargs):
        pass

class Aquaring:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Aromatherapy:
    def onHit(self, *args, **kwargs):
        pass

class Assist:
    def onHit(self, *args, **kwargs):
        pass

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
        pass

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
        pass

class Autotomize:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Barbbarrage:
    def onBasePower(self, *args, **kwargs):
        pass

class Batonpass:
    def onHit(self, *args, **kwargs):
        pass

class Beakblast:
    def onAfterMove(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def priorityChargeCallback(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Bestow:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Burningbulwark:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Burningjealousy:
    def onHit(self, *args, **kwargs):
        pass

class Burnup:
    def onHit(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Camouflage:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Clearsmog:
    def onHit(self, *args, **kwargs):
        pass

class Collisioncourse:
    def onBasePower(self, *args, **kwargs):
        pass

class Comeuppance:
    def damageCallback(self, *args, **kwargs):
        pass
    def onModifyTarget(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Conversion:
    def onHit(self, *args, **kwargs):
        pass

class Conversion2:
    def onHit(self, *args, **kwargs):
        pass

class Copycat:
    def onHit(self, *args, **kwargs):
        pass

class Coreenforcer:
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

class Corrosivegas:
    def onHit(self, *args, **kwargs):
        pass

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
        pass

class Courtchange:
    def onHitField(self, *args, **kwargs):
        pass

class Covet:
    def onAfterHit(self, *args, **kwargs):
        pass

class Craftyshield:
    def onSideStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass
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
        pass

class Defog:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Doomdesire:
    def onTry(self, *args, **kwargs):
        pass

class Doubleshock:
    def onHit(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Entrainment:
    def onHit(self, *args, **kwargs):
        pass
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
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
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
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Fling:
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onUpdate(self, *args, **kwargs):
        pass

class Floralhealing:
    def onHit(self, *args, **kwargs):
        pass

class Flowershield:
    def onHitField(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
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
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Freezedry:
    def onEffectiveness(self, *args, **kwargs):
        pass

class Freezeshock:
    def onTryMove(self, *args, **kwargs):
        pass

class Freezyfrost:
    def onHit(self, *args, **kwargs):
        pass

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
        pass

class Gastroacid:
    def onCopy(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Gearup:
    def onHitSide(self, *args, **kwargs):
        pass

class Genesissupernova:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Gmaxcannonade:
    def onHit(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxcentiferno:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxchistrike:
    def onHit(self, *args, **kwargs):
        pass
    def onModifyCritRatio(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Gmaxcuddle:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxdepletion:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxfinale:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxfoamburst:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxgoldrush:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxmalodor:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxmeltdown:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxreplenish:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxsandblast:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxsmite:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxsnooze:
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

class Gmaxsteelsurge:
    def onEntryHazard(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxstonesurge:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxstunshock:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxsweetness:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxtartness:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxterror:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxvinelash:
    def onHit(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxvolcalith:
    def onHit(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxvoltcrash:
    def onHit(self, *args, **kwargs):
        pass

class Gmaxwildfire:
    def onHit(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Gmaxwindrage:
    def onHit(self, *args, **kwargs):
        pass

class Grassknot:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Grasspledge:
    def basePowerCallback(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

class Guardswap:
    def onHit(self, *args, **kwargs):
        pass

class Gyroball:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Happyhour:
    def onTryHit(self, *args, **kwargs):
        pass

class Hardpress:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Haze:
    def onHitField(self, *args, **kwargs):
        pass

class Healbell:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Heartswap:
    def onHit(self, *args, **kwargs):
        pass

class Heatcrash:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Heavyslam:
    def basePowerCallback(self, *args, **kwargs):
        pass
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
    def basePowerCallback(self, *args, **kwargs):
        pass

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
        pass

class Iceball:
    def basePowerCallback(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

class Infernalparade:
    def basePowerCallback(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Judgment:
    def onModifyType(self, *args, **kwargs):
        pass

class Jumpkick:
    def onMoveFail(self, *args, **kwargs):
        pass

class Junglehealing:
    def onHit(self, *args, **kwargs):
        pass

class Kingsshield:
    def onHit(self, *args, **kwargs):
        pass
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
        pass

class Lastrespects:
    def basePowerCallback(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onSourceAccuracy(self, *args, **kwargs):
        pass
    def onSourceInvulnerability(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Lowkick:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Luckychant:
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Lunarblessing:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHitSide(self, *args, **kwargs):
        pass

class Magnetrise:
    def onEnd(self, *args, **kwargs):
        pass
    def onImmunity(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Magnitude:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onUseMoveMessage(self, *args, **kwargs):
        pass

class Matblock:
    def onSideStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Maxairstream:
    def onHit(self, *args, **kwargs):
        pass

class Maxdarkness:
    def onHit(self, *args, **kwargs):
        pass

class Maxflare:
    def onHit(self, *args, **kwargs):
        pass

class Maxflutterby:
    def onHit(self, *args, **kwargs):
        pass

class Maxgeyser:
    def onHit(self, *args, **kwargs):
        pass

class Maxguard:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Maxhailstorm:
    def onHit(self, *args, **kwargs):
        pass

class Maxknuckle:
    def onHit(self, *args, **kwargs):
        pass

class Maxlightning:
    def onHit(self, *args, **kwargs):
        pass

class Maxmindstorm:
    def onHit(self, *args, **kwargs):
        pass

class Maxooze:
    def onHit(self, *args, **kwargs):
        pass

class Maxovergrowth:
    def onHit(self, *args, **kwargs):
        pass

class Maxphantasm:
    def onHit(self, *args, **kwargs):
        pass

class Maxquake:
    def onHit(self, *args, **kwargs):
        pass

class Maxrockfall:
    def onHit(self, *args, **kwargs):
        pass

class Maxstarfall:
    def onHit(self, *args, **kwargs):
        pass

class Maxsteelspike:
    def onHit(self, *args, **kwargs):
        pass

class Maxstrike:
    def onHit(self, *args, **kwargs):
        pass

class Maxwyrmwind:
    def onHit(self, *args, **kwargs):
        pass

class Meanlook:
    def onHit(self, *args, **kwargs):
        pass

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
        pass

class Meteorbeam:
    def onTryMove(self, *args, **kwargs):
        pass

class Metronome:
    def onHit(self, *args, **kwargs):
        pass

class Mimic:
    def onHit(self, *args, **kwargs):
        pass

class Mindblown:
    def onAfterMove(self, *args, **kwargs):
        pass

class Mindreader:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Morningsun:
    def onHit(self, *args, **kwargs):
        pass

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
        pass

class Obstruct:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Partingshot:
    def onHit(self, *args, **kwargs):
        pass

class Payback:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Perishsong:
    def onEnd(self, *args, **kwargs):
        pass
    def onHitField(self, *args, **kwargs):
        pass
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
    def basePowerCallback(self, *args, **kwargs):
        pass

class Pluck:
    def onHit(self, *args, **kwargs):
        pass

class Pollenpuff:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass

class Poltergeist:
    def onTry(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

class Powerswap:
    def onHit(self, *args, **kwargs):
        pass

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
    def basePowerCallback(self, *args, **kwargs):
        pass

class Present:
    def onModifyMove(self, *args, **kwargs):
        pass

class Protect:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Psychup:
    def onHit(self, *args, **kwargs):
        pass

class Psywave:
    def damageCallback(self, *args, **kwargs):
        pass

class Punishment:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Purify:
    def onHit(self, *args, **kwargs):
        pass

class Pursuit:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def beforeTurnCallback(self, *args, **kwargs):
        pass
    def onBeforeSwitchOut(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Quash:
    def onHit(self, *args, **kwargs):
        pass

class Quickguard:
    def onHitSide(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Rage:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Ragefist:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Ragepowder:
    def onFoeRedirectTarget(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Refresh:
    def onHit(self, *args, **kwargs):
        pass

class Relicsong:
    def onAfterMoveSecondarySelf(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

class Rest:
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Retaliate:
    def onBasePower(self, *args, **kwargs):
        pass

class Return:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Revelationdance:
    def onModifyType(self, *args, **kwargs):
        pass

class Revenge:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Reversal:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Revivalblessing:
    def onTryHit(self, *args, **kwargs):
        pass

class Risingvoltage:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Roleplay:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Rollout:
    def basePowerCallback(self, *args, **kwargs):
        pass
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
    def onHitField(self, *args, **kwargs):
        pass

class Round:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Secretpower:
    def onModifyMove(self, *args, **kwargs):
        pass

class Shadowforce:
    def onTryMove(self, *args, **kwargs):
        pass

class Shedtail:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Shellsidearm:
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass

class Shelltrap:
    def onHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass
    def priorityChargeCallback(self, *args, **kwargs):
        pass

class Shoreup:
    def onHit(self, *args, **kwargs):
        pass

class Silktrap:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Simplebeam:
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Sketch:
    def onHit(self, *args, **kwargs):
        pass

class Skillswap:
    def onHit(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onMoveFail(self, *args, **kwargs):
        pass
    def onRedirectTarget(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Sleeptalk:
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Smackdown:
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Smellingsalts:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

class Snatch:
    def onAnyPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Snore:
    def onTry(self, *args, **kwargs):
        pass

class Soak:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Speedswap:
    def onHit(self, *args, **kwargs):
        pass

class Spiderweb:
    def onHit(self, *args, **kwargs):
        pass

class Spikes:
    def onEntryHazard(self, *args, **kwargs):
        pass
    def onSideRestart(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Spikyshield:
    def onHit(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Spiritshackle:
    def onHit(self, *args, **kwargs):
        pass

class Spite:
    def onHit(self, *args, **kwargs):
        pass

class Spitup:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onAfterMove(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Splash:
    def onTry(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

class Splinteredstormshards:
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

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
    def onAfterSubDamage(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

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
        pass

class Stompingtantrum:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Stoneaxe:
    def onAfterHit(self, *args, **kwargs):
        pass
    def onAfterSubDamage(self, *args, **kwargs):
        pass

class Storedpower:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Strengthsap:
    def onHit(self, *args, **kwargs):
        pass

class Struggle:
    def onModifyMove(self, *args, **kwargs):
        pass

class Stuffcheeks:
    def onDisableMove(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Substitute:
    def onEnd(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass
    def onTryPrimaryHit(self, *args, **kwargs):
        pass

class Suckerpunch:
    def onTry(self, *args, **kwargs):
        pass

class Supercellslam:
    def onMoveFail(self, *args, **kwargs):
        pass

class Superfang:
    def damageCallback(self, *args, **kwargs):
        pass

class Swallow:
    def onHit(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass

class Switcheroo:
    def onHit(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Synchronoise:
    def onTryImmunity(self, *args, **kwargs):
        pass

class Synthesis:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

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
    def onHitField(self, *args, **kwargs):
        pass

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
        pass
    def onUpdate(self, *args, **kwargs):
        pass

class Teleport:
    def onTry(self, *args, **kwargs):
        pass

class Temperflare:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Terablast:
    def basePowerCallback(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass

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
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Thunder:
    def onModifyMove(self, *args, **kwargs):
        pass

class Thunderclap:
    def onTry(self, *args, **kwargs):
        pass

class Tidyup:
    def onHit(self, *args, **kwargs):
        pass

class Topsyturvy:
    def onHit(self, *args, **kwargs):
        pass

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
    def onHit(self, *args, **kwargs):
        pass

class Triattack:
    def onHit(self, *args, **kwargs):
        pass

class Trick:
    def onHit(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Trickortreat:
    def onHit(self, *args, **kwargs):
        pass

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
    def basePowerCallback(self, *args, **kwargs):
        pass

class Triplekick:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Trumpcard:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Upperhand:
    def onTry(self, *args, **kwargs):
        pass

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
    def basePowerCallback(self, *args, **kwargs):
        pass

class Venomdrench:
    def onHit(self, *args, **kwargs):
        pass

class Venoshock:
    def onBasePower(self, *args, **kwargs):
        pass

class Wakeupslap:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onHit(self, *args, **kwargs):
        pass

class Waterpledge:
    def basePowerCallback(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onPrepareHit(self, *args, **kwargs):
        pass
    def onSideEnd(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass

class Watershuriken:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Watersport:
    def onBasePower(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

class Waterspout:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Weatherball:
    def onModifyMove(self, *args, **kwargs):
        pass
    def onModifyType(self, *args, **kwargs):
        pass

class Wideguard:
    def onHitSide(self, *args, **kwargs):
        pass
    def onSideStart(self, *args, **kwargs):
        pass
    def onTry(self, *args, **kwargs):
        pass
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
    def onHit(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass
    def onTryImmunity(self, *args, **kwargs):
        pass

class Wringout:
    def basePowerCallback(self, *args, **kwargs):
        pass

class Yawn:
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryHit(self, *args, **kwargs):
        pass

