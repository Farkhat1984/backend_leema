# API Tests for Fashion AI Platform

Comprehensive test suite for all API endpoints using pytest and httpx.

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_auth.py` - Authentication endpoint tests
- `test_users.py` - User endpoint tests
- `test_shops.py` - Shop endpoint tests
- `test_products.py` - Product endpoint tests
- `test_payments.py` - Payment endpoint tests
- `test_generations.py` - AI generation endpoint tests
- `test_admin.py` - Admin endpoint tests

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_auth.py
pytest tests/test_users.py
```

### Run specific test class
```bash
pytest tests/test_auth.py::TestAuthEndpoints
```

### Run specific test
```bash
pytest tests/test_auth.py::TestAuthEndpoints::test_create_test_token_user
```

### Run tests by marker
```bash
# Run only auth tests
pytest -m auth

# Run only user tests
pytest -m user

# Run only admin tests
pytest -m admin
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

## Test Markers

- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.user` - User endpoint tests
- `@pytest.mark.shop` - Shop endpoint tests
- `@pytest.mark.product` - Product endpoint tests
- `@pytest.mark.payment` - Payment endpoint tests
- `@pytest.mark.generation` - Generation endpoint tests
- `@pytest.mark.admin` - Admin endpoint tests

## Fixtures Available

### Database
- `db_session` - Test database session (in-memory SQLite)

### HTTP Client
- `client` - Async HTTP client for API requests

### Test Users
- `test_user` - Regular user account
- `test_admin` - Admin user account
- `test_shop` - Shop account
- `test_product` - Test product with approved status

### Authentication
- `user_token` - JWT token for test user
- `admin_token` - JWT token for test admin
- `shop_token` - JWT token for test shop
- `auth_headers_user` - Authorization headers for user
- `auth_headers_admin` - Authorization headers for admin
- `auth_headers_shop` - Authorization headers for shop

## Test Coverage

The test suite covers:

### Authentication (test_auth.py)
- ✓ Google OAuth URL generation
- ✓ Test token creation for users/shops/admin
- ✓ Token refresh functionality
- ✓ Invalid authentication scenarios

### Users (test_users.py)
- ✓ Get current user info
- ✓ Update user profile
- ✓ Get user balance
- ✓ Get transaction history
- ✓ Get generation history
- ✓ Pagination
- ✓ Authorization checks

### Shops (test_shops.py)
- ✓ Get current shop info
- ✓ Update shop profile
- ✓ Get shop products
- ✓ Get shop analytics
- ✓ Get shop transactions
- ✓ Pagination
- ✓ Authorization checks

### Products (test_products.py)
- ✓ List active products
- ✓ Get product by ID
- ✓ Create product (shop)
- ✓ Update product (shop)
- ✓ Delete product (shop)
- ✓ Search functionality
- ✓ Ownership validation
- ✓ Authorization checks

### Payments (test_payments.py)
- ✓ Create top-up payment (user)
- ✓ Create rent payment (shop)
- ✓ Capture payment
- ✓ PayPal webhook handling
- ✓ Payment type validation
- ✓ Authorization checks

### Generations (test_generations.py)
- ✓ Generate fashion with AI
- ✓ Try on product
- ✓ Balance validation
- ✓ Authorization checks
- ✓ Invalid product handling

### Admin (test_admin.py)
- ✓ Dashboard statistics
- ✓ Platform settings management
- ✓ Moderation queue
- ✓ Approve/reject products
- ✓ Refund management
- ✓ Admin role verification

## Notes

- Tests use in-memory SQLite database for speed
- External services (PayPal, Gemini AI) are mocked
- Each test gets a fresh database session
- All tests are isolated and can run in parallel
- Authentication uses real JWT tokens for testing
