# PowerShell Build Script for Fashion Backend
# Windows equivalent of Makefile

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  .\make.ps1 install-uv      - Install UV package manager" -ForegroundColor White
    Write-Host "  .\make.ps1 install         - Install dependencies with UV" -ForegroundColor White
    Write-Host "  .\make.ps1 dev             - Run development server" -ForegroundColor White
    Write-Host "  .\make.ps1 test            - Run tests" -ForegroundColor White
    Write-Host "  .\make.ps1 test-cov        - Run tests with coverage" -ForegroundColor White
    Write-Host "  .\make.ps1 clean           - Clean up cache and temporary files" -ForegroundColor White
    Write-Host "  .\make.ps1 docker-build    - Build Docker image" -ForegroundColor White
    Write-Host "  .\make.ps1 docker-up       - Start Docker containers" -ForegroundColor White
    Write-Host "  .\make.ps1 docker-down     - Stop Docker containers" -ForegroundColor White
    Write-Host "  .\make.ps1 docker-logs     - Show Docker logs" -ForegroundColor White
    Write-Host "  .\make.ps1 migrate         - Run database migrations" -ForegroundColor White
    Write-Host "  .\make.ps1 migrate-create  - Create new migration" -ForegroundColor White
    Write-Host "  .\make.ps1 create-admin    - Create admin user" -ForegroundColor White
    Write-Host "  .\make.ps1 setup           - Full setup from scratch" -ForegroundColor White
}

function Install-UV {
    Write-Host "Installing UV package manager..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
    Write-Host "UV installed successfully!" -ForegroundColor Green
}

function Install-Dependencies {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    uv venv
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    uv pip install -r requirements.txt
    Write-Host "Dependencies installed!" -ForegroundColor Green
}

function Start-Dev {
    Write-Host "Starting development server..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    pytest tests/ -v
}

function Run-TestsWithCoverage {
    Write-Host "Running tests with coverage..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term
}

function Clean-Project {
    Write-Host "Cleaning up..." -ForegroundColor Yellow
    
    # Remove __pycache__ directories
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    
    # Remove .pyc files
    Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force
    
    # Remove pytest cache
    Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
    
    # Remove UV cache
    Get-ChildItem -Path . -Recurse -Directory -Filter ".uv" | Remove-Item -Recurse -Force
    
    # Remove coverage files
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage" }
    
    Write-Host "Cleanup complete!" -ForegroundColor Green
}

function Build-Docker {
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    docker build -t fashion-backend .
}

function Build-DockerOptimized {
    Write-Host "Building optimized Docker image..." -ForegroundColor Yellow
    docker build -f Dockerfile.optimized -t fashion-backend:optimized .
}

function Start-Docker {
    Write-Host "Starting Docker containers..." -ForegroundColor Yellow
    docker-compose up -d
}

function Stop-Docker {
    Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
    docker-compose down
}

function Show-DockerLogs {
    docker-compose logs -f backend
}

function Restart-Docker {
    Write-Host "Restarting Docker containers..." -ForegroundColor Yellow
    docker-compose restart backend
}

function Run-Migrations {
    Write-Host "Running database migrations..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    alembic upgrade head
}

function Create-Migration {
    $message = Read-Host "Enter migration message"
    Write-Host "Creating migration: $message" -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    alembic revision --autogenerate -m $message
}

function Migrate-Down {
    Write-Host "Rolling back last migration..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    alembic downgrade -1
}

function Create-AdminUser {
    Write-Host "Creating admin user..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
    python create_admin.py
}

function Setup-Project {
    Install-Dependencies
    Run-Migrations
    Create-AdminUser
    Write-Host "Setup complete! Run '.\make.ps1 dev' to start the server." -ForegroundColor Green
}

function Deploy-Production {
    Write-Host "Building optimized Docker image..." -ForegroundColor Yellow
    Build-DockerOptimized
    Write-Host "Stopping old containers..." -ForegroundColor Yellow
    Stop-Docker
    Write-Host "Starting new containers..." -ForegroundColor Yellow
    Start-Docker
    Write-Host "Deployment complete!" -ForegroundColor Green
}

# Main command router
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install-uv" { Install-UV }
    "install" { Install-Dependencies }
    "dev" { Start-Dev }
    "test" { Run-Tests }
    "test-cov" { Run-TestsWithCoverage }
    "clean" { Clean-Project }
    "docker-build" { Build-Docker }
    "docker-build-optimized" { Build-DockerOptimized }
    "docker-up" { Start-Docker }
    "docker-down" { Stop-Docker }
    "docker-logs" { Show-DockerLogs }
    "docker-restart" { Restart-Docker }
    "migrate" { Run-Migrations }
    "migrate-create" { Create-Migration }
    "migrate-down" { Migrate-Down }
    "create-admin" { Create-AdminUser }
    "setup" { Setup-Project }
    "deploy" { Deploy-Production }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
