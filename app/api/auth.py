from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.google_auth import google_auth
from app.core.apple_auth import apple_auth
from app.core.security import create_access_token, create_refresh_token, verify_token, verify_token_async
from app.services.user_service import user_service
from app.services.shop_service import shop_service
from app.schemas.auth import (
    GoogleAuthRequest, GoogleAuthResponse, AppleAuthRequest, AppleAuthResponse,
    Token, RefreshTokenRequest, LogoutRequest, AccountType, ClientPlatform
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.shop import ShopCreate, ShopResponse
from app.config import settings
from app.models.user import UserRole, User
from app.api.deps import get_current_user
from app.core.redis import redis_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/google/login", response_model=GoogleAuthResponse)
async def google_login(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user/shop via Google OAuth
    Supports two authentication methods:
    1. Web OAuth flow: Send 'code' (authorization code)
    2. Mobile flow: Send 'id_token' (Google ID token)
    
    account_type: 'user' or 'shop'
    platform: 'web' or 'mobile'
    """
    # Debug logging
    print(f"[AUTH DEBUG] Request received:")
    print(f"  - platform: {request.platform}")
    print(f"  - account_type: {request.account_type}")
    print(f"  - has code: {bool(request.code)}")
    print(f"  - has id_token: {bool(request.id_token)}")
    if request.id_token:
        print(f"  - id_token preview: {request.id_token[:50]}...")
    if request.code:
        print(f"  - code preview: {request.code[:50]}...")
    
    # Validate request - must have either code or id_token
    if not request.code and not request.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'code' or 'id_token' must be provided"
        )
    
    if request.code and request.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'code' or 'id_token', not both"
        )
    
    # Get user info from Google
    user_info = None
    
    if request.code:
        # Web flow: Exchange authorization code for tokens
        user_info = await google_auth.verify_oauth_code(request.code)
    elif request.id_token:
        # Mobile flow: Verify ID token directly
        user_info = google_auth.verify_id_token(request.id_token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google authentication credentials"
        )

    if request.account_type == AccountType.USER:
        # Check if user exists
        user = await user_service.get_by_google_id(db, user_info["google_id"])
        if not user:
            # Create new user
            user_data = UserCreate(
                google_id=user_info["google_id"],
                email=user_info["email"],
                name=user_info["name"],
                avatar_url=user_info.get("avatar_url")
            )
            user = await user_service.create(db, user_data)

        # Create tokens with enhanced claims
        token_data = {
            "user_id": user.id,
            "role": user.role.value,
            "platform": request.platform.value,
            "account_type": AccountType.USER.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return GoogleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user).model_dump(),
            account_type=AccountType.USER,
            platform=request.platform
        )

    elif request.account_type == AccountType.SHOP:
        # Check if shop exists
        shop = await shop_service.get_by_google_id(db, user_info["google_id"])
        is_new_shop = shop is None
        
        if not shop:
            # Create new shop
            shop_data = ShopCreate(
                google_id=user_info["google_id"],
                email=user_info["email"],
                shop_name=user_info["name"],  # Can be updated later
                owner_name=user_info["name"],
                avatar_url=user_info.get("avatar_url")
            )
            shop = await shop_service.create(db, shop_data)
            
            # Send WebSocket event for new shop
            from app.core.websocket import connection_manager
            from app.schemas.webhook import create_shop_event, WebhookEventType
            from app.schemas.shop import ShopListItem
            
            # Prepare shop data for event
            shop_dict = ShopListItem(
                id=shop.id,
                shop_name=shop.shop_name,
                description=shop.description,
                avatar_url=shop.avatar_url,
                logo_url=shop.avatar_url,
                products_count=0,
                is_approved=shop.is_approved,
                is_active=shop.is_active,
                created_at=shop.created_at
            ).model_dump(mode='json')
            
            shop_event = create_shop_event(
                event_type=WebhookEventType.SHOP_CREATED,
                shop_id=shop.id,
                shop_name=shop.shop_name,
                owner_name=shop.owner_name,
                action="created",
                is_approved=shop.is_approved,
                is_active=shop.is_active,
                shop=shop_dict
            )
            
            # Broadcast to all users (mobile apps)
            await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
            logger.info(f"✅ Shop created event sent: {shop.shop_name}")

        # Create tokens with enhanced claims
        token_data = {
            "shop_id": shop.id,
            "role": "shop",  # Shop role
            "platform": request.platform.value,
            "account_type": AccountType.SHOP.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return GoogleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            shop=ShopResponse.model_validate(shop).model_dump(),
            account_type=AccountType.SHOP,
            platform=request.platform
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account_type. Must be 'user' or 'shop'"
        )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token (checks blacklist)"""
    # Use async verification to check blacklist
    payload = await verify_token_async(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or blacklisted refresh token"
        )

    # Create new access token with same payload
    new_access_token = create_access_token({
        k: v for k, v in payload.items() if k not in ["exp", "type"]
    })

    return Token(
        access_token=new_access_token,
        refresh_token=request.refresh_token
    )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user/shop by invalidating refresh token.
    Adds token to blacklist (Redis) to prevent reuse.
    """
    # Use async verification to check token validity
    payload = await verify_token_async(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or already blacklisted refresh token"
        )
    
    # Add token to blacklist with TTL = token expiry
    expiry_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    blacklisted = await redis_client.blacklist_token(
        request.refresh_token,
        expiry_seconds
    )
    
    if blacklisted:
        logger.info(f"Token blacklisted successfully")
    else:
        logger.warning("Redis unavailable - token not blacklisted (still expires naturally)")
    
    return {"message": "Successfully logged out"}


@router.post("/user/get-or-create-shop", response_model=GoogleAuthResponse)
async def user_get_or_create_shop(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get or create shop for current user
    This allows users to also become shop owners
    """
    # Check if user already has a shop with same google_id
    shop = await shop_service.get_by_google_id(db, current_user.google_id)
    
    if not shop:
        # Create new shop for this user
        shop_data = ShopCreate(
            google_id=current_user.google_id,
            email=current_user.email,
            shop_name=f"{current_user.name}'s Shop",  # Default name, can be updated
            owner_name=current_user.name,
            avatar_url=current_user.avatar_url
        )
        shop = await shop_service.create(db, shop_data)
    
    # Create shop token
    token_data = {
        "shop_id": shop.id,
        "role": "shop",
        "platform": "web",
        "account_type": AccountType.SHOP.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return GoogleAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        shop=ShopResponse.model_validate(shop).model_dump(),
        account_type=AccountType.SHOP,
        platform=ClientPlatform.WEB
    )


@router.get("/google/url")
async def get_google_auth_url(
    account_type: AccountType = AccountType.USER,
    platform: ClientPlatform = ClientPlatform.WEB
):
    """
    Get Google OAuth authorization URL
    account_type: 'user' or 'shop'
    platform: 'web' or 'mobile'
    """
    url = google_auth.get_authorization_url(account_type.value, platform.value)
    return {"authorization_url": url, "account_type": account_type, "platform": platform}


@router.post("/test-token")
async def create_test_token(
    account_type: str = "user",
    db: AsyncSession = Depends(get_db)
):
    """
    Create test token for development (NO AUTHENTICATION)
    WARNING: This endpoint should be disabled in production!
    """
    # Disable in production
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )
    if account_type == "user":
        # Get or create test user
        user = await user_service.get_by_email(db, "test@example.com")
        if not user:
            user_data = UserCreate(
                google_id="test_user",
                email="test@example.com",
                name="Test User",
            )
            user = await user_service.create(db, user_data)

        access_token = create_access_token({"user_id": user.id, "role": user.role.value})
        refresh_token = create_refresh_token({"user_id": user.id, "role": user.role.value})

        return GoogleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user).model_dump(),
            account_type=AccountType.USER,
            platform=ClientPlatform.MOBILE
        )

    elif account_type == "shop":
        # Get or create test shop
        shop = await shop_service.get_by_email(db, "testshop@example.com")
        if not shop:
            shop_data = ShopCreate(
                google_id="test_shop",
                email="testshop@example.com",
                shop_name="Test Shop",
                owner_name="Test Owner"
            )
            shop = await shop_service.create(db, shop_data)

        access_token = create_access_token({"shop_id": shop.id})
        refresh_token = create_refresh_token({"shop_id": shop.id})

        return GoogleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            shop=ShopResponse.model_validate(shop).model_dump(),
            account_type=AccountType.SHOP,
            platform=ClientPlatform.MOBILE
        )

    elif account_type == "admin":
        # Get or create test admin
        user = await user_service.get_by_email(db, "admin@example.com")
        if not user:
            user_data = UserCreate(
                google_id="test_admin",
                email="admin@example.com",
                name="Test Admin",
            )
            user = await user_service.create(db, user_data)
            # Set as admin
            user.role = UserRole.ADMIN
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token({"user_id": user.id, "role": "admin"})
        refresh_token = create_refresh_token({"user_id": user.id, "role": "admin"})

        return GoogleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user).model_dump(),
            account_type=AccountType.USER,
            platform=ClientPlatform.MOBILE
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account_type. Must be 'user', 'shop', or 'admin'"
        )


@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(
    code: str,
    state: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth callback endpoint (GET)
    This is called by Google after user authorizes
    Returns HTML page that saves token and redirects
    """
    import json as json_lib

    try:
        # Parse state to get client_type and account_type
        state_data = {}
        if state:
            try:
                state_data = json_lib.loads(state)
                print(f"[OAUTH DEBUG] State parsed: {state_data}")
            except Exception as e:
                print(f"[OAUTH DEBUG] Failed to parse state: {e}")
                state_data = {}

        client_type = state_data.get("client_type", "web")
        requested_account_type = state_data.get("account_type", "shop")

        print(f"[OAUTH DEBUG] client_type: {client_type}, account_type: {requested_account_type}")

        if client_type != "mobile":
            from urllib.parse import urlencode

            params = {"code": code}
            if state:
                params["state"] = state
            if requested_account_type:
                params["account_type"] = requested_account_type
            params["client_type"] = client_type

            redirect_url = f"{settings.FRONTEND_URL}/callback?{urlencode(params)}"
            print(f"[OAUTH DEBUG] Redirecting web client to frontend callback: {redirect_url}")
            return RedirectResponse(url=redirect_url, status_code=302)

        # Initialize variables for mobile flow
        refresh_token = None
        user_data_json = {}

        # Verify Google OAuth code for mobile
        user_info = await google_auth.verify_oauth_code(code)
        if not user_info:
            return HTMLResponse(content=f"""
                <html>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Неверный код авторизации Google</p>
                    <a href="{settings.FRONTEND_URL}">Вернуться на главную</a>
                </body>
                </html>
            """, status_code=401)

        if client_type == "mobile":
            # Flutter app - always create/login as USER
            user = await user_service.get_by_google_id(db, user_info["google_id"])
            if not user:
                user_data = UserCreate(
                    google_id=user_info["google_id"],
                    email=user_info["email"],
                    name=user_info["name"],
                    avatar_url=user_info.get("avatar_url")
                )
                user = await user_service.create(db, user_data)

            role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
            token_payload = {"user_id": user.id, "role": role_str}
            access_token = create_access_token(token_payload)
            refresh_token = create_refresh_token(token_payload)
            account_type = 'user'

            # Prepare user data for Flutter
            user_data_json = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "role": role_str,
                "balance": float(user.balance),
                "free_generations_left": user.free_generations_left,
                "free_try_ons_left": user.free_try_ons_left,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported client type"
            )

        print(f"[OAUTH DEBUG] Final account_type: {account_type}, has access_token: {bool(access_token)}")

        # Return HTML that saves token and redirects
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Авторизация...</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                    }}
                    .loader {{
                        text-align: center;
                        color: white;
                    }}
                    .spinner {{
                        border: 4px solid rgba(255,255,255,0.3);
                        border-top: 4px solid white;
                        border-radius: 50%;
                        width: 50px;
                        height: 50px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 20px;
                    }}
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
            </head>
            <body>
                <div class="loader">
                    <div class="spinner"></div>
                    <p>Вход выполнен успешно! Перенаправление...</p>
                </div>
                <script>
                    const clientType = {json_lib.dumps(client_type)};
                    const token = {json_lib.dumps(access_token)};
                    const refreshToken = {json_lib.dumps(refresh_token)};
                    const accountType = {json_lib.dumps(account_type)};
                    const userData = {json_lib.dumps(user_data_json)};
                    const frontendBaseUrl = {json_lib.dumps(settings.FRONTEND_URL)};

                    console.log('[AUTH] Client type:', clientType);
                    console.log('[AUTH] Account type:', accountType);

                    if (clientType === 'mobile') {{
                        // Flutter Web - save to localStorage with special key
                        localStorage.setItem('flutter_auth_token', token);
                        localStorage.setItem('flutter_auth_refresh_token', refreshToken);
                        localStorage.setItem('flutter_auth_account_type', accountType);
                        localStorage.setItem('flutter_auth_user', JSON.stringify(userData));
                        localStorage.setItem('flutter_auth_complete', 'true');

                        console.log('[AUTH] Saved Flutter auth data to localStorage');

                        // Get the Flutter app origin from where we came from
                        const flutterOrigin = document.referrer || frontendBaseUrl;
                        console.log('[AUTH] Detected Flutter origin:', flutterOrigin);

                        // Show success message
                        document.querySelector('.loader').innerHTML =
                            '<h2 style="color: white;">✓ Авторизация успешна!</h2>' +
                            '<p style="color: white;">Возврат в приложение...</p>';

                        // Redirect back to Flutter app
                        setTimeout(function() {{
                            console.log('[AUTH] Redirecting to:', flutterOrigin);
                            window.location.href = flutterOrigin;
                        }}, 1500);
                    }}
                </script>
            </body>
            </html>
        """)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in google_callback: {error_details}")

        return HTMLResponse(content=f"""
            <html>
            <body style="font-family: monospace; padding: 20px;">
                <h1>Ошибка авторизации</h1>
                <p><strong>Сообщение:</strong> {str(e)}</p>
                <pre style="background: #f5f5f5; padding: 10px; overflow: auto;">{error_details}</pre>
                <a href="{settings.FRONTEND_URL}">Вернуться на главную</a>
            </body>
            </html>
        """, status_code=500)


# ============================================================================
# APPLE SIGN IN ENDPOINTS
# ============================================================================

@router.post("/apple/login", response_model=AppleAuthResponse)
async def apple_login(
    request: AppleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user/shop via Apple Sign In
    Supports two authentication methods:
    1. Web OAuth flow: Send 'code' (authorization code)
    2. Mobile flow: Send 'id_token' (Apple ID token)
    
    account_type: 'user' or 'shop'
    platform: 'web' or 'mobile'
    """
    logger.info(f"[APPLE AUTH] Request received:")
    logger.info(f"  - platform: {request.platform}")
    logger.info(f"  - account_type: {request.account_type}")
    logger.info(f"  - has code: {bool(request.code)}")
    logger.info(f"  - has id_token: {bool(request.id_token)}")
    
    # Validate request
    if not request.code and not request.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'code' or 'id_token' must be provided"
        )
    
    if request.code and request.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'code' or 'id_token', not both"
        )
    
    # Get user info from Apple
    user_info = None
    
    if request.code:
        # Web flow: Exchange authorization code
        user_info = await apple_auth.verify_authorization_code(request.code)
    elif request.id_token:
        # Mobile flow: Verify ID token
        user_info = apple_auth.verify_id_token(request.id_token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Apple authentication credentials"
        )
    
    # Extract user data from first-time sign in (Apple only provides this once!)
    if request.user_data:
        first_name = request.user_data.get("name", {}).get("firstName", "")
        last_name = request.user_data.get("name", {}).get("lastName", "")
        full_name = f"{first_name} {last_name}".strip() or "Apple User"
    else:
        full_name = user_info.get("name") or "Apple User"
    
    if request.account_type == AccountType.USER:
        # Check if user exists
        user = await user_service.get_by_apple_id(db, user_info["apple_id"])
        
        if not user:
            # Try to find by email if provided
            if user_info.get("email"):
                user = await user_service.get_by_email(db, user_info["email"])
                if user:
                    # Link Apple ID to existing account
                    user.apple_id = user_info["apple_id"]
                    await db.commit()
                    await db.refresh(user)
        
        if not user:
            # Create new user
            user_data = UserCreate(
                apple_id=user_info["apple_id"],
                email=user_info.get("email") or f"{user_info['apple_id']}@privaterelay.appleid.com",
                name=full_name,
                avatar_url=None  # Apple doesn't provide avatar
            )
            user = await user_service.create(db, user_data)
        
        # Create tokens
        token_data = {
            "user_id": user.id,
            "role": user.role.value,
            "platform": request.platform.value,
            "account_type": AccountType.USER.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return AppleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user).model_dump(),
            account_type=AccountType.USER,
            platform=request.platform
        )
    
    elif request.account_type == AccountType.SHOP:
        # Check if shop exists
        shop = await shop_service.get_by_apple_id(db, user_info["apple_id"])
        
        if not shop:
            # Try to find by email if provided
            if user_info.get("email"):
                shop = await shop_service.get_by_email(db, user_info["email"])
                if shop:
                    # Link Apple ID to existing account
                    shop.apple_id = user_info["apple_id"]
                    await db.commit()
                    await db.refresh(shop)
        
        if not shop:
            # Create new shop
            shop_data = ShopCreate(
                apple_id=user_info["apple_id"],
                email=user_info.get("email") or f"{user_info['apple_id']}@privaterelay.appleid.com",
                shop_name=f"{full_name}'s Shop",
                owner_name=full_name,
                avatar_url=None
            )
            shop = await shop_service.create(db, shop_data)
            
            # Send WebSocket event for new shop
            from app.core.websocket import connection_manager
            from app.schemas.webhook import create_shop_event, WebhookEventType
            from app.schemas.shop import ShopListItem
            
            shop_dict = ShopListItem(
                id=shop.id,
                shop_name=shop.shop_name,
                description=shop.description,
                avatar_url=shop.avatar_url,
                logo_url=shop.avatar_url,
                products_count=0,
                is_approved=shop.is_approved,
                is_active=shop.is_active,
                created_at=shop.created_at
            ).model_dump(mode='json')
            
            shop_event = create_shop_event(
                event_type=WebhookEventType.SHOP_CREATED,
                shop_id=shop.id,
                shop_name=shop.shop_name,
                owner_name=shop.owner_name,
                action="created",
                is_approved=shop.is_approved,
                is_active=shop.is_active,
                shop=shop_dict
            )
            
            await connection_manager.broadcast_to_type(shop_event.model_dump(mode='json'), "user")
            logger.info(f"✅ Shop created via Apple Sign In: {shop.shop_name}")
        
        # Create tokens
        token_data = {
            "shop_id": shop.id,
            "role": "shop",
            "platform": request.platform.value,
            "account_type": AccountType.SHOP.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return AppleAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            shop=ShopResponse.model_validate(shop).model_dump(),
            account_type=AccountType.SHOP,
            platform=request.platform
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account_type. Must be 'user' or 'shop'"
        )


@router.get("/apple/url")
async def get_apple_auth_url(
    account_type: AccountType = AccountType.USER,
    state: str = None
):
    """
    Get Apple Sign In authorization URL
    account_type: 'user' or 'shop'
    """
    import json
    if not state:
        state = json.dumps({"account_type": account_type.value})
    
    url = apple_auth.get_authorization_url(account_type.value, state)
    return {"authorization_url": url, "account_type": account_type}


@router.post("/apple/callback", response_class=HTMLResponse)
async def apple_callback(
    code: str = None,
    state: str = None,
    user: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Apple Sign In callback endpoint (POST)
    Apple sends data via form_post method
    """
    import json as json_lib
    
    try:
        logger.info(f"[APPLE CALLBACK] Received callback")
        logger.info(f"  - code: {code[:20] if code else 'None'}...")
        logger.info(f"  - state: {state}")
        logger.info(f"  - user: {user}")
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No authorization code provided"
            )
        
        # Parse state
        state_data = {}
        if state:
            try:
                state_data = json_lib.loads(state)
            except:
                pass
        
        account_type = state_data.get("account_type", "user")
        
        # Verify code and get user info
        user_info = await apple_auth.verify_authorization_code(code)
        
        if not user_info:
            return HTMLResponse(content=f"""
                <html>
                <body>
                    <h1>Apple Sign In Error</h1>
                    <p>Invalid authorization code</p>
                    <a href="{settings.FRONTEND_URL}">Return to home</a>
                </body>
                </html>
            """, status_code=401)
        
        # Parse user data if provided (first-time sign in only)
        user_data = None
        if user:
            try:
                user_data = json_lib.loads(user)
                logger.info(f"[APPLE CALLBACK] User data received: {user_data}")
            except:
                pass
        
        # Continue with authentication flow similar to Google callback
        # For now, redirect to frontend with code
        from urllib.parse import urlencode
        
        params = {
            "provider": "apple",
            "code": code,
            "account_type": account_type
        }
        
        if user_data:
            params["user_data"] = json_lib.dumps(user_data)
        
        redirect_url = f"{settings.FRONTEND_URL}/callback?{urlencode(params)}"
        logger.info(f"[APPLE CALLBACK] Redirecting to: {redirect_url}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in apple_callback: {error_details}")
        
        return HTMLResponse(content=f"""
            <html>
            <body style="font-family: monospace; padding: 20px;">
                <h1>Apple Sign In Error</h1>
                <p><strong>Message:</strong> {str(e)}</p>
                <pre style="background: #f5f5f5; padding: 10px; overflow: auto;">{error_details}</pre>
                <a href="{settings.FRONTEND_URL}">Return to home</a>
            </body>
            </html>
        """, status_code=500)
