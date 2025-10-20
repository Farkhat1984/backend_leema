# GET /api/v1/shops Endpoint - Implementation Summary

## Endpoint Details

**URL:** `GET /api/v1/shops/`

**Description:** Returns a list of approved shops with active products

**Authentication:** No authentication required (public endpoint)

## Response Format

```json
{
  "shops": [
    {
      "id": 1,
      "shop_name": "Название магазина",
      "description": "Описание магазина",
      "logo_url": "https://...",
      "avatar_url": "https://...",
      "products_count": 3,
      "is_approved": true,
      "created_at": "2025-10-13T13:22:50.440004Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

## Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Number of records to skip (pagination) |
| `limit` | int | 50 | Maximum number of records to return |
| `query` | string | None | Search by shop name or description |
| `sort_by` | string | "created_at" | Sort field: `created_at`, `shop_name`, `products_count` |
| `sort_order` | string | "desc" | Sort order: `asc` or `desc` |

## Features Implemented

✅ **Logo URL** - Both `logo_url` and `avatar_url` fields are included (logo_url is an alias for avatar_url)

✅ **Products Count** - Shows the number of active products for each shop

✅ **Filtering** - Only returns approved shops (`is_approved: true`) that have at least one active product

✅ **Pagination** - Full support with `skip` and `limit` parameters

✅ **Search** - Search by shop name or description using the `query` parameter

✅ **Sorting** - Sort by `created_at`, `shop_name`, or `products_count` with ascending/descending order

## Implementation Files

### 1. Schema (app/schemas/shop.py)
- Added `ShopListItem` - Response model for shop list items
- Added `ShopList` - Response model with shops array, total count, page info

### 2. Service (app/services/shop_service.py)
- Added `get_shops_list()` method with:
  - Subquery to count active products per shop
  - Filters for approved shops with active products
  - Search functionality
  - Sorting by multiple fields
  - Pagination support

### 3. API Route (app/api/shops.py)
- Added `GET /api/v1/shops/` public endpoint
- Supports all query parameters
- Returns paginated list with metadata

## Example Usage

### Get all shops (default)
```bash
curl "http://localhost:8000/api/v1/shops/"
```

### Search for shops
```bash
curl "http://localhost:8000/api/v1/shops/?query=fashion"
```

### Pagination
```bash
curl "http://localhost:8000/api/v1/shops/?skip=10&limit=20"
```

### Sort by products count
```bash
curl "http://localhost:8000/api/v1/shops/?sort_by=products_count&sort_order=desc"
```

### Sort by name
```bash
curl "http://localhost:8000/api/v1/shops/?sort_by=shop_name&sort_order=asc"
```

## Using Existing Endpoints for Shop Products

The existing `/api/v1/products/search` endpoint already supports filtering by shop:

```bash
# Get products from a specific shop
curl "http://localhost:8000/api/v1/products/search?shop_id=1"

# Get products from a shop with additional filters
curl "http://localhost:8000/api/v1/products/search?shop_id=1&min_price=100&max_price=500"
```

**Recommendation:** Use the existing `/api/v1/products/search?shop_id=X` endpoint for getting products of a specific shop. No need to create a new endpoint as this one provides:
- Full product details
- Price filtering
- Sorting options
- Pagination
- Moderation status filtering

## Testing

The endpoint has been tested and verified:
- ✅ Returns correct response format
- ✅ Includes all required fields (logo_url, products_count, etc.)
- ✅ Filters work correctly (approved shops with active products)
- ✅ Pagination works
- ✅ Search functionality works
- ✅ Sorting by different fields works
- ✅ OpenAPI documentation is auto-generated

## Database Query Optimization

The implementation uses:
- Efficient subquery for counting products
- LEFT JOIN to include shops even if product count is 0 (then filtered)
- Single database query with proper indexing support
- Only returns shops with at least 1 active product
