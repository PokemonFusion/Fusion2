"""Semantic local-login probes for the formerly smoke-only move catalog.

Expected effects are grounded in the checked-in reference move data. Preparation
uses disposable owned Pokémon; all tested actions use ordinary player commands.
"""

from dataclasses import dataclass, replace

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa.live_dex_cases import DexCase, Mon, key, turn


@dataclass(frozen=True)
class EffectProbe:
    """One catalog subject, independent stimuli, and observable effect rules."""

    subject: str
    cases: tuple[DexCase, ...]
    rules: tuple[dict, ...] = ()
    fixture: tuple[dict, ...] = ()
    chance: bool = False
    scope: str = "Only the declared effect and prepared context."


def check(kind, side="A", **values):
    """Declare a normal runner assertion."""
    return {"type": kind, "side": side, **values}


def actor(moves, species="Mew", **values):
    """Prepare ordinary canonical stats, never hand-made battle stat values."""
    return Mon(species, tuple(moves), ability=values.pop("ability", "No Guard"), **values)


def idle(species="Wailord", **values):
    """Supply a durable idle target with no interfering ability."""
    return actor(("Splash",), species, ability="No Ability", level=values.pop("level", 100), **values)


def scenario(subject, a=None, b=None, turns=None, assertions=(), suffix="positive", mode="single"):
    """Keep each exact case and its subject explicit and serializable."""
    return DexCase("effect-" + key(subject) + "-" + suffix, "Actual effect: " + subject,
                   tuple(a or (actor((subject, "Splash")),)), tuple(b or (idle(),)),
                   tuple(turns or (turn("+attack " + subject),)), "dex", mode=mode,
                   kind="regression", subject=subject, assertions=tuple(assertions),
                   expected="Verify the declared observable effect, beyond PP/execution.",
                   limitations=("Prepared local QA fixtures; no claim of all interactions or natural learnsets.",))


def no_ability_probe():
    """Verify the placeholder's intended absence of an effect, with a control."""
    cases = []
    for index, ability in enumerate(("Run Away", "No Ability")):
        cases.append(scenario("No Ability", (actor(("Tackle",), ability=ability),),
                              turns=(turn("+attack Tackle"),),
                              assertions=(check("damage", "B"), check("immune")),
                              suffix="control" if index == 0 else "variant"))
    return EffectProbe("No Ability", tuple(cases), ({"type": "no_ability"},),
                       scope="Expected no-effect placeholder in PvP, compared with an ability whose escape effect is inactive in PvP; not a positive ability trigger.")


def probes():
    """Build independent actual effects, with controls for conditional behavior."""
    result = []

    def add(subject, a=None, b=None, turns=None, assertions=(), rules=(), **values):
        result.append(EffectProbe(subject, (scenario(subject, a, b, turns, assertions),), tuple(rules), **values))

    # Status cures include a benched party member where the move affects a team.
    for name in ("Aromatherapy", "Heal Bell"):
        add(name, a=(actor((name,), status="psn"), actor(("Splash",), "Eevee", status="par")),
            assertions=(check("not_status", value="psn"), check("not_status", index=1, value="par")),
            rules=({"type": "party_cure"},))
    add("Refresh", a=(actor(("Refresh",), status="psn"),), assertions=(check("not_status", value="psn"),))
    add("Take Heart", a=(actor(("Take Heart",), status="psn"),),
        assertions=(check("not_status", value="psn"), check("boosts", values={"spa": 1, "spd": 1})))
    add("Purify", a=(actor(("Purify",), hp_fraction=.2),), b=(idle(status="par"),),
        assertions=(check("not_status", "B", value="par"), check("heal")), rules=({"type": "heal_fraction", "numerator": 1, "denominator": 2},))
    add("Acupressure", rules=({"type": "one_random_boost", "amount": 2},))
    add("Belly Drum", assertions=(check("boosts", values={"atk": 6}),), rules=({"type": "hp_cost", "numerator": 1, "denominator": 2},))
    for name, values in (("Curse", {"atk": 1, "def": 1, "spe": -1}),
                         ("Venom Drench", {"atk": -1, "spa": -1, "spe": -1})):
        add(name, b=(idle(status="psn" if name == "Venom Drench" else ""),),
            assertions=(check("boosts", "B" if name == "Venom Drench" else "A", values=values),))
    add("Pain Split", a=(actor(("Pain Split",), hp_fraction=.25),), b=(idle(hp_fraction=.2),),
        rules=({"type": "pain_split"},))
    add("Strength Sap", a=(actor(("Strength Sap",), hp_fraction=.2),),
        assertions=(check("boosts", "B", values={"atk": -1}), check("heal")), rules=({"type": "strength_sap"},))
    add("Leech Seed", a=(actor(("Leech Seed", "Splash"), hp_fraction=.3),),
        turns=(turn("+attack Leech Seed"), turn("+attack Splash")),
        assertions=(check("damage", "B"), check("heal")), rules=({"type": "leech_seed"},))
    add("Nightmare", b=(idle(status="slp"),), assertions=(check("damage", "B"),),
        rules=({"type": "target_loss_fraction", "numerator": 1, "denominator": 4},))
    add("Octolock", a=(actor(("Octolock", "Splash")),),
        turns=(turn("+attack Octolock"), turn("+attack Splash")),
        assertions=(check("boosts", "B", values={"def": -2, "spd": -2}), check("volatile", "B", value="octolock")))
    for name, receiver, ability in (("Entrainment", "B", "Blaze"), ("Role Play", "A", "Overgrow"),
                                    ("Simple Beam", "B", "Simple"), ("Worry Seed", "B", "Insomnia")):
        add(name, a=(actor((name,), ability="Blaze"),), b=(actor(("Splash",), ability="Overgrow"),),
            assertions=(check("ability", receiver, value=ability),))
    add("Skill Swap", a=(actor(("Skill Swap",), ability="Blaze"),), b=(actor(("Splash",), ability="Overgrow"),),
        assertions=(check("ability", value="Overgrow"), check("ability", "B", value="Blaze")))
    # Doodle must affect both living allies, not just its user.
    doodle_commands = (("a", "+attack A1 Doodle B1"), ("a", "+attack A2 Splash"),
                       ("b", "+attack B1 Splash"), ("b", "+attack B2 Splash"))
    case = scenario("Doodle", (actor(("Doodle",)), actor(("Splash",), "Eevee", ability="No Ability")),
                    (actor(("Splash",), ability="Overgrow"), idle()), (doodle_commands,),
                    (check("ability", value="Overgrow"), check("ability", index=1, value="Overgrow")), mode="double")
    result.append(EffectProbe("Doodle", (case,)))
    for name in ("Trick", "Switcheroo"):
        add(name, a=(actor((name, "Splash"), item="Lagging Tail"),), b=(idle(item="Iron Ball"),),
            turns=(turn("+attack " + name), turn("+attack Splash")),
            assertions=(check("item", value="Iron Ball"), check("item", "B", value="Lagging Tail")),
            rules=({"type": "checkpoint_items", "a": "Iron Ball", "b": "Lagging Tail"},))
    add("Bestow", a=(actor(("Bestow",), item="Lagging Tail"),),
        assertions=(check("item", value=""), check("item", "B", value="Lagging Tail")))
    add("Corrosive Gas", b=(idle(item="Lagging Tail"),), assertions=(check("item", "B", value=""),))
    # Entry consumes the berry and heals above half HP, so the restored item
    # survives the turn. At .2 HP a second legal consumption hides restoration.
    add("Recycle", a=(actor(("Recycle",), item="Oran Berry", hp_fraction=.49),),
        assertions=(check("item", value="Oran Berry"),), rules=({"type": "recycle"},))
    add("Natural Gift", a=(actor(("Natural Gift",), item="Cheri Berry"),),
        assertions=(check("damage", "B"), check("item", value="")), rules=({"type": "executed_type", "value": "Fire"},))
    # Ability suppression has a functional consequence: Levitate no longer blocks Ground.
    add("Gastro Acid", a=(actor(("Gastro Acid", "Earthquake")),),
        b=(actor(("Splash",), "Weezing", ability="Levitate", level=100),),
        turns=(turn("+attack Gastro Acid"), turn("+attack Earthquake")), assertions=(check("damage", "B"),),
        rules=({"type": "gastro_acid"},))
    for name in ("Stockpile", "Spit Up", "Swallow"):
        turns = [turn("+attack Stockpile"), turn("+attack Stockpile")]
        assertions = [check("boosts", values={"def": 2, "spd": 2}, after_turn=2)]
        if name == "Stockpile":
            turns += [turn("+attack Stockpile"), turn("+attack Stockpile")]
            assertions.append(check("boosts", values={"def": 3, "spd": 3}))
        else:
            turns.append(turn("+attack " + name))
            assertions.append(check("boosts", values={"def": 0, "spd": 0}))
            assertions.append(check("damage", "B") if name == "Spit Up" else check("heal"))
        add(name, a=(actor(("Stockpile", name) if name != "Stockpile" else (name,), hp_fraction=.2 if name == "Swallow" else 1),),
            turns=turns, assertions=assertions, rules=({"type": "stockpile", "consumed": name != "Stockpile"},))
    for name in ("Power Trick", "Power Shift"):
        add(name, a=(actor((name,), "Shuckle"),), rules=({"type": "attack_defense_swap"},))
    # These moves expose gameplay restrictions; functional attempts are appended by the runner.
    for name in ("Block", "Mean Look", "Spider Web"):
        attempt = (("b", "+switch 2"), ("a", "+attack Splash"), ("b", "+attack Splash"))
        add(name, b=(idle(), idle("Eevee")), turns=(turn("+attack " + name), attempt),
            assertions=(check("active_species", "B", value="Wailord"),), rules=({"type": "blocked_switch"},))
    for name in ("Taunt", "Embargo", "Heal Block", "Imprison", "Torment", "Disable", "Encore"):
        first = {"Taunt": "Growl", "Embargo": "Splash", "Heal Block": "Recover", "Imprison": "Tackle",
                 "Torment": "Tackle", "Disable": "Tackle", "Encore": "Tackle"}[name]
        a_moves = (name, "Splash", "Tackle") if name == "Imprison" else (name, "Splash")
        b_moves = tuple(dict.fromkeys((first, "Splash", "Water Gun")))
        setup = (turn("+attack Splash", "+attack " + first),) if name in {"Disable", "Encore", "Torment"} else ()
        apply_turn = turn("+attack " + name, "+attack Tackle" if name in {"Torment", "Encore"} else "+attack Splash")
        blocked = "Water Gun" if name == "Encore" else first
        fallback = "Tackle" if name == "Encore" else "Water Gun"
        attempt = (("a", "+attack Splash"), ("b", "+attack " + blocked), ("b", "+attack " + fallback))
        allowed = "Tackle" if name == "Encore" else "Splash" if name == "Torment" else "Water Gun"
        allowed_turn = turn("+attack Splash", "+attack " + allowed)
        add(name, a=(actor(a_moves, level=100),),
            b=(actor(b_moves, "Chansey", ability="No Ability", hp_fraction=.4, item="Leftovers" if name == "Embargo" else ""),),
            turns=setup + (apply_turn,) + (() if name == "Embargo" else (attempt, allowed_turn)),
            rules=({"type": "restricted_command", "move": first, "effect": key(name)},),
            scope="Applied restriction plus a rejected ordinary command or forced allowed move; separate from a completed idle turn.")
    # Protect-like moves must stop damage this turn and let an ordinary later hit through.
    for name in ("Protect", "Detect", "Max Guard", "Baneful Bunker", "Burning Bulwark", "King's Shield", "Obstruct", "Silk Trap", "Spiky Shield"):
        values = [check("immune", after_turn=1), check("damage")]
        if name in {"Baneful Bunker", "Burning Bulwark"}:
            values.append(check("status", "B", value="psn" if name == "Baneful Bunker" else "brn", after_turn=1))
        if name in {"King's Shield", "Obstruct", "Silk Trap"}:
            stages = {"King's Shield": {"atk": -1}, "Obstruct": {"def": -2}, "Silk Trap": {"spe": -1}}[name]
            values.append(check("boosts", "B", values=stages, after_turn=1))
        if name == "Spiky Shield":
            values.append(check("damage", "B", after_turn=1))
        add(name, a=(actor((name, "Splash"), level=100),), b=(actor(("Tackle",), ability="No Ability"),),
            turns=(turn("+attack " + name, "+attack Tackle"), turn("+attack Splash", "+attack Tackle")), assertions=values)
    add("Endure", a=(actor(("Endure", "Splash"), "Abra", hp_fraction=.1),),
        b=(actor(("Tackle",), "Mewtwo", level=100),), turns=(turn("+attack Endure", "+attack Tackle"),),
        rules=({"type": "exact_hp", "value": 1},))
    for name in ("Fissure", "Guillotine", "Horn Drill"):
        add(name, b=(idle(level=50),), assertions=(check("hp_fraction", "B", minimum=0, maximum=0),),
            scope="Same-level nonimmune target; No Guard fixture guarantees accuracy but does not bypass level/type restrictions.")
    for name in ("Magnet Rise", "Telekinesis"):
        a = actor((name, "Splash"), "Gengar" if name == "Telekinesis" else "Mew", level=100)
        if name == "Telekinesis":
            a, b = actor((name, "Earthquake"), level=100), actor(("Splash",), "Pikachu", ability="No Ability", level=50)
            turns = (turn("+attack Telekinesis"), turn("+attack Earthquake"))
            values = (check("immune", "B"), check("volatile", "B", value="telekinesis"))
        else:
            b = actor(("Earthquake",), "Mew", ability="No Ability", level=50)
            turns = (turn("+attack Magnet Rise", "+attack Earthquake"),)
            values = (check("immune"), check("volatile", value="magnetrise"))
        add(name, a=(a,), b=(b,), turns=turns, assertions=values)
    for name, target, attack in (("Foresight", "Gengar", "Tackle"), ("Odor Sleuth", "Gengar", "Tackle"),
                                  ("Miracle Eye", "Umbreon", "Confusion")):
        add(name, a=(actor((name, attack)),), b=(idle(target),),
            turns=(turn("+attack " + name), turn("+attack " + attack)), assertions=(check("damage", "B"),))
    for name in ("Lock-On", "Mind Reader"):
        cases = []
        for index in (0, 1):
            first = name if index else "Splash"
            moves = (first, "Zap Cannon")
            assertions = (check("pp_cost", move="Zap Cannon", value=1),)
            if index:
                assertions += (check("damage", "B"), check("status", "B", value="par"))
            case = scenario(name, (actor(moves, ability="No Ability"),),
                            turns=(turn("+attack " + first), turn("+attack Zap Cannon")),
                            assertions=assertions, suffix="variant" if index else "control")
            cases.append(replace(case, seed_each_turn=True))
        result.append(EffectProbe(name, tuple(cases), ({"type": "accuracy_control"},), chance=True))
    for name in ("Destiny Bond", "Grudge"):
        add(name, a=(actor((name,), "Alakazam", hp_fraction=.01, level=100), actor(("Splash",), "Eevee")),
            b=(actor(("Water Gun",), level=100),), turns=(turn("+attack " + name, "+attack Water Gun"),),
            assertions=(check("hp_fraction", minimum=0, maximum=0, original=True),),
            rules=({"type": "destiny_bond" if name == "Destiny Bond" else "grudge"},))
    add("Assist", a=(actor(("Assist",)), actor(("Tackle",), "Eevee")),
        assertions=(check("damage", "B"),), rules=({"type": "called_move", "value": "Tackle"},))
    add("Copycat", a=(actor(("Copycat", "Splash")),), b=(actor(("Tackle", "Splash"), ability="No Ability", level=100),),
        turns=(turn("+attack Splash", "+attack Tackle"), turn("+attack Copycat", "+attack Tackle")),
        assertions=(check("damage", "B"),), rules=({"type": "called_move", "value": "Tackle"},))
    add("Nature Power", assertions=(check("damage", "B"),), rules=({"type": "called_move", "value": "Tri Attack"},))
    add("Metronome", a=(actor(("Metronome",), level=100),), b=(idle(level=100),),
        turns=(turn("+attack Metronome"),),
        assertions=(check("pp_cost", move="Metronome", value=1),), rules=({"type": "called_effect"},), chance=True,
        scope="A naturally selected called move must produce observed damage. Each bounded retry uses a fresh one-turn battle so a natural faint cannot invalidate later requested turns.")
    add("Instruct", a=(actor(("Instruct", "Splash"), level=100),),
        b=(actor(("Tackle",), level=100, ability="No Ability"),),
        turns=(turn("+attack Splash", "+attack Tackle"), turn("+attack Instruct", "+attack Tackle")),
        rules=({"type": "instruct"},))
    for name in ("Confuse Ray", "Supersonic", "Sweet Kiss", "Teeter Dance", "Attract"):
        a = actor((name, "Splash"), "Eevee", level=100, gender="M")
        b = actor(("Tackle",), "Chansey", ability="No Ability", gender="F", level=50)
        turns = (turn("+attack " + name, "+attack Tackle"),) + tuple(turn("+attack Splash", "+attack Tackle") for _ in range(6))
        add(name, a=(a,), b=(b,), turns=turns,
            rules=({"type": "infatuation" if name == "Attract" else "confusion"},), chance=True)
    # Conditional damage must respond to its actual input, not merely deal HP loss.
    for name in ("Crush Grip", "Wring Out", "Hard Press", "Flail", "Reversal", "Electro Ball", "Gyro Ball",
                 "Grass Knot", "Low Kick", "Heat Crash", "Heavy Slam", "Punishment", "Return", "Frustration", "Pika Papow", "Veevee Volley", "Trump Card"):
        cases, fixtures = [], []
        for index in (0, 1):
            a, b = actor((name, "Splash")), idle()
            turns = (turn("+attack " + name),)
            fixture = {}
            if name in {"Crush Grip", "Wring Out", "Hard Press"}:
                b = replace(b, hp_fraction=1 if index == 0 else .2)
            elif name in {"Flail", "Reversal"}:
                a = replace(a, hp_fraction=1 if index == 0 else .02)
            elif name in {"Electro Ball", "Gyro Ball"}:
                a, b = actor((name, "Agility", "Splash")), idle("Mew", level=50)
                turns = (turn("+attack " + ("Splash" if index == 0 else "Agility")), turn("+attack " + name))
            elif name in {"Grass Knot", "Low Kick", "Heat Crash", "Heavy Slam"}:
                a = actor((name, "Splash"), "Aggron" if name in {"Heat Crash", "Heavy Slam"} else "Mew")
                b = actor(("Autotomize", "Splash"), "Bronzong", ability="No Ability", level=50)
                turns = tuple(turn("+attack Splash", "+attack " + ("Splash" if index == 0 else "Autotomize")) for _ in range(3)) + (turn("+attack " + name),)
            elif name == "Punishment":
                b = actor(("Nasty Plot", "Splash"), "Wailord", ability="No Ability", level=100)
                turns = (turn("+attack Splash", "+attack " + ("Splash" if index == 0 else "Nasty Plot")), turn("+attack " + name))
            elif name in {"Return", "Frustration", "Pika Papow", "Veevee Volley"}:
                fixture = {"friendship": {"a": {"0": 0 if index == 0 else 255}}}
            elif name == "Trump Card":
                fixture = {"move_pp": {"a": {"0": {"Trump Card": 5 if index == 0 else 1}}}}
            case = scenario(name, (a,), (b,), turns, (check("damage", "B"),), suffix="control" if index == 0 else "variant")
            cases.append(replace(case, seed_each_turn=True))
            fixtures.append(fixture)
        greater = name not in {"Crush Grip", "Wring Out", "Hard Press", "Gyro Ball", "Grass Knot", "Low Kick", "Frustration"}
        result.append(EffectProbe(name, tuple(cases), ({"type": "damage_relation", "relation": "greater" if greater else "less",
                                                     "minimum_ratio": 1.5, "maximum_ratio": .75},), tuple(fixtures)))
    add("Magnitude", a=(actor(("Magnitude",)),), turns=tuple(turn("+attack Magnitude") for _ in range(5)),
        assertions=(check("damage", "B"),), rules=({"type": "magnitude"},), chance=True)
    for name in ("Parting Shot", "Shed Tail"):
        add(name, a=(actor((name,)), actor(("Splash",), "Eevee")),
            assertions=(check("active_species", value="Eevee"),),
            rules=({"type": "parting_shot" if name == "Parting Shot" else "shed_tail"},))
    for name in ("Defog", "Tidy Up"):
        a = actor((name, "Spikes", "Reflect", "Substitute"))
        b = actor(("Spikes", "Reflect", "Electric Terrain", "Substitute"), "Wailord", ability="No Ability", level=100)
        turns = (turn("+attack Spikes", "+attack Spikes"),)
        if name == "Defog":
            turns += (turn("+attack Reflect", "+attack Reflect"), turn("+attack Spikes", "+attack Electric Terrain"), turn("+attack Defog", "+attack Spikes"))
        else:
            turns += (turn("+attack Substitute", "+attack Substitute"), turn("+attack Tidy Up", "+attack Reflect"))
        assertions = (check("side_condition", "A", value="spikes", present=False),
                      check("side_condition", "B", value="spikes", present=False))
        add(name, a=(a,), b=(b,), turns=turns, assertions=assertions,
            rules=({"type": "field_cleanup", "move": key(name)},))
    for name in ("Electrify", "Powder"):
        a = actor((name, "Splash"), "Garchomp" if name == "Electrify" else "Mew", level=100)
        b = actor(("Tackle",) if name == "Electrify" else ("Ember",), "Mew", ability="No Ability")
        attack = "Tackle" if name == "Electrify" else "Ember"
        turns = (turn("+attack " + name, "+attack " + attack),)
        if name == "Electrify":
            turns += (turn("+attack Splash", "+attack Tackle"),)
        assertions = (check("immune", after_turn=1),) + ((check("damage"),) if name == "Electrify" else ())
        add(name, a=(a,), b=(b,), turns=turns, assertions=assertions, rules=({"type": key(name)},))
    for name in ("Focus Energy", "Laser Focus"):
        cases = []
        for index in (0, 1):
            turns = (turn("+attack " + ("Splash" if index == 0 else name)), turn("+attack Slash"))
            case = scenario(name, (actor((name, "Slash", "Splash") if index else ("Splash", "Slash", name)),), turns=turns,
                            assertions=(check("damage", "B"),), suffix="control" if index == 0 else "variant")
            cases.append(replace(case, seed_each_turn=True))
        result.append(EffectProbe(name, tuple(cases), ({"type": "damage_relation", "relation": "greater", "minimum_ratio": 1.25,
                                                     "critical_control": True},), chance=True))
    # The extra healthy bench attackers must add real hits to Beat Up.
    cases = []
    for index in (0, 1):
        team = (actor(("Beat Up",)),) + ((idle("Eevee", level=50), idle("Eevee", level=50)) if index else ())
        cases.append(scenario("Beat Up", team, assertions=(check("damage", "B"),), suffix="control" if index == 0 else "variant"))
    result.append(EffectProbe("Beat Up", tuple(cases), ({"type": "damage_relation", "relation": "greater", "minimum_ratio": 1.5},)))
    for name in ("After You", "Quash", "Follow Me", "Rage Powder", "Spotlight", "Helping Hand", "Dragon Cheer"):
        cases = []
        for index in (0, 1):
            move = name if index else "Splash"
            ally = actor(("Tackle", "Splash"), "Rampardos", level=50)
            holder = actor((name, "Splash") if index else ("Splash", name), "Alakazam", level=100)
            foe = actor(("Water Gun", "Splash"), "Mew", ability="No Ability", hp_fraction=.05 if name in {"After You", "Quash"} else 1)
            if name in {"Helping Hand", "Dragon Cheer"}:
                ally = actor(("Slash",), "Dragonite" if name == "Dragon Cheer" else "Mew", level=50)
                foe = idle()
            a_command = "+attack A1 " + move
            if index and name in {"After You", "Helping Hand", "Dragon Cheer", "Spotlight"}:
                a_command += " A2"
            if index and name == "Quash":
                a_command += " B1"
            ally_move = "+attack A2 " + ("Slash B1" if name in {"Helping Hand", "Dragon Cheer"} else "Tackle B1" if name in {"After You", "Quash"} else "Splash")
            foe_move = "+attack B1 " + ("Splash" if name in {"Helping Hand", "Dragon Cheer"} else "Water Gun " + ("A1" if name == "Spotlight" else "A2"))
            commands = (("a", a_command), ("a", ally_move), ("b", foe_move), ("b", "+attack B2 Splash"))
            cases.append(scenario(name, (holder, ally), (foe, idle("Chansey")), (commands,),
                                  suffix="control" if index == 0 else "variant", mode="double"))
        rule = "queue_order" if name in {"After You", "Quash"} else "damage_relation" if name in {"Helping Hand", "Dragon Cheer"} else "redirection"
        result.append(EffectProbe(name, tuple(cases), ({"type": rule, "relation": "greater", "minimum_ratio": 1.25,
                                                     "critical_control": name == "Dragon Cheer",
                                                     "recipient": 1 if name == "Spotlight" else 0},), chance=name == "Dragon Cheer"))
    assert len(result) == 108 and len({probe.subject for probe in result}) == 108
    return result
