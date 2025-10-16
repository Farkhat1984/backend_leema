# Comprehensive API Testing Guide

## Overview
This test suite provides complete coverage of the Fashion AI Platform API using real credentials and scenarios.

## Test Credentials

### User Account
- **Email**: zfaragj@gmail.com
- **Role**: User/Admin
- **Purpose**: Testing user endpoints, AI generations, purchases

### Shop Account
- **Email**: ckdshfh@gmail.com
- **Role**: Shop Owner
- **Purpose**: Testing shop endpoints, product management

### PayPal Sandbox
- **Mode**: sandbox
- **Client ID**: From .env `PAYPAL_CLIENT_ID`
- **Client Secret**: From .env `PAYPAL_CLIENT_SECRET`
- **Test Account**: sb-0qexx39406981@business.example.com
- **Test Password**: YPETl7&<

### Gemini AI
- **API Key**: From .env `GEMINI_API_KEY`
- **Model**: gemini-2.0-flash-exp

## Test Files

### 1. `test_full_api_integration.py`
Complete API endpoint coverage with all operations:
- **Authentication**: Google OAuth, test tokens, refresh, logout
- **User Operations**: Profile, balance, transactions, history, orders
- **Shop Operations**: Profile, products, analytics, transactions
- **Products**: CRUD operations, search, reviews, purchase
- **Payments**: Top-up (user/shop), product rent, PayPal integration
- **AI Generations**: Text-to-image, person generation, clothing generation, try-on
- **Admin**: Dashboard, moderation, settings, user management

### 2. `test_real_scenarios.py`
Real-world user journey testing:
- **User First Login**: Complete onboarding flow
- **Product Browsing**: Search, filter, view details
- **AI Generation**: Using Gemini AI for fashion generation
- **Shop Management**: Product creation, analytics tracking
- **Payment Processing**: PayPal integration testing
- **Reviews & Ratings**: User feedback system
- **Admin Moderation**: Product approval workflow

### 3. `conftest.py`
Pytest configuration and fixtures:
- Database session management
- Test client setup
- User/Shop/Product fixtures
- Token generation helpers
- Credential management

## Running Tests

### Run All Tests
```bash
./run_full_api_tests.sh
```

### Run Specific Test Categories
```bash
# Authentication tests only
pytest tests/test_full_api_integration.py::TestAuthenticationFlow -v

# User endpoint tests
pytest tests/test_full_api_integration.py::TestUserEndpoints -v

# Shop endpoint tests
pytest tests/test_full_api_integration.py::TestShopEndpoints -v

# Product tests
pytest tests/test_full_api_integration.py::TestProductEndpoints -v

# Payment tests
pytest tests/test_full_api_integration.py::TestPaymentEndpoints -v -m payments

# AI generation tests
pytest tests/test_full_api_integration.py::TestGenerationEndpoints -v -m generations

# Admin tests
pytest tests/test_full_api_integration.py::TestAdminEndpoints -v -m admin

# Real scenarios
pytest tests/test_real_scenarios.py -v -s
```

### Run with Coverage
```bash
pytest tests/test_full_api_integration.py --cov=app --cov-report=html
```

### Run Specific Test
```bash
pytest tests/test_full_api_integration.py::TestAuthenticationFlow::test_create_test_token_user -v
```

## Test Scenarios Coverage

### User Journey
1. ✅ User registration/login via Google OAuth
2. ✅ View profile with free credits
3. ✅ Browse and search products
4. ✅ Generate AI fashion items
5. ✅ Try on products virtually
6. ✅ Top up balance via PayPal
7. ✅ Purchase products
8. ✅ Write product reviews
9. ✅ View order history
10. ✅ Check transaction history

### Shop Owner Journey
1. ✅ Shop registration/login
2. ✅ Create products with images
3. ✅ View shop analytics
4. ✅ Update product details
5. ✅ Top up shop balance
6. ✅ Rent product slots for visibility
7. ✅ View sales and revenue
8. ✅ Manage product inventory

### Admin Journey
1. ✅ View admin dashboard
2. ✅ Moderate pending products
3. ✅ Approve/reject products
4. ✅ Manage platform settings
5. ✅ View all users and shops
6. ✅ Process refund requests
7. ✅ Bulk operations
8. ✅ User role management

### Payment Flows
1. ✅ User balance top-up via PayPal
2. ✅ Shop balance top-up via PayPal
3. ✅ Product rent payment
4. ✅ Product purchase payment
5. ✅ Payment success callback
6. ✅ Payment cancellation
7. ✅ PayPal webhook handling

### AI Generation Flows
1. ✅ Generate image from text prompt
2. ✅ Generate person/model image
3. ✅ Generate clothing image
4. ✅ Apply clothing to model
5. ✅ Generate from text and reference images
6. ✅ Balance deduction on generation
7. ✅ Free credits usage

## Expected Test Results

### Successful Tests (200/201 responses)
- Health check
- Authentication endpoints
- Public product listing
- Product search
- User/Shop profile retrieval
- Analytics endpoints
- Review endpoints

### Expected Failures (due to business logic)
- 401: Unauthorized access without token
- 403: Forbidden (wrong role)
- 404: Resource not found
- 422: Validation errors
- 402: Insufficient balance for paid operations

## Environment Setup

### Required Environment Variables
```bash
# From .env file
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GEMINI_API_KEY=AIzaSy...
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
```

### Database
Tests use SQLite in-memory database for isolation:
- Fresh database for each test
- No data pollution between tests
- Fast execution

## Test Markers

Use pytest markers for selective testing:
```bash
# Run only integration tests
pytest -m integration

# Run only payment tests
pytest -m payments

# Run only generation tests
pytest -m generations

# Run only admin tests
pytest -m admin

# Skip slow tests
pytest -m "not slow"
```

## PayPal Testing

### Manual PayPal Flow Testing
1. Run the payment creation test
2. Copy the approval URL from output
3. Open URL in browser
4. Login with sandbox credentials:
   - Email: sb-0qexx39406981@business.example.com
   - Password: YPETl7&<
5. Approve the payment
6. Observe redirect to success callback

### Automated PayPal Testing
The test suite creates PayPal orders but doesn't complete them automatically (requires manual approval in sandbox).

## Gemini AI Testing

### API Key Setup
Ensure `GEMINI_API_KEY` in .env is valid:
```bash
GEMINI_API_KEY=AIzaSyBkuZtWOZGfo3exgJovUO5s0DZ59dh2TmQ
```

### Generation Testing
- Tests create actual API calls to Gemini
- May incur API usage costs
- Some tests may fail if quota exceeded
- Response time varies (2-10 seconds)

## Troubleshooting

### Database Connection Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
```

### Test Token Issues
```bash
# Regenerate test tokens
pytest tests/test_full_api_integration.py::TestAuthenticationFlow::test_create_test_token_user -v
```

### PayPal Connection Issues
- Verify `PAYPAL_MODE=sandbox`
- Check client ID and secret are valid
- Ensure PayPal sandbox is accessible

### Gemini API Issues
- Verify API key is valid
- Check quota limits
- Ensure internet connectivity

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
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

## Test Maintenance

### Adding New Tests
1. Add test method to appropriate test class
2. Use existing fixtures for setup
3. Follow naming convention: `test_<scenario>_<action>`
4. Add appropriate markers
5. Update this documentation

### Updating Credentials
1. Update .env file
2. Update conftest.py fixtures if needed
3. Update TEST_GUIDE.md documentation

## Performance Benchmarks

Expected test execution times:
- Authentication tests: ~2-5 seconds
- User/Shop CRUD: ~1-3 seconds per test
- Product operations: ~2-4 seconds per test
- Payment creation: ~3-7 seconds (PayPal API)
- AI generations: ~5-15 seconds (Gemini API)
- Full suite: ~5-10 minutes

## Coverage Goals

Target coverage: 80%+
- API endpoints: 100%
- Business logic: 85%+
- Error handling: 90%+
- Edge cases: 70%+

Run coverage report:
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
open htmlcov/index.html
```

## Support

For issues or questions:
1. Check test output for detailed error messages
2. Review API logs in `app.log`
3. Verify .env configuration
4. Check database connectivity
5. Validate external API credentials (PayPal, Gemini)
