.PHONY: setup lint test

setup:
	pip install -r requirements.txt && pip install -r requirements-dev.txt

lint:
	ruff .

test:
	pytest
