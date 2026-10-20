"""Small, explicit scenarios for logged-in local battle acceptance.

These are behavioral expectations, not a claim of exhaustive dex coverage.
Teams are staff-prepared fixtures; battle choices must travel over Telnet.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Mon:
    """A real owned Pokemon to prepare before a scenario."""

    species: str
    moves: tuple[str, ...]
    ability: str = ""
    hp_fraction: float = 1.0
    item: str = ""
    level: int = 50
    gender: str = "M"
    status: str = ""


@dataclass(frozen=True)
class Scenario:
    """One independent battle, its normal-player commands and outcome check."""

    key: str
    purpose: str
    a: tuple[Mon, ...]
    b: tuple[Mon, ...]
    turns: tuple[tuple[tuple[str, str], ...], ...]
    check: str
    mode: str = "single"
    opponent: str = "Rattata"
    seed: int = 104729
    expected: str = ""
    inventory: dict[str, int] = field(default_factory=dict)
    failure_conditions: tuple[str, ...] = (
        "Check PP, move and target legality, accuracy/evasion, immunities, ability suppression, status prevention, protection and field effects.",
        "Check whether a charging/recharge turn or an intentionally ineffective move explains the result.",
    )


IDLE = Mon("Magikarp", ("Splash",), "Swift Swim")
EEVEE = Mon("Eevee", ("Tackle", "Growl", "Tail Whip", "Protect"), "Run Away")


def turn(a, b="+attack Splash"):
    """Declare both players' choices for a singles turn."""
    return (("a", a), ("b", b))


SCENARIOS = (
    Scenario("01-damage-pp", "Damaging move and PP consumption", (EEVEE,), (IDLE,),
             (turn("+attack Tackle"),), "damage_pp",
             expected="Tackle reduces the opponent's HP and consumes exactly one PP."),
    Scenario("02-type-immunity", "Normal attack versus Ghost", (EEVEE,),
             (Mon("Gastly", ("Lick",), "Levitate"),),
             (turn("+attack Tackle", "+attack Lick"),), "type_immunity",
             expected="Normal/Ghost attacks do no damage to their immune opponents."),
    Scenario("03-stat-drop", "Growl lowers Attack", (EEVEE,), (EEVEE,),
             (turn("+attack Growl", "+attack Tail Whip"),), "stat_drop",
             expected="Growl lowers the target's Attack stage by one."),
    Scenario("04-self-boost", "Swords Dance raises Attack", 
             (Mon("Scyther", ("Swords Dance",), "Swarm"),), (IDLE,),
             (turn("+attack Swords Dance"),), "self_boost",
             expected="Swords Dance raises its user's Attack stage by two."),
    Scenario("05-recover", "Recover restores half maximum HP",
             (Mon("Alakazam", ("Recover",), "Synchronize", .25),), (IDLE,),
             (turn("+attack Recover"),), "recover",
             expected="Recover restores floor(maximum HP / 2), capped at maximum HP."),
    Scenario("06-burn", "Will-O-Wisp applies burn and residual damage",
             (Mon("Vulpix", ("Will-O-Wisp",), "Flash Fire"),), (IDLE,),
             (turn("+attack Will-O-Wisp"),), "burn",
             expected="The target is burned and loses HP during the turn."),
    Scenario("07-paralysis", "Thunder Wave applies paralysis",
             (Mon("Pikachu", ("Thunder Wave",), "Static"),), (IDLE,),
             (turn("+attack Thunder Wave"),), "paralysis",
             expected="The target's status becomes paralysis."),
    Scenario("08-protect", "Protect prevents an incoming hit", (EEVEE,), (EEVEE,),
             (turn("+attack Protect", "+attack Tackle"),), "protect",
             expected="Protect prevents Tackle from reducing its user's HP."),
    Scenario("09-water-absorb", "Water Absorb prevents damage and heals",
             (Mon("Vaporeon", ("Tail Whip",), "Water Absorb", .5),),
             (Mon("Squirtle", ("Water Gun",), "Torrent"),),
             (turn("+attack Tail Whip", "+attack Water Gun"),), "water_absorb",
             expected="Water Gun causes no damage and heals floor(maximum HP / 4)."),
    Scenario("10-levitate", "Levitate blocks a Ground attack",
             (Mon("Gastly", ("Spite",), "Levitate"),),
             (Mon("Sandshrew", ("Mud-Slap",), "Sand Veil"),),
             (turn("+attack Spite", "+attack Mud-Slap"),), "levitate",
             expected="Mud-Slap consumes PP but causes no damage to the Levitate holder."),
    Scenario("11-flash-fire", "Flash Fire absorbs a Fire attack",
             (Mon("Vulpix", ("Tail Whip", "Ember"), "Flash Fire"),),
             (Mon("Charmander", ("Ember", "Growl"), "Blaze"),),
             (turn("+attack Tail Whip", "+attack Ember"),
              turn("+attack Ember", "+attack Growl")), "flash_fire",
             expected="Incoming Ember causes no damage; Flash Fire stays armed and its user attacks with Ember next turn.",
             failure_conditions=("Only an incoming Fire move arms the boost; it applies only to the holder's Fire attacks.",
                                 "The boost legitimately expires on switching out, fainting or loss/suppression of the ability.")),
    Scenario("12-intimidate", "Intimidate triggers on battle entry",
             (Mon("Arcanine", ("Leer",), "Intimidate"),), (EEVEE,),
             (), "intimidate", expected="The opposing Pokemon starts at Attack stage -1."),
    Scenario("13-leftovers", "Leftovers heals at end of turn",
             (Mon("Snorlax", ("Amnesia",), "Immunity", .5, "Leftovers"),), (IDLE,),
             (turn("+attack Amnesia"),), "leftovers",
             expected="Leftovers restores floor(maximum HP / 16) at end of turn."),
    Scenario("14-stealth-rock", "Stealth Rock damages a switching target",
             (Mon("Onix", ("Stealth Rock", "Harden"), "Rock Head"),),
             (IDLE, Mon("Charizard", ("Growl",), "Blaze")),
             (turn("+attack Stealth Rock"), turn("+attack Harden", "+switch 2")),
             "stealth_rock", expected="Switching Charizard into Stealth Rock removes half its maximum HP."),
    Scenario("15-switch", "Canonical party-slot switching",
             (EEVEE, Mon("Pikachu", ("Growl",), "Static")), (IDLE,),
             (turn("+switch 2"),), "switch", expected="Party slot 2 becomes active and both owned Pokemon remain present."),
    Scenario("16-two-turn-fly", "Fly charges then strikes",
             (Mon("Pidgey", ("Fly",), "Keen Eye"),), (IDLE,),
             (turn("+attack Fly"), turn("+attack Fly")), "fly",
             expected="Fly charges without damage, strikes on turn two, clears its charge, and consumes one PP in total.",
             failure_conditions=("No damage on Fly's charging turn is expected.",
                                 "Fly has 95 percent base accuracy and can legitimately miss.",
                                 "Protection, invulnerability, status prevention or grounding field effects can legitimately block the strike.")),
    Scenario("17-doubles-surf", "Surf hits foes and activates an ally's Water Absorb",
             (Mon("Blastoise", ("Surf",), "Torrent"),
              Mon("Vaporeon", ("Haze",), "Water Absorb", .5)),
             (IDLE, Mon("Gyarados", ("Splash",), "Moxie")),
             ((("a", "+attack A1 Surf"), ("a", "+attack A2 Haze"),
               ("b", "+attack B1 Splash"), ("b", "+attack B2 Splash")),),
             "doubles", mode="double",
             expected="Both opponents lose HP and the ally heals one quarter maximum HP without taking Surf damage."),
    Scenario("18-wild-flee", "Run Away in a generated wild battle",
             (Mon("Rattata", ("Tackle",), "Run Away"),), (),
             ((("a", "+flee"),),), "flee", mode="wild",
             expected="The ordinary player escapes and their battle locks clear."),
    Scenario("19-wild-capture", "Master Ball capture and canonical storage placement",
             (EEVEE,), (), ((("a", "+item Master Ball"),),), "capture", mode="wild",
             expected="One new owned Rattata is placed, the ball is consumed, and the battle ends.",
             inventory={"Master Ball": 1}),
    Scenario("20-trainer-no-flee", "Flee restriction in a generated trainer battle",
             (EEVEE,), (), ((("a", "+flee"),),), "trainer_flee", mode="trainer",
             expected="Fleeing does not end a trainer battle; normal concession can end it."),
)
