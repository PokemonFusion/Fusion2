from random import random

from pokemon.dex.functions.moves_funcs import type_effectiveness


class Abilityshield:
    def onSetAbility(self, ability=None, target=None, source=None, effect=None):
        """Prevent ability-changing effects from abilities other than Trace."""
        if effect and getattr(effect, "effectType", None) == "Ability" and getattr(effect, "name", None) != "Trace":
            return None
        return ability

class Abomasite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        """Mega Stones cannot be removed from their matching Pokémon."""
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Absolite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Absorbbulb:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            if hasattr(target, "boosts"):
                target.boosts["spa"] = target.boosts.get("spa", 0) + 1
            if hasattr(target, "item"):
                target.item = None

class Adamantcrystal:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Dialga") and move.type in {"Steel", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Dialga"):
            return False
        if source and source.name.startswith("Dialga"):
            return False
        return True

class Adamantorb:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Dialga") and move.type in {"Steel", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

class Adrenalineorb:
    def onAfterBoost(self, boost=None, target=None, source=None, effect=None):
        if effect and getattr(effect, "name", None) == "Intimidate" and target:
            if hasattr(target, "boosts") and target.boosts.get("spe", 0) < 6:
                target.boosts["spe"] += 1
            if hasattr(target, "item"):
                target.item = None

class Aerodactylite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Aggronite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Aguavberry:
    def onEat(self, pokemon=None):
        if not pokemon:
            return
        heal = pokemon.max_hp // 3
        pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Airballoon:
    def _pop(self, pokemon=None):
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles.pop("airballoon", None)

    def onAfterSubDamage(self, damage, target=None, source=None, effect=None):
        if effect and getattr(effect, "effectType", "") == "Move":
            self._pop(target)

    def onDamagingHit(self, damage, target=None, source=None, move=None):
        self._pop(target)

    def onStart(self, pokemon=None):
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles["airballoon"] = True

class Alakazite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Altarianite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Ampharosite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Apicotberry:
    def onEat(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spd"] = pokemon.boosts.get("spd", 0) + 1

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Aspearberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "frz":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "frz":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Assaultvest:
    def onDisableMove(self, pokemon=None):
        if not pokemon:
            return
        for move in getattr(pokemon, "moves", []):
            if getattr(move, "category", "") == "Status":
                setattr(move, "disabled", True)

    def onModifySpD(self, spd, pokemon=None):
        if pokemon:
            return int(spd * 1.5)
        return spd

class Audinite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Babiriberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Steel" and target:
            return int(damage * 0.5)
        return damage

class Banettite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Beedrillite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Berry:
    def onEat(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 8
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onResidual(self, pokemon=None):
        return

    def onTryEatItem(self, pokemon=None):
        return True

class Berryjuice:
    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            pokemon.hp = min(pokemon.hp + 20, pokemon.max_hp)
            if hasattr(pokemon, "item"):
                pokemon.item = None

class Berserkgene:
    def onUpdate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["atk"] = pokemon.boosts.get("atk", 0) + 2
            pokemon.boosts["spe"] = pokemon.boosts.get("spe", 0) + 2
            if hasattr(pokemon, "volatiles"):
                pokemon.volatiles["confusion"] = True
            if hasattr(pokemon, "item"):
                pokemon.item = None

class Bigroot:
    def onTryHeal(self, heal, target=None, source=None, effect=None):
        draining = {"drain", "leechseed", "ingrain", "aquaring", "strengthsap"}
        if effect and getattr(effect, "id", None) in draining:
            return int(heal * 1.3)
        return heal

class Bitterberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "confusion":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "confusion":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Blackbelt:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fighting":
            return int(base_power * 1.2)
        return base_power

class Blackglasses:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Dark":
            return int(base_power * 1.2)
        return base_power

class Blacksludge:
    def onResidual(self, pokemon=None):
        if not pokemon:
            return
        if getattr(pokemon, "types", [None])[0] == "Poison":
            pokemon.hp = min(pokemon.hp + pokemon.max_hp // 16, pokemon.max_hp)
        else:
            pokemon.hp = max(pokemon.hp - pokemon.max_hp // 8, 0)

class Blastoisinite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Blazikenite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Blueorb:
    def onPrimal(self, pokemon=None):
        if pokemon and pokemon.name == "Kyogre":
            if hasattr(pokemon, "formeChange"):
                pokemon.formeChange("Kyogre-Primal")

    def onSwitchIn(self, pokemon=None):
        if pokemon and pokemon.name == "Kyogre" and getattr(pokemon, "is_active", False):
            if hasattr(pokemon, "queue_primal"):
                pokemon.queue_primal()

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name == "Kyogre":
            return False
        if source and source.name == "Kyogre":
            return False
        return True

class Boosterenergy:
    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["boosterenergy"] = True

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and "Paradox" in getattr(pokemon, "tags", []):
            return False
        if source and "Paradox" in getattr(source, "tags", []):
            return False
        return True

    def onUpdate(self, pokemon=None):
        if not pokemon or pokemon.volatiles.get("used_booster"):
            return
        if ("protosynthesis" in getattr(pokemon, "abilities", [])) or (
            "quarkdrive" in getattr(pokemon, "abilities", [])
        ):
            pokemon.volatiles["used_booster"] = True
            if hasattr(pokemon, "item"):
                pokemon.item = None

class Brightpowder:
    def onModifyAccuracy(self, accuracy, user=None, target=None, move=None):
        if isinstance(accuracy, (int, float)):
            return accuracy * 0.9
        return accuracy

class Buggem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Bug" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Bugmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Burndrive:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Genesect"):
            return False
        if source and source.name.startswith("Genesect"):
            return False
        return True

class Burntberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) in {"brn", "frz"}:
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) in {"brn", "frz"}:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Cameruptite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Cellbattery:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Electric" and target:
            if hasattr(target, "boosts"):
                target.boosts["atk"] = target.boosts.get("atk", 0) + 1
            if hasattr(target, "item"):
                target.item = None

class Charcoal:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fire":
            return int(base_power * 1.2)
        return base_power

class Charizarditex:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Charizarditey:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Chartiberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Rock" and target:
            return int(damage * 0.5)
        return damage

class Cheriberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "par":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "par":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Chestoberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "slp":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "slp":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Chilanberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Normal" and target:
            return int(damage * 0.5)
        return damage

class Chilldrive:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Genesect"):
            return False
        if source and source.name.startswith("Genesect"):
            return False
        return True

class Choiceband:
    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and not getattr(pokemon, "volatiles", {}).get("dynamax"):
            return int(atk * 1.5)
        return atk

    def onModifyMove(self, move=None, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["choicelock"] = True

    def onStart(self, pokemon=None):
        if pokemon and getattr(pokemon, "volatiles", {}).get("choicelock"):
            pokemon.volatiles.pop("choicelock", None)

class Choicescarf:
    def onModifyMove(self, move=None, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["choicelock"] = True

    def onModifySpe(self, spe, pokemon=None):
        if pokemon and not getattr(pokemon, "volatiles", {}).get("dynamax"):
            return int(spe * 1.5)
        return spe

    def onStart(self, pokemon=None):
        if pokemon and getattr(pokemon, "volatiles", {}).get("choicelock"):
            pokemon.volatiles.pop("choicelock", None)

class Choicespecs:
    def onModifyMove(self, move=None, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["choicelock"] = True

    def onModifySpA(self, spa, pokemon=None, target=None, move=None):
        if pokemon and not getattr(pokemon, "volatiles", {}).get("dynamax"):
            return int(spa * 1.5)
        return spa

    def onStart(self, pokemon=None):
        if pokemon and getattr(pokemon, "volatiles", {}).get("choicelock"):
            pokemon.volatiles.pop("choicelock", None)

class Chopleberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Fighting" and target:
            return int(damage * 0.5)
        return damage

class Clearamulet:
    def onTryBoost(self, boosts, target=None, source=None, effect=None):
        if target is source:
            return boosts
        for stat in list(boosts.keys()):
            if boosts[stat] < 0:
                boosts.pop(stat)
        if not boosts:
            return None
        return boosts

class Cobaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Flying" and target:
            return int(damage * 0.5)
        return damage

class Colburberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Dark" and target:
            return int(damage * 0.5)
        return damage

class Cornerstonemask:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Ogerpon") and move.type == "Rock":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Ogerpon"):
            return False
        if source and source.name.startswith("Ogerpon"):
            return False
        return True

class Covertcloak:
    def onModifySecondaries(self, secondaries, target=None, source=None, move=None):
        if target and source and target is not source:
            return []
        return secondaries

class Crucibellite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Custapberry:
    def onEat(self, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["custap"] = True

    def onFractionalPriority(self, pokemon=None):
        if pokemon and pokemon.volatiles.get("custap"):
            pokemon.volatiles.pop("custap", None)
            return 0.1
        return 0

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Darkgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Dark" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Darkmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Deepseascale:
    def onModifySpD(self, spd, pokemon=None):
        if pokemon and pokemon.name == "Clamperl":
            return int(spd * 2)
        return spd

class Deepseatooth:
    def onModifySpA(self, spa, pokemon=None):
        if pokemon and pokemon.name == "Clamperl":
            return int(spa * 2)
        return spa

class Destinyknot:
    def onAttract(self, pokemon=None, source=None):
        if pokemon and source and hasattr(source, "volatiles"):
            source.volatiles["attract"] = True

class Diancite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Dousedrive:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Genesect"):
            return False
        if source and source.name.startswith("Genesect"):
            return False
        return True

class Dracoplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Dragon":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Dragonfang:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Dragon":
            return int(base_power * 1.2)
        return base_power

class Dragongem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Dragon" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Dragonmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Dreadplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Dark":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Earthplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ground":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Ejectbutton:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if move and target and source and move.category != "Status" and target.hp > 0:
            if hasattr(target, "switch_out"):
                target.switch_out()
            if hasattr(target, "item"):
                target.item = None

class Ejectpack:
    def onAfterBoost(self, boost=None, target=None, source=None, effect=None):
        if not boost or not target:
            return
        if any(v < 0 for v in boost.values()):
            if hasattr(target, "switch_out"):
                target.switch_out()
            if hasattr(target, "item"):
                target.item = None

class Electricgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Electric" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Electricmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Electricseed:
    def _activate(self, pokemon):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["def"] = pokemon.boosts.get("def", 0) + 1
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None

    def onStart(self, pokemon=None):
        terrain = getattr(getattr(pokemon, "battle", None), "terrain", None)
        if terrain == "electricterrain":
            self._activate(pokemon)

    def onTerrainChange(self, pokemon=None):
        self.onStart(pokemon)

class Enigmaberry:
    def onEat(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 4
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onHit(self, damage, target=None, source=None, move=None):
        if target and move and type_effectiveness(target, move) > 1:
            if hasattr(target, "eat_item"):
                target.eat_item()

    def onTryEatItem(self, pokemon=None):
        return True

class Eviolite:
    def onModifyDef(self, defense, pokemon=None):
        if pokemon and not getattr(pokemon, "fully_evolved", True):
            return int(defense * 1.5)
        return defense

    def onModifySpD(self, spd, pokemon=None):
        if pokemon and not getattr(pokemon, "fully_evolved", True):
            return int(spd * 1.5)
        return spd

class Expertbelt:
    def onModifyDamage(self, damage, source=None, target=None, move=None):
        if target and move and type_effectiveness(target, move) > 1:
            return int(damage * 1.2)
        return damage

class Fairyfeather:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fairy":
            return int(base_power * 1.2)
        return base_power

class Fairygem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Fairy" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Fairymemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Fightinggem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Fighting" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Fightingmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Figyberry:
    def onEat(self, pokemon=None):
        if not pokemon:
            return
        heal = pokemon.max_hp // 3
        pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Firegem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Fire" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Firememory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Fistplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fighting":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Flameorb:
    def onResidual(self, pokemon=None):
        if pokemon and not getattr(pokemon, "status", None):
            pokemon.setStatus("brn")

class Flameplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fire":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Floatstone:
    def onModifyWeight(self, weight, pokemon=None):
        return weight / 2 if weight else weight

class Flyinggem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Flying" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Flyingmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Focusband:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if target and damage >= target.hp and random() < 0.1:
            return target.hp - 1
        return damage

class Focussash:
    def onDamage(self, damage, target=None, source=None, effect=None):
        if target and damage >= target.hp and target.hp == target.max_hp:
            if hasattr(target, "item"):
                target.item = None
            return target.hp - 1
        return damage

class Galladite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Ganlonberry:
    def onEat(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["def"] = pokemon.boosts.get("def", 0) + 1

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Garchompite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Gardevoirite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Gengarite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Ghostgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Ghost" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Ghostmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Glalitite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Goldberry:
    def onEat(self, pokemon=None):
        if pokemon:
            pokemon.hp = min(pokemon.hp + 30, pokemon.max_hp)

    def onResidual(self, pokemon=None):
        return

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp < pokemon.max_hp

class Grassgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Grass" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Grassmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Grassyseed:
    def _activate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["def"] = pokemon.boosts.get("def", 0) + 1
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None

    def onStart(self, pokemon=None):
        terrain = getattr(getattr(pokemon, "battle", None), "terrain", None)
        if terrain == "grassyterrain":
            self._activate(pokemon)

    def onTerrainChange(self, pokemon=None):
        self.onStart(pokemon)

class Griseouscore:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Giratina") and move.type in {"Ghost", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Giratina"):
            return False
        if source and source.name.startswith("Giratina"):
            return False
        return True

class Griseousorb:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Giratina") and move.type in {"Ghost", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

class Groundgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Ground" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Groundmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Gyaradosite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Habanberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Dragon" and target:
            return int(damage * 0.5)
        return damage

class Hardstone:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Rock":
            return int(base_power * 1.2)
        return base_power

class Hearthflamemask:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Ogerpon") and move.type == "Fire":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Ogerpon"):
            return False
        if source and source.name.startswith("Ogerpon"):
            return False
        return True

class Heracronite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Houndoominite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Iapapaberry:
    def onEat(self, pokemon=None):
        if not pokemon:
            return
        heal = pokemon.max_hp // 3
        pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Iceberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "frz":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "frz":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Icegem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Ice" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Icememory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Icicleplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ice":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Insectplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Bug":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Ironball:
    def onEffectiveness(self, type_mod, target=None, type=None, move=None):
        if move and move.type == "Ground" and type_mod < 1 and target:
            return 1
        return type_mod

    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

class Ironplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Steel":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Jabocaberry:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.category == "Physical":
            if hasattr(source, "hp") and hasattr(source, "max_hp"):
                source.hp = max(source.hp - source.max_hp // 8, 0)
            if target and hasattr(target, "item"):
                target.item = None

    def onEat(self, pokemon=None):
        return

class Kangaskhanite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Kasibberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Ghost" and target:
            return int(damage * 0.5)
        return damage

class Kebiaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Poison" and target:
            return int(damage * 0.5)
        return damage

class Keeberry:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if target and source and target is not source and move and move.category == "Physical":
            if hasattr(target, "boosts"):
                target.boosts["def"] = target.boosts.get("def", 0) + 1
            if hasattr(target, "item"):
                target.item = None

    def onEat(self, pokemon=None):
        return

class Kingsrock:
    def onModifyMove(self, move=None, pokemon=None):
        if move and move.category != "Status":
            move.secondaries = getattr(move, "secondaries", []) + [{"chance": 10, "volatileStatus": "flinch"}]

class Lansatberry:
    def onEat(self, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["focusenergy"] = True

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Latiasite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Latiosite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Laxincense:
    def onModifyAccuracy(self, accuracy, user=None, target=None, move=None):
        if isinstance(accuracy, (int, float)):
            return accuracy * 0.9
        return accuracy

class Leek:
    def onModifyCritRatio(self, crit_ratio, pokemon=None, target=None):
        return crit_ratio + 2

class Leftovers:
    def onResidual(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 16
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

class Leppaberry:
    def onEat(self, pokemon=None):
        if not pokemon:
            return
        for move in getattr(pokemon, "moves", []):
            if getattr(move, "pp", 1) == 0:
                move.pp = min(getattr(move, "max_pp", 0), move.pp + 10)
                break

    def onUpdate(self, pokemon=None):
        if pokemon:
            for move in getattr(pokemon, "moves", []):
                if getattr(move, "pp", 1) == 0:
                    if hasattr(pokemon, "eat_item"):
                        pokemon.eat_item()
                    break

class Liechiberry:
    def onEat(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["atk"] = pokemon.boosts.get("atk", 0) + 1

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Lifeorb:
    def onAfterMoveSecondarySelf(self, source=None, target=None, move=None):
        if source and move and move.category != "Status":
            source.hp = max(source.hp - source.max_hp // 10, 0)

    def onModifyDamage(self, damage, source=None, target=None, move=None):
        if source and move and move.category != "Status":
            return int(damage * 1.3)
        return damage

class Lightball:
    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and pokemon.name.startswith("Pikachu"):
            return atk * 2
        return atk

    def onModifySpA(self, spa, pokemon=None, target=None, move=None):
        if pokemon and pokemon.name.startswith("Pikachu"):
            return spa * 2
        return spa

class Loadeddice:
    def onModifyMove(self, move=None, pokemon=None):
        if move and getattr(move, "multihit", None) and isinstance(move.multihit, (list, tuple)):
            move.multihit = (4, 5)

class Lopunnite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Lucarionite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Luckypunch:
    def onModifyCritRatio(self, crit_ratio, pokemon=None, target=None):
        if pokemon and pokemon.name == "Chansey":
            return crit_ratio + 2
        return crit_ratio

class Luckyegg:
    def onModifyExp(self, exp, pokemon=None):
        """Boost EXP gained by 50%."""
        if isinstance(exp, (int, float)):
            return int(exp * 1.5)
        return exp

class Lumberry:
    def onAfterSetStatus(self, status=None, target=None, source=None, effect=None):
        if target and status:
            if hasattr(target, "setStatus"):
                target.setStatus(0)
            if hasattr(target, "item"):
                target.item = None

    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None):
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None):
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Luminousmoss:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Water" and target:
            if hasattr(target, "boosts"):
                target.boosts["spd"] = target.boosts.get("spd", 0) + 1
            if hasattr(target, "item"):
                target.item = None

class Lustrousglobe:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Palkia") and move.type in {"Water", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Palkia"):
            return False
        if source and source.name.startswith("Palkia"):
            return False
        return True

class Lustrousorb:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Palkia") and move.type in {"Water", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

class Machobrace:
    def onModifySpe(self, spe, pokemon=None):
        """Halve the holder's Speed."""
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        """Double EV gains."""
        if isinstance(gains, dict):
            return {k: v * 2 for k, v in gains.items()}
        return gains

class Magnet:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Electric":
            return int(base_power * 1.2)
        return base_power

class Magoberry:
    def onEat(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 3
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Mail:
    def onTakeItem(self, *args, **kwargs):
        """Mail cannot be removed."""
        return False

class Manectite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Marangaberry:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if target and source and target is not source and move and move.category == "Special":
            if hasattr(target, "boosts"):
                target.boosts["spd"] = target.boosts.get("spd", 0) + 1
            if hasattr(target, "item"):
                target.item = None

    def onEat(self, pokemon=None):
        return

class Mawilite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Meadowplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Grass":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Medichamite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Mentalherb:
    def effect(self, pokemon=None):
        conditions = ["attract", "taunt", "encore", "torment", "disable", "healblock"]
        if not pokemon:
            return
        for cond in conditions:
            if getattr(pokemon, "volatiles", {}).get(cond):
                for c in conditions:
                    pokemon.volatiles.pop(c, None)
                if cond == "attract":
                    if hasattr(pokemon.battle, "add"):  # in battle environment
                        pokemon.battle.add("-end", pokemon, "move: Attract", "[from] item: Mental Herb")
                if hasattr(pokemon, "item"):
                    pokemon.item = None
                break

    def onUpdate(self, pokemon=None):
        self.effect(pokemon)

class Metagrossite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Metalcoat:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Steel":
            return int(base_power * 1.2)
        return base_power

class Metalpowder:
    def onModifyDef(self, defense, pokemon=None):
        if pokemon and pokemon.name == "Ditto" and not getattr(pokemon, "transformed", False):
            return defense * 2
        return defense

class Metronome:
    def onModifyDamage(self, damage, source=None, target=None, move=None):
        state = getattr(source, "volatiles", {}).get("metronome", {})
        count = state.get("num_consecutive", 0)
        if count > 5:
            count = 5
        modifier = 1 + 0.2 * count
        return int(damage * modifier)

    def onStart(self, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["metronome"] = {"last_move": None, "num_consecutive": 0}

    def onTryMove(self, pokemon=None, target=None, move=None):
        if not pokemon or not move:
            return
        state = pokemon.volatiles.setdefault("metronome", {"last_move": None, "num_consecutive": 0})
        if state["last_move"] == getattr(move, "id", None):
            state["num_consecutive"] = min(state["num_consecutive"] + 1, 6)
        else:
            state["num_consecutive"] = 0
            state["last_move"] = getattr(move, "id", None)

class Mewtwonitex:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Mewtwonitey:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Micleberry:
    def onEat(self, pokemon=None):
        if pokemon:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["micleberry"] = 2

    def onResidual(self, pokemon=None):
        if pokemon and pokemon.volatiles.get("micleberry"):
            pokemon.volatiles["micleberry"] -= 1
            if pokemon.volatiles["micleberry"] <= 0:
                pokemon.volatiles.pop("micleberry", None)

    def onSourceAccuracy(self, accuracy, target=None, source=None, move=None):
        if source and source.volatiles.get("micleberry") and not getattr(move, "ohko", False):
            source.volatiles.pop("micleberry", None)
            if isinstance(accuracy, (int, float)):
                return accuracy * 1.2
        return accuracy

class Mindplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Psychic":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Mintberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "slp":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "slp":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Miracleberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None):
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None):
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Miracleseed:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Grass":
            return int(base_power * 1.2)
        return base_power

class Mirrorherb:
    def onFoeAfterBoost(self, boost=None, target=None, source=None, effect=None):
        if not boost or not target or target is source:
            return
        if effect and getattr(effect, "name", None) in {"Opportunist", "Mirror Herb"}:
            return
        gains = {stat: amount for stat, amount in boost.items() if amount > 0}
        if not gains:
            return
        if hasattr(target, "boosts") and hasattr(target, "item"):
            for stat, amt in gains.items():
                target.boosts[stat] = target.boosts.get(stat, 0) + amt
            target.item = None

class Mistyseed:
    def _activate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spd"] = pokemon.boosts.get("spd", 0) + 1
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None

    def onStart(self, pokemon=None):
        terrain = getattr(getattr(pokemon, "battle", None), "terrain", None)
        if terrain == "mistyterrain":
            self._activate(pokemon)

    def onTerrainChange(self, pokemon=None):
        self.onStart(pokemon)

class Muscleband:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.category == "Physical":
            return int(base_power * 1.1)
        return base_power

class Mysteryberry:
    def onEat(self, pokemon=None):
        if not pokemon:
            return
        for move in getattr(pokemon, "moves", []):
            if getattr(move, "pp", 0) <= 5:
                move.pp = min(getattr(move, "max_pp", 0), move.pp + 5)
                break

    def onUpdate(self, pokemon=None):
        if pokemon:
            for move in getattr(pokemon, "moves", []):
                if getattr(move, "pp", 0) <= 5:
                    if hasattr(pokemon, "eat_item"):
                        pokemon.eat_item()
                    break

class Mysticwater:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Water":
            return int(base_power * 1.2)
        return base_power

class Nevermeltice:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ice":
            return int(base_power * 1.2)
        return base_power

class Normalgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status" or getattr(move, "flags", {}).get("pledgecombo"):
            return
        if move.type == "Normal" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Occaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Fire" and target:
            return int(damage * 0.5)
        return damage

class Oddincense:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Psychic":
            return int(base_power * 1.2)
        return base_power

class Oranberry:
    def onEat(self, pokemon=None):
        if pokemon:
            pokemon.hp = min(pokemon.hp + 10, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Passhoberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Water" and target:
            return int(damage * 0.5)
        return damage

class Payapaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Psychic" and target:
            return int(damage * 0.5)
        return damage

class Pechaberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "psn":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "psn":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Persimberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "volatiles", {}).get("confusion"):
            pokemon.volatiles.pop("confusion", None)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "volatiles", {}).get("confusion"):
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Petayaberry:
    def onEat(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spa"] = pokemon.boosts.get("spa", 0) + 1

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Pidgeotite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Pinkbow:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Normal":
            return int(base_power * 1.2)
        return base_power

class Pinsirite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Pixieplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Fairy":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Poisonbarb:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Poison":
            return int(base_power * 1.2)
        return base_power

class Poisongem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Poison" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Poisonmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Polkadotbow:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Normal":
            return int(base_power * 1.2)
        return base_power

class Poweranklet:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["spe"] = gains.get("spe", 0) + 8
            return gains
        return gains

class Powerband:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["spd"] = gains.get("spd", 0) + 8
            return gains
        return gains

class Powerbelt:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["def"] = gains.get("def", 0) + 8
            return gains
        return gains

class Powerbracer:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["atk"] = gains.get("atk", 0) + 8
            return gains
        return gains

class Powerherb:
    def onChargeMove(self, pokemon=None, target=None, move=None):
        if move and getattr(move, "flags", {}).get("charge") and pokemon and hasattr(pokemon, "item"):
            pokemon.item = None
            return False
        return True

class Powerlens:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["spa"] = gains.get("spa", 0) + 8
            return gains
        return gains

class Powerweight:
    def onModifySpe(self, spe, pokemon=None):
        return spe // 2 if isinstance(spe, int) else spe

    def onModifyEVs(self, gains, pokemon=None):
        if isinstance(gains, dict):
            gains = gains.copy()
            gains["hp"] = gains.get("hp", 0) + 8
            return gains
        return gains

class Ppup:
    def onUse(self, pokemon=None, move_name=None):
        if not pokemon or not move_name:
            return False
        return pokemon.apply_pp_up(move_name)

class Ppmax:
    def onUse(self, pokemon=None, move_name=None):
        if not pokemon or not move_name:
            return False
        return pokemon.apply_pp_max(move_name)

class Potion:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        healed = min(cur_hp + 20, max_hp)
        if healed <= cur_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = healed
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = healed
        return True

class Superpotion:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        healed = min(cur_hp + 60, max_hp)
        if healed <= cur_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = healed
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = healed
        return True

class Hyperpotion:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        healed = min(cur_hp + 120, max_hp)
        if healed <= cur_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = healed
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = healed
        return True

class Maxpotion:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        if cur_hp >= max_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = max_hp
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = max_hp
        return True

class Fullrestore:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        if hasattr(pokemon, "hp"):
            pokemon.hp = max_hp
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = max_hp
        if hasattr(pokemon, "status"):
            pokemon.status = 0
        return True

class Antidote:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        status = getattr(pokemon, "status", None)
        if status not in {"psn", "tox"}:
            return False
        pokemon.status = 0
        return True

class Paralyzeheal:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if getattr(pokemon, "status", None) != "par":
            return False
        pokemon.status = 0
        return True

class Burnheal:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if getattr(pokemon, "status", None) != "brn":
            return False
        pokemon.status = 0
        return True

class Iceheal:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if getattr(pokemon, "status", None) != "frz":
            return False
        pokemon.status = 0
        return True

class Awakening:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if getattr(pokemon, "status", None) != "slp":
            return False
        pokemon.status = 0
        return True

class Fullheal:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if hasattr(pokemon, "status"):
            if getattr(pokemon, "status", None) == 0:
                return False
            pokemon.status = 0
            return True
        return False

class Revive:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        hp_attr = "hp" if hasattr(pokemon, "hp") else "current_hp"
        cur_hp = getattr(pokemon, hp_attr, 0)
        if cur_hp > 0:
            return False
        max_hp = getattr(pokemon, "max_hp", cur_hp)
        heal = max_hp // 2
        setattr(pokemon, hp_attr, heal)
        if hasattr(pokemon, "status"):
            pokemon.status = 0
        if hasattr(pokemon, "fainted"):
            pokemon.fainted = False
        return True

class Maxrevive:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        hp_attr = "hp" if hasattr(pokemon, "hp") else "current_hp"
        cur_hp = getattr(pokemon, hp_attr, 0)
        if cur_hp > 0:
            return False
        max_hp = getattr(pokemon, "max_hp", cur_hp)
        setattr(pokemon, hp_attr, max_hp)
        if hasattr(pokemon, "status"):
            pokemon.status = 0
        if hasattr(pokemon, "fainted"):
            pokemon.fainted = False
        return True

class Ether:
    def onUse(self, pokemon=None, move_name=None):
        if not pokemon or not move_name:
            return False
        get_max = getattr(pokemon, "get_max_pp", None)
        slots = getattr(pokemon, "activemoveslot_set", None)
        if not slots or not get_max:
            return False
        try:
            slot_iter = slots.all()
        except Exception:
            slot_iter = slots
        for slot in slot_iter:
            if slot.move.name.lower() == move_name.lower():
                max_pp = get_max(move_name)
                if max_pp is None:
                    return False
                if slot.current_pp >= max_pp:
                    return False
                slot.current_pp = min(slot.current_pp + 10, max_pp)
                if hasattr(slot, "save"):
                    slot.save()
                return True
        return False

class Maxether:
    def onUse(self, pokemon=None, move_name=None):
        if not pokemon or not move_name:
            return False
        get_max = getattr(pokemon, "get_max_pp", None)
        slots = getattr(pokemon, "activemoveslot_set", None)
        if not slots or not get_max:
            return False
        try:
            slot_iter = slots.all()
        except Exception:
            slot_iter = slots
        for slot in slot_iter:
            if slot.move.name.lower() == move_name.lower():
                max_pp = get_max(move_name)
                if max_pp is None:
                    return False
                if slot.current_pp >= max_pp:
                    return False
                slot.current_pp = max_pp
                if hasattr(slot, "save"):
                    slot.save()
                return True
        return False

class Elixir:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        get_max = getattr(pokemon, "get_max_pp", None)
        slots = getattr(pokemon, "activemoveslot_set", None)
        if not slots or not get_max:
            return False
        changed = False
        try:
            slot_iter = slots.all()
        except Exception:
            slot_iter = slots
        for slot in slot_iter:
            max_pp = get_max(slot.move.name)
            if max_pp is None:
                continue
            if slot.current_pp < max_pp:
                slot.current_pp = min(slot.current_pp + 10, max_pp)
                if hasattr(slot, "save"):
                    slot.save()
                changed = True
        return changed

class Maxelixir:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        get_max = getattr(pokemon, "get_max_pp", None)
        slots = getattr(pokemon, "activemoveslot_set", None)
        if not slots or not get_max:
            return False
        changed = False
        try:
            slot_iter = slots.all()
        except Exception:
            slot_iter = slots
        for slot in slot_iter:
            max_pp = get_max(slot.move.name)
            if max_pp is None:
                continue
            if slot.current_pp < max_pp:
                slot.current_pp = max_pp
                if hasattr(slot, "save"):
                    slot.save()
                changed = True
        return changed

class Hpup:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"hp": 10})
        return True

class Protein:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"atk": 10})
        return True

class Iron:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"def": 10})
        return True

class Calcium:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spa": 10})
        return True

class Carbos:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spe": 10})
        return True

class Zinc:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spd": 10})
        return True

class Healthfeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"hp": 1})
        return True

class Musclefeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"atk": 1})
        return True

class Resistfeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"def": 1})
        return True

class Geniusfeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spa": 1})
        return True

class Cleverfeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spd": 1})
        return True

class Swiftfeather:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.models.stats import add_evs
        except Exception:
            return False
        add_evs(pokemon, {"spe": 1})
        return True

class Healpowder:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        if getattr(pokemon, "status", None) == 0:
            return False
        pokemon.status = 0
        return True

class Energypowder:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        healed = min(cur_hp + 60, max_hp)
        if healed <= cur_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = healed
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = healed
        return True

class Energyroot:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        cur_hp = getattr(pokemon, "hp", getattr(pokemon, "current_hp", 0))
        healed = min(cur_hp + 120, max_hp)
        if healed <= cur_hp:
            return False
        if hasattr(pokemon, "hp"):
            pokemon.hp = healed
        if hasattr(pokemon, "current_hp"):
            pokemon.current_hp = healed
        return True

class Revivalherb:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        hp_attr = "hp" if hasattr(pokemon, "hp") else "current_hp"
        cur_hp = getattr(pokemon, hp_attr, 0)
        if cur_hp > 0:
            return False
        max_hp = getattr(pokemon, "max_hp", cur_hp)
        setattr(pokemon, hp_attr, max_hp)
        if hasattr(pokemon, "status"):
            pokemon.status = 0
        if hasattr(pokemon, "fainted"):
            pokemon.fainted = False
        return True

class Abilitycapsule:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.dex import POKEDEX
        except Exception:
            return False
        species = getattr(pokemon, "species", getattr(pokemon, "name", None))
        data = POKEDEX.get(species)
        if not data:
            return False
        abilities = data.get("abilities", {})
        cur = getattr(pokemon, "ability", None)
        if cur == abilities.get("0") and "1" in abilities:
            pokemon.ability = abilities["1"]
            return True
        if cur == abilities.get("1") and "0" in abilities:
            pokemon.ability = abilities["0"]
            return True
        return False

class Abilitypatch:
    def onUse(self, pokemon=None):
        if not pokemon:
            return False
        try:
            from pokemon.dex import POKEDEX
        except Exception:
            return False
        species = getattr(pokemon, "species", getattr(pokemon, "name", None))
        data = POKEDEX.get(species)
        if not data:
            return False
        hidden = data.get("abilities", {}).get("H")
        if not hidden or getattr(pokemon, "ability", None) == hidden:
            return False
        pokemon.ability = hidden
        return True

class Przcureberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "par":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "par":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Psncureberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "psn":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "psn":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Psychicgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Psychic" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Psychicmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Psychicseed:
    def _activate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spd"] = pokemon.boosts.get("spd", 0) + 1
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None

    def onStart(self, pokemon=None):
        terrain = getattr(getattr(pokemon, "battle", None), "terrain", None)
        if terrain == "psychicterrain":
            self._activate(pokemon)

    def onTerrainChange(self, pokemon=None):
        self.onStart(pokemon)

class Punchingglove:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.flags.get("punch"):
            return int(base_power * 1.1)
        return base_power

    def onModifyMove(self, move=None, pokemon=None):
        if move and move.flags.get("punch"):
            move.flags["contact"] = False

class Quickclaw:
    def onFractionalPriority(self, pokemon=None):
        if pokemon and random() < 0.2:
            return 0.1
        return 0

class Quickpowder:
    def onModifySpe(self, spe, pokemon=None):
        if pokemon and pokemon.name == "Ditto" and not getattr(pokemon, "transformed", False):
            return spe * 2 if isinstance(spe, int) else spe
        return spe

class Rawstberry:
    def onEat(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "brn":
            pokemon.setStatus(0)

    def onUpdate(self, pokemon=None):
        if pokemon and getattr(pokemon, "status", None) == "brn":
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Razorclaw:
    def onModifyCritRatio(self, crit_ratio, pokemon=None, target=None):
        return crit_ratio + 1

class Razorfang:
    def onModifyMove(self, move=None, pokemon=None):
        if move and move.category != "Status":
            move.secondaries = getattr(move, "secondaries", []) + [{"chance": 10, "volatileStatus": "flinch"}]

class Redcard:
    def onAfterMoveSecondary(self, target=None, source=None, move=None):
        if move and target and source and move.category != "Status" and target.hp > 0:
            if hasattr(source, "switch_out"):
                source.switch_out()
            if hasattr(target, "item"):
                target.item = None

class Redorb:
    def onPrimal(self, pokemon=None):
        if pokemon and pokemon.name == "Groudon":
            if hasattr(pokemon, "formeChange"):
                pokemon.formeChange("Groudon-Primal")

    def onSwitchIn(self, pokemon=None):
        if pokemon and pokemon.name == "Groudon" and getattr(pokemon, "is_active", False):
            if hasattr(pokemon, "queue_primal"):
                pokemon.queue_primal()

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name == "Groudon":
            return False
        if source and source.name == "Groudon":
            return False
        return True

class Rindoberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Grass" and target:
            return int(damage * 0.5)
        return damage

class Rockgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Rock" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Rockincense:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Rock":
            return int(base_power * 1.2)
        return base_power

class Rockmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Rockyhelmet:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.flags.get("contact"):
            if hasattr(source, "hp") and hasattr(source, "max_hp"):
                source.hp = max(source.hp - source.max_hp // 6, 0)

class Roomservice:
    def _activate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spe"] = pokemon.boosts.get("spe", 0) - 1
        if pokemon and hasattr(pokemon, "item"):
            pokemon.item = None

    def onAnyPseudoWeatherChange(self, pokemon=None):
        pseudo = getattr(getattr(pokemon, "battle", None), "pseudo_weather", {})
        if "trickroom" in pseudo:
            self._activate(pokemon)

    def onStart(self, pokemon=None):
        self.onAnyPseudoWeatherChange(pokemon)

class Roseincense:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Grass":
            return int(base_power * 1.2)
        return base_power

class Roseliberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Fairy" and target:
            return int(damage * 0.5)
        return damage

class Rowapberry:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if source and move and move.category == "Special":
            if hasattr(source, "hp") and hasattr(source, "max_hp"):
                source.hp = max(source.hp - source.max_hp // 8, 0)
            if target and hasattr(target, "item"):
                target.item = None

    def onEat(self, pokemon=None):
        return

class Rustedshield:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Zamazenta"):
            return False
        if source and source.name.startswith("Zamazenta"):
            return False
        return True

class Rustedsword:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Zacian"):
            return False
        if source and source.name.startswith("Zacian"):
            return False
        return True

class Sablenite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Safetygoggles:
    def onImmunity(self, status=None, pokemon=None):
        if status in {"sandstorm", "hail", "snow"}:
            return False
        return True

    def onTryHit(self, target=None, source=None, move=None):
        if move and move.flags.get("powder"):
            if target:
                target.immune = "Safety Goggles"
            return False
        return True

class Salacberry:
    def onEat(self, pokemon=None):
        if pokemon and hasattr(pokemon, "boosts"):
            pokemon.boosts["spe"] = pokemon.boosts.get("spe", 0) + 1

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Salamencite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Sceptilite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Scizorite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Scopelens:
    def onModifyCritRatio(self, crit_ratio, pokemon=None, target=None):
        return crit_ratio + 1

class Seaincense:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Water":
            return int(base_power * 1.2)
        return base_power

class Sharpbeak:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Flying":
            return int(base_power * 1.2)
        return base_power

class Sharpedonite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Shedshell:
    def onTrapPokemon(self, pokemon=None):
        if pokemon:
            pokemon.trapped = False

class Shellbell:
    def onAfterMoveSecondarySelf(self, source=None, target=None, move=None):
        if source and move and move.category != "Status" and hasattr(source, "last_damage", None):
            heal = source.last_damage // 8
            source.hp = min(source.hp + heal, source.max_hp)

class Shockdrive:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Genesect"):
            return False
        if source and source.name.startswith("Genesect"):
            return False
        return True

class Shucaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Ground" and target:
            return int(damage * 0.5)
        return damage

class Silkscarf:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Normal":
            return int(base_power * 1.2)
        return base_power

class Silverpowder:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Bug":
            return int(base_power * 1.2)
        return base_power

class Sitrusberry:
    def onEat(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 4
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 2:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Skyplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Flying":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Slowbronite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Snowball:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if move and move.type == "Ice" and target:
            if hasattr(target, "boosts"):
                target.boosts["atk"] = target.boosts.get("atk", 0) + 1
            if hasattr(target, "item"):
                target.item = None

class Softsand:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ground":
            return int(base_power * 1.2)
        return base_power

class Souldew:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name in {"Latias", "Latios"} and move.type in {"Psychic", "Dragon"}:
            return int(base_power * 1.2)
        return base_power

class Spelltag:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ghost":
            return int(base_power * 1.2)
        return base_power

class Splashplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Water":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Spookyplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Ghost":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Starfberry:
    def onEat(self, pokemon=None):
        if not pokemon or not hasattr(pokemon, "boosts"):
            return
        stats = ["atk", "def", "spa", "spd", "spe"]
        stat = stats[int(random() * len(stats))]
        pokemon.boosts[stat] = min(pokemon.boosts.get(stat, 0) + 2, 6)

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Steelgem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Steel" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Steelixite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Steelmemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Stick:
    def onModifyCritRatio(self, crit_ratio, pokemon=None, target=None):
        return crit_ratio + 2

class Stickybarb:
    def onHit(self, target=None, source=None, move=None):
        if move and move.flags.get("contact") and target and source and not getattr(source, "item", None):
            source.item = target.item
            target.item = None

    def onResidual(self, pokemon=None):
        if pokemon:
            pokemon.hp = max(pokemon.hp - pokemon.max_hp // 8, 0)

class Stoneplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Rock":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Swampertite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Tangaberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Bug" and target:
            return int(damage * 0.5)
        return damage

class Thickclub:
    def onModifyAtk(self, atk, pokemon=None, target=None, move=None):
        if pokemon and pokemon.name in {"Cubone", "Marowak", "Marowak-Alola", "Marowak-Alola-Totem"}:
            return atk * 2
        return atk

class Throatspray:
    def onAfterMoveSecondarySelf(self, source=None, target=None, move=None):
        if move and move.flags.get("sound") and source and hasattr(source, "item"):
            if hasattr(source, "boosts"):
                source.boosts["spa"] = source.boosts.get("spa", 0) + 1
            source.item = None

class Toxicorb:
    def onResidual(self, pokemon=None):
        if pokemon and not getattr(pokemon, "status", None):
            pokemon.setStatus("tox")

class Toxicplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Poison":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Twistedspoon:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Psychic":
            return int(base_power * 1.2)
        return base_power

class Tyranitarite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Utilityumbrella:
    def onEnd(self, pokemon=None):
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles.pop("utilityumbrella", None)

    def onStart(self, pokemon=None):
        if pokemon and hasattr(pokemon, "volatiles"):
            pokemon.volatiles["utilityumbrella"] = True

    def onUpdate(self, pokemon=None):
        if pokemon and hasattr(pokemon, "volatiles") and "utilityumbrella" not in pokemon.volatiles:
            pokemon.volatiles["utilityumbrella"] = True

class Venusaurite:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and item and getattr(item, "mega_evolves", None) == getattr(pokemon, "name", None):
            return False
        if source and item and getattr(item, "mega_evolves", None) == getattr(source, "name", None):
            return False
        return True

class Vilevial:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Venomicon") and move.type in {"Poison", "Flying"}:
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Venomicon"):
            return False
        if source and source.name.startswith("Venomicon"):
            return False
        return True

class Wacanberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Electric" and target:
            return int(damage * 0.5)
        return damage

class Watergem:
    def onSourceTryPrimaryHit(self, target=None, source=None, move=None):
        if target is source or not move or move.category == "Status":
            return
        if move.type == "Water" and source and hasattr(source, "item"):
            source.item = None
            if hasattr(source, "boosts"):
                source.boosts["atk"] = source.boosts.get("atk", 0) + 1

class Watermemory:
    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Silvally"):
            return False
        if source and source.name.startswith("Silvally"):
            return False
        return True

class Waveincense:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Water":
            return int(base_power * 1.2)
        return base_power

class Weaknesspolicy:
    def onDamagingHit(self, damage, target=None, source=None, move=None):
        if target and move and type_effectiveness(target, move) > 1:
            if hasattr(target, "boosts"):
                target.boosts["atk"] = min(target.boosts.get("atk", 0) + 2, 6)
                target.boosts["spa"] = min(target.boosts.get("spa", 0) + 2, 6)
            if hasattr(target, "item"):
                target.item = None

class Wellspringmask:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if user and move and user.name.startswith("Ogerpon") and move.type == "Water":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Ogerpon"):
            return False
        if source and source.name.startswith("Ogerpon"):
            return False
        return True

class Whiteherb:
    def effect(self, pokemon=None):
        if not pokemon or not hasattr(pokemon, "boosts"):
            return
        lowered = [stat for stat, val in pokemon.boosts.items() if val < 0]
        if lowered:
            for stat in lowered:
                pokemon.boosts[stat] = 0
            if hasattr(pokemon, "item"):
                pokemon.item = None

    def onUpdate(self, pokemon=None):
        self.effect(pokemon)

class Widelens:
    def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
        if isinstance(accuracy, (int, float)):
            return accuracy * 1.1
        return accuracy

class Wikiberry:
    def onEat(self, pokemon=None):
        if pokemon:
            heal = pokemon.max_hp // 3
            pokemon.hp = min(pokemon.hp + heal, pokemon.max_hp)

    def onTryEatItem(self, pokemon=None):
        return pokemon and pokemon.hp <= pokemon.max_hp // 2

    def onUpdate(self, pokemon=None):
        if pokemon and pokemon.hp <= pokemon.max_hp // 4:
            if hasattr(pokemon, "eat_item"):
                pokemon.eat_item()

class Wiseglasses:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.category == "Special":
            return int(base_power * 1.1)
        return base_power

class Yacheberry:
    def onEat(self, pokemon=None):
        return

    def onSourceModifyDamage(self, damage, source=None, target=None, move=None):
        if move and move.type == "Ice" and target:
            return int(damage * 0.5)
        return damage

class Zapplate:
    def onBasePower(self, base_power, user=None, target=None, move=None):
        if move and move.type == "Electric":
            return int(base_power * 1.2)
        return base_power

    def onTakeItem(self, item=None, pokemon=None, source=None):
        if pokemon and pokemon.name.startswith("Arceus"):
            return False
        if source and source.name.startswith("Arceus"):
            return False
        return True

class Zoomlens:
    def onSourceModifyAccuracy(self, accuracy, source=None, target=None, move=None):
        if isinstance(accuracy, (int, float)):
            return accuracy * 1.2
        return accuracy

