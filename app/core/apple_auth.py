import jwt
import time
import httpx
from typing import Optional, Dict
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AppleAuth:
    """Apple Sign In authentication handler"""

    def __init__(self):
        self.team_id = settings.APPLE_TEAM_ID
        self.client_id = settings.APPLE_CLIENT_ID
        self.key_id = settings.APPLE_KEY_ID
        self.private_key = settings.APPLE_PRIVATE_KEY
        self.redirect_uri = settings.APPLE_REDIRECT_URI
        
        # Apple's authentication endpoints
        self.auth_url = "https://appleid.apple.com/auth/authorize"
        self.token_url = "https://appleid.apple.com/auth/token"
        self.public_key_url = "https://appleid.apple.com/auth/keys"

    def generate_client_secret(self) -> str:
        """
        Generate JWT client secret for Apple Sign In
        This is used instead of a traditional client secret
        """
        headers = {
            "kid": self.key_id,
            "alg": "ES256"
        }
        
        payload = {
            "iss": self.team_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 180,  # 180 days (max allowed)
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }
        
        # Sign with ES256 algorithm using the private key
        client_secret = jwt.encode(
            payload,
            self.private_key,
            algorithm="ES256",
            headers=headers
        )
        
        return client_secret

    def get_authorization_url(self, account_type: str = "user", state: str = None) -> str:
        """
        Get Apple Sign In authorization URL
        
        Args:
            account_type: 'user' or 'shop'
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL
        """
        import json
        from urllib.parse import urlencode
        
        if not state:
            state = json.dumps({"account_type": account_type})
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code id_token",
            "response_mode": "form_post",
            "scope": "name email",
            "state": state,
        }
        
        return f"{self.auth_url}?{urlencode(params)}"

    async def verify_authorization_code(self, code: str) -> Optional[Dict]:
        """
        Exchange authorization code for tokens and user info
        
        Args:
            code: Authorization code from Apple
            
        Returns:
            Dictionary with user info or None if verification fails
        """
        try:
            client_secret = self.generate_client_secret()
            
            async with httpx.AsyncClient() as client:
                # Exchange code for tokens
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Apple token exchange failed: {response.text}")
                    return None
                
                token_data = response.json()
                id_token = token_data.get("id_token")
                
                if not id_token:
                    logger.error("No id_token in Apple response")
                    return None
                
                # Decode and verify ID token
                user_info = self.verify_id_token(id_token)
                return user_info
                
        except Exception as e:
            logger.error(f"Apple authorization code verification error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def verify_id_token(self, id_token: str) -> Optional[Dict]:
        """
        Verify and decode Apple ID token
        
        Args:
            id_token: JWT ID token from Apple
            
        Returns:
            Dictionary with user info or None if verification fails
        """
        try:
            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(id_token)
            
            # For now, decode without verification (in production, verify with Apple's public key)
            # TODO: Implement proper JWT verification with Apple's public keys
            decoded = jwt.decode(
                id_token,
                options={
                    "verify_signature": False,  # TODO: Enable in production
                    "verify_aud": True,
                    "verify_iss": True,
                },
                audience=self.client_id,
                issuer="https://appleid.apple.com"
            )
            
            # Extract user information
            apple_id = decoded.get("sub")  # Unique user identifier
            email = decoded.get("email")
            email_verified = decoded.get("email_verified", False)
            
            if not apple_id:
                logger.error("No 'sub' (user ID) in Apple ID token")
                return None
            
            # Note: Apple only provides name on first sign in
            # Store it immediately if provided
            return {
                "apple_id": apple_id,
                "email": email if email_verified else None,
                "email_verified": email_verified,
                "name": None,  # Will be provided separately in first sign in
            }
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Apple ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"Apple ID token verification error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def get_apple_public_keys(self) -> Optional[Dict]:
        """
        Fetch Apple's public keys for JWT verification
        
        Returns:
            Dictionary of public keys or None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.public_key_url)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch Apple public keys: {response.text}")
                    return None
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Error fetching Apple public keys: {e}")
            return None


# Global instance
apple_auth = AppleAuth()
