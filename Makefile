.PHONY: help install install-uv dev test clean docker-build docker-up docker-down docker-logs docker-restart docker-rebuild

# Default target
help:
	@echo "Available commands:"
	@echo "  make install-uv      - Install UV package manager"
	@echo "  make install         - Install dependencies with UV"
	@echo "  make dev             - Run development server"
	@echo "  make test            - Run tests"
	@echo "  make clean           - Clean up cache and temporary files"
	@echo ""
	@echo "Docker commands (Development - with hot-reload):"
	@echo "  make docker-up       - Start Docker containers (hot-reload enabled)"
	@echo "  make docker-down     - Stop Docker containers"
	@echo "  make docker-restart  - Restart backend container (code changes auto-reload)"
	@echo "  make docker-rebuild  - Full rebuild (only if Dockerfile changed)"
	@echo "  make docker-logs     - Show Docker logs"
	@echo ""
	@echo "Database commands:"
	@echo "  make migrate         - Run database migrations"
	@echo "  make migrate-create  - Create new migration"
	@echo "  make create-admin    - Create admin user"

# Install UV package manager
install-uv:
	@echo "Installing UV package manager..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "UV installed successfully!"

# Create virtual environment and install dependencies
install:
	@echo "Creating virtual environment..."
	uv venv
	@echo "Installing dependencies..."
	uv pip install -r requirements.txt
	@echo "Dependencies installed!"

# Run development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".uv" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
	@echo "Cleanup complete!"

# Docker commands - Development mode (with hot-reload)
docker-up:
	@echo "🚀 Starting Docker containers with hot-reload enabled..."
	@echo "📝 Code changes will be automatically reflected (no rebuild needed)"
	docker-compose up -d
	@echo "✅ Containers started! View logs with: make docker-logs"

docker-down:
	@echo "🛑 Stopping Docker containers..."
	docker-compose down
	@echo "✅ Containers stopped!"

docker-restart:
	@echo "🔄 Restarting backend container..."
	@echo "💡 Note: With hot-reload, you usually don't need this!"
	docker-compose restart backend
	@echo "✅ Backend restarted!"

docker-rebuild:
	@echo "🔨 Full rebuild (use only if Dockerfile or requirements.txt changed)..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Rebuild complete!"

docker-logs:
	@echo "📋 Showing backend logs (Ctrl+C to exit)..."
	docker-compose logs -f backend

docker-logs-all:
	@echo "📋 Showing all logs (Ctrl+C to exit)..."
	docker-compose logs -f

docker-shell:
	@echo "🐚 Opening shell in backend container..."
	docker-compose exec backend /bin/sh

# Quick restart without rebuild (for most code changes)
docker-quick:
	@echo "⚡ Quick restart (code changes should auto-reload)..."
	docker-compose restart backend
	@echo "✅ Done! Changes should be reflected immediately."

# Database migrations
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-down:
	alembic downgrade -1

# Create admin user
create-admin:
	python create_admin.py

# Format code
format:
	black app/ tests/
	isort app/ tests/

# Lint code
lint:
	flake8 app/ tests/
	mypy app/

# Full setup from scratch
setup: install migrate create-admin
	@echo "Setup complete! Run 'make dev' to start the server."

# Production deployment (without hot-reload)
deploy-prod:
	@echo "⚠️  Deploying to PRODUCTION (no hot-reload)..."
	docker-compose -f docker-compose.prod.yml down
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment complete!"
