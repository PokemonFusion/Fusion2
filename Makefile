.PHONY: setup lint test test-semantic test-battle test-dex test-callbacks test-showdown battle-coverage org

setup:
	pip install -r requirements.txt && pip install -r requirements-dev.txt

lint:
	ruff .

test:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -n auto --dist=loadgroup --durations=25

test-semantic:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q tests/test_battle_semantic_contracts.py

test-battle:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q pokemon/battle/tests

test-dex:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q tests/test_all_moves_and_abilities.py pokemon/battle/tests/test_exhaustive_dex_smoke.py --run-dex-tests

test-callbacks:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q pokemon/battle/tests/test_generated_move_callbacks.py --run-callback-tests

test-showdown:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q pokemon/battle/tests/test_showdown_differential.py --run-showdown-tests

battle-coverage:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m tests.battle_contract_coverage

org:
	python tools/org_score.py
