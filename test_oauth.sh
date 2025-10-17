#!/bin/bash

echo "=========================================="
echo "Google OAuth Testing Script"
echo "=========================================="
echo ""

echo "🔍 Testing OAuth endpoints..."
echo ""

# Test 1: Get OAuth URL
echo "1️⃣ Testing GET /api/v1/auth/google/url"
echo "   Request: GET http://localhost:8000/api/v1/auth/google/url?account_type=shop&platform=web"
OAUTH_URL=$(curl -s "http://localhost:8000/api/v1/auth/google/url?account_type=shop&platform=web")
echo "   Response:"
echo "$OAUTH_URL" | jq '.' 2>/dev/null || echo "$OAUTH_URL"
echo ""

# Extract authorization URL
AUTH_URL=$(echo "$OAUTH_URL" | jq -r '.authorization_url' 2>/dev/null)

if [ "$AUTH_URL" != "null" ] && [ ! -z "$AUTH_URL" ]; then
    echo "   ✅ OAuth URL generated successfully!"
    echo ""
    echo "   🌐 Open this URL in browser to test:"
    echo "   $AUTH_URL"
    echo ""
else
    echo "   ❌ Failed to get OAuth URL"
    echo ""
fi

# Test 2: Check callback endpoint exists
echo "2️⃣ Testing GET /api/v1/auth/google/callback (without params)"
echo "   Request: GET http://localhost:8000/api/v1/auth/google/callback"
CALLBACK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/auth/google/callback")
echo "   Status Code: $CALLBACK_STATUS"

if [ "$CALLBACK_STATUS" == "404" ]; then
    echo "   ❌ ERROR: Callback endpoint returns 404!"
    echo "   This should return 302 (redirect) or 400 (bad request), not 404"
elif [ "$CALLBACK_STATUS" == "302" ] || [ "$CALLBACK_STATUS" == "400" ]; then
    echo "   ✅ Callback endpoint is accessible"
else
    echo "   ⚠️  Unexpected status: $CALLBACK_STATUS"
fi
echo ""

# Test 3: Check login endpoint
echo "3️⃣ Testing POST /api/v1/auth/google/login"
echo "   Request: POST http://localhost:8000/api/v1/auth/google/login (without body)"
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8000/api/v1/auth/google/login" -H "Content-Type: application/json" -d '{}')
echo "   Status Code: $LOGIN_STATUS"

if [ "$LOGIN_STATUS" == "404" ]; then
    echo "   ❌ ERROR: Login endpoint returns 404!"
elif [ "$LOGIN_STATUS" == "422" ] || [ "$LOGIN_STATUS" == "400" ]; then
    echo "   ✅ Login endpoint is accessible (validation error expected)"
else
    echo "   ⚠️  Unexpected status: $LOGIN_STATUS"
fi
echo ""

echo "=========================================="
echo "Configuration Check"
echo "=========================================="
echo ""

# Check .env file
if [ -f ".env" ]; then
    echo "📋 Current .env Google configuration:"
    echo ""
    grep "GOOGLE_CLIENT_ID=" .env
    grep "GOOGLE_REDIRECT_URI=" .env
    grep "GOOGLE_MOBILE_CLIENT_ID=" .env
    grep "GOOGLE_ANDROID_CLIENT_ID=" .env
    echo ""
else
    echo "❌ .env file not found!"
    echo ""
fi

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Проверьте Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials"
echo ""
echo "2. Для Web Client ID (236011762515-q48adtqtgd72na7lp861339offh3b9k3):"
echo "   Добавьте в Authorized Redirect URIs:"
echo "   - https://api.leema.kz/api/v1/auth/google/callback"
echo "   - https://www.leema.kz/public/auth/callback.html"
echo ""
echo "3. Добавьте в Authorized JavaScript Origins:"
echo "   - https://api.leema.kz"
echo "   - https://www.leema.kz"
echo "   - https://leema.kz"
echo ""
echo "4. Сохраните и подождите 5-10 минут"
echo ""
echo "5. Очистите кэш браузера"
echo ""
echo "6. Протестируйте OAuth URL выше в браузере"
echo ""
echo "📖 Полная инструкция: cat GOOGLE_OAUTH_SETUP.md"
echo ""
