.PHONY: install migrate dev test

install:
	python3 -m venv backend/venv
	backend/venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
	cd frontend && npm install

migrate:
	cd backend && venv/bin/alembic upgrade head

dev:
	docker compose up

test:
	cd backend && venv/bin/pytest
	cd frontend && npm run test
