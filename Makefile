.PHONY: help install install-uv dev test clean docker-build docker-up docker-down docker-logs

# Default target
help:
	@echo "Available commands:"
	@echo "  make install-uv      - Install UV package manager"
	@echo "  make install         - Install dependencies with UV"
	@echo "  make dev             - Run development server"
	@echo "  make test            - Run tests"
	@echo "  make clean           - Clean up cache and temporary files"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-up       - Start Docker containers"
	@echo "  make docker-down     - Stop Docker containers"
	@echo "  make docker-logs     - Show Docker logs"
	@echo "  make migrate         - Run database migrations"
	@echo "  make migrate-create  - Create new migration"

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

# Docker commands
docker-build:
	docker build -t fashion-backend .

docker-build-optimized:
	docker build -f Dockerfile.optimized -t fashion-backend:optimized .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

docker-restart:
	docker-compose restart backend

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

# Production deployment
deploy:
	@echo "Building optimized Docker image..."
	docker build -f Dockerfile.optimized -t fashion-backend:optimized .
	@echo "Stopping old containers..."
	docker-compose down
	@echo "Starting new containers..."
	docker-compose up -d
	@echo "Deployment complete!"
