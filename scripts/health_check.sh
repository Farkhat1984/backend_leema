#!/bin/bash
# Health check script for Fashion AI Platform
# Run this periodically to monitor service health

echo "======================================"
echo "  Fashion AI - Health Check"
echo "  $(date)"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check Docker containers
echo ""
echo "1. Docker Containers:"
CONTAINERS="fashion_backend_prod fashion_postgres_prod fashion_redis_prod"
for container in $CONTAINERS; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "  ${GREEN}✓${NC} $container is running"
    else
        echo -e "  ${RED}✗${NC} $container is NOT running"
        ((ERRORS++))
    fi
done

# Check backend health
echo ""
echo "2. Backend API:"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Backend is responding"
else
    echo -e "  ${RED}✗${NC} Backend is NOT responding"
    ((ERRORS++))
fi

# Check Redis
echo ""
echo "3. Redis:"
if docker exec fashion_redis_prod redis-cli ping 2>/dev/null | grep -q PONG; then
    echo -e "  ${GREEN}✓${NC} Redis is responding"
else
    echo -e "  ${RED}✗${NC} Redis is NOT responding"
    ((ERRORS++))
fi

# Check PostgreSQL
echo ""
echo "4. PostgreSQL:"
if docker exec fashion_postgres_prod pg_isready -U fashionuser > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL is ready"
else
    echo -e "  ${RED}✗${NC} PostgreSQL is NOT ready"
    ((ERRORS++))
fi

# Check Nginx
echo ""
echo "5. Nginx:"
if systemctl is-active --quiet nginx; then
    echo -e "  ${GREEN}✓${NC} Nginx is running"
else
    echo -e "  ${RED}✗${NC} Nginx is NOT running"
    ((ERRORS++))
fi

# Check SSL certificate expiry
echo ""
echo "6. SSL Certificate:"
if [ -d /etc/letsencrypt/live ]; then
    CERT_DOMAIN=$(ls /etc/letsencrypt/live/ | grep -v README | head -1)
    if [ -n "$CERT_DOMAIN" ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/$CERT_DOMAIN/cert.pem | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
        
        if [ $DAYS_LEFT -gt 30 ]; then
            echo -e "  ${GREEN}✓${NC} SSL certificate valid for $DAYS_LEFT days"
        elif [ $DAYS_LEFT -gt 7 ]; then
            echo -e "  ${YELLOW}⚠${NC} SSL certificate expires in $DAYS_LEFT days"
        else
            echo -e "  ${RED}✗${NC} SSL certificate expires in $DAYS_LEFT days!"
            ((ERRORS++))
        fi
    fi
else
    echo -e "  ${YELLOW}⚠${NC} No SSL certificate found"
fi

# Check disk space
echo ""
echo "7. Disk Space:"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo -e "  ${GREEN}✓${NC} Disk usage: ${DISK_USAGE}%"
elif [ $DISK_USAGE -lt 90 ]; then
    echo -e "  ${YELLOW}⚠${NC} Disk usage: ${DISK_USAGE}% (warning)"
else
    echo -e "  ${RED}✗${NC} Disk usage: ${DISK_USAGE}% (critical!)"
    ((ERRORS++))
fi

# Check memory
echo ""
echo "8. Memory Usage:"
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ $MEM_USAGE -lt 80 ]; then
    echo -e "  ${GREEN}✓${NC} Memory usage: ${MEM_USAGE}%"
elif [ $MEM_USAGE -lt 90 ]; then
    echo -e "  ${YELLOW}⚠${NC} Memory usage: ${MEM_USAGE}% (warning)"
else
    echo -e "  ${RED}✗${NC} Memory usage: ${MEM_USAGE}% (critical!)"
    ((ERRORS++))
fi

# Summary
echo ""
echo "======================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $ERRORS error(s)${NC}"
    exit 1
fi
