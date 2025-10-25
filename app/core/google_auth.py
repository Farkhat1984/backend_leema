from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from app.config import settings
import httpx
from typing import Optional, Dict


class GoogleAuth:
    """Google OAuth authentication handler"""

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        # Mobile client IDs for token verification
        self.mobile_client_id = settings.GOOGLE_MOBILE_CLIENT_ID
        self.ios_client_id = settings.GOOGLE_IOS_CLIENT_ID
        self.android_client_id = settings.GOOGLE_ANDROID_CLIENT_ID

    def get_authorization_url(self, account_type: str = "shop", client_type: str = "web") -> str:
        """
        Get Google OAuth authorization URL
        account_type: 'user' or 'shop'
        client_type: 'web' (admin panel) or 'mobile' (Flutter app)
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
        )
        flow.redirect_uri = self.redirect_uri

        # Use state to pass both account_type and client_type
        import json
        state = json.dumps({"account_type": account_type, "client_type": client_type})

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state
        )
        return authorization_url

    async def verify_oauth_code(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for user info"""
        try:
            # Exchange code for token using httpx directly
            async with httpx.AsyncClient() as client:
                # Get access token
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": self.redirect_uri,
                        "grant_type": "authorization_code",
                    }
                )

                if token_response.status_code != 200:
                    print(f"Token exchange failed: {token_response.text}")
                    return None

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    print("No access token in response")
                    return None

                # Get user info
                user_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if user_response.status_code != 200:
                    print(f"User info fetch failed: {user_response.text}")
                    return None

                user_info = user_response.json()

            return {
                "google_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "avatar_url": user_info.get("picture"),
            }
        except Exception as e:
            import traceback
            print(f"Google OAuth error: {e}")
            print(traceback.format_exc())
            return None

    def verify_id_token(self, token: str) -> Optional[Dict]:
        """Verify Google ID token (for mobile apps)"""
        try:
            # Try to verify with multiple client IDs (web, iOS, android)
            client_ids = [
                self.ios_client_id,  # iOS client ID
                self.android_client_id,  # Android client ID
                self.mobile_client_id,  # Web client ID from Firebase
                self.client_id  # Fallback to main web client ID
            ]
            
            idinfo = None
            last_error = None
            
            for client_id in client_ids:
                if not client_id:
                    continue
                try:
                    idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
                    print(f"[AUTH DEBUG] Token verified successfully with client_id: {client_id[:50]}...")
                    break  # Successfully verified
                except Exception as e:
                    last_error = e
                    print(f"[AUTH DEBUG] Failed to verify with client_id {client_id[:50]}...: {str(e)[:100]}")
                    continue
            
            if not idinfo:
                print(f"Token verification failed with all client IDs. Last error: {last_error}")
                return None
                
            return {
                "google_id": idinfo.get("sub"),
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "avatar_url": idinfo.get("picture"),
            }
        except Exception as e:
            print(f"Token verification error: {e}")
            return None


google_auth = GoogleAuth()
