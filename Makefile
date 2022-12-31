src-paths := src scripts

.PHONY: all up down backup-dashbaords requirements

requirements:
	poetry export -f requirements.txt --output requirements.txt

up: requirements
	docker compose up --detach --build --always-recreate-deps

down:
	docker compose down

restart: down up

backup-dashboards:
	python scripts/backup_dashboards.py