.PHONY: setup lint test org

setup:
	pip install -r requirements.txt && pip install -r requirements-dev.txt

lint:
	ruff .

test:
	pytest

org:
	python tools/org_score.py
