#!/usr/bin/env python3
"""
Google OAuth Configuration Checker
This script helps diagnose Google OAuth issues
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_config():
    print("=" * 80)
    print("GOOGLE OAUTH CONFIGURATION CHECK")
    print("=" * 80)
    print()
    
    # Check environment variables
    print("📋 ENVIRONMENT VARIABLES:")
    print("-" * 80)
    
    configs = {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI"),
        "GOOGLE_MOBILE_CLIENT_ID": os.getenv("GOOGLE_MOBILE_CLIENT_ID"),
        "GOOGLE_MOBILE_CLIENT_SECRET": os.getenv("GOOGLE_MOBILE_CLIENT_SECRET"),
        "GOOGLE_ANDROID_CLIENT_ID": os.getenv("GOOGLE_ANDROID_CLIENT_ID"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL"),
    }
    
    for key, value in configs.items():
        if value:
            # Mask secrets
            if "SECRET" in key:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {key}: {display_value}")
        else:
            print(f"❌ {key}: NOT SET")
    
    print()
    print("=" * 80)
    print("🔍 REQUIRED GOOGLE CLOUD CONSOLE SETTINGS:")
    print("=" * 80)
    print()
    
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    frontend_url = os.getenv("FRONTEND_URL", "")
    
    print("1️⃣  AUTHORIZED REDIRECT URIs (in Google Cloud Console):")
    print("   You MUST add these exact URIs to your OAuth client:")
    print()
    if redirect_uri:
        print(f"   ✓ {redirect_uri}")
    print(f"   ✓ https://api.leema.kz/api/v1/auth/google/callback")
    print(f"   ✓ http://localhost:8000/api/v1/auth/google/callback  (for testing)")
    print()
    
    print("2️⃣  AUTHORIZED JAVASCRIPT ORIGINS (in Google Cloud Console):")
    print("   You MUST add these origins:")
    print()
    if frontend_url:
        print(f"   ✓ {frontend_url}")
    print(f"   ✓ https://api.leema.kz")
    print(f"   ✓ https://www.leema.kz")
    print(f"   ✓ https://leema.kz")
    print(f"   ✓ http://localhost:8000  (for testing)")
    print(f"   ✓ http://localhost:3000  (for testing)")
    print()
    
    print("=" * 80)
    print("📝 BACKEND API ENDPOINTS:")
    print("=" * 80)
    print()
    print("Get OAuth URL:")
    print(f"   GET https://api.leema.kz/api/v1/auth/google/url?account_type=shop&platform=web")
    print()
    print("OAuth Callback:")
    print(f"   GET https://api.leema.kz/api/v1/auth/google/callback?code=XXX&state=XXX")
    print()
    print("Login with code:")
    print(f"   POST https://api.leema.kz/api/v1/auth/google/login")
    print(f"   Body: {{'code': 'XXX', 'account_type': 'shop', 'platform': 'web'}}")
    print()
    
    print("=" * 80)
    print("🔧 TROUBLESHOOTING STEPS:")
    print("=" * 80)
    print()
    print("If you're getting 404 errors:")
    print()
    print("1. Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/credentials")
    print()
    print("2. Select your project")
    print()
    print("3. Click on your OAuth 2.0 Client ID")
    print()
    print("4. Verify AUTHORIZED REDIRECT URIs contains:")
    print(f"   - {redirect_uri}")
    print("   - https://api.leema.kz/api/v1/auth/google/callback")
    print()
    print("5. Verify AUTHORIZED JAVASCRIPT ORIGINS contains:")
    print(f"   - {frontend_url}")
    print("   - https://api.leema.kz")
    print("   - https://www.leema.kz")
    print()
    print("6. Save changes and wait 5-10 minutes for Google to propagate")
    print()
    print("7. Clear browser cache and cookies")
    print()
    print("8. Test again")
    print()
    
    print("=" * 80)
    print("🚨 COMMON ISSUES:")
    print("=" * 80)
    print()
    print("❌ Error 404 'redirect_uri_mismatch':")
    print("   → The redirect URI in your code doesn't match Google Console")
    print("   → Solution: Add the exact URI to Authorized Redirect URIs")
    print()
    print("❌ Error 'origin_mismatch':")
    print("   → JavaScript origin not authorized")
    print("   → Solution: Add your domain to Authorized JavaScript Origins")
    print()
    print("❌ Error 'invalid_client':")
    print("   → Wrong client ID or secret")
    print("   → Solution: Double-check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    print()
    
    # Check if client ID looks valid
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if client_id:
        if not client_id.endswith(".apps.googleusercontent.com"):
            print("⚠️  WARNING: GOOGLE_CLIENT_ID doesn't look like a valid Google client ID")
            print(f"   Expected format: XXXXXXXXX-XXXXXXXX.apps.googleusercontent.com")
            print(f"   Got: {client_id}")
            print()
    
    print("=" * 80)
    print()

if __name__ == "__main__":
    check_config()
