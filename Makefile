.PHONY: env check up down logs test test-unit test-integration test-frontend test-containers test-e2e verify-indexing worker-up worker-logs verify-search benchmark-text benchmark-image verify-advanced-search lint format migrate health clean
env:
	python3 scripts/init_env.py
check:
	bash scripts/check_environment.sh
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs --tail=100 -f
test: test-unit test-frontend
test-unit:
	uv run --project backend --extra dev --frozen pytest backend/tests/unit
test-integration:
	docker compose exec -e RUN_INTEGRATION=1 backend pytest backend/tests/integration -p no:cacheprovider
test-frontend:
	npm --prefix frontend test
test-containers:
	docker compose exec -T backend pytest backend/tests/unit -p no:cacheprovider
	docker compose exec -T -e RUN_INTEGRATION=1 backend pytest backend/tests/integration -p no:cacheprovider
	docker compose exec -T backend ruff check backend scripts
	docker compose exec -T backend ruff format --check backend scripts
	docker compose exec -T frontend npm run typecheck
	docker compose exec -T frontend npm run lint
	docker compose exec -T frontend npm test
	docker compose exec -T frontend npm run build
test-e2e:
	uv run --project backend python scripts/run_local.py --env-file .env -- npm --prefix frontend run test:e2e
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
	bash scripts/verify_services.sh
clean:
	@printf 'Không xóa volumes/data tự động. make down giữ dữ liệu; xem docs/DEVELOPMENT.md.\n'

verify-indexing:
	python3 scripts/verify_indexing.py
worker-up:
	docker compose --profile indexing up -d indexing-worker
worker-logs:
	docker compose --profile indexing logs --tail=100 -f indexing-worker
verify-search:
	python3 scripts/verify_search.py
benchmark-text:
	bash scripts/benchmark_search.sh text
benchmark-image:
	bash scripts/benchmark_search.sh image
verify-advanced-search:
	bash scripts/verify_advanced_search.sh

.PHONY: verify-evaluation benchmark-evaluation annotate-evaluation
verify-evaluation:
	bash scripts/verify_evaluation.sh
benchmark-evaluation:
	backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.evaluation benchmark --config evaluation/experiments/phase07/fast_default.json
annotate-evaluation:
	backend/.venv/bin/python -m app.cli.evaluation annotation-pack

.PHONY: verify-rag benchmark-rag
verify-rag:
	bash scripts/verify_rag.sh
benchmark-rag:
	backend/.venv/bin/python scripts/run_local.py --env-file .env -- backend/.venv/bin/python -m app.cli.rag --requests 20
