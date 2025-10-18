#!/bin/bash
# WebSocket Deployment Check Script

echo "🔍 Checking WebSocket deployment..."
echo ""

ERRORS=0

# 1. Check nginx
echo "1️⃣ Checking nginx configuration..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "   ✅ Nginx config is valid"
else
    echo "   ❌ Nginx config has errors"
    ERRORS=$((ERRORS + 1))
fi

# 2. Check backend container
echo "2️⃣ Checking backend container..."
if docker ps | grep -q fashion_backend; then
    echo "   ✅ Backend container is running"
else
    echo "   ❌ Backend container is not running"
    ERRORS=$((ERRORS + 1))
fi

# 3. Check .env variables
echo "3️⃣ Checking .env variables..."
if grep -q "API_BASE_URL=https://api.leema.kz" /var/www/backend/.env && \
   grep -q "WEBSOCKET_URL=wss://api.leema.kz" /var/www/backend/.env; then
    echo "   ✅ .env variables are set"
else
    echo "   ❌ .env variables are missing or incorrect"
    ERRORS=$((ERRORS + 1))
fi

# 4. Check config endpoint
echo "4️⃣ Checking config endpoint..."
CONFIG_RESPONSE=$(curl -s https://api.leema.kz/api/v1/config 2>&1)
if echo "$CONFIG_RESPONSE" | grep -q "websocket_url"; then
    echo "   ✅ Config endpoint is working"
    echo "   📋 WebSocket URL: $(echo "$CONFIG_RESPONSE" | jq -r '.websocket_url' 2>/dev/null || echo 'N/A')"
else
    echo "   ⚠️  Config endpoint may not be working (check if backend is fully started)"
    echo "   Response: $CONFIG_RESPONSE"
fi

# 5. Check WebSocket stats
echo "5️⃣ Checking WebSocket stats endpoint..."
STATS_RESPONSE=$(curl -s https://api.leema.kz/ws/stats 2>&1)
if echo "$STATS_RESPONSE" | grep -q "total"; then
    echo "   ✅ WebSocket stats endpoint is working"
    echo "   📊 Active connections: $(echo "$STATS_RESPONSE" | jq -r '.total' 2>/dev/null || echo 'N/A')"
else
    echo "   ⚠️  WebSocket stats endpoint may not be working"
fi

# 6. Check nginx WebSocket config
echo "6️⃣ Checking nginx WebSocket configuration..."
if grep -q "proxy_set_header Upgrade" /etc/nginx/sites-available/api.leema.kz && \
   grep -q "proxy_set_header Connection" /etc/nginx/sites-available/api.leema.kz; then
    echo "   ✅ Nginx WebSocket proxy headers are configured"
else
    echo "   ❌ Nginx WebSocket proxy headers are missing"
    ERRORS=$((ERRORS + 1))
fi

# 7. Check backend logs for errors
echo "7️⃣ Checking backend logs for WebSocket errors..."
RECENT_ERRORS=$(docker logs fashion_backend --tail 50 2>&1 | grep -i "error\|exception\|failed" | head -5)
if [ -z "$RECENT_ERRORS" ]; then
    echo "   ✅ No recent errors in backend logs"
else
    echo "   ⚠️  Recent errors found in logs:"
    echo "$RECENT_ERRORS" | sed 's/^/      /'
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ]; then
    echo "✅ All critical checks passed!"
    echo ""
    echo "📱 Flutter developers can now:"
    echo "   1. Fetch config: GET https://api.leema.kz/api/v1/config"
    echo "   2. Use WebSocket URL: wss://api.leema.kz/ws/{user|shop|admin}"
    echo "   3. Add query params: ?token=JWT_TOKEN&platform=mobile"
    echo ""
    echo "📖 See WEBSOCKET_FIX_FLUTTER.md for Flutter implementation"
    exit 0
else
    echo "❌ $ERRORS critical check(s) failed!"
    echo ""
    echo "Please fix the issues and run this script again."
    echo "See DEPLOYMENT_WEBSOCKET_FIX.md for troubleshooting."
    exit 1
fi
