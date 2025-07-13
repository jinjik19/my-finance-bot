# Команды для Docker Compose
up:
	docker-compose up --build -d

down:
	docker-compose down

down-v:
	docker-compose down -v

logs:
	docker-compose logs -f bot

lint-check:
	ruff check src

lint-fix:
	ruff check --fix src --preview

lint-format:
	ruff format src --preview

generate-data:
	@echo "Generating test data for the last year..."
	docker-compose exec bot python -m scripts.generate_test_data