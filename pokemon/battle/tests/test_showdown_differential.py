"""Differential validation against the local Pokemon Showdown checkout."""

from __future__ import annotations

import json

import pytest

from .differential import run_fusion_scenario, run_showdown_scenario


def _normalize_for_scenario(scenario, snapshots):
    normalized = json.loads(json.dumps(snapshots))
    ignore_all_hp = scenario.get("ignore_hp")
    ignore_hp_sides = set(scenario.get("ignore_hp_sides", []) or [])
    if not ignore_all_hp and not ignore_hp_sides:
        return normalized
    for snapshot in normalized:
        for side in snapshot.get("sides", []):
            if not ignore_all_hp and side.get("name") not in ignore_hp_sides:
                continue
            for active in side.get("active", []):
                active.pop("hp", None)
                active.pop("maxhp", None)
    return normalized


SCENARIOS = [
    {
        "name": "substitute-and-calm-mind",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["substitute", "calmmind"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move substitute", "p2": "move recover"},
            {"p1": "move calmmind", "p2": "move recover"},
        ],
    },
    {
        "name": "electric-type-blocks-thunder-wave",
        "p1": {
            "team": [
                {
                    "species": "Raichu",
                    "ability": "Static",
                    "moves": ["thunderwave"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Pikachu",
                    "ability": "Static",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move thunderwave", "p2": "move recover"},
        ],
    },
    {
        "name": "tailwind-side-condition",
        "p1": {
            "team": [
                {
                    "species": "Talonflame",
                    "ability": "Flame Body",
                    "moves": ["tailwind"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move tailwind", "p2": "move recover"},
        ],
    },
    {
        "name": "burn-applies-and-ticks",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["willowisp"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move willowisp", "p2": "move recover"},
        ],
    },
    {
        "name": "steel-type-blocks-toxic",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["toxic"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Steelix",
                    "ability": "Sturdy",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move toxic", "p2": "move recover"},
        ],
    },
    {
        "name": "insomnia-blocks-sleep",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["hypnosis"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Banette",
                    "ability": "Insomnia",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move hypnosis", "p2": "move recover"},
        ],
    },
    {
        "name": "spikes-side-condition",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["spikes"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move spikes", "p2": "move recover"},
        ],
    },
    {
        "name": "substitute-blocks-opponent-status",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["substitute", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "moves": ["willowisp"],
                }
            ]
        },
        "turns": [
            {"p1": "move substitute", "p2": "move willowisp"},
        ],
    },
    {
        "name": "spikes-damages-on-switch-in",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["spikes", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                },
                {
                    "species": "Pikachu",
                    "ability": "Static",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move spikes", "p2": "move recover"},
            {"p1": "move recover", "p2": "switch 2"},
        ],
    },
    {
        "name": "stealth-rock-damages-on-switch-in",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["stealthrock", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                },
                {
                    "species": "Charizard",
                    "ability": "Blaze",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move stealthrock", "p2": "move recover"},
            {"p1": "move recover", "p2": "switch 2"},
        ],
    },
    {
        "name": "toxic-spikes-poisons-on-switch-in",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["toxicspikes", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                },
                {
                    "species": "Eevee",
                    "ability": "Run Away",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move toxicspikes", "p2": "move recover"},
            {"p1": "move recover", "p2": "switch 2"},
        ],
    },
    {
        "name": "u-turn-switches-after-hitting-substitute",
        "p1": {
            "team": [
                {
                    "species": "Beedrill",
                    "ability": "Swarm",
                    "moves": ["uturn"],
                },
                {
                    "species": "Kakuna",
                    "ability": "Shed Skin",
                    "moves": ["harden"],
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Alakazam",
                    "ability": "Magic Guard",
                    "moves": ["substitute"],
                }
            ]
        },
        "turns": [
            {
                "p1": "move uturn",
                "p2": "move substitute",
                "post": {"p1": "switch 2"},
            },
        ],
    },
    {
        "name": "shed-tail-switches-and-passes-substitute",
        "p1": {
            "team": [
                {
                    "species": "Cyclizar",
                    "ability": "Shed Skin",
                    "moves": ["shedtail"],
                },
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {
                "p1": "move shedtail",
                "p2": "move splash",
                "post": {"p1": "switch 2"},
            },
        ],
    },
    {
        "name": "double-edge-recoil-through-substitute",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["substitute", "doubleedge"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["nastyplot"],
                }
            ]
        },
        "turns": [
            {"p1": "move substitute", "p2": "move nastyplot"},
            {"p1": "move doubleedge", "p2": "move nastyplot"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "drain-punch-heals-based-on-substitute-damage",
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "ability": "Pressure",
                    "moves": ["substitute"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Zangoose",
                    "ability": "No Guard",
                    "moves": ["bellydrum", "drainpunch"],
                }
            ]
        },
        "turns": [
            {"p1": "move substitute", "p2": "move bellydrum"},
            {"p1": "move substitute", "p2": "move drainpunch"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "roar-forces-switch",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["roar"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                },
                {
                    "species": "Pikachu",
                    "ability": "Static",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move roar", "p2": "move splash"},
        ],
    },
    {
        "name": "whirlwind-forces-switch",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["whirlwind"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Eevee",
                    "ability": "Run Away",
                    "moves": ["recover"],
                },
                {
                    "species": "Raichu",
                    "ability": "Static",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move whirlwind", "p2": "move recover"},
        ],
    },
    {
        "name": "dragon-tail-damages-and-forces-switch",
        "p1": {
            "team": [
                {
                    "species": "Dragonite",
                    "ability": "Inner Focus",
                    "moves": ["dragontail"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Eevee",
                    "ability": "Run Away",
                    "moves": ["recover"],
                },
                {
                    "species": "Pikachu",
                    "ability": "Static",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move dragontail", "p2": "move recover"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "circle-throw-damages-and-forces-switch",
        "p1": {
            "team": [
                {
                    "species": "Poliwrath",
                    "ability": "Water Absorb",
                    "moves": ["circlethrow"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Eevee",
                    "ability": "Run Away",
                    "moves": ["recover"],
                },
                {
                    "species": "Pikachu",
                    "ability": "Static",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move circlethrow", "p2": "move recover"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "head-smash-recoil-ko",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["doubleedge"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move doubleedge", "p2": "move splash"},
        ],
    },
    {
        "name": "drain-punch-ko-heals-user",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["drainpunch"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move drainpunch", "p2": "move splash"},
        ],
    },
    {
        "name": "destiny-bond-trades-on-ko",
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "ability": "Magic Guard",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "moves": ["tackle"],
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "aftermath-trades-after-contact-ko",
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "rapid-spin-clears-own-hazards",
        "p1": {
            "team": [
                {
                    "species": "Starmie",
                    "ability": "Natural Cure",
                    "moves": ["rapidspin", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["spikes", "recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move recover", "p2": "move spikes"},
            {"p1": "move rapidspin", "p2": "move recover"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "defog-clears-hazards",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["spikes", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Scyther",
                    "ability": "Technician",
                    "moves": ["defog", "recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move spikes", "p2": "move recover"},
            {"p1": "move recover", "p2": "move defog"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "court-change-swaps-hazards",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["spikes", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Cinderace",
                    "ability": "Blaze",
                    "moves": ["courtchange", "recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move spikes", "p2": "move recover"},
            {"p1": "move recover", "p2": "move courtchange"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "poison-switch-clears-toxic-spikes",
        "p1": {
            "team": [
                {
                    "species": "Skarmory",
                    "ability": "Keen Eye",
                    "moves": ["toxicspikes", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Eevee",
                    "ability": "Run Away",
                    "moves": ["recover"],
                },
                {
                    "species": "Grimer",
                    "ability": "Stench",
                    "moves": ["recover"],
                },
            ]
        },
        "turns": [
            {"p1": "move toxicspikes", "p2": "move recover"},
            {"p1": "move recover", "p2": "switch 2"},
        ],
    },
    {
        "name": "sitrus-berry-consumes-after-hit",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Sitrus Berry",
                    "moves": ["splash"],
                    "hp_percent": 51,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "focus-sash-prevents-ohko",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["psystrike"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "item": "Focus Sash",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move psystrike", "p2": "move splash"},
        ],
    },
    {
        "name": "choice-band-locks-user-into-first-move",
        "known_gap": "Showdown rejects illegal disabled-move choices before turn resolution.",
        "p1": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Choice Band",
                    "moves": ["tackle", "growl"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move recover"},
            {"p1": "move growl", "p2": "move recover"},
        ],
    },
    {
        "name": "choice-lock-clears-after-item-removal",
        "p1": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Choice Band",
                    "moves": ["tackle", "growl"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["knockoff", "recover"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move knockoff"},
            {"p1": "move growl", "p2": "move recover"},
        ],
        "ignore_hp": True,
    },
    {
        "name": "rocky-helmet-damages-contact-user",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Rocky Helmet",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "leftovers-heals-at-end-of-turn",
        "p1": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Leftovers",
                    "moves": ["splash"],
                    "hp_percent": 80,
                }
            ]
        },
        "turns": [
            {"p1": "move splash", "p2": "move splash"},
        ],
    },
    {
        "name": "black-sludge-damages-non-poison-holder",
        "p1": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "moves": ["splash"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Black Sludge",
                    "moves": ["splash"],
                    "hp_percent": 80,
                }
            ]
        },
        "turns": [
            {"p1": "move splash", "p2": "move splash"},
        ],
    },
    {
        "name": "focus-sash-only-saves-once",
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "moves": ["psystrike"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Magikarp",
                    "ability": "Swift Swim",
                    "item": "Focus Sash",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move psystrike", "p2": "move splash"},
            {"p1": "move psystrike", "p2": "move splash"},
        ],
    },
    {
        "name": "aftermath-does-not-trigger-without-ko",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "life-orb-recoils-after-damaging-hit",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "ability": "Pressure",
                    "item": "Life Orb",
                    "moves": ["swift"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move swift", "p2": "move splash"},
        ],
    },
    {
        "name": "knock-off-prevents-leftovers-heal",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["knockoff"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Leftovers",
                    "moves": ["splash"],
                    "hp_percent": 80,
                }
            ]
        },
        "turns": [
            {"p1": "move knockoff", "p2": "move splash"},
        ],
    },
    {
        "name": "pickpocket-steals-contact-item",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "item": "Leftovers",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Sneasel",
                    "ability": "Pickpocket",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "pickpocket-does-not-trigger-on-immune-hit",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "item": "Leftovers",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Banette",
                    "ability": "Pickpocket",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "magician-steals-after-damaging-hit",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Delphox",
                    "ability": "Magician",
                    "moves": ["swift"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Leftovers",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move swift", "p2": "move splash"},
        ],
    },
    {
        "name": "life-orb-and-rocky-helmet-stack-on-user",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "item": "Life Orb",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Rocky Helmet",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "life-orb-aftermath-trade-on-ko",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "item": "Life Orb",
                    "moves": ["tackle"],
                    "hp": 60,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "rocky-helmet-aftermath-trade-on-ko",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                    "hp": 90,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "item": "Rocky Helmet",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "eject-pack-switches-on-intimidate-drop",
        "p1": {
            "team": [
                {
                    "species": "Gyarados",
                    "ability": "Intimidate",
                    "moves": ["splash"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "item": "Eject Pack",
                    "moves": ["splash"],
                },
                {
                    "species": "Blissey",
                    "ability": "Natural Cure",
                    "moves": ["splash"],
                },
            ]
        },
        "setup_post": {"p2": "switch 2"},
        "turns": [],
    },
    {
        "name": "weakness-policy-boosts-on-super-effective-hit",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Raichu",
                    "ability": "Static",
                    "moves": ["shockwave"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Blastoise",
                    "ability": "Torrent",
                    "item": "Weakness Policy",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move shockwave", "p2": "move splash"},
        ],
    },
    {
        "name": "red-card-forces-attacker-switch",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                },
                {
                    "species": "Blissey",
                    "ability": "Natural Cure",
                    "moves": ["splash"],
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Red Card",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash", "post": {"p1": "switch 2"}},
        ],
    },
    {
        "name": "eject-button-switches-holder-on-hit",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "ability": "Immunity",
                    "item": "Eject Button",
                    "moves": ["splash"],
                },
                {
                    "species": "Blissey",
                    "ability": "Natural Cure",
                    "moves": ["splash"],
                },
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash", "post": {"p2": "switch 2"}},
        ],
    },
    {
        "name": "moxie-does-not-boost-through-aftermath-trade",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Gyarados",
                    "ability": "Moxie",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "beast-boost-does-not-boost-through-aftermath-trade",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Kartana",
                    "ability": "Beast Boost",
                    "moves": ["tackle"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move tackle", "p2": "move splash"},
        ],
    },
    {
        "name": "weakness-policy-does-not-trigger-on-ko",
        "ignore_hp_sides": ["p2"],
        "p1": {
            "team": [
                {
                    "species": "Raichu",
                    "ability": "Static",
                    "moves": ["shockwave"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Gyarados",
                    "ability": "Intimidate",
                    "item": "Weakness Policy",
                    "moves": ["splash"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move shockwave", "p2": "move splash"},
        ],
    },
    {
        "name": "destiny-bond-with-aftermath-trade",
        "p1": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "ability": "No Guard",
                    "moves": ["tackle"],
                    "hp": 1,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "destiny-bond-with-life-orb-trade",
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "ability": "Magic Guard",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "item": "Life Orb",
                    "moves": ["tackle"],
                    "hp": 20,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "destiny-bond-with-life-orb-noncontact-trade",
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Blastoise",
                    "item": "Life Orb",
                    "moves": ["watergun"],
                    "hp": 30,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move watergun"},
        ],
    },
    {
        "name": "destiny-bond-and-rocky-helmet-trade",
        "ignore_hp_sides": ["p1"],
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "moves": ["destinybond"],
                    "item": "Rocky Helmet",
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "moves": ["tackle"],
                    "hp": 40,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "life-orb-contact-into-rocky-helmet-and-destiny-bond",
        "ignore_hp_sides": ["p1"],
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "moves": ["destinybond"],
                    "item": "Rocky Helmet",
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "moves": ["tackle"],
                    "item": "Life Orb",
                    "hp": 40,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "life-orb-contact-into-aftermath-and-destiny-bond",
        "ignore_hp_sides": ["p1"],
        "p1": {
            "team": [
                {
                    "species": "Electrode",
                    "ability": "Aftermath",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "moves": ["tackle"],
                    "item": "Life Orb",
                    "hp": 40,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move tackle"},
        ],
    },
    {
        "name": "destiny-bond-does-not-trigger-on-recoil-only",
        "ignore_hp_sides": ["p1"],
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "moves": ["destinybond"],
                    "hp": 1,
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Machamp",
                    "moves": ["doubleedge"],
                    "hp": 5,
                }
            ]
        },
        "turns": [
            {"p1": "move destinybond", "p2": "move doubleedge"},
        ],
    },
    {
        "name": "taunt-forces-damaging-move-followup",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "moves": ["taunt", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Blissey",
                    "moves": ["recover", "tackle"],
                }
            ]
        },
        "turns": [
            {"p1": "move taunt", "p2": "move recover"},
            {"p1": "move recover", "p2": "move tackle"},
        ],
    },
    {
        "name": "encore-keeps-last-move-usable",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Alakazam",
                    "moves": ["recover", "encore"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Blissey",
                    "moves": ["recover", "tackle"],
                }
            ]
        },
        "turns": [
            {"p1": "move recover", "p2": "move recover"},
            {"p1": "move encore", "p2": "move recover"},
            {"p1": "move recover", "p2": "move recover"},
        ],
    },
    {
        "name": "torment-forces-alternate-move",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "moves": ["torment", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "moves": ["tackle", "doubleedge"],
                }
            ]
        },
        "turns": [
            {"p1": "move torment", "p2": "move tackle"},
            {"p1": "move recover", "p2": "move doubleedge"},
        ],
    },
    {
        "name": "disable-blocks-last-move-then-allows-alternate",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Mewtwo",
                    "moves": ["disable", "recover"],
                }
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "moves": ["tackle", "growl"],
                }
            ]
        },
        "turns": [
            {"p1": "move recover", "p2": "move tackle"},
            {"p1": "move disable", "p2": "move tackle"},
            {"p1": "move recover", "p2": "move growl"},
        ],
    },
    {
        "name": "wish-heals-replacement-on-switch",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Blissey",
                    "moves": ["wish", "recover"],
                },
                {
                    "species": "Mewtwo",
                    "moves": ["recover"],
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "moves": ["tackle"],
                }
            ]
        },
        "turns": [
            {"p1": "move wish", "p2": "move tackle"},
            {"p1": "switch 2", "p2": "move tackle"},
        ],
    },
    {
        "name": "healing-wish-heals-replacement",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Latias",
                    "moves": ["healingwish"],
                    "hp": 1,
                },
                {
                    "species": "Mewtwo",
                    "moves": ["recover"],
                    "hp": 100,
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move healingwish", "p2": "move splash", "post": {"p1": "switch 2"}},
        ],
    },
    {
        "name": "lunar-dance-restores-replacement",
        "ignore_hp": True,
        "p1": {
            "team": [
                {
                    "species": "Cresselia",
                    "moves": ["lunardance"],
                    "hp": 1,
                },
                {
                    "species": "Mewtwo",
                    "moves": ["recover", "tackle"],
                    "hp": 100,
                },
            ]
        },
        "p2": {
            "team": [
                {
                    "species": "Snorlax",
                    "moves": ["splash"],
                }
            ]
        },
        "turns": [
            {"p1": "move lunardance", "p2": "move splash", "post": {"p1": "switch 2"}},
        ],
    },
]


@pytest.mark.parametrize(
    "scenario",
    [scenario for scenario in SCENARIOS if not scenario.get("known_gap")],
    ids=lambda item: item["name"],
)
def test_fusion_matches_showdown_for_scripted_scenario(scenario):
    fusion = _normalize_for_scenario(scenario, run_fusion_scenario(scenario))
    showdown = _normalize_for_scenario(scenario, run_showdown_scenario(scenario))

    assert fusion == showdown, (
        f"Differential mismatch for {scenario['name']}\n"
        f"Fusion:\n{json.dumps(fusion, indent=2, sort_keys=True)}\n"
        f"Showdown:\n{json.dumps(showdown, indent=2, sort_keys=True)}"
    )
