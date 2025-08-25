.PHONY: setup lint test org

setup:
	pip install -r requirements.txt && pip install -r requirements-dev.txt

lint:
	ruff .

test:
	PF2_NO_EVENNIA=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -n auto --dist=loadgroup --durations=25 --run-dex-tests

org:
	python tools/org_score.py
