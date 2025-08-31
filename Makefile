.PHONY: deps up down reset env run lint fmt test unit integration coverage

PY?=python
PIP?=pip

env:
	$(PY) -m venv .venv

deps: env
	. .venv/bin/activate && $(PIP) install -U pip && pip install -r requirements.txt

up:
	docker-compose up -d localstack
	./scripts/start_localstack.sh

down:
	docker-compose down -v

reset:
	docker-compose down -v && rm -rf localstack
	./scripts/reset_localstack.sh

run:
	. .venv/bin/activate && uvicorn api.main:app --reload --port 8000

lint:
	. .venv/bin/activate && ruff check . && black --check . && mypy .

fmt:
	. .venv/bin/activate && black . && ruff check . --fix

test:
	. .venv/bin/activate && pytest -q

unit:
	. .venv/bin/activate && pytest -q tests/unit

integration:
	. .venv/bin/activate && pytest -q tests/integration

coverage:
	. .venv/bin/activate && pytest --cov=api --cov=infra --cov=services --cov=schemas -q
