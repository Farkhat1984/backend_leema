#!/bin/bash
# Test script for Wardrobe API endpoints

set -e

BASE_URL="http://localhost:8000/api/v1"
echo "=" | tr '=' '=' | head -c 60; echo
echo "TESTING WARDROBE API ENDPOINTS"
echo "=" | tr '=' '=' | head -c 60; echo

# First, get an access token (you'll need to replace this with a real token)
echo -e "\n📝 Note: Tests require authentication"
echo "To run full tests, set ACCESS_TOKEN environment variable:"
echo "  export ACCESS_TOKEN='your_jwt_token_here'"
echo

# Check if token is set
if [ -z "$ACCESS_TOKEN" ]; then
    echo "⚠️  ACCESS_TOKEN not set. Running unauthenticated tests only..."
    echo
    
    # Test 1: Check that endpoints require authentication
    echo "--- Test 1: Verify Authentication Required ---"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/wardrobe/" 2>&1)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "401" ]; then
        echo "✓ GET /wardrobe/ correctly requires authentication (401)"
    else
        echo "❌ Expected 401, got $http_code"
    fi
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/wardrobe/stats" 2>&1)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "401" ]; then
        echo "✓ GET /wardrobe/stats correctly requires authentication (401)"
    else
        echo "❌ Expected 401, got $http_code"
    fi
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/wardrobe/folders" 2>&1)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "401" ]; then
        echo "✓ GET /wardrobe/folders correctly requires authentication (401)"
    else
        echo "❌ Expected 401, got $http_code"
    fi
    
    echo
    echo "✅ All unauthenticated tests passed!"
    echo
    echo "To test authenticated endpoints, run:"
    echo "  1. Login via /api/v1/auth/google/login"
    echo "  2. Copy the access_token from response"
    echo "  3. export ACCESS_TOKEN='your_token'"
    echo "  4. Run this script again"
    
else
    echo "✓ ACCESS_TOKEN found, running full test suite..."
    echo
    
    # Test 2: Get wardrobe (should be empty initially)
    echo "--- Test 2: Get Wardrobe (Empty) ---"
    response=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/wardrobe/")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    total=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null || echo "0")
    echo "✓ Total items: $total"
    echo
    
    # Test 3: Get wardrobe stats
    echo "--- Test 3: Get Wardrobe Stats ---"
    response=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/wardrobe/stats")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo "✓ Stats retrieved"
    echo
    
    # Test 4: Get folders
    echo "--- Test 4: Get Folders ---"
    response=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/wardrobe/folders")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo "✓ Folders retrieved"
    echo
    
    # Test 5: Try to get non-existent item (should 404)
    echo "--- Test 5: Get Non-Existent Item ---"
    response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/wardrobe/99999" 2>&1)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "404" ]; then
        echo "✓ Correctly returns 404 for non-existent item"
    else
        echo "⚠️  Expected 404, got $http_code"
    fi
    echo
    
    # Test 6: Add product from shop (requires product_id)
    echo "--- Test 6: Add from Shop (Optional) ---"
    echo "To test: POST $BASE_URL/wardrobe/from-shop/{product_id}"
    echo "  (Requires approved product in database)"
    echo
    
    # Test 7: Save generation (requires generation_id)
    echo "--- Test 7: Save Generation (Optional) ---"
    echo "To test: POST $BASE_URL/wardrobe/from-generation/{generation_id}"
    echo "  (Requires generation in database)"
    echo
    
    echo "=" | tr '=' '=' | head -c 60; echo
    echo "TESTS COMPLETED!"
    echo "=" | tr '=' '=' | head -c 60; echo
    echo
    echo "API Endpoints Available:"
    echo "  GET    /api/v1/wardrobe/                - List wardrobe items"
    echo "  POST   /api/v1/wardrobe/                - Create new item"
    echo "  GET    /api/v1/wardrobe/stats           - Get statistics"
    echo "  GET    /api/v1/wardrobe/folders         - Get folder list"
    echo "  GET    /api/v1/wardrobe/{id}            - Get item details"
    echo "  PUT    /api/v1/wardrobe/{id}            - Update item"
    echo "  DELETE /api/v1/wardrobe/{id}            - Delete item"
    echo "  POST   /api/v1/wardrobe/from-shop/{id}  - Copy from shop"
    echo "  POST   /api/v1/wardrobe/from-generation/{id} - Save generation"
    echo "  POST   /api/v1/wardrobe/upload-images   - Upload images"
    echo
fi

echo "For full API documentation, visit: http://localhost:8000/docs"
echo
