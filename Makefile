# ============================================================
# 皇甫谧数字人文平台 — Makefile
# ============================================================

.PHONY: help setup dev test lint format docs docker clean verify-env backup restore monitor

# Default target
.DEFAULT_GOAL := help

# Colors
GREEN  := \033[0;32m
BLUE   := \033[0;34m
YELLOW := \033[1;33m
NC     := \033[0m
BOLD   := \033[1m

help: ## Show this help
	@echo "$(BOLD)皇甫谧数字人文平台 — 开发命令$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## Initialize development environment
	@echo "$(BLUE)🔧 Setting up development environment...$(NC)"
	@bash scripts/setup.sh

dev: ## Start development servers
	@echo "$(BLUE)🚀 Starting development environment...$(NC)"
	@bash scripts/dev.sh

test: ## Run all tests
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@bash scripts/test.sh

test-unit: ## Run unit tests only
	@echo "$(BLUE)🧪 Running unit tests...$(NC)"
	@pytest tests/unit -v --tb=short

test-e2e: ## Run end-to-end tests only
	@echo "$(BLUE)🧪 Running E2E tests...$(NC)"
	@pytest tests/e2e -v --tb=short

lint: ## Run all linters
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@bash scripts/lint.sh

lint-python: ## Run Python linters only
	@ruff check . && ruff format --check .

lint-node: ## Run Node linters only
	@pnpm run lint && pnpm run format:check

format: ## Format all code
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	@bash scripts/format.sh

docs: ## Build documentation
	@echo "$(BLUE)📚 Building documentation...$(NC)"
	@echo "Documentation files:"
	@find docs -name "*.md" | wc -l | xargs echo "  Total .md files:"

docker-build: ## Build Docker images
	@echo "$(BLUE)🐳 Building Docker images...$(NC)"
	@docker compose -f docker-compose.dev.yml build

docker-up: ## Start Docker services
	@echo "$(BLUE)🐳 Starting Docker services...$(NC)"
	@docker compose -f docker-compose.dev.yml up -d

docker-down: ## Stop Docker services
	@echo "$(BLUE)🐳 Stopping Docker services...$(NC)"
	@docker compose -f docker-compose.dev.yml down

docker-clean: ## Remove Docker volumes and images
	@echo "$(BLUE)🐳 Cleaning Docker resources...$(NC)"
	@docker compose -f docker-compose.dev.yml down -v --rmi all 2>/dev/null || true

docker-build-prod: ## Build production Docker images
	@echo "$(BLUE)🐳 Building production Docker images...$(NC)"
	@docker compose -f docker-compose.prod.yml build

docker-up-prod: ## Start production Docker services
	@echo "$(BLUE)🐳 Starting production Docker services...$(NC)"
	@docker compose -f docker-compose.prod.yml up -d

verify-env: ## Validate .env against .env.example
	@echo "$(BLUE)🔍 Validating .env...$(NC)"
	@bash scripts/verify-env.sh

verify-env-strict: ## Validate .env (strict mode — no empty values)
	@echo "$(BLUE)🔍 Validating .env (strict)...$(NC)"
	@bash scripts/verify-env.sh --strict

backup: ## Create full backup (PostgreSQL + Neo4j + config)
	@echo "$(BLUE)💾 Creating backup...$(NC)"
	@bash scripts/backup.sh

backup-postgres: ## Backup PostgreSQL only
	@echo "$(BLUE)💾 Backing up PostgreSQL...$(NC)"
	@bash scripts/backup.sh postgres

backup-neo4j: ## Backup Neo4j only
	@echo "$(BLUE)💾 Backing up Neo4j...$(NC)"
	@bash scripts/backup.sh neo4j

restore: ## Restore from backup (usage: make restore DIR=backups/20250101_120000)
	@echo "$(BLUE)📥 Restoring from backup...$(NC)"
	@bash scripts/restore.sh $(DIR)

restore-list: ## List available backups
	@bash scripts/restore.sh --list

monitor: ## One-shot health check of all services
	@bash scripts/monitor.sh

monitor-watch: ## Continuous health monitoring (every 30s)
	@bash scripts/monitor.sh --watch

monitor-json: ## Health check in JSON format
	@bash scripts/monitor.sh --json

monitor-prometheus: ## Health check in Prometheus format
	@bash scripts/monitor.sh --prometheus

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)🔒 Running pre-commit...$(NC)"
	@pre-commit run --all-files

clean: ## Clean build artifacts
	@echo "$(BLUE)🧹 Cleaning...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.tsbuildinfo" -delete 2>/dev/null || true
	@rm -rf node_modules .pnpm-store 2>/dev/null || true
	@echo "$(GREEN)✅ Clean complete$(NC)"
