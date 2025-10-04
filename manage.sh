#!/bin/bash

# Fashion Platform Management Script
# Скрипт для управления приложением на сервере

set -e

PROJECT_DIR="/opt/fashion-platform"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then 
    SUDO=""
else 
    SUDO="sudo"
fi

case "$1" in
    start)
        print_header "Starting Fashion Platform"
        cd $PROJECT_DIR
        docker compose up -d
        print_success "All services started"
        docker compose ps
        ;;
    
    stop)
        print_header "Stopping Fashion Platform"
        cd $PROJECT_DIR
        docker compose down
        print_success "All services stopped"
        ;;
    
    restart)
        print_header "Restarting Fashion Platform"
        cd $PROJECT_DIR
        docker compose restart
        print_success "All services restarted"
        docker compose ps
        ;;
    
    status)
        print_header "Fashion Platform Status"
        cd $PROJECT_DIR
        docker compose ps
        echo ""
        print_info "Resource usage:"
        docker stats --no-stream
        ;;
    
    logs)
        print_header "Fashion Platform Logs"
        cd $PROJECT_DIR
        if [ -z "$2" ]; then
            docker compose logs -f
        else
            docker compose logs -f $2
        fi
        ;;
    
    update)
        print_header "Updating Fashion Platform"
        cd $PROJECT_DIR
        
        print_info "Pulling latest changes..."
        git pull
        
        print_info "Building new images..."
        docker compose build --no-cache
        
        print_info "Stopping services..."
        docker compose down
        
        print_info "Starting updated services..."
        docker compose up -d
        
        print_info "Running migrations..."
        sleep 5
        docker compose exec backend alembic upgrade head
        
        print_success "Update completed!"
        docker compose ps
        ;;
    
    migrate)
        print_header "Running Database Migrations"
        cd $PROJECT_DIR
        docker compose exec backend alembic upgrade head
        print_success "Migrations completed"
        ;;
    
    backup)
        print_header "Creating Backup"
        BACKUP_DIR="/opt/backups"
        DATE=$(date +%Y%m%d_%H%M%S)
        
        mkdir -p $BACKUP_DIR
        
        print_info "Backing up database..."
        cd $PROJECT_DIR
        docker compose exec -T postgres pg_dump -U fashionuser fashion_platform > $BACKUP_DIR/db_$DATE.sql
        
        print_info "Backing up uploads..."
        tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C $PROJECT_DIR uploads
        
        print_info "Backing up environment..."
        cp $PROJECT_DIR/.env.production $BACKUP_DIR/env_$DATE.backup
        
        print_success "Backup completed: $BACKUP_DIR"
        ls -lh $BACKUP_DIR/*$DATE*
        ;;
    
    restore)
        if [ -z "$2" ]; then
            print_error "Usage: $0 restore <backup_date>"
            print_info "Example: $0 restore 20250105_120000"
            exit 1
        fi
        
        print_header "Restoring Backup from $2"
        BACKUP_DIR="/opt/backups"
        DATE=$2
        
        if [ ! -f "$BACKUP_DIR/db_$DATE.sql" ]; then
            print_error "Backup not found: $BACKUP_DIR/db_$DATE.sql"
            exit 1
        fi
        
        read -p "This will overwrite current data. Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_info "Restore cancelled"
            exit 0
        fi
        
        print_info "Restoring database..."
        cd $PROJECT_DIR
        docker compose exec -T postgres psql -U fashionuser -d fashion_platform < $BACKUP_DIR/db_$DATE.sql
        
        print_info "Restoring uploads..."
        tar -xzf $BACKUP_DIR/uploads_$DATE.tar.gz -C $PROJECT_DIR
        
        print_success "Restore completed!"
        ;;
    
    shell)
        print_header "Opening Backend Shell"
        cd $PROJECT_DIR
        docker compose exec backend bash
        ;;
    
    db-shell)
        print_header "Opening Database Shell"
        cd $PROJECT_DIR
        docker compose exec postgres psql -U fashionuser -d fashion_platform
        ;;
    
    clean)
        print_header "Cleaning Docker Resources"
        
        read -p "This will remove unused Docker resources. Continue? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_info "Cleanup cancelled"
            exit 0
        fi
        
        print_info "Removing stopped containers..."
        docker container prune -f
        
        print_info "Removing unused images..."
        docker image prune -a -f
        
        print_info "Removing unused networks..."
        docker network prune -f
        
        print_success "Cleanup completed!"
        docker system df
        ;;
    
    ssl-renew)
        print_header "Renewing SSL Certificates"
        cd $PROJECT_DIR
        docker compose run --rm certbot renew
        docker compose restart nginx
        print_success "SSL certificates renewed"
        ;;
    
    health)
        print_header "Health Check"
        
        print_info "Checking backend health..."
        if curl -sf https://api.leema.kz/health > /dev/null; then
            print_success "Backend is healthy"
            curl -s https://api.leema.kz/health | python3 -m json.tool
        else
            print_error "Backend is not responding"
        fi
        
        echo ""
        print_info "Checking frontend..."
        if curl -sf https://www.leema.kz > /dev/null; then
            print_success "Frontend is accessible"
        else
            print_error "Frontend is not responding"
        fi
        
        echo ""
        print_info "Docker services status:"
        cd $PROJECT_DIR
        docker compose ps
        ;;
    
    *)
        echo "Usage: $0 {command}"
        echo ""
        echo "Available commands:"
        echo "  start           - Start all services"
        echo "  stop            - Stop all services"
        echo "  restart         - Restart all services"
        echo "  status          - Show services status"
        echo "  logs [service]  - Show logs (optional: specific service)"
        echo "  update          - Update application (git pull + rebuild)"
        echo "  migrate         - Run database migrations"
        echo "  backup          - Create backup of database and uploads"
        echo "  restore <date>  - Restore from backup"
        echo "  shell           - Open backend container shell"
        echo "  db-shell        - Open PostgreSQL shell"
        echo "  clean           - Clean unused Docker resources"
        echo "  ssl-renew       - Renew SSL certificates"
        echo "  health          - Check application health"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs backend"
        echo "  $0 backup"
        echo "  $0 restore 20250105_120000"
        exit 1
        ;;
esac
