# Fashion AI Platform - Comprehensive API Test Suite

## Quick Start

### Run All Tests
```bash
# Using bash script
./run_full_api_tests.sh

# Or using Python script
python run_api_tests.py all
```

### Run Specific Test Categories
```bash
# Authentication tests
python run_api_tests.py auth

# User tests
python run_api_tests.py user

# Shop tests
python run_api_tests.py shop

# Product tests
python run_api_tests.py products

# Payment tests (PayPal integration)
python run_api_tests.py payments

# AI Generation tests (Gemini)
python run_api_tests.py generations

# Admin tests
python run_api_tests.py admin

# Real-world scenarios
python run_api_tests.py scenarios

# With coverage report
python run_api_tests.py coverage
```

## Test Credentials

All credentials are loaded from `.env` file:

### User Account
- **Email**: zfaragj@gmail.com
- **Purpose**: User operations, AI generations

### Shop Account
- **Email**: ckdshfh@gmail.com
- **Purpose**: Shop management, product creation

### PayPal Sandbox
- **Test Email**: sb-0qexx39406981@business.example.com
- **Test Password**: YPETl7&<
- **Mode**: sandbox

### Gemini AI
- **API Key**: From .env
- **Model**: gemini-2.0-flash-exp

## Test Coverage

### 🔐 Authentication (8 tests)
- ✅ Google OAuth URL generation
- ✅ Test token creation (user/shop)
- ✅ Token refresh
- ✅ Logout
- ✅ OAuth callback handling

### 👤 User Endpoints (6 tests)
- ✅ Get current user
- ✅ Update user profile
- ✅ Get user balance
- ✅ View transactions
- ✅ View generation history
- ✅ View orders

### 🏪 Shop Endpoints (5 tests)
- ✅ Get shop info
- ✅ Update shop profile
- ✅ List shop products
- ✅ View shop analytics
- ✅ View shop transactions

### 🛍️ Product Endpoints (10 tests)
- ✅ List products (public)
- ✅ Advanced product search
- ✅ Create product
- ✅ Get product by ID
- ✅ Update product
- ✅ Delete product
- ✅ Upload product images
- ✅ Purchase product
- ✅ Create review
- ✅ Get reviews & stats

### 💳 Payment Endpoints (3 tests)
- ✅ User balance top-up (PayPal)
- ✅ Shop balance top-up (PayPal)
- ✅ Product rent payment (PayPal)
- ✅ Payment capture
- ✅ Success/cancel callbacks

### 🎨 AI Generation Endpoints (6 tests)
- ✅ Generate from text
- ✅ Generate person/model
- ✅ Generate clothing
- ✅ Generate from text + images
- ✅ Apply clothing to model
- ✅ Try-on virtual fashion

### 👑 Admin Endpoints (12 tests)
- ✅ Admin dashboard
- ✅ List all users
- ✅ List all shops
- ✅ Platform settings
- ✅ Moderation queue
- ✅ Approve/reject products
- ✅ User management
- ✅ Bulk operations
- ✅ Transaction monitoring

### 🌐 Health & Utility (3 tests)
- ✅ Root endpoint
- ✅ Health check
- ✅ WebSocket stats

### 🎯 Real-World Scenarios (8 scenarios)
- ✅ New user first login flow
- ✅ User browses and purchases
- ✅ User generates AI fashion
- ✅ Shop owner adds product
- ✅ Shop owner top-up & rent
- ✅ Admin moderates products
- ✅ User writes review
- ✅ Payment flow testing

## Test Files

```
tests/
├── TEST_GUIDE.md                      # Detailed testing guide
├── README_TESTS.md                    # This file
├── conftest.py                        # Pytest configuration & fixtures
├── test_full_api_integration.py       # All API endpoint tests
├── test_real_scenarios.py             # Real-world user scenarios
└── ... (other existing test files)
```

## Requirements

All tests use:
- **pytest**: Test framework
- **FastAPI TestClient**: HTTP client
- **SQLite (in-memory)**: Test database (isolated)
- **Real API credentials**: From .env file

## Running Tests

### Method 1: Bash Script (Recommended)
```bash
./run_full_api_tests.sh
```

### Method 2: Python Script
```bash
python run_api_tests.py all
```

### Method 3: Direct pytest
```bash
# All integration tests
pytest tests/test_full_api_integration.py -v -m integration

# Specific test class
pytest tests/test_full_api_integration.py::TestAuthenticationFlow -v

# Specific test
pytest tests/test_full_api_integration.py::TestAuthenticationFlow::test_create_test_token_user -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## Test Output

### Success Example
```
====================================
Fashion AI Platform - Full API Tests
====================================

✓ Loading environment variables from .env

Checking credentials...
✓ User Email: zfaragj@gmail.com
✓ Shop Email: ckdshfh@gmail.com
✓ PayPal Mode: sandbox
✓ Gemini API Key: AIzaSyBkuZtWOZGfo3e...

====================================
Running Full API Integration Tests
====================================

test_full_api_integration.py::TestAuthenticationFlow::test_get_google_auth_url_user PASSED
test_full_api_integration.py::TestAuthenticationFlow::test_create_test_token_user PASSED
test_full_api_integration.py::TestUserEndpoints::test_get_current_user PASSED
...

====================================
✓ All tests passed!
====================================
```

## Expected Results

### Should PASS (200/201)
- Health check
- Authentication endpoints
- Public product listing
- User/shop profile retrieval
- Analytics endpoints

### Expected Failures (Business Logic)
- **401 Unauthorized**: Access without token
- **403 Forbidden**: Wrong role access
- **404 Not Found**: Non-existent resources
- **422 Validation Error**: Invalid input
- **402 Payment Required**: Insufficient balance

## PayPal Testing

To test complete PayPal flow:

1. Run payment test to get approval URL
2. Copy the URL from test output
3. Open in browser
4. Login with sandbox credentials:
   - Email: `sb-0qexx39406981@business.example.com`
   - Password: `YPETl7&<`
5. Approve payment
6. Observe redirect to success callback

## Gemini AI Testing

AI generation tests make real API calls:
- May incur API usage costs
- Requires valid API key in .env
- Response time: 5-15 seconds
- May fail if quota exceeded

## Troubleshooting

### Database Issues
```bash
# Restart database
docker-compose down -v
docker-compose up -d postgres
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Issues
```bash
# Check .env file exists
ls -la .env

# Verify environment variables
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GEMINI_API_KEY'))"
```

### Test Failures
1. Check test output for error details
2. Verify .env credentials
3. Ensure database is accessible
4. Check external API availability (PayPal, Gemini)
5. Review logs in app.log

## Coverage Report

Generate HTML coverage report:
```bash
python run_api_tests.py coverage
open htmlcov/index.html
```

Target coverage: **80%+**

## CI/CD Integration

Tests can be run in CI/CD pipelines:

```yaml
# .github/workflows/tests.yml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          PAYPAL_CLIENT_ID: ${{ secrets.PAYPAL_CLIENT_ID }}
          PAYPAL_CLIENT_SECRET: ${{ secrets.PAYPAL_CLIENT_SECRET }}
        run: pytest tests/test_full_api_integration.py -v
```

## Performance

Expected execution times:
- **Full test suite**: 5-10 minutes
- **Auth tests**: ~5 seconds
- **User/Shop tests**: ~10 seconds
- **Product tests**: ~15 seconds
- **Payment tests**: ~20 seconds (PayPal API)
- **AI generation tests**: ~60 seconds (Gemini API)
- **Admin tests**: ~10 seconds

## Support & Maintenance

### Adding New Tests
1. Add to appropriate test file
2. Use existing fixtures
3. Follow naming: `test_<scenario>_<action>`
4. Add appropriate pytest markers
5. Update documentation

### Updating Credentials
1. Update `.env` file
2. Restart test environment
3. Verify new credentials work

## Next Steps

After running tests:
1. ✅ Review test output
2. ✅ Check coverage report
3. ✅ Fix any failing tests
4. ✅ Add tests for new features
5. ✅ Update documentation

## Resources

- **OpenAPI Spec**: See JSON provided
- **Test Guide**: `tests/TEST_GUIDE.md`
- **Pytest Docs**: https://docs.pytest.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

**Built with ❤️ for Fashion AI Platform**
