#!/bin/bash
# Ucok Store - Health Check Script
# Monitor service health and send alerts

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✓${NC} $name is healthy (HTTP $status_code)"
        return 0
    else
        echo -e "${RED}✗${NC} $name is down (HTTP $status_code)"
        return 1
    fi
}

echo "🏥 Ucok Store - Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check PM2 process
echo "📊 PM2 Status:"
if pm2 list | grep -q "ucok-store.*online"; then
    echo -e "${GREEN}✓${NC} PM2 process is running"
    PM2_OK=true
else
    echo -e "${RED}✗${NC} PM2 process is not running"
    PM2_OK=false
fi
echo ""

# Check services
echo "🌐 Service Health:"
API_OK=false
WEBCHECKER_OK=false

check_service "Main API" "http://localhost:8000/api/health" && API_OK=true
check_service "Webchecker" "http://localhost:8001/api/cleanup" && WEBCHECKER_OK=true

echo ""

# Check ports
echo "🔌 Port Status:"
if netstat -tulpn 2>/dev/null | grep -q ":8000"; then
    echo -e "${GREEN}✓${NC} Port 8000 (API) is listening"
else
    echo -e "${RED}✗${NC} Port 8000 (API) is not listening"
fi

if netstat -tulpn 2>/dev/null | grep -q ":8001"; then
    echo -e "${GREEN}✓${NC} Port 8001 (Webchecker) is listening"
else
    echo -e "${RED}✗${NC} Port 8001 (Webchecker) is not listening"
fi

if netstat -tulpn 2>/dev/null | grep -q ":3000"; then
    echo -e "${GREEN}✓${NC} Port 3000 (Webapp) is listening"
else
    echo -e "${RED}✗${NC} Port 3000 (Webapp) is not listening"
fi

echo ""

# Check resources
echo "💾 System Resources:"
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "  Memory usage: ${MEMORY_USAGE}%"
echo "  Disk usage: ${DISK_USAGE}%"

if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    echo -e "${RED}⚠${NC} High memory usage!"
fi

if (( $DISK_USAGE > 90 )); then
    echo -e "${RED}⚠${NC} High disk usage!"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Overall status
if [ "$PM2_OK" = true ] && [ "$API_OK" = true ] && [ "$WEBCHECKER_OK" = true ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    exit 0
else
    echo -e "${RED}✗ Some systems are down${NC}"
    echo ""
    echo "Run 'pm2 logs ucok-store' to see errors"
    echo "Run 'pm2 restart ucok-store' to restart services"
    exit 1
fi
