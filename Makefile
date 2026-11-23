.PHONY: env check up down logs test test-unit test-integration test-frontend test-containers test-e2e verify-indexing worker-up worker-logs verify-search benchmark-text benchmark-image verify-advanced-search lint format migrate health clean
env:
	python3 scripts/init_env.py
check:
	bash scripts/checks/check_environment.sh
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs --tail=100 -f
test: test-unit test-frontend
test-unit:
	uv run --project backend --extra dev --extra evaluation --frozen pytest backend/tests/unit backend/tests/security backend/tests/reliability
test-integration: qa-up
	python3 scripts/qa.py services
test-frontend:
	npm --prefix frontend test
test-containers: qa-up
	python3 scripts/qa.py fast
	python3 scripts/qa.py services
	python3 scripts/qa.py frontend
test-e2e: qa-up
	python3 scripts/qa.py browser
lint:
	uv run --project backend --extra dev --frozen ruff check backend scripts
	uv run --project backend --extra dev --frozen ruff format --check backend scripts
	npm --prefix frontend run typecheck
	npm --prefix frontend run lint
format:
	uv run --project backend --extra dev --frozen ruff check backend scripts --fix
	uv run --project backend --extra dev --frozen ruff format backend scripts
	cd frontend && npm exec -- prettier --write src *.json *.ts *.js index.html
migrate:
	docker compose exec backend alembic -c backend/alembic.ini upgrade head
health:
	bash scripts/checks/verify_services.sh
clean:
	@printf 'Không xóa volumes/data tự động. make down giữ dữ liệu; xem docs/operations/DEVELOPMENT.md.\n'

verify-indexing:
	python3 scripts/verification/verify_indexing.py
worker-up:
	docker compose --profile indexing up -d indexing-worker
worker-logs:
	docker compose --profile indexing logs --tail=100 -f indexing-worker
verify-search:
	python3 scripts/verification/verify_search.py
benchmark-text:
	bash scripts/evaluation/benchmark_search.sh text
benchmark-image:
	bash scripts/evaluation/benchmark_search.sh image
verify-advanced-search:
	bash scripts/verification/verify_advanced_search.sh

.PHONY: verify-evaluation benchmark-evaluation annotate-evaluation
verify-evaluation:
	bash scripts/evaluation/verify_evaluation.sh
benchmark-evaluation:
	backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/fast_default.json
annotate-evaluation:
	backend/.venv/bin/python -m app.cli.evaluation annotation-pack

.PHONY: verify-rag benchmark-rag
verify-rag:
	bash scripts/verification/verify_rag.sh
benchmark-rag:
	backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.rag --requests 20

.PHONY: qa-up qa-down qa-fast qa-ai qa-seed qa-browser qa-faults
qa-up:
	python3 scripts/qa.py up
qa-down:
	python3 scripts/qa.py down
qa-fast:
	python3 scripts/qa.py fast
qa-ai:
	python3 scripts/qa.py ai
qa-seed:
	python3 scripts/qa.py seed
qa-browser:
	python3 scripts/qa.py browser
qa-faults:
	python3 scripts/qa.py faults

DEPLOY_ENV ?= .env.deploy
.PHONY: deploy-init deploy-build deploy-up deploy-down deploy-check deploy-status deploy-backup
deploy-init:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) init
deploy-build:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) build
deploy-up:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) up
deploy-down:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) down
deploy-check:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) check
deploy-status:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) status
deploy-backup:
	python3 scripts/deploy.py --env-file $(DEPLOY_ENV) backup --output backups
