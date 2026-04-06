.PHONY: help up down restart logs build clean test ps health

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Show logs from all services
	docker compose logs -f

build: ## Build all images
	docker compose build

clean: ## Stop services and remove volumes
	docker compose down -v

test: ## Run tests inside API container
	docker compose exec api pytest

ps: ## Show running containers
	docker compose ps

health: ## Check health of all services
	@echo "Checking service health..."
	@docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
