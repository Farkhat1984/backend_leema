"""
Quick Test Reference Guide
===========================

RUNNING TESTS
-------------

# Run all tests
./run_tests.sh

# Run specific test file
pytest tests/test_auth_comprehensive.py -v
pytest tests/test_users_comprehensive.py -v
pytest tests/test_shops_comprehensive.py -v
pytest tests/test_products_comprehensive.py -v
pytest tests/test_payments_comprehensive.py -v
pytest tests/test_generations_comprehensive.py -v
pytest tests/test_admin_comprehensive.py -v
pytest tests/test_integration.py -v

# Run specific test function
pytest tests/test_auth_comprehensive.py::TestAuthEndpoints::test_google_login_user_success -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run fast (skip integration)
./run_tests.sh --fast

# Run without coverage
./run_tests.sh --no-coverage


TEST CREDENTIALS
----------------

User Account: zfaragj@gmail.com
Shop Account: ckdshfh@gmail.com

PayPal Sandbox:
- Client ID: ASFzSjsoyZ2FVCU9aCprMeTGjBr14DDN5i_6e52N6NuZ60Jk_4bLy2zKFiYTEHG9uOlZso52sAVaCUrG
- Secret: EA5O0wQnrbK3XNz1ykm9H3Ac3IxNWWGDX4hPP8KTnuKCEkDuuNkW2L9CetC3MxXLLg0LI8Xr_4SDXsrt
- Test Email: sb-0qexx39406981@business.example.com

Gemini API:
- Key: AIzaSyBkuZtWOZGfo3exgJovUO5s0DZ59dh2TmQ


TEST CATEGORIES
---------------

Authentication (test_auth_comprehensive.py):
✓ Google OAuth login (user/shop)
✓ Token refresh and logout
✓ Invalid/expired tokens
✓ Platform-specific auth
✓ Test token generation

Users (test_users_comprehensive.py):
✓ Profile management
✓ Balance and credits
✓ Transaction history
✓ Generation history
✓ Order management
✓ Access control

Shops (test_shops_comprehensive.py):
✓ Shop profile management
✓ Product management
✓ Analytics
✓ Transactions
✓ Data isolation

Products (test_products_comprehensive.py):
✓ CRUD operations
✓ Search and filters
✓ Moderation
✓ Reviews
✓ Ownership validation

Payments (test_payments_comprehensive.py):
✓ User/shop top-up
✓ Purchases and rentals
✓ PayPal webhooks
✓ Payment verification
✓ Amount validation

Generations (test_generations_comprehensive.py):
✓ Fashion generation
✓ Try-on
✓ Apply clothing
✓ Generate person/clothing
✓ Credit charging
✓ Gemini integration

Admin (test_admin_comprehensive.py):
✓ User/shop management
✓ Dashboard stats
✓ Product moderation
✓ Settings management
✓ Refunds
✓ Access control

Integration (test_integration.py):
✓ Full user workflows
✓ Shop workflows
✓ Product lifecycle
✓ Payment workflows
✓ Data isolation


COMMON COMMANDS
---------------

# Install dependencies
pip install -r requirements.txt

# Make test runner executable
chmod +x run_tests.sh

# Run with specific marker
pytest -m auth
pytest -m payments
pytest -m admin

# Run with verbose output
pytest -vv

# Run with stdout (print statements)
pytest -s

# Run last failed tests
pytest --lf

# Run only failed tests
pytest --ff

# Stop on first failure
pytest -x

# Show slowest tests
pytest --durations=10


DEBUGGING
---------

# Run single test with print output
pytest tests/test_auth_comprehensive.py::TestAuthEndpoints::test_google_login_user_success -s -v

# Run with detailed traceback
pytest --tb=long

# Run with pdb debugger
pytest --pdb

# Show local variables in traceback
pytest -l


COVERAGE
--------

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View coverage in terminal
pytest --cov=app --cov-report=term-missing

# Coverage for specific module
pytest --cov=app.api --cov-report=term

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux


EXPECTED RESULTS
----------------

Total Tests: ~280+
Expected Pass Rate: 70-90% (depending on implementation completeness)

Some tests may fail if:
- Endpoints are not fully implemented
- Schema validation differs
- Business logic differs from assumptions
- External services not properly mocked

This is NORMAL - the tests help identify what needs to be implemented!


TROUBLESHOOTING
---------------

Error: "ModuleNotFoundError: No module named 'app'"
Solution: Run from project root: cd /var/www/backend

Error: "Database connection failed"
Solution: Set environment: export TESTING=1

Error: "Fixture not found"
Solution: Check conftest.py is in tests/ directory

Error: "AsyncIO event loop error"
Solution: Install pytest-asyncio: pip install pytest-asyncio

Error: "Coverage not working"
Solution: Install pytest-cov: pip install pytest-cov


NEXT STEPS
----------

1. Run all tests: ./run_tests.sh
2. Review failed tests
3. Implement missing functionality
4. Re-run tests until passing
5. Check coverage report
6. Add tests for any new endpoints
