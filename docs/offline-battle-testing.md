# Offline Battle Testing

Fusion2 battle behavior should be testable without live Evennia sessions. Manual
testing is useful for UX, but it cannot cover hundreds of moves, abilities,
Pokemon, and held items.

## Test Targets

Use these targets as separate checks:

```powershell
.\evenv\Scripts\python.exe -m pytest
```

Runs the default suite, including default examples that prove move, ability,
species, and held-item outcomes can be asserted offline.

```powershell
.\evenv\Scripts\python.exe -m pytest fusion2\tests\test_battle_semantic_contracts.py
```

Runs the focused semantic proof contracts. These assert exact post-move and
post-residual state, including HP, status, stat stages, immunity markers,
ability state, and held-item healing.

```powershell
.\evenv\Scripts\python.exe -m pytest fusion2\pokemon\battle\tests
```

Runs the focused battle-mechanics suite. Keep this as a separate process from
the legacy app tests because several older tests still install import-time
module stubs.

```powershell
.\evenv\Scripts\python.exe -m pytest fusion2\tests\test_all_moves_and_abilities.py --run-dex-tests
.\evenv\Scripts\python.exe -m pytest fusion2\pokemon\battle\tests\test_exhaustive_dex_smoke.py --run-dex-tests
```

Runs high-volume dex checks for all loaded moves, abilities, held items, and
Pokemon specs. These are opt-in because they are broad validation sweeps.

```powershell
.\evenv\Scripts\python.exe -m pytest fusion2\pokemon\battle\tests\test_generated_move_callbacks.py --run-callback-tests
```

Runs generated move callback checks. These verify callback references resolve
and compatible hook groups can be invoked offline. They are breadth smoke tests,
not correctness proofs unless paired with a semantic contract or Showdown case.

```powershell
.\evenv\Scripts\python.exe -m pytest fusion2\pokemon\battle\tests\test_showdown_differential.py --run-showdown-tests
```

Runs scripted comparisons against the local Pokemon Showdown checkout.

The same gates are available from `fusion2/Makefile`:

```powershell
make test
make test-semantic
make test-battle
make test-dex
make test-callbacks
make test-showdown
make battle-coverage
```

## Outcome Harness

Use `pokemon.battle.tests.outcome_harness` for deterministic tests. It builds a
small battle directly, executes one move or residual phase, and returns stable
before/after snapshots.

```python
from pokemon.battle.tests.outcome_harness import PokemonSpec, dex_move, run_move_outcome


def test_will_o_wisp_burns_target():
	result = run_move_outcome(
		user=PokemonSpec(name="Caster", types=("Fire",)),
		target=PokemonSpec(name="Target", types=("Normal",)),
		move=dex_move("Will-O-Wisp", accuracy=True),
	)

	assert result.after.target.status == "brn"
```

Held items use the same pattern:

```python
from pokemon.battle.tests.outcome_harness import PokemonSpec, run_residual_outcome


def test_leftovers_heals_on_residual():
	result = run_residual_outcome(
		user=PokemonSpec(name="Holder", hp=100, max_hp=160, item="Leftovers"),
	)

	assert result.after.user.hp == 110
```

Snapshots are typed dataclass objects (`BattleSnapshot`, `PokemonSnapshot`, and
`SideSnapshot`) so new tests should prefer attribute access. They also retain
dictionary-style access for older tests, for example
`result.after["target"]["status"]`.

Move outcomes also capture `DamageSnapshot` objects in `result.damage`. These
record per-hit damage, total damage, resolved power, random variance, crit flag,
STAB, type effectiveness, attack, defense, move name, and whether HP was
updated. Use these snapshots when proving exact calculated damage.

## Semantic Contracts

Use `MoveOutcomeContract` and `ResidualOutcomeContract` when a mechanic is
important enough to lock down as expected behavior rather than a smoke test.
Shared contract definitions live in `tests/battle_contract_catalog.py`; the
pytest file only executes that catalog.

```python
from pokemon.battle.tests.outcome_harness import (
	MoveOutcomeContract,
	PokemonExpectation,
	PokemonSpec,
	assert_move_outcome,
	dex_move,
)


def test_water_absorb_blocks_and_heals():
	assert_move_outcome(
		MoveOutcomeContract(
			name="water absorb heals and blocks water damage",
			user=PokemonSpec(name="Caster", types=("Water",)),
			target=PokemonSpec(
				name="Absorber",
				hp=100,
				max_hp=200,
				ability="Water Absorb",
			),
			move=dex_move("Water Gun", accuracy=True),
			expect_target=PokemonExpectation(
				hp=150,
				status=0,
				immune="Water Absorb",
			),
		)
	)
```

Contracts can assert:

- Pokemon state: HP, HP delta, status, stat stages, volatiles, immunity markers, ability state, item, fainting, and tempvals.
- Field state: weather, terrain, and pseudo-weather.
- Side state: side conditions and hazards.
- Damage state: event count, exact total damage, per-hit damage, power, random roll, crit, STAB, type effectiveness, and move name.

Use the factory helpers in `pokemon.battle.tests.outcome_harness` for common
mechanic groups:

- `status_contract`
- `boost_contract`
- `healing_contract`
- `drain_contract`
- `recoil_contract`
- `ability_immunity_contract`
- `weather_contract`
- `terrain_contract`
- `side_condition_contract`
- `volatile_contract`
- `forced_switch_contract`
- `self_switch_contract`
- `residual_item_contract`
- `secondary_chance_contract`
- `damage_contract`
- `secondary_contract`
- `callback_damage_contract`
- `combo_contract`

## Random Control

Use `RandomControl` when a contract needs to prove both branches of a
percentage-based mechanic. `random_values` are consumed by `random()` checks in
order, including accuracy, critical hits, and secondary effects. Use
`chance_roll(True)` to force a percent check to succeed and
`chance_roll(False)` to force it to fail. `randint_values` can pin integer rolls
such as damage variance.

For percentage thresholds, prefer `percent_roll(chance_percent, succeeds)`.
It returns the value just below the threshold for the trigger branch and exactly
at the threshold for the no-trigger branch. This proves the boundary behavior
without statistical sampling.

```python
from pokemon.battle.tests.outcome_harness import (
	MoveOutcomeContract,
	MoveSpec,
	PokemonExpectation,
	PokemonSpec,
	RandomControl,
	assert_move_outcome,
	chance_roll,
)


def test_coin_flip_strike_can_be_forced_to_miss():
	assert_move_outcome(
		MoveOutcomeContract(
			name="50 percent accuracy can miss",
			user=PokemonSpec(name="Attacker"),
			target=PokemonSpec(name="Target"),
			move=MoveSpec(name="Coin Flip Strike", power=40, accuracy=50),
			random_control=RandomControl(
				random_values=(chance_roll(False),),
			),
			expect_target=PokemonExpectation(hp_delta=0),
		)
	)
```

## Managed Coverage

Track coverage by mechanic group, not by raw dex count. The current default
semantic suite proves these groups:

| Mechanic group | Representative proof |
| --- | --- |
| Status outcome | Will-O-Wisp burns without damage |
| Stat boosts and drops | Swords Dance, Growl |
| Healing, drain, recoil | Recover, Drain Punch, Double-Edge |
| Ability immunity and state | Water Absorb, Volt Absorb, Flash Fire, Good as Gold |
| Held item residual effects | Leftovers |
| Weather and terrain | Sunny Day, Electric Terrain |
| Side hazards | Stealth Rock |
| Volatiles | Confuse Ray |
| Switching flags | Roar, U-turn |
| Priority turn order | Quick Attack versus faster Tackle |
| Random branches | Forced accuracy hit/miss, forced secondary trigger/no-trigger |
| Exact damage | Neutral, STAB, super-effective, resisted, immune, crit, and fixed variance |
| Secondary effects | Forced status, stat drop, volatile, self boost, drain, and recoil branches |
| Callback damage | Acrobatics, Grass Knot, Low Kick, Hex, Payback, Stored Power, Triple Kick, Triple Axel, Eruption, Water Spout |
| Combo moves | Pledge moves, Round, Fusion Bolt, Fusion Flare |

The coverage inventory classifies every loaded move, ability, item, and Pokemon
species against the current contract catalog:

```powershell
$env:PYTHONPATH = "fusion2"; .\evenv\Scripts\python.exe -m tests.battle_contract_coverage
```

From inside `fusion2`, use:

```powershell
make battle-coverage
```

Inventory statuses:

- `explicit_contract`: the exact dex entry is named by a semantic outcome contract.
- `mechanic_contract`: the dex entry uses at least one mechanic group proven by the contract catalog.
- `smoke_only`: the entry is only covered by broad dex construction/execution smoke tests.
- `known_gap`: the entry is intentionally documented as unsupported or divergent.

When adding or changing a move, ability, Pokemon interaction, or held item:

- If it uses an already-covered shared mechanic, run the semantic suite and the dex smoke sweep.
- If it has unique callback behavior or a new mechanic group, add a semantic contract.
- If exact parity with Pokemon Showdown matters, add or update a Showdown differential case.
- If it only adds a callback reference, run the generated callback suite too, but do not treat that as proof of the expected battle outcome.

## Coverage Policy

For a move, ability, Pokemon interaction, or held item to be considered
supported in combat, it needs at least one semantic contract for the expected
state change. Use the dex smoke tests for broad "all entries load and can be
exercised" coverage, and Showdown differential cases for mechanics where final
state parity matters.
