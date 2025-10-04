#!/bin/bash

# Pre-deployment checklist script
# Проверяет готовность проекта к развертыванию

echo "======================================"
echo "Fashion AI Platform - Pre-Deploy Check"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

function check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

function check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. Check required files
echo "1. Checking required files..."
files=(
    "Dockerfile"
    "docker-compose.yml"
    ".dockerignore"
    "requirements.txt"
    "alembic.ini"
    "app/main.py"
    "app/config.py"
    "nginx/nginx.conf"
    "nginx/conf.d/leema.conf"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file is missing"
    fi
done

# 2. Check .env.production
echo ""
echo "2. Checking environment configuration..."
if [ -f ".env.production" ]; then
    check_pass ".env.production exists"
    
    # Check for placeholder values
    if grep -q "YOUR_SECURE_PASSWORD" .env.production; then
        check_fail ".env.production contains placeholder passwords"
    fi
    
    if grep -q "YOUR_SUPER_SECRET_KEY" .env.production; then
        check_fail ".env.production contains placeholder SECRET_KEY"
    fi
    
    if grep -q "your-google-client-id" .env.production; then
        check_warn ".env.production may contain placeholder Google OAuth credentials"
    fi
    
else
    check_fail ".env.production not found (copy from .env.production.example)"
fi

# 3. Check Docker
echo ""
echo "3. Checking Docker installation..."
if command -v docker &> /dev/null; then
    check_pass "Docker is installed ($(docker --version))"
else
    check_fail "Docker is not installed"
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    check_pass "Docker Compose is installed"
else
    check_fail "Docker Compose is not installed"
fi

# 4. Check Git status
echo ""
echo "4. Checking Git status..."
if [ -d ".git" ]; then
    check_pass "Git repository detected"
    
    if [ -n "$(git status --porcelain)" ]; then
        check_warn "You have uncommitted changes"
        git status --short
    else
        check_pass "No uncommitted changes"
    fi
else
    check_warn "Not a git repository"
fi

# 5. Check ports
echo ""
echo "5. Checking port availability..."
if command -v netstat &> /dev/null || command -v ss &> /dev/null; then
    ports=(80 443)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
            check_warn "Port $port is already in use"
        else
            check_pass "Port $port is available"
        fi
    done
else
    check_warn "Cannot check ports (netstat/ss not found)"
fi

# 6. Check Python requirements
echo ""
echo "6. Checking requirements.txt..."
if grep -q "asyncpg" requirements.txt; then
    check_pass "PostgreSQL driver (asyncpg) found in requirements"
else
    check_fail "PostgreSQL driver (asyncpg) not found in requirements"
fi

if grep -q "psycopg2" requirements.txt; then
    check_pass "PostgreSQL adapter (psycopg2) found in requirements"
else
    check_warn "PostgreSQL adapter (psycopg2) not found (may be optional)"
fi

# 7. Summary
echo ""
echo "======================================"
echo "Summary:"
echo "======================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready for deployment.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found. Please review before deployment.${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found. Please fix before deployment.${NC}"
    exit 1
fi
