"""Developer testing commands for rapid battle prototyping."""

from typing import List

from evennia import Command

from tests.utils.testfactory import make_punching_bag, make_test_pokemon


def _get_unverified_moves() -> List[str]:
    """Return moves not yet verified.

    Verification status is stored in the ``VerifiedMove`` table. If the
    database is unavailable the function falls back to a static placeholder
    list.
    """
    try:  # pragma: no cover - DB access not available in some tests
        from pokemon.models import Move, VerifiedMove

        status = {vm.key.lower(): vm.verified for vm in VerifiedMove.objects.all()}
        return [
            name
            for name in Move.objects.values_list("name", flat=True)
            if not status.get(name.lower(), False)
        ]
    except Exception:
        from utils.constants.unverified_moves import UNVERIFIED_MOVES
        return list(UNVERIFIED_MOVES)


def _start_ephemeral_battle(caller, atk_pkmn, def_pkmn):
    """Start a ``BattleSession`` with temporary Pokémon."""
    try:
        from pokemon.battle.battledata import Move as BMove
        from pokemon.battle.battledata import Pokemon as BPokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import BattleType

        class DummyTrainer:
            """Minimal stand-in opponent."""

            def __init__(self, key, location):
                self.key = key
                self.location = location
                self.ndb = type("NDB", (), {})()

        opponent = DummyTrainer("PunchBag", caller.location)
        battle = BattleSession(caller, opponent)
        atk_moves = [BMove(name=m, pokemon_types=atk_pkmn.types) for m in atk_pkmn.moves]
        def_moves = [BMove(name=m, pokemon_types=def_pkmn.types) for m in def_pkmn.moves]
        atk = BPokemon(
            atk_pkmn.name,
            level=atk_pkmn.level,
            hp=atk_pkmn.hp,
            max_hp=atk_pkmn.max_hp,
            moves=atk_moves,
            ability=atk_pkmn.ability,
            item=atk_pkmn.item,
            ivs=atk_pkmn.ivs,
            evs=atk_pkmn.evs,
            nature=atk_pkmn.nature,
            types=atk_pkmn.types,
        )
        defender = BPokemon(
            def_pkmn.name,
            level=def_pkmn.level,
            hp=def_pkmn.hp,
            max_hp=def_pkmn.max_hp,
            moves=def_moves,
            ability=def_pkmn.ability,
            item=def_pkmn.item,
            ivs=def_pkmn.ivs,
            evs=def_pkmn.evs,
            nature=def_pkmn.nature,
            types=def_pkmn.types,
        )
        battle._init_battle_state(
            caller.location, [atk], defender, opponent.key, BattleType.TRAINER
        )
        battle._setup_battle_room()
        return f"Battle {battle.battle_id}"
    except Exception as e:  # pragma: no cover
        return f"Error: {e}"


class CmdToggleTest(Command):
    """
    @toggletest
    Attach or remove the ``DevTestCmdSet`` to yourself.
    """

    key = "@toggletest"
    aliases = ["toggletest"]
    locks = "cmd:perm(Builder)"
    help_category = "Dev/Test"

    def func(self):
        cmdset_key = "DevTestCmdSet"
        if self.caller.cmdset.has_cmdset(cmdset_key, must_be_default=False):
            self.caller.cmdset.delete(cmdset_key)
            self.caller.msg("|gRemoved DevTest cmdset.|n")
        else:
            from ..cmdsets.devtest import DevTestCmdSet

            self.caller.cmdset.add(DevTestCmdSet)
            self.caller.msg("|gAdded DevTest cmdset. Use +testbattle ...|n")


class CmdTestBattle(Command):
    """
    +testbattle [--random] [--level=<int>] [--ability=<name>] [--item=<name>] [--seed=<int>] [--vs-hp=<int>]
    +testbattle <move1> <move2> <move3> <move4>

    Spin up an ephemeral battle with:
    - Your side: a custom TestMon with either the four moves you specify or random picks
      from the unverified move pool.
    - Opponent: a PunchBagMon with average stats and high HP.

    Flags (optional):
    --random           Use four random moves from the unverified pool.
    --level=50         Level of TestMon (default 50).
    --ability=...      Set TestMon's ability for ability testing.
    --item=...         Give TestMon a held item for item testing.
    --seed=123         Seed RNG for reproducible tests.
    --vs-hp=500        Override PunchBag HP (default 600).
    """

    key = "+testbattle"
    aliases = ["testbattle"]
    locks = "cmd:perm(Builder)"
    help_category = "Dev/Test"

    def parse(self):
        self.args_list = [arg for arg in self.args.split() if not arg.startswith("--")]
        self.switches = {}
        for tok in self.args.split():
            if tok.startswith("--"):
                if "=" in tok:
                    k, v = tok[2:].split("=", 1)
                    self.switches[k.lower()] = v
                else:
                    self.switches[tok[2:].lower()] = True

    def func(self):
        caller = self.caller
        use_random = bool(self.switches.get("random"))
        level = int(self.switches.get("level", 50))
        ability = self.switches.get("ability")
        item = self.switches.get("item")
        seed = self.switches.get("seed")
        vs_hp = int(self.switches.get("vs-hp", 600))

        if seed is not None:
            try:
                seed = int(seed)
            except ValueError:
                return caller.msg("|rInvalid --seed value.|n")

        moves: List[str] = []
        if use_random:
            from random import Random

            rng = Random(seed)
            pool = _get_unverified_moves()
            if len(pool) < 4:
                return caller.msg("|rNo unverified moves available.|n")
            rng.shuffle(pool)
            moves = pool[:4]
        else:
            moves = self.args_list[:4]
            if len(moves) != 4:
                return caller.msg(
                    "|yUsage:|n +testbattle <move1> <move2> <move3> <move4>  or  +testbattle --random [flags]"
                )

        try:
            testmon = make_test_pokemon(
                level=level, moves=moves, ability=ability, item=item, seed=seed
            )
        except Exception as e:
            return caller.msg(f"|rFailed to create TestMon: {e}|n")
        try:
            punchbag = make_punching_bag(hp=vs_hp, level=level)
        except Exception as e:
            return caller.msg(f"|rFailed to create PunchBagMon: {e}|n")

        status = _start_ephemeral_battle(caller, testmon, punchbag)
        caller.msg(f"|gTest battle created.|n Moves: |W{', '.join(moves)}|n  Status: {status}")
