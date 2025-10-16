# Comprehensive Test Suite for Fashion AI Platform

## Overview
This test suite provides comprehensive coverage for all API endpoints, including authentication, user management, shop operations, product handling, payments, AI generations, and admin functions.

## Test Files

### Core Tests
- **test_auth_comprehensive.py** - Authentication tests (Google OAuth, tokens, refresh, logout)
- **test_users_comprehensive.py** - User endpoint tests (profile, balance, orders, history)
- **test_shops_comprehensive.py** - Shop endpoint tests (profile, products, analytics, transactions)
- **test_products_comprehensive.py** - Product tests (CRUD, search, moderation, reviews)
- **test_payments_comprehensive.py** - Payment tests (top-up, PayPal integration, webhooks)
- **test_generations_comprehensive.py** - AI generation tests (fashion gen, try-on, Gemini API)
- **test_admin_comprehensive.py** - Admin tests (moderation, settings, statistics, user management)
- **test_integration.py** - Integration tests (full user workflows, end-to-end scenarios)

### Configuration
- **conftest.py** - Pytest fixtures and configuration
- **pytest.ini** - Pytest settings and markers

## Setup

### Install Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

Or use requirements file:
```bash
pip install -r requirements.txt
```

### Environment Setup
Tests use credentials from `.env` file:
- `PAYPAL_CLIENT_ID` - PayPal sandbox client ID
- `PAYPAL_CLIENT_SECRET` - PayPal sandbox secret
- `GEMINI_API_KEY` - Google Gemini API key
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret

Test users:
- **User Account**: zfaragj@gmail.com (user/admin)
- **Shop Account**: ckdshfh@gmail.com (shop)

## Running Tests

### Run All Tests
```bash
./run_tests.sh
```

### Run Specific Test Suite
```bash
# Authentication tests
pytest tests/test_auth_comprehensive.py -v

# User tests
pytest tests/test_users_comprehensive.py -v

# Payment tests
pytest tests/test_payments_comprehensive.py -v

# AI generation tests
pytest tests/test_generations_comprehensive.py -v

# Admin tests
pytest tests/test_admin_comprehensive.py -v

# Integration tests
pytest tests/test_integration.py -v
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run Fast (Skip Integration Tests)
```bash
./run_tests.sh --fast
```

### Run Specific Test
```bash
./run_tests.sh --test test_auth_comprehensive.py
```

### Run Without Coverage
```bash
./run_tests.sh --no-coverage
```

## Test Markers

Tests are organized with markers:
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.payments` - Payment tests
- `@pytest.mark.admin` - Admin tests

Run tests by marker:
```bash
pytest -m auth  # Run only auth tests
pytest -m "not slow"  # Skip slow tests
```

## Test Scenarios

### Authentication Tests
- ✓ Google OAuth login (user/shop)
- ✓ Token refresh and logout
- ✓ Invalid tokens and expired tokens
- ✓ Platform-specific auth (web/mobile)
- ✓ Test token generation (dev mode)

### User Tests
- ✓ Get/update user profile
- ✓ Check balance and free credits
- ✓ Transaction history
- ✓ Generation history
- ✓ Order history with filters
- ✓ Unauthorized access prevention

### Shop Tests
- ✓ Get/update shop profile
- ✓ Manage products
- ✓ View analytics
- ✓ Transaction history
- ✓ Shop data isolation

### Product Tests
- ✓ CRUD operations
- ✓ Search and filtering
- ✓ Price range queries
- ✓ Moderation status
- ✓ Reviews and ratings
- ✓ Shop ownership validation

### Payment Tests
- ✓ User balance top-up
- ✓ Shop balance top-up
- ✓ Product purchases
- ✓ Product rentals
- ✓ PayPal webhook handling
- ✓ Payment verification
- ✓ Amount validation
- ✓ Admin prevention from user top-up

### Generation Tests
- ✓ Fashion generation
- ✓ Product try-on
- ✓ Apply clothing
- ✓ Generate person/clothing
- ✓ Balance/credit charging
- ✓ Free credit usage
- ✓ Gemini API integration
- ✓ Base64 image handling

### Admin Tests
- ✓ View all users/shops
- ✓ Dashboard statistics
- ✓ Product moderation (approve/reject)
- ✓ Platform settings management
- ✓ Balance management
- ✓ Refund handling
- ✓ Access control (admin-only)

### Integration Tests
- ✓ Complete user registration flow
- ✓ Complete shop workflow
- ✓ Product lifecycle (create -> approve -> active)
- ✓ Payment workflow (create -> webhook -> balance)
- ✓ Try-on workflow
- ✓ User data isolation
- ✓ Cross-platform authentication

## Test Database

Tests use an in-memory SQLite database for isolation:
- Fresh database for each test
- No pollution between tests
- Fast execution
- No cleanup required

## Mocking

External services are mocked:
- **Google OAuth** - Mocked authentication
- **PayPal API** - Mocked payment creation
- **Gemini AI** - Mocked image generation
- **Email service** - Mocked email sending

## Coverage Goals

Target coverage: **80%+** for:
- All API endpoints
- Authentication flows
- Payment processing
- AI generation
- Admin operations

## Continuous Integration

Tests can be integrated into CI/CD:
```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install -r requirements.txt
    ./run_tests.sh
```

## Troubleshooting

### Database Errors
If you get database errors, ensure:
```bash
export TESTING=1
export DEBUG=1
```

### Import Errors
Install all dependencies:
```bash
pip install -r requirements.txt
```

### Async Errors
Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

### Coverage Not Working
Install pytest-cov:
```bash
pip install pytest-cov
```

## Test Results

Test reports are saved in:
- `test_reports/` - JUnit XML reports
- `htmlcov/` - HTML coverage reports

View coverage:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Contributing

When adding new endpoints:
1. Add tests to appropriate test file
2. Update this README
3. Ensure tests pass: `./run_tests.sh`
4. Check coverage: `pytest --cov=app`

## Notes

- Tests use real user/shop emails from .env
- PayPal sandbox credentials included
- Gemini API key configured
- All sensitive operations are mocked in tests
- Database is isolated per test for safety
