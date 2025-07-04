from random import random, choice
from pokemon.battle.utils import apply_boost
from pokemon.dex.functions.moves_funcs import type_effectiveness


class Adaptability:
    def onModifySTAB(self, stab, source=None, target=None, move=None):
        """Increase STAB multiplier from 1.5x to 2x."""
        if not move:
            return stab
        has_type = False
        if getattr(move, "forceSTAB", False):
            has_type = True
        elif source and getattr(source, "types", None):
            has_type = move.type in source.types
        if has_type:
            return 2.25 if stab == 2 else 2
        return stab

class Aerilate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        """Boost power of converted moves by 20%."""
        if move and getattr(move, "typeChangerBoosted", False):
            return int(base_power * 1.2)
        return base_power

    def onModifyType(self, move, user=None):
        """Convert Normal-type moves to Flying before use."""
        if not move or move.type != "Normal":
            return
        no_modify = {
            "judgment",
            "multiattack",
            "naturalgift",
            "revelationdance",
            "technoblast",
            "terrainpulse",
            "weatherball",
        }
        if getattr(move, "id", "").lower() in no_modify:
            return
        if getattr(move, "isZ", False) and move.category != "Status":
            return
        move.type = "Flying"
        move.typeChangerBoosted = True

class Aftermath:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        """Damage the attacker if this Pokémon faints from a contact move."""
        if target is None or source is None or move is None:
            return
        if getattr(target, "hp", 1) > 0:
            return
        if move and getattr(move, "flags", {}).get("contact"):
            recoil = getattr(source, "max_hp", 0) // 4
            if hasattr(source, "hp"):
                source.hp = max(0, source.hp - recoil)

class Airlock:
    def onEnd(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", False)

    def onStart(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", True)

    def onSwitchIn(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", True)

class Analytic:
    def onBasePower(self, base_power, user=None, target=None, move=None, battle=None):
        """Boost power if user moves last."""
        if battle and hasattr(battle, "queue"):
            if any(getattr(battle.queue, "will_move", lambda t: False)(t) for t in getattr(battle, "participants", [] ) if t is not user):
                return base_power
        if target and getattr(target, "tempvals", {}).get("moved"):
            return int(base_power * 1.3)
        return base_power

class Angerpoint:
    def onHit(self, target=None, source=None, move=None):
        """Maximize Attack when hit by a critical move."""
        if not target or not move:
            return
        if getattr(move, "crit", False):
            if hasattr(target, "boosts"):
                target.boosts["atk"] = 6

class Angershell:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if not target or not source or not move:
            return
        if getattr(target, "hp", 0) <= 0:
            return
        last_hp = getattr(target, "max_hp", 1) // 2
        if target.hp <= last_hp and getattr(target, "_angerShellPrev", target.hp + 1) > last_hp:
            if hasattr(target, "boosts"):
                apply_boost(target, {"atk": 1, "spa": 1, "spe": 1, "def": -1, "spd": -1})
        target._angerShellPrev = target.hp

    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and not getattr(effect, "multihit", False):
            target._angerShellChecked = False
        else:
            target._angerShellChecked = True
        return damage

    def onTryEatItem(self, item, pokemon=None):
        healing_items = {
            "aguavberry",
            "enigmaberry",
            "figyberry",
            "iapapaberry",
            "magoberry",
            "sitrusberry",
            "wikiberry",
            "oranberry",
            "berryjuice",
        }
        if item and getattr(item, "id", "").lower() in healing_items:
            return getattr(pokemon, "_angerShellChecked", True)
        return True

class Anticipation:
    def onStart(self, pokemon=None):
        """Inform if foes have a super-effective or OHKO move."""
        if not pokemon:
            return
        for foe in getattr(pokemon, "foes", lambda: [])():
            for move in getattr(foe, "moves", []):
                mtype = getattr(move, "type", None)
                if not mtype or getattr(move, "category", "Status") == "Status":
                    continue
                if getattr(move, "ohko", False):
                    setattr(pokemon, "anticipated", True)
                    return
                if hasattr(pokemon, "types") and mtype in pokemon.types:
                    setattr(pokemon, "anticipated", True)
                    return

class Arenatrap:
    def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
        if not source:
            source = getattr(self, "effect_state", {}).get("target")
        if source and pokemon and getattr(pokemon, "is_grounded", lambda _: True)(not getattr(pokemon, "knownType", True)):
            pokemon.maybeTrapped = True

    def onFoeTrapPokemon(self, pokemon=None):
        if not pokemon:
            return
        if getattr(pokemon, "isAdjacent", lambda o: True)(getattr(self, "effect_state", {}).get("target")) and getattr(pokemon, "is_grounded", lambda: True)():
            getattr(pokemon, "tryTrap", lambda *_: None)(True)

class Armortail:
    def onFoeTryMove(self, target=None, source=None, move=None):
        if not move or not source:
            return
        target_all_exceptions = {"perishsong", "flowershield", "rototiller"}
        if move.target in {"foeSide"} or (move.target == "all" and move.id not in target_all_exceptions):
            return
        if move.priority > 0 and (source.is_ally(target) or move.target == "all"):
            if hasattr(source, "tempvals"):
                source.tempvals["cant_move"] = "armortail"
            return False

class Aromaveil:
    def onAllyTryAddVolatile(self, status, target=None, source=None, effect=None):
        block = {"attract", "disable", "encore", "healblock", "taunt", "torment"}
        if status in block:
            if effect and getattr(effect, "effectType", "") == "Move":
                if target and hasattr(target, "tempvals"):
                    target.tempvals.setdefault("blocked", []).append("Aroma Veil")
            return None

class Asoneglastrier:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unnerved"] = False

    def onFoeTryEatItem(self):
        return not getattr(self, "effect_state", {}).get("unnerved", False)

    def onPreStart(self, pokemon=None):
        if pokemon:
            self.onStart(pokemon)

    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            apply_boost(source, {"atk": length})

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unnerved"] = True

class Asonespectrier:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unnerved"] = False

    def onFoeTryEatItem(self):
        return not getattr(self, "effect_state", {}).get("unnerved", False)

    def onPreStart(self, pokemon=None):
        if pokemon:
            self.onStart(pokemon)

    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            apply_boost(source, {"spa": length})

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unnerved"] = True

class Aurabreak:
    def onAnyTryPrimaryHit(self, target=None, source=None, move=None):
        if move and move.category != "Status" and target is not source:
            move.hasAuraBreak = True

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "aura_break", True)

class Baddreams:
    def onResidual(self, pokemon=None):
        if not pokemon or getattr(pokemon, "hp", 0) <= 0:
            return
        for foe in getattr(pokemon, "foes", lambda: [])():
            if getattr(foe, "status", None) == "slp" or foe.hasAbility("comatose"):
                dmg = getattr(foe, "max_hp", 0) // 8
                foe.hp = max(0, foe.hp - dmg)

class Battery:
    def onAllyBasePower(self, base_power, attacker=None, defender=None, move=None):
        if attacker and move and attacker is not getattr(self, "effect_state", {}).get("target"):
            if getattr(move, "category", "") == "Special":
                return int(base_power * 1.3)
        return base_power

class Battlebond:
    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source and not getattr(source, "transformed", False):
            if getattr(source, "species", {}).get("name", "").lower() == "greninjabond" and source.hp > 0:
                apply_boost(source, {"atk": 1, "spa": 1, "spe": 1})
                source.abilityState = getattr(source, "abilityState", {})
                source.abilityState["battleBondTriggered"] = True

class Beadsofruin:
    def onAnyModifySpD(self, spd, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if target and holder and target is not holder and getattr(move, "category", None) != "Status":
            return int(spd * 0.75)
        return spd

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "beads_of_ruin", True)

class Beastboost:
    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            if hasattr(source, "getBestStat"):
                best = source.getBestStat(True, True)
                apply_boost(source, {best: length})

class Berserk:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if not target or not source or not move:
            return
        last_hp = getattr(target, "max_hp", 1) // 2
        if target.hp <= last_hp and getattr(target, "_berserk_prev", target.hp + 1) > last_hp:
            apply_boost(target, {"spa": 1})
        target._berserk_prev = target.hp

    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and not getattr(effect, "multihit", False):
            target._berserk_checked = False
        else:
            target._berserk_checked = True
        return damage

    def onTryEatItem(self, item, pokemon=None):
        healing_items = {
            "aguavberry",
            "enigmaberry",
            "figyberry",
            "iapapaberry",
            "magoberry",
            "sitrusberry",
            "wikiberry",
            "oranberry",
            "berryjuice",
        }
        if item and getattr(item, "id", "").lower() in healing_items:
            return getattr(pokemon, "_berserk_checked", True)
        return True

class Bigpecks:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if source and target is source:
            return
        if "def" in boost and boost["def"] < 0:
            del boost["def"]
            if effect and getattr(effect, "id", "") != "octolock" and not getattr(effect, "secondaries", None):
                if target and hasattr(target, "tempvals"):
                    target.tempvals.setdefault("unboost", []).append("def")

class Blaze:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Fire" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Fire" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(spa * 1.5)
        return spa

class Bulletproof:
    def onTryHit(self, pokemon=None, source=None, move=None):
        if move and move.flags.get("bullet"):
            if pokemon:
                setattr(pokemon, "immune", "Bulletproof")
            return None

class Cheekpouch:
    def onEatItem(self, item=None, pokemon=None):
        if pokemon and item:
            heal = getattr(pokemon, "max_hp", 0) // 3
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)

class Chillingneigh:
    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            apply_boost(source, {"atk": length})

class Chlorophyll:
    def onModifySpe(self, spe, pokemon=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
            return int(spe * 2)
        return spe

class Clearbody:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if source and source is target:
            return
        changed = False
        for stat in list(boost.keys()):
            if boost[stat] < 0:
                del boost[stat]
                changed = True
        if changed and effect and getattr(effect, "id", "") != "octolock" and not getattr(effect, "secondaries", None):
            if target and hasattr(target, "tempvals"):
                target.tempvals.setdefault("unboost", []).append("clearbody")

class Cloudnine:
    def onEnd(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", False)

    def onStart(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", True)

    def onSwitchIn(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressWeather", True)

class Colorchange:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if not target or not move or getattr(move, "category", "Status") == "Status":
            return
        mtype = move.type
        if mtype and mtype != "???" and target.isActive and not target.hasType(mtype):
            if hasattr(target, "setType") and target.setType(mtype):
                if hasattr(target, "tempvals"):
                    target.tempvals["typechange"] = mtype

class Comatose:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if effect and getattr(effect, "status", None):
            return False

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "comatose", True)

class Commander:
    def onUpdate(self, pokemon=None, battle=None):
        if not pokemon or getattr(battle, "gameType", "singles") != "doubles":
            return
        allies = pokemon.allies() if hasattr(pokemon, "allies") else []
        ally = allies[0] if allies else None
        if not ally or pokemon.base_species != "Tatsugiri" or getattr(ally, "base_species", None) != "Dondozo":
            if getattr(pokemon, "volatiles", {}).get("commanding"):
                pokemon.volatiles.pop("commanding", None)
            return
        if not getattr(pokemon, "volatiles", {}).get("commanding"):
            if getattr(ally, "volatiles", {}).get("commanded"):
                return
            if battle and hasattr(battle, "queue"):
                battle.queue.cancel_action(pokemon)
            pokemon.addVolatile("commanding") if hasattr(pokemon, "addVolatile") else None
            ally.addVolatile("commanded", pokemon) if hasattr(ally, "addVolatile") else None

class Competitive:
    def onAfterEachBoost(self, boost, target=None, source=None, effect=None):
        if not source or target.is_ally(source):
            return
        lowered = any(val < 0 for val in boost.values())
        if lowered:
            apply_boost(target, {"spa": 2})

class Compoundeyes:
    def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
        if accuracy is not True:
            return int(accuracy * 1.3)
        return accuracy

class Contrary:
    def onChangeBoost(self, boosts, target=None, source=None, effect=None):
        for stat, value in list(boosts.items()):
            boosts[stat] = -value

class Costar:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        allies = [ally for ally in getattr(pokemon, "allies", lambda: [])() if ally is not pokemon]
        if allies:
            target = allies[0]
            pokemon.boosts = dict(getattr(target, "boosts", {}))

class Cottondown:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and source and getattr(move, "category", "") != "Status":
            apply_boost(target, {"spe": -1})

class Cudchew:
    def onEatItem(self, item=None, pokemon=None):
        if pokemon and item:
            pokemon.addVolatile("cudchew") if hasattr(pokemon, "addVolatile") else None
            pokemon.consumed_item = item

    def onEnd(self, pokemon=None):
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles.pop("cudchew", None)

    def onRestart(self, pokemon=None):
        self.onEatItem(getattr(pokemon, "consumed_item", None), pokemon)

class Curiousmedicine:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        allies = pokemon.allies() if hasattr(pokemon, "allies") else []
        for ally in allies:
            ally.boosts = {stat: 0 for stat in ally.boosts}

class Cursedbody:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and hasattr(source, "disable_move"):
            if random.random() < 0.3:
                source.disable_move(move.id)

class Cutecharm:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and getattr(move, "flags", {}).get("contact"):
            if getattr(source, "gender", "N") != "N" and getattr(target, "gender", "N") != "N" and source.gender != target.gender:
                if random() < 0.3 and hasattr(source, "volatiles"):
                    source.volatiles["attract"] = target

class Damp:
    def onAnyDamage(self, damage, target=None, source=None, effect=None):
        if effect and effect.id in {"aftermath", "explosion", "mindblown", "selfdestruct"}:
            return 0
        return damage

    def onAnyTryMove(self, pokemon=None, target=None, move=None):
        if move and move.id in {"explosion", "selfdestruct", "mindblown"}:
            return False

class Darkaura:
    def onAnyBasePower(self, base_power, source=None, target=None, move=None):
        if move and move.type == "Dark" and source is not target:
            return int(base_power * 1.33)
        return base_power

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "dark_aura", True)

class Dauntlessshield:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"def": 1})

class Dazzling:
    def onFoeTryMove(self, target=None, source=None, move=None):
        if move and move.priority > 0 and not source.is_ally(target):
            if hasattr(source, "tempvals"):
                source.tempvals["cant_move"] = "dazzling"
            return False

class Defeatist:
    def onModifyAtk(self, atk, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            return atk // 2
        return atk

    def onModifySpA(self, spa, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            return spa // 2
        return spa

class Defiant:
    def onAfterEachBoost(self, boost, target=None, source=None, effect=None):
        if source and source.is_ally(target):
            return
        lowered = any(val < 0 for val in boost.values())
        if lowered:
            apply_boost(target, {"atk": 2})

class Deltastream:
    def onAnySetWeather(self, target=None, source=None, weather=None):
        strong_weathers = {"desolateland", "primordialsea", "deltastream"}
        if weather and weather.id not in strong_weathers and getattr(self, "field_weather", "") == "deltastream":
            return False

    def onEnd(self, pokemon=None, battle=None):
        if battle and battle.weather_state.get("source") == pokemon:
            battle.clearWeather()

    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("deltastream", source)

class Desolateland:
    def onAnySetWeather(self, target=None, source=None, weather=None):
        strong = {"desolateland", "primordialsea", "deltastream"}
        if getattr(self, "field_weather", "") == "desolateland" and weather and weather.id not in strong:
            return False

    def onEnd(self, pokemon=None, battle=None):
        if battle and battle.weather_state.get("source") == pokemon:
            battle.clearWeather()

    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("desolateland", source)

class Disguise:
    def onCriticalHit(self, target=None, source=None, move=None):
        if target and target.species.name.lower().startswith("mimikyu"):
            if not target.volatiles.get("substitute"):
                return False

    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and effect.effectType == "Move" and target and target.species.name.lower().startswith("mimikyu"):
            target.volatiles["disguise_busted"] = True
            return 0
        return damage

    def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
        if target and move and move.category != "Status" and target.species.name.lower().startswith("mimikyu"):
            if not target.volatiles.get("substitute") and target.runImmunity(move.type):
                return 0
        return type_mod

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.volatiles.get("disguise_busted"):
            speciesid = "Mimikyu-Busted" if pokemon.species.name.lower() == "mimikyu" else "Mimikyu-Busted-Totem"
            pokemon.formeChange(speciesid)
            dmg = pokemon.max_hp // 8
            pokemon.hp = max(0, pokemon.hp - dmg)

class Download:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        total_def = 0
        total_spd = 0
        for foe in pokemon.foes():
            total_def += foe.getStat("def", False, True)
            total_spd += foe.getStat("spd", False, True)
        if total_def and total_def >= total_spd:
            apply_boost(pokemon, {"spa": 1})
        elif total_spd:
            apply_boost(pokemon, {"atk": 1})

class Dragonsmaw:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Dragon":
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Dragon":
            return int(spa * 1.5)
        return spa

class Drizzle:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("raindance", source)

class Drought:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("sunnyday", source)

class Dryskin:
    def onSourceBasePower(self, base_power, attacker=None, defender=None, move=None):
        if move and move.type == "Fire":
            return int(base_power * 1.25)
        return base_power

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            heal = target.max_hp // 4
            target.hp = min(target.max_hp, target.hp + heal)
            if hasattr(target, "immune"):
                target.immune = "Dry Skin"
            return None

    def onWeather(self, pokemon=None):
        if not pokemon:
            return
        weather = getattr(pokemon, "effective_weather", lambda: "")()
        if weather in {"raindance", "primordialsea"}:
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + pokemon.max_hp // 16)
        elif weather in {"sunnyday", "desolateland"}:
            pokemon.hp = max(0, pokemon.hp - pokemon.max_hp // 8)

class Eartheater:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Ground" and target:
            heal = target.max_hp // 4
            target.hp = min(target.max_hp, target.hp + heal)
            if hasattr(target, "immune"):
                target.immune = "Earth Eater"
            return None

class Effectspore:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            roll = random()
            if roll < 1 / 3:
                if hasattr(source, "setStatus"):
                    source.setStatus("par")
            elif roll < 2 / 3:
                if hasattr(source, "setStatus"):
                    source.setStatus("slp")
            else:
                if hasattr(source, "setStatus"):
                    source.setStatus("psn")

class Electricsurge:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setTerrain("electricterrain", source)

class Electromorphosis:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target:
            target.volatiles = getattr(target, "volatiles", {})
            target.volatiles["charged"] = True

class Embodyaspectcornerstone:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"def": 1})

    def onSwitchIn(self, pokemon=None):
        self.onStart(pokemon)

class Embodyaspecthearthflame:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"atk": 1})

    def onSwitchIn(self, pokemon=None):
        self.onStart(pokemon)

class Embodyaspectteal:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"spe": 1})

    def onSwitchIn(self, pokemon=None):
        self.onStart(pokemon)

class Embodyaspectwellspring:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"spd": 1})

    def onSwitchIn(self, pokemon=None):
        self.onStart(pokemon)

class Emergencyexit:
    def onEmergencyExit(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            pokemon.switch_flag = True

class Fairyaura:
    def onAnyBasePower(self, base_power, source=None, target=None, move=None):
        if move and move.type == "Fairy" and source is not target:
            if getattr(move, "hasAuraBreak", False):
                return int(base_power * 0.75)
            return int(base_power * 1.33)
        return base_power

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "fairy_aura", True)

class Filter:
    def onSourceModifyDamage(self, damage, target=None, source=None, move=None):
        if target and move and type_effectiveness(target, move) > 1:
            return int(damage * 0.75)
        return damage

class Flamebody:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            if random() < 0.3 and hasattr(source, "setStatus"):
                source.setStatus("brn")

class Flareboost:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and user.status == "brn" and move and move.category == "Special":
            return int(base_power * 1.5)
        return base_power

class Flashfire:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["flashfire"] = False

    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Fire" and getattr(attacker, "abilityState", {}).get("flashfire"):
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Fire" and getattr(attacker, "abilityState", {}).get("flashfire"):
            return int(spa * 1.5)
        return spa

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["flashfire"] = False

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Fire" and target:
            target.abilityState = getattr(target, "abilityState", {})
            target.abilityState["flashfire"] = True
            if hasattr(target, "immune"):
                target.immune = "Flash Fire"
            return None

class Flowergift:
    def onAllyModifyAtk(self, atk, pokemon=None, move=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
            return int(atk * 1.5)
        return atk

    def onAllyModifySpD(self, spd, pokemon=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
            return int(spd * 1.5)
        return spd

    def _update_form(self, pokemon=None):
        if not pokemon or pokemon.species.name.lower() != "cherrim":
            return
        sunny = getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}
        form = "Cherrim-Sunshine" if sunny else "Cherrim"
        pokemon.formeChange(form)

    def onStart(self, pokemon=None):
        self._update_form(pokemon)

    def onWeatherChange(self, pokemon=None):
        self._update_form(pokemon)

class Flowerveil:
    def onAllySetStatus(self, status, target=None, source=None, effect=None):
        if target and "Grass" in getattr(target, "types", []):
            return False

    def onAllyTryAddVolatile(self, status, target=None, source=None, effect=None):
        if target and "Grass" in getattr(target, "types", []) and status == "attract":
            return None

    def onAllyTryBoost(self, boost, target=None, source=None, effect=None):
        if target and "Grass" in getattr(target, "types", []):
            for stat in list(boost.keys()):
                if boost[stat] < 0:
                    del boost[stat]

class Fluffy:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if not move:
            return damage
        if move.flags.get("contact"):
            damage = damage // 2
        if move.type == "Fire":
            damage = int(damage * 2)
        return damage

class Forecast:
    def _update_form(self, pokemon=None):
        if not pokemon or pokemon.base_species != "Castform":
            return
        weather = getattr(pokemon, "effective_weather", lambda: "")()
        form = "Castform"
        if weather in {"sunnyday", "desolateland"}:
            form = "Castform-Sunny"
        elif weather in {"raindance", "primordialsea"}:
            form = "Castform-Rainy"
        elif weather in {"hail", "snow"}:
            form = "Castform-Snowy"
        pokemon.formeChange(form)

    def onStart(self, pokemon=None):
        self._update_form(pokemon)

    def onWeatherChange(self, pokemon=None):
        self._update_form(pokemon)

class Forewarn:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        best_move = None
        best_power = -1
        for foe in pokemon.foes():
            for move in getattr(foe, "moves", []):
                power = getattr(move, "power", 0) or 0
                if power > best_power:
                    best_power = power
                    best_move = move.name
        if best_move:
            pokemon.forewarn = best_move

class Friendguard:
    def onAnyModifyDamage(self, damage, source=None, target=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target and target is not holder and target.is_ally(holder):
            return int(damage * 0.75)
        return damage

class Frisk:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        for foe in pokemon.foes():
            item = getattr(foe, "item", None)
            if item:
                pokemon.frisked = getattr(pokemon, "frisked", [])
                pokemon.frisked.append(item)

class Fullmetalbody:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if source and source is target:
            return
        for stat in list(boost.keys()):
            if boost[stat] < 0:
                del boost[stat]

class Furcoat:
    def onModifyDef(self, defense, pokemon=None):
        return defense * 2

class Galewings:
    def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
        if pokemon and move and move.type == "Flying" and pokemon.hp == pokemon.max_hp:
            return priority + 1
        return priority

class Galvanize:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "typeChangerBoosted", False):
            return int(base_power * 1.2)
        return base_power

    def onModifyType(self, move, pokemon=None):
        if move and move.type == "Normal":
            move.type = "Electric"
            move.typeChangerBoosted = True

class Gluttony:
    def onDamage(self, damage, pokemon=None, source=None, effect=None):
        berries = {"aguavberry", "figyberry", "iapapaberry", "magoberry", "wikiberry"}
        item = getattr(pokemon, "item", None)
        if item and item.id.lower() in berries and pokemon.hp - damage <= pokemon.max_hp // 2:
            pokemon.eat_item = item
        return damage

    def onStart(self, pokemon=None):
        setattr(pokemon, "gluttony", True)

class Goodasgold:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.category == "Status" and target is not source:
            if hasattr(target, "immune"):
                target.immune = "Good as Gold"
            return False

class Gooey:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            apply_boost(source, {"spe": -1})

class Gorillatactics:
    def onBeforeMove(self, pokemon=None, target=None, move=None):
        locked = getattr(pokemon, "abilityState", {}).get("locked_move")
        if locked and move and move.id != locked:
            return False

    def onDisableMove(self, pokemon=None):
        locked = getattr(pokemon, "abilityState", {}).get("locked_move")
        if locked:
            for m in pokemon.moves:
                if m.id != locked:
                    pokemon.disabled_moves = getattr(pokemon, "disabled_moves", set())
                    pokemon.disabled_moves.add(m.id)

    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState.pop("locked_move", None)

    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        return int(atk * 1.5)

    def onModifyMove(self, move, pokemon=None):
        if pokemon and not pokemon.abilityState.get("locked_move"):
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["locked_move"] = move.id

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["locked_move"] = None

class Grasspelt:
    def onModifyDef(self, defense, pokemon=None):
        terrain = getattr(pokemon, "terrain", "")
        if terrain == "grassyterrain":
            return int(defense * 1.5)
        return defense

class Grassysurge:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setTerrain("grassyterrain", source)

class Grimneigh:
    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            apply_boost(source, {"spa": length})

class Guarddog:
    def onDragOut(self, pokemon=None):
        return False

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if "atk" in boost and boost["atk"] < 0:
            del boost["atk"]
            apply_boost(target, {"atk": 1})

class Gulpmissile:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        state = getattr(target, "volatiles", {}).pop("gulpmissile", None)
        if state and source:
            source.hp = max(0, source.hp - source.max_hp // 4)
            if state == "gorging":
                apply_boost(source, {"def": -1})
            else:
                apply_boost(source, {"spe": -1})

    def onSourceTryPrimaryHit(self, user=None, target=None, move=None):
        if user and move and move.id in {"surf", "dive"}:
            user.volatiles = getattr(user, "volatiles", {})
            user.volatiles["gulpmissile"] = "gorging" if user.species.name.endswith("2") else "gulping"

class Guts:
    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and pokemon.status:
            return int(atk * 1.5)
        return atk

class Hadronengine:
    def onModifySpA(self, spa, pokemon=None, target=None, move=None):
        terrain = getattr(pokemon, "terrain", "")
        if terrain == "electricterrain":
            return int(spa * 1.3)
        return spa

    def onStart(self, source=None, battle=None):
        if battle:
            battle.setTerrain("electricterrain", source)

class Harvest:
    def onResidual(self, pokemon=None):
        if not pokemon or getattr(pokemon, "item", None):
            return
        berry = getattr(pokemon, "consumed_berry", None)
        if not berry:
            return
        chance = 1.0 if getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"} else 0.5
        if random() < chance:
            pokemon.item = berry
            pokemon.consumed_berry = None

class Healer:
    def onResidual(self, pokemon=None):
        if not pokemon:
            return
        for ally in pokemon.allies():
            if ally.status and random() < 0.3:
                ally.setStatus(0)

class Heatproof:
    def onDamage(self, damage, pokemon=None, source=None, effect=None):
        if effect and effect.id == "brn":
            return damage // 2
        return damage

    def onSourceModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Fire":
            return atk // 2
        return atk

    def onSourceModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Fire":
            return spa // 2
        return spa

class Heavymetal:
    def onModifyWeight(self, weight, pokemon=None):
        return weight * 2

class Hospitality:
    def onStart(self, pokemon=None):
        allies = [a for a in pokemon.allies() if a is not pokemon] if pokemon else []
        if allies:
            ally = allies[0]
            heal = ally.max_hp // 3
            ally.hp = min(ally.max_hp, ally.hp + heal)

class Hugepower:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        return atk * 2

class Hungerswitch:
    def onResidual(self, pokemon=None):
        if not pokemon:
            return
        if pokemon.species.name.endswith("Hangry"):
            new_form = pokemon.species.name.replace("Hangry", "")
        else:
            new_form = pokemon.species.name + "Hangry"
        pokemon.formeChange(new_form)

class Hustle:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        return int(atk * 1.5)

    def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
        if move and accuracy is not True:
            return int(accuracy * 0.8)
        return accuracy

class Hydration:
    def onResidual(self, pokemon=None):
        if pokemon and pokemon.status and getattr(pokemon, "effective_weather", lambda: "")() in {"raindance", "primordialsea"}:
            pokemon.setStatus(0)

class Hypercutter:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if "atk" in boost and boost["atk"] < 0:
            del boost["atk"]

class Icebody:
    def onImmunity(self, status=None, pokemon=None):
        """Prevent hail or snow damage."""
        if status in {"hail", "snow"}:
            return False

    def onWeather(self, pokemon=None):
        """Heal in hail or snow."""
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"hail", "snow"}:
            heal = pokemon.max_hp // 16
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)

class Iceface:
    def onCriticalHit(self, target=None, source=None, move=None):
        if getattr(target, "abilityState", {}).get("iceface_intact"):
            return False

    def onDamage(self, damage, target=None, source=None, move=None):
        if move and move.category == "Physical" and target and target.abilityState.get("iceface_intact"):
            target.abilityState["iceface_intact"] = False
            if target.species.name.lower().startswith("eiscue") and not target.species.name.lower().endswith("noice"):
                target.formeChange("Eiscue-Noice")
            return 0
        return damage

    def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
        if move and move.category == "Physical" and target and target.abilityState.get("iceface_intact"):
            return 0
        return type_mod

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["iceface_intact"] = True

    def onUpdate(self, pokemon=None):
        weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
        if pokemon and not pokemon.abilityState.get("iceface_intact") and weather in {"hail", "snow"}:
            if pokemon.species.name.lower().endswith("noice"):
                pokemon.formeChange("Eiscue")
            pokemon.abilityState["iceface_intact"] = True

    def onWeatherChange(self, pokemon=None):
        self.onUpdate(pokemon)

class Icescales:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        """Halve damage from special moves."""
        if move and move.category == "Special":
            return damage // 2
        return damage

class Illuminate:
    def onModifyMove(self, move, user=None):
        if move and getattr(move, "accuracy", True) is not True:
            move.accuracy = int(move.accuracy * 1.1)

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if "accuracy" in boost and boost["accuracy"] < 0:
            del boost["accuracy"]

class Illusion:
    def onBeforeSwitchIn(self, pokemon=None):
        if not pokemon:
            return
        bench = [p for p in getattr(pokemon, "side", {}).get("pokemon", []) if not getattr(p, "fainted", False) and p is not pokemon]
        if bench:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["illusion"] = bench[-1]

    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and target.abilityState.get("illusion"):
            target.abilityState.pop("illusion", None)
        return damage

    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState.pop("illusion", None)

    def onFaint(self, pokemon=None):
        self.onEnd(pokemon)

class Immunity:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status in {"psn", "tox"}:
            if target and hasattr(target, "immune"):
                target.immune = "Immunity"
            return False

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status in {"psn", "tox"}:
            pokemon.setStatus(0)

class Imposter:
    def _try_transform(self, pokemon=None, battle=None):
        if not pokemon or getattr(pokemon, "transformed", False):
            return
        if not battle:
            return
        part = battle.participant_for(pokemon)
        opponent = battle.opponent_of(part) if part else None
        target = opponent.active[0] if opponent and opponent.active else None
        if target:
            try:
                from pokemon.dex.functions.moves_funcs import Transform
                Transform().onHit(pokemon, target, battle)
            except Exception:
                pass

    def onStart(self, pokemon=None, battle=None):
        if not pokemon:
            return
        pokemon.abilityState = getattr(pokemon, "abilityState", {})
        pokemon.abilityState["switching_in"] = True

    def onSwitchIn(self, pokemon=None, battle=None):
        if not pokemon:
            return
        state = getattr(pokemon, "abilityState", {})
        if state.get("switching_in"):
            self._try_transform(pokemon, battle)
            state["switching_in"] = False

class Infiltrator:
    def onModifyMove(self, move, user=None):
        if move:
            move.infiltrates = True

class Innardsout:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and getattr(target, "hp", 0) <= 0 and source:
            recoil = getattr(target, "max_hp", 0)
            source.hp = max(0, source.hp - recoil)

class Innerfocus:
    def onTryAddVolatile(self, status, pokemon=None):
        if status == "flinch":
            return None

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost and boost["atk"] < 0:
            del boost["atk"]

class Insomnia:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "slp":
            if target and hasattr(target, "immune"):
                target.immune = "Insomnia"
            return False

    def onTryAddVolatile(self, status, pokemon=None):
        if status == "yawn":
            return None

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "slp":
            pokemon.setStatus(0)

class Intimidate:
    def onStart(self, pokemon=None):
        if not pokemon:
            return
        for foe in pokemon.foes() if hasattr(pokemon, "foes") else []:
            apply_boost(foe, {"atk": -1})

class Intrepidsword:
    def onStart(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"atk": 1})

class Ironbarbs:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            recoil = getattr(source, "max_hp", 0) // 8
            source.hp = max(0, source.hp - recoil)

class Ironfist:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("punch"):
            return int(base_power * 1.2)
        return base_power

class Justified:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Dark" and target:
            apply_boost(target, {"atk": 1})

class Keeneye:
    def onModifyMove(self, move, user=None):
        if move:
            move.ignore_evasion = True

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if "accuracy" in boost and boost["accuracy"] < 0:
            del boost["accuracy"]

class Klutz:
    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "klutz", True)

class Leafguard:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        weather = getattr(target, "effective_weather", lambda: "")() if target else ""
        if status and weather in {"sunnyday", "desolateland"}:
            return False

    def onTryAddVolatile(self, status, pokemon=None):
        weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
        if status == "yawn" and weather in {"sunnyday", "desolateland"}:
            return None

class Libero:
    def onPrepareHit(self, move=None, pokemon=None, target=None):
        if pokemon and move and not getattr(pokemon, "libero_used", False):
            pokemon.types = [move.type]
            pokemon.libero_used = True

    def onSwitchIn(self, pokemon=None):
        if pokemon:
            pokemon.libero_used = False

class Lightmetal:
    def onModifyWeight(self, weight, pokemon=None):
        return weight / 2

class Lightningrod:
    def onAnyRedirectTarget(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is not holder and move and move.type == "Electric" and move.target in {"normal", "any"}:
            return holder

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Electric" and target:
            apply_boost(target, {"spa": 1})
            if hasattr(target, "immune"):
                target.immune = "Lightning Rod"
            return None

class Limber:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "par":
            if target and hasattr(target, "immune"):
                target.immune = "Limber"
            return False

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "par":
            pokemon.setStatus(0)

class Lingeringaroma:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            source.ability = "lingeringaroma"

class Liquidooze:
    def onSourceTryHeal(self, damage, source=None, target=None, move=None):
        if move and move.flags.get("drain"):
            return -damage
        return damage

class Liquidvoice:
    def onModifyType(self, move, user=None):
        if move and move.flags.get("sound"):
            move.type = "Water"

class Longreach:
    def onModifyMove(self, move, user=None):
        if move:
            move.flags = dict(move.flags)
            move.flags.pop("contact", None)

class Magicbounce:
    def onAllyTryHitSide(self, target=None, source=None, move=None):
        if move and move.category == "Status" and source is not target:
            if target and hasattr(target, "immune"):
                target.immune = "Magic Bounce"
            return False

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.category == "Status" and source is not target:
            if target and hasattr(target, "immune"):
                target.immune = "Magic Bounce"
            return False

class Magicguard:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") != "Move":
            return 0
        return damage

class Magician:
    def onAfterMoveSecondarySelf(self, source=None, target=None, move=None):
        if source and move and not getattr(source, "item", None) and target and getattr(target, "item", None):
            source.item = target.item
            target.item = None

class Magmaarmor:
    def onImmunity(self, status=None, pokemon=None):
        if status == "frz":
            return False

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "frz":
            pokemon.setStatus(0)

class Magnetpull:
    def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
        if pokemon and pokemon.hasType("Steel"):
            pokemon.maybeTrapped = True

    def onFoeTrapPokemon(self, pokemon=None):
        if pokemon and pokemon.hasType("Steel"):
            pokemon.tryTrap(True)

class Marvelscale:
    def onModifyDef(self, defense, pokemon=None):
        if pokemon and pokemon.status:
            return int(defense * 1.5)
        return defense

class Megalauncher:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("pulse"):
            return int(base_power * 1.5)
        return base_power

class Merciless:
    def onModifyCritRatio(self, crit_ratio, attacker=None, defender=None):
        if defender and defender.status:
            return crit_ratio + 1
        return crit_ratio

class Mimicry:
    def _apply(self, pokemon):
        terrain = getattr(pokemon, "terrain", "") if pokemon else ""
        mapping = {
            "electricterrain": "Electric",
            "grassyterrain": "Grass",
            "mistyterrain": "Fairy",
            "psychicterrain": "Psychic",
        }
        new = mapping.get(terrain)
        if new and hasattr(pokemon, "setType"):
            pokemon.setType(new)

    def onStart(self, pokemon=None):
        self._apply(pokemon)

    def onTerrainChange(self, pokemon=None):
        self._apply(pokemon)

class Mindseye:
    def onModifyMove(self, move, user=None):
        if move:
            move.ignore_evasion = True
            if move.type in {"Normal", "Fighting"}:
                move.ignore_immunity = {"Ghost": True}

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if "accuracy" in boost and boost["accuracy"] < 0:
            del boost["accuracy"]

class Minus:
    def onModifySpA(self, spa, pokemon=None):
        allies = [a for a in getattr(pokemon, "allies", lambda: [])() if a is not pokemon] if pokemon else []
        for ally in allies:
            if ally.hasAbility("plus") or ally.hasAbility("minus"):
                return int(spa * 1.5)
        return spa

class Mirrorarmor:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if source and source is not target:
            for stat, val in list(boost.items()):
                if val < 0:
                    boost[stat] = 0
                    apply_boost(source, {stat: val})

class Mistysurge:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setTerrain("mistyterrain", source)

class Moldbreaker:
    def onModifyMove(self, move, pokemon=None):
        if move:
            move.ignore_ability = True

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "mold_breaker", True)

class Moody:
    def onResidual(self, pokemon=None):
        if not pokemon:
            return
        stats = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
        raise_stat = choice(stats)
        lower_stat = choice([s for s in stats if s != raise_stat])
        apply_boost(pokemon, {raise_stat: 2, lower_stat: -1})

class Motordrive:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Electric" and target:
            apply_boost(target, {"spe": 1})
            if hasattr(target, "immune"):
                target.immune = "Motor Drive"
            return None

class Mountaineer:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and effect.type == "Rock" and not getattr(target, "mountaineer_used", False):
            target.mountaineer_used = True
            return 0
        return damage

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Rock" and not getattr(target, "mountaineer_used", False):
            target.mountaineer_used = True
            if hasattr(target, "immune"):
                target.immune = "Mountaineer"
            return False

class Moxie:
    def onSourceAfterFaint(self, length=1, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move" and source:
            apply_boost(source, {"atk": length})

class Multiscale:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if target and target.hp == target.max_hp:
            return damage // 2
        return damage

class Mummy:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            source.ability = "mummy"

class Myceliummight:
    def onFractionalPriority(self, priority, pokemon=None, target=None, move=None):
        if move and move.category == "Status":
            return -0.1
        return priority

    def onModifyMove(self, move, pokemon=None):
        if move and move.category == "Status":
            move.ignore_ability = True

class Naturalcure:
    def onCheckShow(self, pokemon=None):
        if pokemon and pokemon.status:
            pokemon.natural_cure = True

    def onSwitchOut(self, pokemon=None):
        if pokemon and getattr(pokemon, "natural_cure", False):
            pokemon.setStatus(0)
            pokemon.natural_cure = False

class Neuroforce:
    def onModifyDamage(self, damage, source=None, target=None, move=None):
        if move and target:
            eff = type_effectiveness(move, target)
            if eff > 1:
                return int(damage * 1.25)
        return damage

class Neutralizinggas:
    def onEnd(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressingAbilities", False)

    def onPreStart(self, pokemon=None, battle=None):
        if battle:
            setattr(battle, "suppressingAbilities", True)

class Noguard:
    def onAnyAccuracy(self, accuracy, user=None, target=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and (user is holder or target is holder):
            return True
        return accuracy

    def onAnyInvulnerability(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and (target is holder or source is holder):
            return 0

class Normalize:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "typeChangerBoosted", False):
            return int(base_power * 1.2)
        return base_power

    def onModifyType(self, move, pokemon=None):
        if not move or move.type == "Normal" or move.category == "Status":
            return
        block = {
            "judgment",
            "multiattack",
            "naturalgift",
            "revelationdance",
            "technoblast",
            "terrainpulse",
            "weatherball",
        }
        if getattr(move, "id", "").lower() in block:
            return
        move.type = "Normal"
        move.typeChangerBoosted = True

class Oblivious:
    def onImmunity(self, status=None, pokemon=None):
        if status in {"attract", "taunt"}:
            return False
        return True

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost:
            del boost["atk"]

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.id in {"captivate", "taunt"}:
            if target:
                target.immune = "Oblivious"
            return False

    def onUpdate(self, pokemon=None):
        if pokemon:
            pokemon.volatiles.pop("taunt", None)
            pokemon.volatiles.pop("attract", None)

class Opportunist:
    def onFoeAfterBoost(self, boost=None, target=None, source=None, effect=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if not holder or not boost:
            return
        gains = {stat: amount for stat, amount in boost.items() if amount > 0}
        if gains:
            apply_boost(holder, gains)

class Orichalcumpulse:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        weather = attacker.effective_weather() if attacker else ""
        if weather in {"sunnyday", "desolateland"}:
            return int(atk * 1.3)
        return atk

    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("sunnyday", source)

class Overcoat:
    def onImmunity(self, status=None, pokemon=None):
        if status in {"sandstorm", "hail", "snow"}:
            return False
        return True

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.flags.get("powder"):
            if target:
                target.immune = "Overcoat"
            return False

class Overgrow:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Grass" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Grass" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(spa * 1.5)
        return spa

class Owntempo:
    def onHit(self, target=None, source=None, move=None):
        if move and move.id in {"swagger", "flatter", "teeterdance"}:
            if target:
                target.immune = "Own Tempo"
            return False

    def onTryAddVolatile(self, status, pokemon=None):
        if status == "confusion":
            return None

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost:
            del boost["atk"]

    def onUpdate(self, pokemon=None):
        if pokemon:
            pokemon.volatiles.pop("confusion", None)

class Parentalbond:
    def onPrepareHit(self, move=None, pokemon=None, target=None):
        if move and move.category != "Status" and not getattr(move, "multihit", False):
            move.multihit = 2
            move.multihit_type = "parentalbond"

    def onSourceModifySecondaries(self, secondaries, source=None, target=None, move=None):
        if move and getattr(move, "multihit_type", "") == "parentalbond" and getattr(move, "hit", 1) == 2:
            return []
        return secondaries

class Pastelveil:
    def onAllySetStatus(self, status, target=None, source=None, effect=None):
        if status in {"psn", "tox"}:
            if target:
                target.immune = "Pastel Veil"
            return False

    def onAllySwitchIn(self, pokemon=None):
        if pokemon and pokemon.status in {"psn", "tox"}:
            pokemon.setStatus(0)

    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status in {"psn", "tox"}:
            if target:
                target.immune = "Pastel Veil"
            return False

    def onStart(self, pokemon=None):
        if pokemon and pokemon.status in {"psn", "tox"}:
            pokemon.setStatus(0)
        for ally in pokemon.allies() if hasattr(pokemon, "allies") else []:
            if ally.status in {"psn", "tox"}:
                ally.setStatus(0)

    def onUpdate(self, pokemon=None):
        self.onStart(pokemon)

class Perishbody:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and source and move and move.flags.get("contact"):
            target.volatiles["perishsong"] = 3
            source.volatiles["perishsong"] = 3

class Pickpocket:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if target and source and move and move.flags.get("contact"):
            if not target.item and getattr(source, "item", None):
                target.item = source.item
                source.item = None

class Pickup:
    def onResidual(self, pokemon=None):
        if pokemon and not getattr(pokemon, "item", None):
            used = getattr(pokemon, "side", {}).get("used_items", [])
            if used:
                pokemon.item = used[-1]

class Pixilate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "typeChangerBoosted", False):
            return int(base_power * 1.2)
        return base_power

    def onModifyType(self, move, pokemon=None):
        if move and move.type == "Normal":
            ban = {"judgment", "multiattack", "naturalgift", "revelationdance", "technoblast", "terrainpulse", "weatherball"}
            if getattr(move, "id", "").lower() not in ban:
                move.type = "Fairy"
                move.typeChangerBoosted = True

class Plus:
    def onModifySpA(self, spa, pokemon=None, target=None, move=None):
        if not pokemon:
            return spa
        for ally in pokemon.allies() if hasattr(pokemon, "allies") else []:
            if ally.ability in {"minus", "plus"} and ally is not pokemon:
                return int(spa * 1.5)
        return spa

class Poisonheal:
    def onDamage(self, damage, pokemon=None, source=None, effect=None):
        if effect and effect in {"psn", "tox"} and pokemon:
            heal = pokemon.max_hp // 8
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)
            return 0
        return damage

class Poisonpoint:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact") and random() < 0.3:
            if not getattr(source, "status", None):
                source.setStatus("psn")

class Poisonpuppeteer:
    def onAnyAfterSetStatus(self, status=None, target=None, source=None, effect=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if status in {"psn", "tox"} and source is holder and target:
            target.volatiles["confusion"] = True

class Poisontouch:
    def onSourceDamagingHit(self, target=None, source=None, move=None):
        if move and move.flags.get("contact") and target and random() < 0.3:
            if not getattr(target, "status", None):
                target.setStatus("psn")

class Powerconstruct:
    def onResidual(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2 and "complete" not in pokemon.species.name.lower():
            if pokemon.species.name.lower().startswith("zygarde"):
                pokemon.formeChange("Zygarde-Complete")

class Powerofalchemy:
    def onAllyFaint(self, target=None, source=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target and target.ability not in {"powerofalchemy", "receiver", "trace"}:
            holder.ability = target.ability

class Powerspot:
    def onAllyBasePower(self, base_power, pokemon=None, target=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if pokemon is not holder:
            return int(base_power * 1.3)
        return base_power

class Prankster:
    def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
        if move and move.category == "Status":
            return priority + 0.1
        return priority

class Pressure:
    def onDeductPP(self, deduction, target=None):
        return deduction + 1

    def onStart(self, pokemon=None):
        pass

class Primordialsea:
    def onAnySetWeather(self, target=None, source=None, weather=None):
        strong = {"desolateland", "primordialsea", "deltastream"}
        if getattr(self, "field_weather", "") == "primordialsea" and weather and weather.id not in strong:
            return False

    def onEnd(self, pokemon=None, battle=None):
        if battle and battle.weather_state.get("source") == pokemon:
            battle.clearWeather()

    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("primordialsea", source)

class Prismarmor:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and target:
            eff = type_effectiveness(move, target)
            if eff > 1:
                return int(damage * 0.75)
        return damage

class Propellertail:
    def onModifyMove(self, move, user=None):
        if move:
            move.tracks_target = True

class Protean:
    def onPrepareHit(self, move=None, pokemon=None, target=None):
        if pokemon and move and not getattr(pokemon, "protean_used", False):
            pokemon.types = [move.type]
            pokemon.protean_used = True

    def onSwitchIn(self, pokemon=None):
        if pokemon:
            pokemon.protean_used = False

class Protosynthesis:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.protosynthesis_active = False

    def _boost_active(self, pokemon):
        return getattr(pokemon, "protosynthesis_active", False)

    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "protosynthesis_stat", "") == "atk":
            return int(atk * 1.3)
        return atk

    def onModifyDef(self, value, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "protosynthesis_stat", "") == "def":
            return int(value * 1.3)
        return value

    def onModifySpA(self, value, pokemon=None, target=None, move=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "protosynthesis_stat", "") == "spa":
            return int(value * 1.3)
        return value

    def onModifySpD(self, value, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "protosynthesis_stat", "") == "spd":
            return int(value * 1.3)
        return value

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "protosynthesis_stat", "") == "spe":
            return int(spe * 1.5)
        return spe

    def _choose_stat(self, pokemon):
        stats = {k: v for k, v in getattr(pokemon, "stats", {}).items() if k != "hp"}
        if not stats:
            return None
        return max(stats, key=stats.get)

    def onStart(self, pokemon=None):
        if not pokemon:
            return
        weather = pokemon.effective_weather()
        item = getattr(pokemon, "item", None)
        if weather in {"sunnyday", "desolateland"} or (item and item.id == "boosterenergy"):
            pokemon.protosynthesis_active = True
            pokemon.protosynthesis_stat = self._choose_stat(pokemon)

    def onWeatherChange(self, pokemon=None):
        self.onStart(pokemon)

class Psychicsurge:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setTerrain("psychicterrain", source)

class Punkrock:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("sound"):
            return int(base_power * 1.3)
        return base_power

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.flags.get("sound"):
            return damage // 2
        return damage

class Purepower:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        return atk * 2

class Purifyingsalt:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status and target and status not in {0, None}:
            target.immune = "Purifying Salt"
            return False

    def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
        if move and move.type == "Ghost" and target is getattr(self, "effect_state", {}).get("target"):
            return atk // 2
        return atk

    def onSourceModifySpA(self, spa, source=None, target=None, move=None):
        if move and move.type == "Ghost" and target is getattr(self, "effect_state", {}).get("target"):
            return spa // 2
        return spa

    def onTryAddVolatile(self, status, pokemon=None):
        if status in {"yawn", "confusion", "attract"}:
            return None

class Quarkdrive:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.quarkdrive_active = False

    def _boost_active(self, pokemon):
        return getattr(pokemon, "quarkdrive_active", False)

    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "quarkdrive_stat", "") == "atk":
            return int(atk * 1.3)
        return atk

    def onModifyDef(self, value, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "quarkdrive_stat", "") == "def":
            return int(value * 1.3)
        return value

    def onModifySpA(self, value, pokemon=None, target=None, move=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "quarkdrive_stat", "") == "spa":
            return int(value * 1.3)
        return value

    def onModifySpD(self, value, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "quarkdrive_stat", "") == "spd":
            return int(value * 1.3)
        return value

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and self._boost_active(pokemon) and getattr(pokemon, "quarkdrive_stat", "") == "spe":
            return int(spe * 1.5)
        return spe

    def _choose_stat(self, pokemon):
        stats = {k: v for k, v in getattr(pokemon, "stats", {}).items() if k != "hp"}
        if not stats:
            return None
        return max(stats, key=stats.get)

    def onStart(self, pokemon=None):
        if not pokemon:
            return
        terrain = getattr(pokemon, "terrain", "")
        item = getattr(pokemon, "item", None)
        if terrain == "electricterrain" or (item and item.id == "boosterenergy"):
            pokemon.quarkdrive_active = True
            pokemon.quarkdrive_stat = self._choose_stat(pokemon)

    def onTerrainChange(self, pokemon=None):
        self.onStart(pokemon)

class Queenlymajesty:
    def onFoeTryMove(self, target=None, source=None, move=None):
        if move and move.priority > 0 and not source.is_ally(target):
            if hasattr(source, "tempvals"):
                source.tempvals["cant_move"] = "queenlymajesty"
            return False

class Quickdraw:
    def onFractionalPriority(self, priority, pokemon=None, target=None, move=None):
        if move and move.category != "Status" and random() < 0.3:
            return priority + 0.1
        return priority

class Quickfeet:
    def onModifySpe(self, spe, pokemon=None):
        if pokemon and pokemon.status:
            return int(spe * 1.5)
        return spe

class Raindish:
    def onWeather(self, pokemon=None):
        if not pokemon:
            return
        weather = getattr(pokemon, "effective_weather", lambda: "")()
        if weather in {"raindance", "primordialsea"}:
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + pokemon.max_hp // 16)

class Rattled:
    def onAfterBoost(self, boost, target=None, source=None, effect=None):
        if effect and getattr(effect, "id", "") == "intimidate":
            apply_boost(target, {"spe": 1})

    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type in {"Bug", "Dark", "Ghost"}:
            apply_boost(target, {"spe": 1})

class Rebound:
    def onAllyTryHitSide(self, target=None, source=None, move=None):
        if move and move.category == "Status" and source is not target:
            if target:
                target.immune = "Rebound"
            return False

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.category == "Status" and source is not target:
            if target:
                target.immune = "Rebound"
            return False

class Receiver:
    def onAllyFaint(self, target=None, source=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target and target.ability not in {"powerofalchemy", "receiver", "trace"}:
            holder.ability = target.ability

class Reckless:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and (getattr(move, "recoil", False) or getattr(move, "hasCrashDamage", False)):
            return int(base_power * 1.2)
        return base_power

class Refrigerate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "typeChangerBoosted", False):
            return int(base_power * 1.2)
        return base_power

    def onModifyType(self, move, pokemon=None):
        if move and move.type == "Normal":
            ban = {"judgment", "multiattack", "naturalgift", "revelationdance", "technoblast", "terrainpulse", "weatherball"}
            if getattr(move, "id", "").lower() not in ban:
                move.type = "Ice"
                move.typeChangerBoosted = True

class Regenerator:
    def onSwitchOut(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 3
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + heal)

class Ripen:
    def onChangeBoost(self, boost, pokemon=None, effect=None):
        if getattr(pokemon, "ripen_active", False):
            for stat in boost:
                boost[stat] *= 2
            pokemon.ripen_active = False

    def onEatItem(self, item=None, pokemon=None):
        if item and getattr(item, "isBerry", False):
            pokemon.ripen_active = True

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        return damage

    def onTryEatItem(self, item=None, pokemon=None):
        return True

    def onTryHeal(self, heal, pokemon=None):
        if getattr(pokemon, "ripen_active", False):
            pokemon.ripen_active = False
            return heal * 2
        return heal

class Rivalry:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and target and user.gender and target.gender and user.gender != "N" and target.gender != "N":
            if user.gender == target.gender:
                return int(base_power * 1.25)
            return int(base_power * 0.75)
        return base_power

class Rockhead:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if effect and getattr(effect, "recoil", False):
            return 0
        return damage

class Rockypayload:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Rock":
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Rock":
            return int(spa * 1.5)
        return spa

class Roughskin:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            recoil = source.max_hp // 8
            source.hp = max(0, source.hp - recoil)

class Sandforce:
    def onBasePower(self, base_power, attacker=None, defender=None, move=None):
        """Boost specific move types in sand."""
        weather = getattr(attacker, "effective_weather", lambda: "")() if attacker else ""
        if weather == "sandstorm" and move and move.type in {"Rock", "Ground", "Steel"}:
            return int(base_power * 1.3)
        return base_power

    def onImmunity(self, status=None, pokemon=None):
        if status == "sandstorm":
            return False

class Sandrush:
    def onImmunity(self, status=None, pokemon=None):
        if status == "sandstorm":
            return False

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() == "sandstorm":
            return int(spe * 2)
        return spe

class Sandspit:
    def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
        if battle:
            battle.setWeather("sandstorm", target)

class Sandstream:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("sandstorm", source)

class Sandveil:
    def onImmunity(self, status=None, pokemon=None):
        if status == "sandstorm":
            return False

    def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
        if defender and getattr(defender, "effective_weather", lambda: "")() == "sandstorm":
            return int(accuracy * 0.8)
        return accuracy

class Sapsipper:
    def onAllyTryHitSide(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is not holder and move and move.type == "Grass":
            if target:
                target.immune = "Sap Sipper"
            return False

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Grass" and target:
            apply_boost(target, {"atk": 1})
            target.immune = "Sap Sipper"
            return None

class Schooling:
    def _update_form(self, pokemon):
        if not pokemon or not pokemon.species.name.lower().startswith("wishiwashi"):
            return
        if pokemon.hp > pokemon.max_hp // 4:
            form = "Wishiwashi-School"
        else:
            form = "Wishiwashi"
        if pokemon.species.name != form:
            pokemon.formeChange(form)

    def onResidual(self, pokemon=None):
        self._update_form(pokemon)

    def onStart(self, pokemon=None):
        self._update_form(pokemon)

class Scrappy:
    def onModifyMove(self, move, pokemon=None):
        if move and move.type in {"Normal", "Fighting"}:
            move.ignoreImmunity = True

    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if effect and getattr(effect, "id", "") == "intimidate" and "atk" in boost and boost["atk"] < 0:
            del boost["atk"]

class Screencleaner:
    def onStart(self, pokemon=None):
        if not pokemon or not getattr(pokemon, "side", None):
            return
        screens = {"reflect", "lightscreen", "auroraveil"}
        for side in (pokemon.side, getattr(pokemon.side, "foe", None)):
            if not side:
                continue
            for scr in screens:
                side.side_conditions.pop(scr, None)

class Seedsower:
    def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
        if battle:
            battle.setTerrain("grassyterrain", target)

class Serenegrace:
    def onModifyMove(self, move, pokemon=None):
        if move and getattr(move, "secondaries", None):
            for sec in move.secondaries:
                if "chance" in sec:
                    sec["chance"] *= 2

class Shadowshield:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if target and target.hp == target.max_hp:
            return damage // 2
        return damage

class Shadowtag:
    def onFoeMaybeTrapPokemon(self, pokemon=None, source=None):
        if not source:
            source = getattr(self, "effect_state", {}).get("target")
        if pokemon and source and not pokemon.is_ally(source):
            pokemon.maybeTrapped = True

    def onFoeTrapPokemon(self, pokemon=None):
        source = getattr(self, "effect_state", {}).get("target")
        if pokemon and source and getattr(pokemon, "isAdjacent", lambda o: True)(source):
            getattr(pokemon, "tryTrap", lambda *_: None)(True)

class Sharpness:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("slicing"):
            return int(base_power * 1.5)
        return base_power

class Shedskin:
    def onResidual(self, pokemon=None):
        if pokemon and pokemon.status and random() < 1/3:
            pokemon.setStatus(0)

class Sheerforce:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "secondaries", None):
            return int(base_power * 1.3)
        return base_power

    def onModifyMove(self, move, user=None):
        if move and getattr(move, "secondaries", None):
            move.secondaries = []
            move.sheer_force_boosted = True

class Shielddust:
    def onModifySecondaries(self, secondaries, source=None, target=None, move=None):
        if target and secondaries:
            return [s for s in secondaries if s.get("self")]
        return secondaries

class Shieldsdown:
    def _update_form(self, pokemon):
        if not pokemon or "minior" not in pokemon.species.name.lower():
            return
        if pokemon.hp <= pokemon.max_hp // 2:
            if "meteor" in pokemon.species.name.lower():
                pokemon.formeChange(pokemon.species.name.replace("Meteor", "Core"))
        else:
            if "core" in pokemon.species.name.lower():
                pokemon.formeChange(pokemon.species.name.replace("Core", "Meteor"))

    def onResidual(self, pokemon=None):
        self._update_form(pokemon)

    def onSetStatus(self, status, target=None, source=None, effect=None):
        if target and "meteor" in target.species.name.lower() and status not in {0, None}:
            target.immune = "Shields Down"
            return False

    def onStart(self, pokemon=None):
        self._update_form(pokemon)

    def onTryAddVolatile(self, status, pokemon=None):
        if status == "yawn" and pokemon and "meteor" in pokemon.species.name.lower():
            return None

class Simple:
    def onChangeBoost(self, boost, pokemon=None, source=None, effect=None):
        for stat in boost:
            boost[stat] *= 2

class Skilllink:
    def onModifyMove(self, move, pokemon=None):
        if move and getattr(move, "multihit", None):
            if isinstance(move.multihit, (list, tuple)):
                move.multihit = max(move.multihit)
            elif isinstance(move.multihit, int) and move.multihit < 5:
                move.multihit = 5

class Slowstart:
    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState.pop("slowstart", None)

    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if attacker and attacker.abilityState.get("slowstart", 0) > 0:
            return atk // 2
        return atk

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and pokemon.abilityState.get("slowstart", 0) > 0:
            return spe // 2
        return spe

    def onResidual(self, pokemon=None):
        if pokemon:
            turns = pokemon.abilityState.get("slowstart", 0)
            if turns > 0:
                pokemon.abilityState["slowstart"] = turns - 1

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["slowstart"] = 5

class Slushrush:
    def onModifySpe(self, spe, pokemon=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"hail", "snow"}:
            return int(spe * 2)
        return spe

class Sniper:
    def onModifyDamage(self, damage, source=None, target=None, move=None):
        if move and getattr(move, "crit", False):
            return int(damage * 1.5)
        return damage

class Snowcloak:
    def onImmunity(self, status=None, pokemon=None):
        if status in {"hail", "snow"}:
            return False

    def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
        if defender and getattr(defender, "effective_weather", lambda: "")() in {"hail", "snow"}:
            return int(accuracy * 0.8)
        return accuracy

class Snowwarning:
    def onStart(self, source=None, battle=None):
        if battle:
            battle.setWeather("snow", source)

class Solarpower:
    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if attacker and getattr(attacker, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
            return int(spa * 1.5)
        return spa

    def onWeather(self, pokemon=None):
        if pokemon and getattr(pokemon, "effective_weather", lambda: "")() in {"sunnyday", "desolateland"}:
            pokemon.hp = max(0, pokemon.hp - pokemon.max_hp // 8)

class Solidrock:
    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if target and move and type_effectiveness(move, target) > 1:
            return int(damage * 0.75)
        return damage

class Soulheart:
    def onAnyFaint(self, length=1, target=None, source=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is not holder:
            apply_boost(holder, {"spa": 1})

class Soundproof:
    def onAllyTryHitSide(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is not holder and move and move.flags.get("sound"):
            target.immune = "Soundproof"
            return False

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.flags.get("sound") and target:
            target.immune = "Soundproof"
            return None

class Speedboost:
    def onResidual(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"spe": 1})

class Stakeout:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if defender and getattr(defender, "active_turns", 0) == 0:
            return int(atk * 2)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if defender and getattr(defender, "active_turns", 0) == 0:
            return int(spa * 2)
        return spa

class Stalwart:
    def onModifyMove(self, move, user=None):
        if move:
            move.tracks_target = True

class Stamina:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target:
            apply_boost(target, {"def": 1})

class Stancechange:
    def onModifyMove(self, move, user=None):
        if not user or not move or not user.species.name.lower().startswith("aegislash"):
            return
        if move.category != "Status":
            form = "Aegislash-Blade"
        else:
            form = "Aegislash"
        if user.species.name != form:
            user.formeChange(form)

class Static:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact") and random() < 0.3:
            if not getattr(source, "status", None):
                source.setStatus("par")

class Steadfast:
    def onFlinch(self, pokemon=None):
        if pokemon:
            apply_boost(pokemon, {"spe": 1})

class Steamengine:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type in {"Fire", "Water"} and target:
            apply_boost(target, {"spe": 6})

class Steelworker:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Steel":
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Steel":
            return int(spa * 1.5)
        return spa

class Steelyspirit:
    def onAllyBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Steel":
            return int(base_power * 1.5)
        return base_power

class Stench:
    def onModifyMove(self, move, user=None):
        if move and move.category != "Status":
            move.secondaries = getattr(move, "secondaries", []) + [{"chance": 10, "volatileStatus": "flinch"}]

class Stickyhold:
    def onTakeItem(self, item=None, source=None):
        return False

class Stormdrain:
    def onAnyRedirectTarget(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is not holder and move and move.type == "Water" and move.target in {"normal", "any"}:
            return holder

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            apply_boost(target, {"spa": 1})
            target.immune = "Storm Drain"
            return None

class Strongjaw:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("bite"):
            return int(base_power * 1.5)
        return base_power

class Sturdy:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if target and target.hp == target.max_hp and damage >= target.hp:
            return target.hp - 1
        return damage

    def onTryHit(self, target=None, source=None, move=None):
        if move and getattr(move, "ohko", False) and target:
            target.immune = "Sturdy"
            return False

class Suctioncups:
    def onDragOut(self, pokemon=None):
        return False

class Superluck:
    def onModifyCritRatio(self, ratio, attacker=None, target=None, move=None):
        return ratio + 1

class Supersweetsyrup:
    def onStart(self, pokemon=None):
        if pokemon:
            for foe in pokemon.foes() if hasattr(pokemon, "foes") else []:
                apply_boost(foe, {"evasion": -1})

class Supremeoverlord:
    def onBasePower(self, base_power, attacker=None, defender=None, move=None):
        boost = getattr(attacker, "abilityState", {}).get("supreme_overlord", 1.0)
        return int(base_power * boost)

    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState.pop("supreme_overlord", None)

    def onStart(self, pokemon=None):
        if pokemon:
            fainted = sum(1 for p in pokemon.side.pokemons if p.hp <= 0 and p is not pokemon)
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["supreme_overlord"] = 1 + 0.1 * fainted

class Surgesurfer:
    def onModifySpe(self, spe, pokemon=None):
        if pokemon and getattr(pokemon, "terrain", "") == "electricterrain":
            return int(spe * 2)
        return spe

class Swarm:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Bug" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Bug" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(spa * 1.5)
        return spa

class Sweetveil:
    def onAllySetStatus(self, status, target=None, source=None, effect=None):
        if status == "slp":
            if target:
                target.immune = "Sweet Veil"
            return False

    def onAllyTryAddVolatile(self, status, target=None):
        if status == "yawn":
            return None

    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "slp":
            if target:
                target.immune = "Sweet Veil"
            return False

class Swiftswim:
    def onModifySpe(self, spe, pokemon=None):
        weather = getattr(pokemon, "effective_weather", lambda: "")() if pokemon else ""
        if weather in {"raindance", "primordialsea"}:
            return int(spe * 2)
        return spe

class Swordofruin:
    def onAnyModifyDef(self, defense, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if target and holder and target is not holder and getattr(move, "category", None) != "Status":
            return int(defense * 0.75)
        return defense

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "sword_of_ruin", True)

class Symbiosis:
    def onAllyAfterUseItem(self, item=None, source=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and source is not holder and not getattr(source, "item", None) and getattr(holder, "item", None):
            source.item = holder.item
            holder.item = None

class Synchronize:
    def onAfterSetStatus(self, status, target=None, source=None, effect=None):
        if target and source and target is getattr(self, "effect_state", {}).get("target") and source is not target:
            if status not in {0, None} and hasattr(source, "setStatus"):
                source.setStatus(status)

class Tabletsofruin:
    def onAnyModifyAtk(self, atk, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if target and holder and target is not holder and getattr(move, "category", None) != "Status":
            return int(atk * 0.75)
        return atk

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "tablets_of_ruin", True)

class Tangledfeet:
    def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
        if defender and defender.volatiles.get("confusion"):
            if accuracy is not True:
                return int(accuracy * 0.5)
        return accuracy

class Tanglinghair:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            apply_boost(source, {"spe": -1})

class Technician:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and getattr(move, "base_power", 0) <= 60:
            return int(base_power * 1.5)
        return base_power

class Telepathy:
    def onTryHit(self, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and target is holder and source and source.is_ally(holder):
            if move and move.category != "Status":
                target.immune = "Telepathy"
                return None

class Teraformzero:
    def onAfterTerastallization(self, pokemon=None):
        if pokemon and "Terapagos" in pokemon.species.name:
            pokemon.formeChange("Terapagos-Stellar")

class Terashell:
    def onAnyAfterMove(self, pokemon=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and pokemon is holder and move and move.category != "Status":
            holder.abilityState = getattr(holder, "abilityState", {})
            holder.abilityState["terashell_broken"] = True

    def onEffectiveness(self, type_mod, target=None, type_=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if target is holder and not getattr(holder, "abilityState", {}).get("terashell_broken"):
            if type_mod > 0:
                return type_mod - 1
        return type_mod

class Terashift:
    def onPreStart(self, pokemon=None):
        if pokemon and getattr(pokemon, "terastal_type", None):
            pokemon.teratype = pokemon.terastal_type

class Teravolt:
    def onModifyMove(self, move, pokemon=None):
        if move:
            move.ignore_ability = True

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "mold_breaker", True)

class Thermalexchange:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Fire" and target:
            apply_boost(target, {"atk": 1})

    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "brn":
            if target:
                target.immune = "Thermal Exchange"
            return False

    def onUpdate(self, pokemon=None):
        pass

class Thickfat:
    def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
        if move and move.type in {"Fire", "Ice"}:
            return int(atk * 0.5)
        return atk

    def onSourceModifySpA(self, spa, source=None, target=None, move=None):
        if move and move.type in {"Fire", "Ice"}:
            return int(spa * 0.5)
        return spa

class Tintedlens:
    def onModifyDamage(self, damage, source=None, target=None, move=None):
        if move and target and type_effectiveness(move, target) < 1:
            return int(damage * 2)
        return damage

class Torrent:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Water" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Water" and attacker and attacker.hp <= attacker.max_hp // 3:
            return int(spa * 1.5)
        return spa

class Toughclaws:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("contact"):
            return int(base_power * 1.3)
        return base_power

class Toxicboost:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and user.status in {"psn", "tox"} and move and move.category != "Status":
            return int(base_power * 1.5)
        return base_power

class Toxicchain:
    def onSourceDamagingHit(self, damage, source=None, target=None, move=None):
        if source and target and move and move.category != "Status" and random() < 0.3:
            if not target.status:
                target.setStatus("tox")

class Toxicdebris:
    def onDamagingHit(self, damage, target=None, source=None, move=None, battle=None):
        if battle and move and move.category == "Physical" and source:
            side = source.side
            layers = side.side_conditions.get("toxicspikes", 0)
            side.side_conditions["toxicspikes"] = min(2, layers + 1)

class Trace:
    def _copy(self, pokemon):
        foes = [f for f in pokemon.foes() if f.ability not in {"trace", None}]
        if foes:
            choice_foe = choice(foes)
            pokemon.ability = choice_foe.ability

    def onStart(self, pokemon=None):
        if pokemon:
            self._copy(pokemon)

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.ability == "trace":
            self._copy(pokemon)

class Transistor:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Electric":
            return int(atk * 1.5)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Electric":
            return int(spa * 1.5)
        return spa

class Triage:
    def onModifyPriority(self, priority, pokemon=None, target=None, move=None):
        if move and move.flags.get("heal"):
            return priority + 0.1
        return priority

class Truant:
    def onBeforeMove(self, pokemon=None, target=None, move=None):
        state = getattr(pokemon, "abilityState", {})
        if state.get("truant_skip"):
            state["truant_skip"] = False
            if hasattr(pokemon, "tempvals"):
                pokemon.tempvals["cant_move"] = "truant"
            return False
        state["truant_skip"] = True

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["truant_skip"] = False

class Turboblaze:
    def onModifyMove(self, move, pokemon=None):
        if move:
            move.ignore_ability = True

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "mold_breaker", True)

class Unaware:
    def onAnyModifyBoost(self, boosts, pokemon=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if pokemon is not holder:
            for stat in boosts:
                boosts[stat] = 0

class Unburden:
    def onAfterUseItem(self, item=None, pokemon=None):
        if pokemon and item:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unburden"] = True

    def onEnd(self, pokemon=None):
        if pokemon:
            pokemon.abilityState.pop("unburden", None)

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and pokemon.abilityState.get("unburden"):
            return int(spe * 2)
        return spe

    def onTakeItem(self, item=None, pokemon=None):
        if pokemon and item:
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["unburden"] = True

class Unnerve:
    def onEnd(self, pokemon=None):
        if pokemon:
            for foe in pokemon.foes():
                foe.nerve = False

    def onFoeTryEatItem(self, item=None, pokemon=None):
        if item and getattr(item, "isBerry", False):
            if pokemon:
                pokemon.immune = "Unnerve"
            return False

    def onPreStart(self, pokemon=None):
        self.onStart(pokemon)

    def onStart(self, pokemon=None):
        if pokemon:
            for foe in pokemon.foes():
                foe.nerve = True

class Unseenfist:
    def onModifyMove(self, move, pokemon=None):
        if move and move.flags.get("contact"):
            move.breaksProtect = True

class Vesselofruin:
    def onAnyModifySpA(self, spa, target=None, source=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if target and holder and target is not holder and getattr(move, "category", None) != "Status":
            return int(spa * 0.75)
        return spa

    def onStart(self, pokemon=None):
        if pokemon:
            setattr(pokemon, "vessel_of_ruin", True)

class Victorystar:
    def onAnyModifyAccuracy(self, accuracy, source=None, target=None, move=None):
        holder = getattr(self, "effect_state", {}).get("target")
        if holder and source and (source is holder or source.is_ally(holder)):
            if accuracy is not True:
                return int(accuracy * 1.1)
        return accuracy

class Vitalspirit:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "slp":
            if target:
                target.immune = "Vital Spirit"
            return False

    def onTryAddVolatile(self, status, pokemon=None):
        if status == "yawn":
            return None

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "slp":
            pokemon.setStatus(0)

class Voltabsorb:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Electric" and target:
            heal = target.max_hp // 4
            target.hp = min(target.max_hp, target.hp + heal)
            target.immune = "Volt Absorb"
            return None

class Wanderingspirit:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and source and move and move.flags.get("contact"):
            if source.ability not in {"wanderingspirit"}:
                target.ability, source.ability = source.ability, target.ability

class Waterabsorb:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            heal = target.max_hp // 4
            target.hp = min(target.max_hp, target.hp + heal)
            target.immune = "Water Absorb"
            return None

class Waterbubble:
    def onModifyAtk(self, atk, attacker=None, defender=None, move=None):
        if move and move.type == "Water":
            return int(atk * 2)
        return atk

    def onModifySpA(self, spa, attacker=None, defender=None, move=None):
        if move and move.type == "Water":
            return int(spa * 2)
        return spa

    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "brn":
            if target:
                target.immune = "Water Bubble"
            return False

    def onSourceModifyAtk(self, atk, source=None, target=None, move=None):
        if move and move.type == "Fire":
            return int(atk * 0.5)
        return atk

    def onSourceModifySpA(self, spa, source=None, target=None, move=None):
        if move and move.type == "Fire":
            return int(spa * 0.5)
        return spa

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "brn":
            pokemon.setStatus(0)

class Watercompaction:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            apply_boost(target, {"def": 2})

class Waterveil:
    def onSetStatus(self, status, target=None, source=None, effect=None):
        if status == "brn":
            if target:
                target.immune = "Water Veil"
            return False

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.status == "brn":
            pokemon.setStatus(0)

class Weakarmor:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and move and move.category == "Physical":
            apply_boost(target, {"def": -1, "spe": 2})

class Wellbakedbody:
    def onTryHit(self, target=None, source=None, move=None):
        if move and move.type == "Fire" and target:
            apply_boost(target, {"def": 2})
            target.immune = "Well-Baked Body"
            return None

class Whitesmoke:
    def onTryBoost(self, boost, target=None, source=None, effect=None):
        if source and source is target:
            return
        for stat in list(boost.keys()):
            if boost[stat] < 0:
                del boost[stat]

class Wimpout:
    def onEmergencyExit(self, pokemon=None):
        if pokemon:
            pokemon.switch_out = True

class Windpower:
    def onAllySideConditionStart(self, side_condition=None, pokemon=None):
        if side_condition == "tailwind" and pokemon:
            pokemon.volatiles["charge"] = True

    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.flags.get("wind") and target:
            target.volatiles["charge"] = True

class Windrider:
    def onAllySideConditionStart(self, side_condition=None, pokemon=None):
        if side_condition == "tailwind" and pokemon:
            apply_boost(pokemon, {"atk": 1})

    def onStart(self, pokemon=None):
        pass

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.flags.get("wind") and target:
            apply_boost(target, {"atk": 1})
            target.immune = "Wind Rider"
            return None

class Wonderguard:
    def onTryHit(self, target=None, source=None, move=None):
        if not move or move.category == "Status" or move.id == "struggle":
            return
        if target and type_effectiveness(move, target) <= 1:
            target.immune = "Wonder Guard"
            return False

class Wonderskin:
    def onModifyAccuracy(self, accuracy, attacker=None, defender=None, move=None):
        if move and move.category == "Status" and accuracy is not True:
            return min(accuracy, 50)
        return accuracy

class Zenmode:
    def _update_form(self, pokemon):
        if not pokemon or "darmanitan" not in pokemon.base_species.lower():
            return
        if pokemon.hp <= pokemon.max_hp // 2:
            if "zen" not in pokemon.species.name.lower():
                pokemon.formeChange(f"{pokemon.base_species}-Zen")
        else:
            if "zen" in pokemon.species.name.lower():
                pokemon.formeChange(pokemon.base_species)

    def onEnd(self, pokemon=None):
        self._update_form(pokemon)

    def onResidual(self, pokemon=None):
        self._update_form(pokemon)

    def onStart(self, pokemon=None):
        self._update_form(pokemon)

class Zerotohero:
    def onStart(self, pokemon=None):
        if pokemon and pokemon.base_species.lower() == "palafin":
            pokemon.abilityState = getattr(pokemon, "abilityState", {})
            pokemon.abilityState["hero_ready"] = False

    def onSwitchIn(self, pokemon=None):
        if pokemon and pokemon.abilityState.get("hero_ready") and pokemon.species.name.lower() == "palafin":
            pokemon.formeChange("Palafin-Hero")

    def onSwitchOut(self, pokemon=None):
        if pokemon and pokemon.base_species.lower() == "palafin":
            pokemon.abilityState["hero_ready"] = True

