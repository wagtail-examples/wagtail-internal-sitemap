# Makefile for Docker Compose commands

# --- Un-comment to suite your needs --- #

# Default SQLite Database
# DC = docker compose -f compose.yaml

# MySQL Database
# DC = docker compose -f compose.yaml -f compose.mysql.override.yaml

# PostgreSQL Database
DC = BUILDKIT_PROGRESS=plain docker compose -f compose.yaml -f compose.postgresql.override.yaml

# Default target
.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo " Docker Compose commands"
	@echo "  build          Build the Docker containers"
	@echo "  up             Start the Docker containers"
	@echo "  down           Stop and remove the Docker containers"
	@echo "  destroy        Stop and remove the Docker containers, networks, and volumes"
	@echo "  run            Run the Django development server"
	@echo ""
	@echo " Container commands"
	@echo "  migrate        Run Django migrations"
	@echo "  superuser      Create a superuser"
	@echo "  restoredb      Restore the database from a backup"
	@echo "  sh             Execute a command in a running container"
	@echo "  restart        Restart the containers"
	@echo ""
	@echo " Miscellaneous"
	@echo "  quickstart     Build, start, and run the containers (npm & docker)"
	@echo "  requirements   Export requirements.txt (poetry)"
	@echo "  clean          Clean up generated files and folders (node_modules, static, media, etc.)"
	@echo "  frontend       Build the frontend (npm)"
	@echo "  start          Build the front end and start local development server (npm)"
	@echo ""

# Build the containers
.PHONY: build
build:
	$(DC) build

# Start the containers
.PHONY: up
up:
	$(DC) up -d

# Stop and remove containers, networks, and volumes
.PHONY: down
down:
	$(DC) down

# Restart the containers
.PHONY: restart
restart:
	$(DC) restart

# Execute a command in a running container
.PHONY: sh
sh:
	$(DC) exec app bash

# Run the Django development server
.PHONY: run
run:
	$(DC) exec app python manage.py runserver 0.0.0.0:8000

# Stop and remove the Docker containers, networks, and volumes
.PHONY: destroy
destroy:
	$(DC) down -v

# Run migrations
.PHONY: migrate
migrate:
	$(DC) exec app python manage.py migrate

# Create a superuser
.PHONY: superuser
superuser:
	$(DC) exec app python manage.py createsuperuser

# Collect static files
.PHONY: collectstatic
collectstatic:
	$(DC) exec app python manage.py collectstatic --noinput

# Run tests, you will need to have run `make collectstatic` first
.PHONY: test
test:
	$(DC) exec app python manage.py test

# Quickstart
.PHONY: quickstart
quickstart: frontend build up migrate collectstatic test run

# Build the fontend
.PHONY: frontend
frontend:
	npm install
	npm run build

# Start the frontend and run the local development server
.PHONY: start
start:
	npm install
	npm run build
	npm run start

# Export requirements.txt
.PHONY: requirements
requirements:
	poetry export -f requirements.txt --output requirements.txt  --without-urls --without-hashes

# Clean up
.PHONY: clean
clean:
	rm -rf ./node_modules ./static ./static_compiled ./media
