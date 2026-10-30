"""Paired real-login ability triggers against otherwise identical controls.

These experiments compare an ability with No Ability on the same prepared
species, moves, HP, item, status, field sequence and battle seed. They prove
only the named directional outcome, not every branch of the ability.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa import live_battle_pilot as pilot
from tools.qa.live_dex_cases import DexCase, Mon, key, turn, unique_entries
from tools.qa.live_dex_runner import DexRunner, evaluate, mon, now, verify


@dataclass(frozen=True)
class Trigger:
    """One reproducible trigger and its expected direction versus the control."""

    ability: str
    move: str = "Tackle"
    direction: str = "greater"
    side: str = "B"
    hp: float = 1.0
    status: str = ""
    setup: str = ""
    item: str = ""
    target_species: str = "Wailord"
    blocked_status: str = ""
    arming_attack: str = ""
    label: str = ""
    assertions: tuple[dict, ...] = ()
    control_assertions: tuple[dict, ...] = ()
    target_level: int = 100
    target_ability: str = "No Ability"
    target_status: str = ""
    owner_species: str = ""
    target_item: str = ""
    target_hp: float = 1.0
    situation: str = ""
    index: int = 0
    foe_setup: str = ""
    measure_side: str = ""
    turn_repeats: int = 1
    probabilistic: bool = False
    target_reserve: bool = False
    positive_trigger: bool = True


def boosts(side, **values):
    """Declare independently observed stage values for a matched trigger."""
    return {"type": "boosts", "side": side, "values": values}


def volatile(side, name, present=True):
    """Declare a volatile's presence or absence without relying on move text."""
    return {"type": "volatile", "side": side, "value": name, "present": present}


TRIGGERS = (
    # Good as Gold proves persistent status bypass. Limber can legally cure
    # paralysis on update after the move's temporary ability bypass ends.
    Trigger("Mycelium Might", "Thunder Wave", "outcomes", owner_species="Toedscruel",
            target_species="Gholdengo", target_ability="Good as Gold", label="status-through-good-as-gold",
            assertions=({"type": "status", "side": "B", "value": "par"},),
            control_assertions=({"type": "not_status", "side": "B", "value": "par"},)),
    Trigger("Mycelium Might", "Thunder Wave", "outcomes", owner_species="Toedscruel",
            target_species="Persian", target_ability="Limber", label="limber-cure-negative",
            positive_trigger=False,
            assertions=({"type": "not_status", "side": "B", "value": "par"},),
            control_assertions=({"type": "not_status", "side": "B", "value": "par"},)),
    Trigger("Mycelium Might", "Thunder Wave", "outcomes", owner_species="Toedscruel",
            target_species="Pikachu", target_ability="No Ability", label="innate-type-negative",
            positive_trigger=False,
            assertions=({"type": "not_status", "side": "B", "value": "par"},),
            control_assertions=({"type": "not_status", "side": "B", "value": "par"},)),
    *(Trigger(ability, "False Swipe", "outcomes", side, owner_species=species, label="contact-window",
              turn_repeats=4, probabilistic=True,
              assertions=({"type": "damage", "side": side, "after_turn": 1},
                          {"type": "status", "side": "B", "value": status}),
              control_assertions=({"type": "damage", "side": side, "after_turn": 1},
                                  {"type": "not_status", "side": "B", "value": status}))
      for ability, species, status, side in (
          ("Static", "Pikachu", "par", "A"), ("Flame Body", "Magmar", "brn", "A"),
          ("Poison Point", "Nidorino", "psn", "A"), ("Poison Touch", "Muk", "psn", "B"),
          ("Toxic Chain", "Okidogi", "tox", "B"),
      )),
    Trigger("Berserk", "Tackle", "equal", "A", hp=.8, label="no-crossing",
            assertions=(boosts("A", spa=0),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Berserk", "Tackle", "equal", "A", hp=.3, label="already-low",
            assertions=(boosts("A", spa=0),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Berserk", "Tackle", "outcomes", "A", hp=.51, item="Oran Berry", label="berry-order",
            assertions=(boosts("A", spa=1), {"type": "item", "side": "A", "value": ""}),
            control_assertions=(boosts("A", spa=0), {"type": "item", "side": "A", "value": ""})),
    Trigger("Berserk", "Water Pulse", "equal", "A", hp=.51, target_ability="Sheer Force", label="sheer-force",
            assertions=(boosts("A", spa=0),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Shield Dust", "Thunder Wave", "equal", "A", label="primary-status",
            assertions=({"type": "status", "side": "A", "value": "par"},),
            control_assertions=({"type": "status", "side": "A", "value": "par"},)),
    Trigger("Merciless", "Water Gun", "equal", target_status="brn", label="non-poison"),
    Trigger("Merciless", "Water Gun", "equal", target_status="psn", target_ability="Battle Armor", label="critical-guard"),
    Trigger("Liquid Ooze", "Absorb", "equal", "A", target_ability="Magic Guard", measure_side="B", label="magic-guard"),
    Trigger("Galvanize", "Tackle"),
    Trigger("Galvanize", "Water Gun", "equal"),
    Trigger("Liquid Voice", "Hyper Voice", owner_species="Primarina", target_species="Chansey"),
    Trigger("Liquid Voice", "Water Gun", "equal", owner_species="Primarina"),
    Trigger("Dark Aura", "Bite"), Trigger("Dark Aura", "Water Gun", "equal"),
    Trigger("Fairy Aura", "Fairy Wind"), Trigger("Fairy Aura", "Water Gun", "equal"),
    Trigger("Rough Skin", "Tackle", "greater", "A", measure_side="B"),
    Trigger("Iron Barbs", "Tackle", "greater", "A", measure_side="B"),
    Trigger("Rough Skin", "Water Gun", "equal", "A", measure_side="B"),
    Trigger("Iron Barbs", "Water Gun", "equal", "A", measure_side="B"),
    Trigger("Liquid Ooze", "Absorb", "greater", "A", measure_side="B"),
    Trigger("Liquid Ooze", "Tackle", "equal", "A", measure_side="B"),
    Trigger("Leaf Guard", "Thunder Wave", side="A", setup="Sunny Day", blocked_status="par"),
    Trigger("Own Tempo", "Confuse Ray", "outcomes", "A",
            assertions=(volatile("A", "confusion", False),), control_assertions=(volatile("A", "confusion"),)),
    Trigger("Damp", "Explosion", "less", "A"),
    Trigger("Wonder Guard", "Water Gun", "less", "A", owner_species="Shedinja"),
    Trigger("Wonder Guard", "Ember", "equal", "A", owner_species="Shedinja", label="super-effective"),
    Trigger("Zen Mode", "Splash", "outcomes", hp=.4, owner_species="Darmanitan",
            assertions=({"type": "active_species", "side": "A", "value": "Darmanitan-Zen"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Darmanitan"},)),
    Trigger("Mimicry", "Splash", "outcomes", setup="Electric Terrain", owner_species="Stunfisk-Galar",
            assertions=({"type": "types", "side": "A", "value": ["Electric"]},),
            control_assertions=({"type": "types", "side": "A", "value": ["Ground", "Steel"]},)),
    Trigger("Parental Bond", "Tackle", owner_species="Kangaskhan-Mega"),
    Trigger("Skill Link", "Icicle Spear"),
    Trigger("Merciless", "Water Gun", target_status="psn"),
    Trigger("Merciless", "Water Gun", "equal", label="healthy"),
    Trigger("Heavy Metal", "Low Kick", "greater", "A", owner_species="Aron"),
    Trigger("Light Metal", "Low Kick", "less", "A", owner_species="Beldum"),
    Trigger("Adaptability", direction="equal"), Trigger("Adaptability", "Water Gun"),
    Trigger("Aerilate"), Trigger("Analytic", item="Lagging Tail"),
    Trigger("Blaze", "Ember", hp=.25), Trigger("Defeatist", direction="less", hp=.4),
    Trigger("Dragon's Maw", "Dragon Breath"), Trigger("Flare Boost", "Water Gun", status="brn"),
    Trigger("Gorilla Tactics"), Trigger("Guts", status="psn"), Trigger("Huge Power"),
    Trigger("Hustle", "Aerial Ace"), Trigger("Iron Fist", "Mach Punch"), Trigger("Iron Fist", "Fire Punch"),
    Trigger("Mega Launcher", "Water Pulse"), Trigger("Neuroforce", "Thunder Shock"),
    Trigger("Normalize", "Water Gun", target_species="Chansey"), Trigger("Overgrow", "Vine Whip", hp=.25),
    Trigger("Pixilate"), Trigger("Punk Rock", "Round"), Trigger("Pure Power"),
    Trigger("Reckless", "Take Down"), Trigger("Refrigerate", target_species="Chansey"),
    Trigger("Rocky Payload", "Rock Throw"), Trigger("Sand Force", "Mud-Slap", setup="Sandstorm"),
    Trigger("Sharpness", "Aerial Ace"), Trigger("Sheer Force", "Water Pulse"),
    Trigger("Sniper", "Frost Breath"), Trigger("Solar Power", "Water Gun", setup="Sunny Day"),
    Trigger("Steelworker", "Metal Claw"), Trigger("Steely Spirit", "Metal Claw"),
    Trigger("Strong Jaw", "Bite"), Trigger("Swarm", "Struggle Bug", hp=.25),
    Trigger("Technician"), Trigger("Tinted Lens", "Water Gun"), Trigger("Torrent", "Water Gun", hp=.25),
    Trigger("Tough Claws"), Trigger("Toxic Boost", status="psn"), Trigger("Transistor", "Thunder Shock"),
    Trigger("Water Bubble", "Water Gun"), Trigger("Water Bubble", "Flamethrower", "less", "A"),
    Trigger("Fluffy", "Tackle", "less", "A"), Trigger("Fluffy", "Flamethrower", "greater", "A"),
    Trigger("Fur Coat", "Tackle", "less", "A"), Trigger("Heatproof", "Flamethrower", "less", "A"),
    Trigger("Ice Scales", "Water Gun", "less", "A"), Trigger("Marvel Scale", "Tackle", "less", "A", status="psn"),
    Trigger("Multiscale", "Water Gun", "less", "A"), Trigger("Shadow Shield", "Water Gun", "less", "A"),
    Trigger("Punk Rock", "Round", "less", "A"), Trigger("Thick Fat", "Flamethrower", "less", "A"),
    Trigger("Filter", "Water Gun", "equal", "A"), Trigger("Filter", "Flamethrower", "less", "A"),
    Trigger("Solid Rock", "Water Gun", "less", "A"),
    Trigger("Prism Armor", "Bite", "less", "A"), Trigger("Dry Skin", "Flamethrower", "greater", "A"),
    Trigger("Ice Face", "Tackle", "less", "A"),
    Trigger("Magic Guard", "Splash", "less", "A", status="psn"),
    Trigger("Overcoat", "Splash", "less", "A", setup="Sandstorm"),
    Trigger("Poison Heal", "Splash", "less", "A", hp=.5, status="psn"),
    Trigger("Rain Dish", "Splash", "less", "A", hp=.5, setup="Rain Dance"),
    Trigger("Dry Skin", "Splash", "less", "A", hp=.5, setup="Rain Dance"),
    Trigger("Ice Body", "Splash", "less", "A", hp=.5, setup="Snowscape"),
    Trigger("Hydration", "Splash", "less", "A", status="psn", setup="Rain Dance"),
    Trigger("Insomnia", "Spore", side="A", blocked_status="slp"),
    Trigger("Vital Spirit", "Spore", side="A", blocked_status="slp"),
    Trigger("Sweet Veil", "Spore", side="A", blocked_status="slp"),
    Trigger("Purifying Salt", "Spore", side="A", blocked_status="slp"),
    Trigger("Limber", "Thunder Wave", side="A", blocked_status="par"),
    Trigger("Water Veil", "Will-O-Wisp", side="A", blocked_status="brn"),
    Trigger("Immunity", "Poison Powder", side="A", blocked_status="psn"),
    Trigger("Pastel Veil", "Poison Powder", side="A", blocked_status="psn"),
    Trigger("Good as Gold", "Thunder Wave", side="A", blocked_status="par"),
    Trigger("Flash Fire", "Ember", arming_attack="Ember"),
    # Independent incoming attacks establish immunity/defense causally, even
    # when a native carrier's ordinary smoke attack cannot trigger its ability.
    Trigger("Battle Armor", "Frost Breath", "less", "A"),
    Trigger("Shell Armor", "Frost Breath", "less", "A"),
    Trigger("Bulletproof", "Aura Sphere", "less", "A"),
    Trigger("Soundproof", "Round", "less", "A"),
    Trigger("Disguise", "Shadow Ball", "less", "A"),
    Trigger("Levitate", "Mud-Slap", "less", "A"),
    Trigger("Water Absorb", "Water Gun", "less", "A", hp=.5),
    Trigger("Storm Drain", "Water Gun", "less", "A"),
    Trigger("Volt Absorb", "Thunder Shock", "less", "A", hp=.5),
    Trigger("Lightning Rod", "Thunder Shock", "less", "A"),
    Trigger("Motor Drive", "Thunder Shock", "less", "A"),
    Trigger("Sap Sipper", "Vine Whip", "less", "A"),
    Trigger("Earth Eater", "Mud-Slap", "less", "A", hp=.5),
    Trigger("Well-Baked Body", "Ember", "less", "A"),
    Trigger("Flash Fire", "Ember", "less", "A"),
    Trigger("Dry Skin", "Water Gun", "less", "A", hp=.5),
    Trigger("Purifying Salt", "Shadow Ball", "less", "A"),
    Trigger("Water Bubble", "Will-O-Wisp", side="A", blocked_status="brn"),
    Trigger("Slow Start", direction="less"),
    # Relevant negatives prevent a broad modifier repair from applying bonuses
    # without the qualifying HP, status, move type, contact or secondary effect.
    Trigger("Blaze", "Ember", "equal", label="healthy"), Trigger("Overgrow", "Vine Whip", "equal", label="healthy"),
    Trigger("Torrent", "Water Gun", "equal", label="healthy"), Trigger("Swarm", "Struggle Bug", "equal", label="healthy"),
    Trigger("Guts", direction="equal", label="healthy"), Trigger("Toxic Boost", direction="equal", label="healthy"),
    Trigger("Flare Boost", "Water Gun", "equal", label="healthy"), Trigger("Defeatist", direction="equal", label="healthy"),
    Trigger("Sheer Force", direction="equal"), Trigger("Reckless", direction="equal"),
    Trigger("Iron Fist", direction="equal"), Trigger("Mega Launcher", direction="equal"),
    Trigger("Sharpness", direction="equal"), Trigger("Strong Jaw", direction="equal"),
    Trigger("Aerilate", "Water Gun", "equal"), Trigger("Pixilate", "Water Gun", "equal"),
    Trigger("Refrigerate", "Water Gun", "equal"),
    Trigger("Fluffy", "Water Gun", "equal", "A"),
    Trigger("Heatproof", "Water Gun", "equal", "A"),
    Trigger("Ice Scales", "Tackle", "equal", "A"),
    Trigger("Thick Fat", "Water Gun", "equal", "A"),
    Trigger("Magic Guard", "Tackle", "equal", "A"),
    Trigger("Magic Guard", "Splash", "less", "A", setup="Sandstorm", label="weather"),
    Trigger("Overcoat", "Splash", "less", "A", setup="Hail", label="hail"),
    Trigger("Simple", "Swords Dance", "outcomes", assertions=(boosts("A", atk=4),), control_assertions=(boosts("A", atk=2),)),
    Trigger("Contrary", "Growl", "outcomes", "A", assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("Defiant", "Growl", "outcomes", "A", assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("Competitive", "Growl", "outcomes", "A", assertions=(boosts("A", atk=-1, spa=2),), control_assertions=(boosts("A", atk=-1, spa=0),)),
    Trigger("Mirror Armor", "Growl", "outcomes", "A", assertions=(boosts("A", atk=0), boosts("B", atk=-1)), control_assertions=(boosts("A", atk=-1), boosts("B", atk=0))),
    Trigger("Stamina", "Tackle", "outcomes", "A", assertions=(boosts("A", **{"def": 1}),), control_assertions=(boosts("A", **{"def": 0}),)),
    Trigger("Weak Armor", "Tackle", "outcomes", "A", assertions=(boosts("A", **{"def": -1, "spe": 2}),), control_assertions=(boosts("A", **{"def": 0, "spe": 0}),)),
    Trigger("Water Compaction", "Water Gun", "outcomes", "A", assertions=(boosts("A", **{"def": 2}),), control_assertions=(boosts("A", **{"def": 0}),)),
    Trigger("Steam Engine", "Water Gun", "outcomes", "A", assertions=(boosts("A", spe=6),), control_assertions=(boosts("A", spe=0),)),
    Trigger("Justified", "Bite", "outcomes", "A", assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Rattled", "Bite", "outcomes", "A", assertions=(boosts("A", spe=1),), control_assertions=(boosts("A", spe=0),)),
    Trigger("Thermal Exchange", "Ember", "outcomes", "A", assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Gooey", "Tackle", "outcomes", "A", assertions=(boosts("B", spe=-1),), control_assertions=(boosts("B", spe=0),)),
    Trigger("Tangling Hair", "Tackle", "outcomes", "A", assertions=(boosts("B", spe=-1),), control_assertions=(boosts("B", spe=0),)),
    Trigger("Cotton Down", "Tackle", "outcomes", "A", assertions=(boosts("B", spe=-1), boosts("A", spe=0)), control_assertions=(boosts("B", spe=0), boosts("A", spe=0))),
    Trigger("Sand Spit", "Tackle", "outcomes", "A", assertions=({"type": "weather", "value": "sandstorm"},), control_assertions=({"type": "weather", "value": "None"},)),
    Trigger("Seed Sower", "Tackle", "outcomes", "A", assertions=({"type": "terrain", "value": "grassyterrain"},), control_assertions=({"type": "terrain", "value": "None"},)),
    Trigger("Toxic Debris", "Tackle", "outcomes", "A", assertions=({"type": "side_condition", "side": "B", "value": "toxicspikes"},), control_assertions=({"type": "side_condition", "side": "B", "value": "toxicspikes", "present": False},)),
    Trigger("Wind Rider", "Gust", "less", "A"),
    Trigger("Electromorphosis", "Tackle", "outcomes", "A", assertions=(volatile("A", "charge"),), control_assertions=(volatile("A", "charge", False),)),
    Trigger("Wind Power", "Gust", "outcomes", "A", assertions=(volatile("A", "charge"),), control_assertions=(volatile("A", "charge", False),)),
    Trigger("Perish Body", "Bite", "outcomes", "A", assertions=(volatile("A", "perishsong"), volatile("B", "perishsong")), control_assertions=(volatile("A", "perishsong", False), volatile("B", "perishsong", False))),
    Trigger("Mummy", "Bite", "outcomes", "A", assertions=({"type": "ability", "side": "B", "value": "Mummy"},), control_assertions=({"type": "ability", "side": "B", "value": "No Ability"},)),
    Trigger("Lingering Aroma", "Tackle", "outcomes", "A", assertions=({"type": "ability", "side": "B", "value": "Lingering Aroma"},), control_assertions=({"type": "ability", "side": "B", "value": "No Ability"},)),
    Trigger("Wandering Spirit", "Bite", "outcomes", "A", assertions=({"type": "ability", "side": "A", "value": "No Ability"}, {"type": "ability", "side": "B", "value": "Wandering Spirit"}), control_assertions=({"type": "ability", "side": "B", "value": "No Ability"},)),
    Trigger("Clear Body", "Growl", "outcomes", "A", assertions=(boosts("A", atk=0),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("White Smoke", "Growl", "outcomes", "A", assertions=(boosts("A", atk=0),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("Full Metal Body", "Growl", "outcomes", "A", assertions=(boosts("A", atk=0),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("Hyper Cutter", "Growl", "outcomes", "A", assertions=(boosts("A", atk=0),), control_assertions=(boosts("A", atk=-1),)),
    Trigger("Big Pecks", "Tail Whip", "outcomes", "A", assertions=(boosts("A", **{"def": 0}),), control_assertions=(boosts("A", **{"def": -1}),)),
    Trigger("Keen Eye", "Sand Attack", "outcomes", "A", assertions=(boosts("A", accuracy=0),), control_assertions=(boosts("A", accuracy=-1),)),
    Trigger("Mind's Eye", "Sand Attack", "outcomes", "A", assertions=(boosts("A", accuracy=0),), control_assertions=(boosts("A", accuracy=-1),)),
    Trigger("Aroma Veil", "Taunt", "outcomes", "A", assertions=(volatile("A", "taunt", False),), control_assertions=(volatile("A", "taunt"),)),
    Trigger("Oblivious", "Taunt", "outcomes", "A", assertions=(volatile("A", "taunt", False),), control_assertions=(volatile("A", "taunt"),)),
    Trigger("Inner Focus", "Fake Out", "outcomes", "A", assertions=({"type": "pp_cost", "side": "A", "move": "Splash", "value": 1},), control_assertions=({"type": "pp_cost", "side": "A", "move": "Splash", "value": 0},)),
    Trigger("Shield Dust", "Fake Out", "outcomes", "A", assertions=({"type": "pp_cost", "side": "A", "move": "Splash", "value": 1},), control_assertions=({"type": "pp_cost", "side": "A", "move": "Splash", "value": 0},)),
    Trigger("Steadfast", "Fake Out", "outcomes", "A", assertions=(boosts("A", spe=1),), control_assertions=(boosts("A", spe=0),)),
    Trigger("Speed Boost", direction="outcomes", assertions=(boosts("A", spe=1),), control_assertions=(boosts("A", spe=0),)),
    Trigger("Intimidate", direction="outcomes", assertions=(boosts("B", atk=-1),), control_assertions=(boosts("B", atk=0),)),
    Trigger("Intrepid Sword", direction="outcomes", assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Dauntless Shield", direction="outcomes", assertions=(boosts("A", **{"def": 1}),), control_assertions=(boosts("A", **{"def": 0}),)),
    Trigger("Download", direction="outcomes", assertions=(boosts("A", spa=1),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Moxie", target_species="Magikarp", target_level=5, target_reserve=True, direction="outcomes",
            assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Chilling Neigh", target_species="Magikarp", target_level=5, target_reserve=True, direction="outcomes",
            assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Grim Neigh", target_species="Magikarp", target_level=5, target_reserve=True, direction="outcomes",
            assertions=(boosts("A", spa=1),), control_assertions=(boosts("A", spa=0),)),
    Trigger("As One (Glastrier)", target_species="Magikarp", target_level=5, target_reserve=True, direction="outcomes",
            assertions=(boosts("A", atk=1),), control_assertions=(boosts("A", atk=0),)),
    Trigger("As One (Spectrier)", target_species="Magikarp", target_level=5, target_reserve=True, direction="outcomes",
            assertions=(boosts("A", spa=1),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Soul-Heart", target_species="Magikarp", target_level=5, direction="outcomes",
            assertions=(boosts("A", spa=1),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Beast Boost", target_species="Magikarp", target_level=5, target_reserve=True, owner_species="Nihilego", direction="outcomes",
            assertions=(boosts("A", spd=1),), control_assertions=(boosts("A", spd=0),)),
    Trigger("Anger Point", "Frost Breath", "outcomes", "A", assertions=(boosts("A", atk=6),), control_assertions=(boosts("A", atk=0),)),
    Trigger("Berserk", "Tackle", "outcomes", "A", hp=.51, assertions=(boosts("A", spa=1),), control_assertions=(boosts("A", spa=0),)),
    Trigger("Anger Shell", "Tackle", "outcomes", "A", hp=.51,
            assertions=(boosts("A", atk=1, spa=1, spe=1, **{"def": -1, "spd": -1}),),
            control_assertions=(boosts("A", atk=0, spa=0, spe=0, **{"def": 0, "spd": 0}),)),
    Trigger("Dazzling", "Quick Attack", "less", "A"),
    Trigger("Queenly Majesty", "Quick Attack", "less", "A"),
    Trigger("Armor Tail", "Quick Attack", "less", "A"),
    Trigger("Mold Breaker", "Mud-Slap", target_species="Gengar", target_ability="Levitate",
            control_assertions=({"type": "immune", "side": "B"},)),
    Trigger("Teravolt", "Mud-Slap", target_species="Gengar", target_ability="Levitate",
            control_assertions=({"type": "immune", "side": "B"},)),
    Trigger("Turboblaze", "Mud-Slap", target_species="Gengar", target_ability="Levitate",
            control_assertions=({"type": "immune", "side": "B"},)),
    Trigger("Klutz", direction="less", item="Choice Band"),
    Trigger("Protean", direction="outcomes", owner_species="Greninja", assertions=({"type": "types", "side": "A", "value": ["Normal"]},),
            control_assertions=({"type": "types", "side": "A", "value": ["Water", "Dark"]},)),
    Trigger("Libero", direction="outcomes", owner_species="Cinderace", assertions=({"type": "types", "side": "A", "value": ["Normal"]},),
            control_assertions=({"type": "types", "side": "A", "value": ["Fire"]},)),
    Trigger("Color Change", "Water Gun", "outcomes", "A", owner_species="Kecleon",
            assertions=({"type": "types", "side": "A", "value": ["Water"]},),
            control_assertions=({"type": "types", "side": "A", "value": ["Normal"]},)),
    Trigger("Forecast", "Splash", "outcomes", setup="Sunny Day", owner_species="Castform",
            assertions=({"type": "active_species", "side": "A", "value": "Castform-Sunny"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Castform"},)),
    Trigger("Flower Gift", "Splash", "outcomes", setup="Sunny Day", owner_species="Cherrim",
            assertions=({"type": "active_species", "side": "A", "value": "Cherrim-Sunshine"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Cherrim"},)),
    Trigger("Hunger Switch", "Splash", "outcomes", owner_species="Morpeko",
            assertions=({"type": "active_species", "side": "A", "value": "Morpeko-Hangry"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Morpeko"},)),
    Trigger("Schooling", "Splash", "outcomes", owner_species="Wishiwashi",
            assertions=({"type": "active_species", "side": "A", "value": "Wishiwashi-School"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Wishiwashi"},)),
    Trigger("Power Construct", "Splash", "outcomes", hp=.25, owner_species="Zygarde",
            assertions=({"type": "active_species", "side": "A", "value": "Zygarde-Complete"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Zygarde"},)),
    Trigger("Gulp Missile", "Surf", "outcomes", owner_species="Cramorant",
            assertions=({"type": "active_species", "side": "A", "value": "Cramorant-Gulping"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Cramorant"},)),
    Trigger("Stance Change", "Shadow Ball", "outcomes", owner_species="Aegislash",
            assertions=({"type": "active_species", "side": "A", "value": "Aegislash-Blade"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Aegislash"},)),
    Trigger("Bad Dreams", "Splash", "greater", target_status="slp"),
    Trigger("Dry Skin", "Splash", "greater", "A", setup="Sunny Day", label="sun"),
    Trigger("Solar Power", "Splash", "greater", "A", setup="Sunny Day", label="sun"),
    Trigger("Regenerator", "Splash", "outcomes", hp=.4, situation="switch",
            assertions=({"type": "heal", "side": "A"},), control_assertions=({"type": "immune", "side": "A"},)),
    Trigger("Natural Cure", "Splash", "outcomes", status="psn", situation="switch",
            assertions=({"type": "not_status", "side": "A", "value": "psn", "original": True},),
            control_assertions=({"type": "status", "side": "A", "value": "psn", "original": True},)),
    Trigger("Zero to Hero", "Splash", "outcomes", owner_species="Palafin", situation="switch",
            assertions=({"type": "active_species", "side": "A", "value": "Palafin-Hero", "original": True},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Palafin", "original": True},)),
    Trigger("Power Spot", "Tackle", situation="ally_power"),
    Trigger("Battery", "Water Gun", situation="ally_power"),
    Trigger("Steely Spirit", "Metal Claw", situation="ally_power", label="ally"),
    Trigger("Friend Guard", "Tackle", "less", "A", situation="ally_damage", index=1),
    Trigger("Flower Veil", "Growl", "outcomes", "A", situation="grass_ally",
            assertions=({"type": "boosts", "side": "A", "index": 1, "values": {"atk": 0}},),
            control_assertions=({"type": "boosts", "side": "A", "index": 1, "values": {"atk": -1}},)),
    Trigger("Aroma Veil", "Taunt", "outcomes", "A", situation="ally_damage", label="ally",
            assertions=({"type": "volatile", "side": "A", "index": 1, "value": "taunt", "present": False},),
            control_assertions=({"type": "volatile", "side": "A", "index": 1, "value": "taunt"},)),
    Trigger("Pastel Veil", "Poison Powder", "outcomes", "A", situation="ally_damage", label="ally",
            assertions=({"type": "not_status", "side": "A", "index": 1, "value": "psn"},),
            control_assertions=({"type": "status", "side": "A", "index": 1, "value": "psn"},)),
    Trigger("Sweet Veil", "Spore", "outcomes", "A", situation="ally_damage", label="ally",
            assertions=({"type": "not_status", "side": "A", "index": 1, "value": "slp"},),
            control_assertions=({"type": "status", "side": "A", "index": 1, "value": "slp"},)),
    Trigger("Hospitality", "Splash", "outcomes", situation="ally_heal",
            assertions=({"type": "hp_fraction", "side": "A", "index": 1, "initial": True, "minimum": .64, "maximum": .66},),
            control_assertions=({"type": "hp_fraction", "side": "A", "index": 1, "initial": True, "minimum": .39, "maximum": .41},)),
    Trigger("Magician", "Tackle", "outcomes", target_item="Lagging Tail",
            assertions=({"type": "item", "side": "A", "value": "Lagging Tail"}, {"type": "item", "side": "B", "value": ""}),
            control_assertions=({"type": "item", "side": "A", "value": ""}, {"type": "item", "side": "B", "value": "Lagging Tail"})),
    Trigger("Pickpocket", "Tackle", "outcomes", "A", target_item="Lagging Tail",
            assertions=({"type": "item", "side": "A", "value": "Lagging Tail"}, {"type": "item", "side": "B", "value": ""}),
            control_assertions=({"type": "item", "side": "A", "value": ""}, {"type": "item", "side": "B", "value": "Lagging Tail"})),
    Trigger("Sticky Hold", "Thief", "outcomes", "A", item="Lagging Tail",
            assertions=({"type": "item", "side": "A", "value": "Lagging Tail"}, {"type": "item", "side": "B", "value": ""}),
            control_assertions=({"type": "item", "side": "A", "value": ""}, {"type": "item", "side": "B", "value": "Lagging Tail"})),
    Trigger("Unnerve", "Splash", "outcomes", target_item="Oran Berry", target_hp=.35,
            assertions=({"type": "item", "side": "B", "value": "Oran Berry"},),
            control_assertions=({"type": "item", "side": "B", "value": ""},)),
    Trigger("Multitype", "Splash", "outcomes", owner_species="Arceus", item="Flame Plate",
            assertions=({"type": "active_species", "side": "A", "value": "Arceus-Fire"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Arceus"},)),
    Trigger("RKS System", "Splash", "outcomes", owner_species="Silvally", item="Fire Memory",
            assertions=({"type": "active_species", "side": "A", "value": "Silvally-Fire"},),
            control_assertions=({"type": "active_species", "side": "A", "value": "Silvally"},)),
    Trigger("Pressure", "Tackle", "outcomes", "A",
            assertions=({"type": "pp_cost", "side": "B", "move": "Tackle", "value": 2},),
            control_assertions=({"type": "pp_cost", "side": "B", "move": "Tackle", "value": 1},)),
    Trigger("Trace", "Splash", "outcomes", target_ability="Overgrow",
            assertions=({"type": "ability", "side": "A", "value": "Overgrow"},),
            control_assertions=({"type": "ability", "side": "A", "value": "No Ability"},)),
    Trigger("Scrappy", "Tackle", target_species="Gastly", control_assertions=({"type": "immune", "side": "B"},)),
    Trigger("Mind's Eye", "Tackle", target_species="Gastly", control_assertions=({"type": "immune", "side": "B"},)),
    Trigger("Unaware", "Tackle", "less", "A", foe_setup="Swords Dance", label="incoming-boost"),
    Trigger("Unaware", "Water Gun", "greater", foe_setup="Amnesia", label="defensive-boost"),
    Trigger("Infiltrator", "Tackle", foe_setup="Reflect", label="screen"),
    Trigger("Long Reach", "Tackle", "less", target_species="Garchomp", target_ability="Rough Skin", measure_side="A"),
    Trigger("Magic Guard", "Tackle", "less", target_species="Garchomp", target_ability="Rough Skin", measure_side="A", label="contact"),
    Trigger("Rock Head", "Take Down", "less", measure_side="A"),
    Trigger("Magic Guard", "Take Down", "less", measure_side="A", label="recoil"),
    Trigger("Shield Dust", "Nuzzle", side="A", blocked_status="par"),
    Trigger("Cloud Nine", "Flamethrower", "less", setup="Sunny Day"),
    Trigger("Air Lock", "Flamethrower", "less", setup="Sunny Day"),
    Trigger("Flower Gift", "Tackle", setup="Sunny Day", label="attack"),
    Trigger("Hadron Engine", "Water Gun", label="special-attack"),
    Trigger("Orichalcum Pulse", "Tackle", label="attack"),
    Trigger("Protosynthesis", "Tackle", setup="Sunny Day", owner_species="Brute Bonnet"),
    Trigger("Quark Drive", "Tackle", setup="Electric Terrain", owner_species="Iron Hands"),
    Trigger("Sword of Ruin", "Tackle"),
    Trigger("Beads of Ruin", "Water Gun"),
    Trigger("Tablets of Ruin", "Tackle", "less", "A"),
    Trigger("Vessel of Ruin", "Water Gun", "less", "A"),
    Trigger("Chlorophyll", "Payback", "less", setup="Sunny Day", owner_species="Bellsprout", target_level=50, label="order"),
    Trigger("Swift Swim", "Payback", "less", setup="Rain Dance", owner_species="Lotad", target_level=50, label="order"),
    Trigger("Sand Rush", "Payback", "less", setup="Sandstorm", owner_species="Sandshrew", target_level=50, label="order"),
    Trigger("Slush Rush", "Payback", "less", setup="Snowscape", owner_species="Sandshrew-Alola", target_level=50, label="order"),
    Trigger("Surge Surfer", "Payback", "less", setup="Electric Terrain", owner_species="Raichu-Alola", label="order"),
    Trigger("Quick Feet", "Payback", "less", status="psn", owner_species="Ursaring", target_level=50, label="order"),
    Trigger("Unburden", "Payback", "less", hp=.35, item="Oran Berry", owner_species="Drifloon", target_level=70, label="order"),
    Trigger("Chlorophyll", "Payback", "equal", owner_species="Bellsprout", target_level=50, label="no-weather"),
    Trigger("Swift Swim", "Payback", "equal", owner_species="Lotad", target_level=50, label="no-weather"),
    Trigger("Sand Rush", "Payback", "equal", owner_species="Sandshrew", target_level=50, label="no-weather"),
    Trigger("Slush Rush", "Payback", "equal", owner_species="Sandshrew-Alola", target_level=50, label="no-weather"),
    Trigger("Surge Surfer", "Payback", "equal", owner_species="Raichu-Alola", label="no-terrain"),
    Trigger("Quick Feet", "Payback", "equal", owner_species="Ursaring", target_level=50, label="healthy"),
    Trigger("Unburden", "Payback", "equal", item="Oran Berry", owner_species="Drifloon", target_level=70, label="no-consumption"),
    *(Trigger(ability, "Splash", "outcomes",
              assertions=({"type": kind, "value": value},),
              control_assertions=({"type": kind, "value": "None"},))
      for ability, kind, value in (
          ("Drought", "weather", "sunnyday"), ("Drizzle", "weather", "raindance"),
          ("Sand Stream", "weather", "sandstorm"), ("Snow Warning", "weather", "snow"),
          ("Desolate Land", "weather", "desolateland"), ("Primordial Sea", "weather", "primordialsea"),
          ("Delta Stream", "weather", "deltastream"), ("Orichalcum Pulse", "weather", "sunnyday"),
          ("Electric Surge", "terrain", "electricterrain"), ("Grassy Surge", "terrain", "grassyterrain"),
          ("Misty Surge", "terrain", "mistyterrain"), ("Psychic Surge", "terrain", "psychicterrain"),
          ("Hadron Engine", "terrain", "electricterrain"),
      )),
)


def fixtures(trigger):
    """Build native-carrier fixtures without changing any running battle state."""
    from pokemon import dex

    if trigger.direction not in {"greater", "less", "equal", "outcomes"} or (trigger.direction == "outcomes" and not trigger.assertions):
        raise ValueError("Outcome comparisons require explicit variant assertions.")
    if trigger.turn_repeats not in range(1, 5) or (trigger.turn_repeats > 1 and (
            not trigger.probabilistic or trigger.setup or trigger.foe_setup or trigger.arming_attack or trigger.situation)):
        raise ValueError("Repeated chance windows require one simple, bounded qualifying action.")

    carriers = {}
    abilities = {key(name): name for name, _ in unique_entries(dex.ABILITYDEX)}
    for name, species in unique_entries(dex.POKEDEX):
        for ability in species.raw.get("abilities", {}).values():
            carriers.setdefault(key(ability), name)
    ability = abilities.get(key(trigger.ability))
    if ability is None:
        raise ValueError("Ability is absent from this local dex: " + trigger.ability)
    owner = Mon(trigger.owner_species or carriers.get(key(ability), "Mew"), (trigger.move,), ability,
                hp_fraction=trigger.hp, item=trigger.item, level=50, status=trigger.status)
    foe = Mon(trigger.target_species, ("Splash",), trigger.target_ability,
              level=trigger.target_level, status=trigger.target_status, item=trigger.target_item, hp_fraction=trigger.target_hp)
    commands = []
    if trigger.side == "A":
        owner = replace(owner, level=100, moves=("Splash",))
        foe = Mon("Mew", tuple(dict.fromkeys((trigger.move, "Splash"))), trigger.target_ability,
                  level=50, item=trigger.target_item)
    if trigger.arming_attack:
        owner = replace(owner, moves=owner.moves + ("Splash",))
        foe = replace(foe, moves=(trigger.arming_attack, "Splash"))
        commands.append(turn("+attack Splash", "+attack " + trigger.arming_attack))
    if trigger.foe_setup:
        owner = replace(owner, moves=tuple(dict.fromkeys(owner.moves + ("Splash",))))
        foe = replace(foe, moves=tuple(dict.fromkeys(foe.moves + (trigger.foe_setup,))))
        commands.append(turn("+attack Splash", "+attack " + trigger.foe_setup))
    if trigger.setup:
        owner = replace(owner, moves=owner.moves + (trigger.setup,))
        commands.append(turn("+attack " + trigger.setup))
    commands.append(turn("+attack " + (trigger.move if trigger.side == "B" else "Splash"),
                         "+attack " + ("Splash" if trigger.side == "B" else trigger.move)))
    commands *= trigger.turn_repeats
    suffix = key(ability) + "-" + key(trigger.move) + "-" + trigger.side.lower()
    if trigger.label:
        suffix += "-" + key(trigger.label)
    foe_team = (foe, Mon("Wailord", ("Splash",))) if trigger.target_reserve else (foe,)
    case = DexCase("probe-" + suffix, "Paired ability trigger: " + ability,
                   (owner,), foe_team, tuple(commands), "dex", kind="regression", subject=ability, seed_each_turn=True,
                   pp_actor="B" if trigger.side == "A" else "A",
                   expected="The named incoming/outgoing outcome matches the declared comparison with the No Ability control.",
                   limitations=(("Only the declared stage, form or state outcomes are checked; other branches remain unverified."
                                 if trigger.direction == "outcomes" else
                                 "Directional damage comparison only; exact multipliers and other interactions remain unverified."),))
    if trigger.probabilistic:
        case = replace(case, limitations=case.limitations + (
            "Four ordinary qualifying opportunities test only whether this status branch is observed. "
            "Global ability randomness is not reseeded; no activation rate or distribution is established.",))
    setup_assertions = ()
    if trigger.setup:
        setup_raw = dex.MOVEDEX[key(trigger.setup)].raw
        setup_assertions = tuple({"type": name, "value": setup_raw[name]} for name in ("weather", "terrain") if setup_raw.get(name))
    if trigger.foe_setup:
        setup_raw = dex.MOVEDEX[key(trigger.foe_setup)].raw
        if setup_raw.get("boosts"):
            setup_assertions += ({"type": "boosts", "side": "B", "values": setup_raw["boosts"]},)
        if setup_raw.get("sideCondition"):
            setup_assertions += ({"type": "side_condition", "side": "B", "value": setup_raw["sideCondition"]},)
    case = replace(case, assertions=setup_assertions + trigger.assertions)
    if trigger.situation == "switch":
        owner = replace(owner, moves=("Splash",))
        case = replace(case, a=(owner, Mon("Eevee", ("Splash",), "No Ability")),
                       turns=(turn("+attack Splash"), turn("+switch 2")))
    elif trigger.situation:
        allowed = {"ally_power", "ally_damage", "grass_ally", "ally_heal"}
        if trigger.situation not in allowed or trigger.setup or trigger.arming_attack:
            raise ValueError("Unsupported doubles fixture situation.")
        owner = replace(owner, moves=("Splash",))
        ally = Mon("Bulbasaur" if trigger.situation == "grass_ally" else "Mew",
                   (trigger.move if trigger.situation == "ally_power" else "Splash",), "No Ability",
                   level=owner.level, hp_fraction=.4 if trigger.situation == "ally_heal" else 1.0)
        if trigger.situation == "ally_power":
            commands = (("a", "+attack A1 Splash"), ("a", "+attack A2 " + trigger.move + " B1"),
                        ("b", "+attack B1 Splash"), ("b", "+attack B2 Splash"))
        elif trigger.situation == "ally_heal":
            commands = (("a", "+attack A1 Splash"), ("a", "+attack A2 Splash"),
                        ("b", "+attack B1 Splash"), ("b", "+attack B2 Splash"))
        else:
            commands = (("a", "+attack A1 Splash"), ("a", "+attack A2 Splash"),
                        ("b", "+attack B1 " + trigger.move + " A2"), ("b", "+attack B2 Splash"))
        case = replace(case, a=(owner, ally), b=(foe, Mon("Chansey", ("Splash",), "No Ability", level=100)),
                       turns=(commands,), mode="double")
    control = replace(case, key="control-" + suffix, a=(replace(owner, ability="No Ability"),),
                      assertions=setup_assertions + trigger.control_assertions,
                      expected="Identical fixture and normal commands with the holder's ability removed.")
    control = replace(control, a=(replace(case.a[0], ability="No Ability"),) + case.a[1:])
    if trigger.blocked_status:
        control = replace(control, pp_actor="B", assertions=control.assertions + ({"type": "status", "side": "A", "value": trigger.blocked_status},))
    return control, case


def hp_loss(result, side, index=0):
    """Measure final attack-turn damage, excluding earlier weather setup turns."""
    states = result["snapshots"]
    return mon(states[-2], side, index)["hp"] - mon(states[-1], side, index)["hp"]


def evidence_hash(output, case_key):
    """Bind a comparison to the exact retained real-login observations."""
    return hashlib.sha256((output / "evidence" / (case_key + ".json.gz")).read_bytes()).hexdigest()


def run(output, selected=None):
    """Execute safe independent pairs and persist a separate proof index."""
    path = output / "ability-probes.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    previous = {row["key"]: row for row in rows}
    runner = DexRunner(output / "manifest.json")
    with pilot.run_lock(output):
        try:
            for label in ("staff", "a", "b"):
                runner.clients[label].open()
            runner.api = pilot.StaffAPI(runner.clients["staff"], runner.manifest, pilot.REPO / "tools/qa/live_dex_server.py")
            runner.clean()
            for trigger in TRIGGERS:
                control, variant = fixtures(trigger)
                if selected and key(trigger.ability) not in selected:
                    continue
                if not selected and variant.key in previous:
                    continue
                row = {"key": variant.key, "ability": trigger.ability, "trigger": asdict(trigger),
                       "positive_trigger": trigger.positive_trigger,
                       "status": "needs_diagnosis", "started_utc": now()}
                baseline = runner.run_case(control)
                if baseline["status"] not in {"smoke_completed", "outcome_verified"}:
                    row["error"] = "Control was not a clean real-login execution: " + baseline.get("error", baseline["status"])
                else:
                    measured_side = trigger.measure_side or trigger.side
                    damage = hp_loss(baseline, measured_side, trigger.index)
                    expectation = None
                    if trigger.blocked_status:
                        expectation = {"type": "not_status", "side": "A", "value": trigger.blocked_status}
                    elif trigger.direction != "outcomes":
                        expectation = {"type": "hp_loss_range", "side": measured_side, "index": trigger.index}
                        if trigger.direction == "greater":
                            expectation["minimum"] = damage + 1
                        elif trigger.direction == "equal":
                            expectation.update(minimum=damage, maximum=damage)
                        else:
                            expectation["maximum"] = damage - 1
                    if expectation is not None:
                        variant = replace(variant, assertions=variant.assertions + (expectation,))
                    actual = runner.run_case(variant)
                    row.update(control_loss=damage, actual_loss=hp_loss(actual, measured_side, trigger.index) if len(actual["snapshots"]) >= 2 else None,
                               control_key=control.key, actual_key=variant.key,
                               control_sha256=evidence_hash(output, control.key), actual_sha256=evidence_hash(output, variant.key))
                    if trigger.blocked_status and actual["snapshots"]:
                        row.update(control_status=mon(baseline["snapshots"][-1]).get("status"),
                                   actual_status=mon(actual["snapshots"][-1]).get("status"))
                    row["status"] = actual["status"]
                    if probability_window_unobserved(trigger, actual):
                        row["status"] = "chance_not_observed"
                        row["probability_assessment"] = (
                            "A qualifying first hit was observed, but no requested status branch was observed in this bounded window. "
                            "This is inconclusive, not a proven mechanics defect or a probability-rate test.")
                    if "error" in actual:
                        row["error"] = actual["error"]
                    if "cleanup_error" in actual:
                        row["cleanup_error"] = actual["cleanup_error"]
                row["completed_utc"] = now()
                previous[variant.key] = row
                pilot.save(path, list(previous.values()))
                print(json.dumps(row, ensure_ascii=True), flush=True)
                write_report(output, list(previous.values()))
                if row.get("cleanup_error") or baseline.get("cleanup_error"):
                    break
                safety = verify(output, audit=False, quiet=True)
                if not safety["protected_rows_unchanged"] or not safety["user_wip_unchanged"]:
                    raise RuntimeError("Protected records changed; stop ability comparisons.")
                if (output / "stop-requested").exists():
                    break
        finally:
            for client in runner.clients.values():
                client.close()
    return list(previous.values())


def probability_window_unobserved(trigger, result):
    """Keep a clean no-proc window inconclusive while retaining genuine failures."""
    if (not trigger.probabilistic or result.get("status") != "needs_diagnosis"
            or not result.get("error", "").startswith("Declared outcome not observed:")
            or result.get("server_errors") or result.get("cleanup_error") or len(result.get("snapshots", [])) < 2):
        return False
    statuses = [entry for entry in trigger.assertions if entry.get("type") == "status"]
    if len(statuses) != 1 or result["error"] != "Declared outcome not observed: " + json.dumps(statuses[0], sort_keys=True):
        return False
    first, second = result["snapshots"][:2]
    return mon(second, trigger.side)["hp"] < mon(first, trigger.side)["hp"]


def audit(output):
    """Recheck matched fixtures, retained checksums and directional outcomes."""
    rows = json.loads((output / "ability-probes.json").read_text(encoding="utf-8"))
    errors, audited = [], 0
    from tools.qa.live_dex_cases import from_dict

    for row in rows:
        if row["status"] != "outcome_verified":
            continue
        try:
            records = []
            for prefix in ("control", "actual"):
                case_key = row[prefix + "_key"]
                assert evidence_hash(output, case_key) == row[prefix + "_sha256"], "Evidence checksum changed."
                with gzip.open(output / "evidence" / (case_key + ".json.gz"), "rt", encoding="utf-8") as stream:
                    record = json.load(stream)
                result = evaluate(from_dict(record["case"]), record["snapshots"], record["outputs"])
                assert result["status"] in {"outcome_verified", "smoke_completed"}
                assert record["cleanup"]["room_clear"] and record["cleanup"]["locks_clear"]
                records.append(record)
            left, right = (dict(record["case"]) for record in records)
            for name in ("key", "expected", "assertions", "pp_actor"):
                left.pop(name)
                right.pop(name)
            left["a"][0]["ability"] = right["a"][0]["ability"]
            assert left == right, "Control differs in more than the tested ability and assertion."
            assert records[0]["seed"] == records[1]["seed"]
            audited += 1
        except Exception as error:
            errors.append({"key": row["key"], "error": str(error)})
    result = {"audited_pairs": audited, "errors": errors}
    pilot.save(output / "ability-probes-audit.json", result)
    return result


def write_report(output, rows):
    """Describe exact trigger proof and unresolved comparisons separately."""
    counts = Counter(row["status"] for row in rows)
    lines = ["# Paired real-login ability triggers", "", f"{len(rows)}/{len(TRIGGERS)} comparisons attempted. {dict(counts)}.", "",
             "Each pair changes only the tested holder's ability. Teams, normal commands, stats, HP, items, status and battle seed match. "
             "A pass proves only the declared damage/status/state outcome. Damage comparisons do not establish exact multipliers or all ability interactions. "
             "For state-outcome rows the numeric columns retain HP loss for context; the saved case contains the actual stage, volatile, PP or ability assertions.", "",
             "Chance windows require a directly observed qualifying hit. `chance_not_observed` is an inconclusive bounded window, "
             "not a mechanics failure or a probability-rate measurement. Callback, cleanup and other outcome errors retain their failure status.", "",
             "| Ability | Trigger and comparison | Control | Ability | Result |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        trigger = row["trigger"]
        relation = "prevents " + trigger["blocked_status"] if trigger.get("blocked_status") else trigger["direction"]
        if relation == "outcomes":
            relation = "declared state outcomes"
        control = row.get("control_status") or "clear" if "control_status" in row else row.get("control_loss", "-")
        actual = row.get("actual_status") or "clear" if "actual_status" in row else row.get("actual_loss", "-")
        measured = trigger.get("measure_side") or trigger["side"]
        path = "incoming" if trigger["side"] == "A" else "outgoing"
        lines.append(f"| {row['ability']} | {trigger['move']} / {path}, HP side {measured} / {relation} | {control} | {actual} | {row['status']} |")
    (output / "ability-probes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    """Run or audit paired triggers in an already prepared local QA run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ability", action="append", default=[])
    parser.add_argument("--rerun-all", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(pilot.ARTIFACTS) or output == pilot.ARTIFACTS:
        parser.error("Output must be an existing run inside .codex-artifacts.")
    if args.action == "run":
        selected = {key(trigger.ability) for trigger in TRIGGERS} if args.rerun_all else {key(name) for name in args.ability}
        run(output, selected)
    else:
        result = audit(output)
        print(json.dumps(result))
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
