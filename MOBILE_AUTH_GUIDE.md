# Mobile Authentication Guide

## Overview

The backend now supports two authentication methods:

1. **Web OAuth Flow** - For web applications (uses authorization code)
2. **Mobile ID Token Flow** - For mobile applications (uses ID token)

## Authentication Methods

### 1. Web OAuth Flow (Authorization Code)

**Used by:** Web applications, admin panels

**Flow:**
1. Web app redirects user to Google OAuth URL
2. User authorizes the app
3. Google redirects back with an authorization `code`
4. Web app sends the `code` to backend
5. Backend exchanges `code` for tokens with Google
6. Backend returns JWT tokens

**Request Example:**
```json
POST /api/v1/auth/google/login
{
  "code": "4/0AeanS0...",
  "account_type": "user",
  "platform": "web"
}
```

### 2. Mobile ID Token Flow (Direct Token Verification)

**Used by:** Mobile applications (iOS, Android, Flutter)

**Flow:**
1. Mobile app uses Google Sign-In SDK
2. App receives ID token directly from Google
3. App sends the `id_token` to backend
4. Backend verifies the ID token with Google
5. Backend returns JWT tokens

**Request Example:**
```json
POST /api/v1/auth/google/login
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5N...",
  "account_type": "user",
  "platform": "mobile"
}
```

## Configuration

### Environment Variables

Add the Firebase configuration to your `.env` file:

```bash
# Firebase (for mobile apps)
FIREBASE_WEB_API=AIzaSyAWJ1YKsZhnZUG-9u_Ycx1pG-PMIP9bVHw
GOOGLE_MOBILE_CLIENT_ID=236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com
GOOGLE_ANDROID_CLIENT_ID=236011762515-ocf56786ddancro84gtb9cfeo1oc046q.apps.googleusercontent.com
```

**Firebase Project Info:**
- Project ID: `virtual-try-on-61143`
- Project Number: `236011762515`
- Android Package: `com.example.virtual_try_on`

The backend will automatically verify ID tokens from both web and Android clients.

### Google Cloud Console Setup

Ensure your Google OAuth2 credentials support both web and mobile:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Your OAuth 2.0 Client should have:
   - **Application type:** Web application (for web flow)
   - **Client ID:** Same one used in mobile apps
   - **Authorized redirect URIs:** Your web callback URL

## Mobile App Implementation

### Flutter Example

```dart
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

final GoogleSignIn _googleSignIn = GoogleSignIn(
  scopes: ['email', 'profile'],
  // Use the Web Client ID from your Firebase project
  clientId: '236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com',
);

Future<void> signInWithGoogle() async {
  try {
    // Sign in with Google
    final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
    if (googleUser == null) return; // User canceled
    
    // Get authentication
    final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
    final String? idToken = googleAuth.idToken;
    
    if (idToken == null) {
      throw Exception('Failed to get ID token');
    }
    
    // Send ID token to your backend
    final response = await http.post(
      Uri.parse('https://api.leema.kz/api/v1/auth/google/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'id_token': idToken,
        'account_type': 'user',
        'platform': 'mobile',
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final String accessToken = data['access_token'];
      final String refreshToken = data['refresh_token'];
      
      // Save tokens securely
      await saveTokens(accessToken, refreshToken);
      
      print('Authenticated successfully!');
    } else {
      throw Exception('Authentication failed: ${response.body}');
    }
  } catch (e) {
    print('Error during sign in: $e');
  }
}
```

### Android Native Example

```kotlin
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException

val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
    .requestIdToken("236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com")
    .requestEmail()
    .build()

val googleSignInClient = GoogleSignIn.getClient(this, gso)

// Start sign-in
val signInIntent = googleSignInClient.signInIntent
startActivityForResult(signInIntent, RC_SIGN_IN)

// Handle result
override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
    super.onActivityResult(requestCode, resultCode, data)
    
    if (requestCode == RC_SIGN_IN) {
        val task = GoogleSignIn.getSignedInAccountFromIntent(data)
        try {
            val account = task.getResult(ApiException::class.java)
            val idToken = account.idToken
            
            // Send to backend
            sendTokenToBackend(idToken)
        } catch (e: ApiException) {
            Log.w(TAG, "Google sign in failed", e)
        }
    }
}
```

### iOS Native Example

```swift
import GoogleSignIn

// Configure Google Sign-In
let config = GIDConfiguration(clientID: "236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com")
GIDSignIn.sharedInstance.configuration = config

// Sign in
GIDSignIn.sharedInstance.signIn(withPresenting: self) { signInResult, error in
    guard let result = signInResult else {
        print("Error: \(error?.localizedDescription ?? "Unknown error")")
        return
    }
    
    guard let idToken = result.user.idToken?.tokenString else {
        print("Failed to get ID token")
        return
    }
    
    // Send to backend
    sendTokenToBackend(idToken: idToken)
}

func sendTokenToBackend(idToken: String) {
    let url = URL(string: "https://api.leema.kz/api/v1/auth/google/login")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "id_token": idToken,
        "account_type": "user",
        "platform": "mobile"
    ]
    
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        // Handle response
    }.resume()
}
```

## API Response

Both authentication methods return the same response format:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "avatar_url": "https://...",
    "role": "user",
    "balance": 0.0,
    "free_generations_left": 3,
    "free_try_ons_left": 5
  },
  "account_type": "user",
  "platform": "mobile"
}
```

## Security Notes

1. **ID Token Verification**: The backend verifies ID tokens using Google's public keys, ensuring tokens are authentic and not tampered with.

2. **Client ID Validation**: ID tokens are validated against your Google OAuth Client ID to prevent token injection attacks.

3. **Token Expiration**: ID tokens expire after 1 hour. Your app should handle token refresh.

4. **HTTPS Only**: Always use HTTPS in production to prevent token interception.

5. **Secure Storage**: Store JWT tokens securely on the device:
   - iOS: Use Keychain
   - Android: Use EncryptedSharedPreferences
   - Flutter: Use flutter_secure_storage

## Troubleshooting

### "Invalid Google authentication credentials"

- Verify the ID token is not expired
- Ensure you're using the correct Google OAuth Client ID
- Check that the Client ID in your app matches the one in Google Cloud Console

### "Either 'code' or 'id_token' must be provided"

- Make sure you're sending either `code` (for web) or `id_token` (for mobile), not both or neither

### "Provide either 'code' or 'id_token', not both"

- Don't send both parameters in the same request. Use `code` for web flow, `id_token` for mobile flow

## Testing

You can test the mobile authentication using curl:

```bash
# Get an ID token from your mobile app first, then:
curl -X POST https://api.leema.kz/api/v1/auth/google/login \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "YOUR_ID_TOKEN_HERE",
    "account_type": "user",
    "platform": "mobile"
  }'
```

## Migration Notes

Existing web authentication continues to work without any changes. The mobile ID token support is an additional feature that doesn't affect the web OAuth flow.

## References

- [Google Sign-In for iOS](https://developers.google.com/identity/sign-in/ios)
- [Google Sign-In for Android](https://developers.google.com/identity/sign-in/android)
- [Google Sign-In for Flutter](https://pub.dev/packages/google_sign_in)
- [Verifying ID Tokens](https://developers.google.com/identity/sign-in/web/backend-auth)
