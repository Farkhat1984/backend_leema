# Apple Sign In Integration - Ready ✅

## Статус: Полностью настроено и готово к использованию!

Apple Sign In полностью настроен на backend и готов к интеграции с iOS/Flutter приложением.

## Конфигурация

### Apple Developer Account
- **Team ID:** MCMQHQ6XT9
- **Service ID (Client ID):** com.leema.leemaapp
- **Key ID:** G8HC4Y8QC6
- **Bundle ID:** com.leema.app
- **Redirect URI:** https://api.leema.kz/api/v1/auth/apple/callback
- **Private Key:** Загружен и работает ✅

### Проверка конфигурации
```bash
# Проверить, что все настройки загружены
docker exec fashion_backend python3 /app/test_apple_auth.py
```

Результат:
```
✅ ALL TESTS PASSED - Apple Sign In is READY!
```

## API Endpoints

### 1. Mobile Flow (для Flutter/iOS приложения)

**Endpoint:** `POST /api/v1/auth/apple/login`

**Request Body:**
```json
{
  "account_type": "user",  // или "shop"
  "platform": "mobile",
  "id_token": "eyJraWQiOiJXNldjT0tCIiwiYWxnIjoiUlMyNTYifQ...",
  "user_data": {
    "first_name": "Иван",
    "last_name": "Иванов"
  }
}
```

**Response (Success - 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "apple_id": "001234.567890abcdef.1234",
    "email": "user@privaterelay.appleid.com",
    "name": "Иван Иванов",
    "balance": 0.0,
    "free_generations_left": 3,
    "free_try_ons_left": 3,
    "role": "user"
  },
  "account_type": "user",
  "platform": "mobile"
}
```

**Response (Error - 401):**
```json
{
  "detail": "Invalid Apple authentication credentials"
}
```

### 2. Web Flow (для веб-приложения)

#### Шаг 1: Получить Authorization URL
**Endpoint:** `GET /api/v1/auth/apple/url?account_type=user`

**Response:**
```json
{
  "authorization_url": "https://appleid.apple.com/auth/authorize?client_id=com.leema.leemaapp&redirect_uri=https%3A%2F%2Fapi.leema.kz%2Fapi%2Fv1%2Fauth%2Fapple%2Fcallback...",
  "account_type": "user"
}
```

#### Шаг 2: Redirect пользователя на `authorization_url`

#### Шаг 3: Callback обрабатывается автоматически
**Endpoint:** `POST /api/v1/auth/apple/callback`
Apple автоматически отправит данные на этот endpoint через form_post.

## Flutter/iOS Integration

### 1. Добавить зависимость
```yaml
# pubspec.yaml
dependencies:
  sign_in_with_apple: ^5.0.0
```

### 2. Настроить iOS проект

#### Xcode Configuration
1. Открыть `ios/Runner.xcworkspace`
2. В **Signing & Capabilities** добавить **Sign in with Apple**
3. В `Info.plist` добавить:
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>com.leema.app</string>
        </array>
    </dict>
</array>
```

### 3. Код авторизации (Flutter)

```dart
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<Map<String, dynamic>> signInWithApple({
  required String accountType, // "user" или "shop"
}) async {
  try {
    // 1. Получить credential от Apple
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );

    // 2. Подготовить данные для backend
    final requestBody = {
      'account_type': accountType,
      'platform': 'mobile',
      'id_token': credential.identityToken,
    };

    // 3. Добавить имя при первом входе (Apple предоставляет только один раз!)
    if (credential.givenName != null || credential.familyName != null) {
      requestBody['user_data'] = {
        'first_name': credential.givenName ?? '',
        'last_name': credential.familyName ?? '',
      };
    }

    // 4. Отправить на backend
    final response = await http.post(
      Uri.parse('https://api.leema.kz/api/v1/auth/apple/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(requestBody),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      
      // 5. Сохранить токены
      await saveTokens(
        accessToken: data['access_token'],
        refreshToken: data['refresh_token'],
      );

      return {
        'success': true,
        'user': data['user'],
      };
    } else {
      return {
        'success': false,
        'error': jsonDecode(response.body)['detail'],
      };
    }
  } catch (e) {
    return {
      'success': false,
      'error': e.toString(),
    };
  }
}

// Использование
void _handleAppleSignIn() async {
  final result = await signInWithApple(accountType: 'user');
  
  if (result['success']) {
    // Успешная авторизация
    print('Пользователь: ${result['user']['name']}');
    // Перейти на главный экран
  } else {
    // Показать ошибку
    print('Ошибка: ${result['error']}');
  }
}
```

### 4. UI Кнопка

```dart
SignInWithAppleButton(
  onPressed: _handleAppleSignIn,
  text: 'Войти через Apple',
  borderRadius: BorderRadius.circular(8),
)
```

## Важные особенности Apple Sign In

### ⚠️ Имя пользователя
**Apple предоставляет имя (first_name, last_name) ТОЛЬКО ПРИ ПЕРВОМ ВХОДЕ!**

При первом входе обязательно сохраните `credential.givenName` и `credential.familyName` и отправьте на backend:
```dart
if (credential.givenName != null || credential.familyName != null) {
  requestBody['user_data'] = {
    'first_name': credential.givenName ?? '',
    'last_name': credential.familyName ?? '',
  };
}
```

При последующих входах Apple НЕ отправит имя - backend будет использовать сохраненное.

### 🔒 Email Privacy
Пользователь может выбрать:
1. **Реальный email** - будет доступен в `user_info["email"]`
2. **Hide My Email** - Apple создаст приватный relay email типа `xyz@privaterelay.appleid.com`

Backend обрабатывает оба случая.

### 🔑 Apple ID
`apple_id` (поле `sub` в ID токене) - это уникальный идентификатор пользователя для вашего приложения.
Он всегда одинаковый для одного пользователя в одном приложении.

## Тестирование

### 1. Проверить конфигурацию на backend:
```bash
curl -s "https://api.leema.kz/api/v1/auth/apple/url?account_type=user" | jq
```

### 2. Тестовый вход (iOS Simulator или реальное устройство):
- Используйте реальный Apple ID
- Simulator поддерживает Apple Sign In начиная с iOS 13.0+

### 3. Проверить логи:
```bash
docker logs fashion_backend | grep "APPLE"
```

## Troubleshooting

### Ошибка: "Invalid Apple authentication credentials"
- Проверьте, что id_token не истёк (токены живут 10 минут)
- Убедитесь, что токен сгенерирован для правильного Client ID
- Проверьте логи backend: `docker logs fashion_backend --tail 50`

### Ошибка: "Invalid client"
- Проверьте, что Client ID в Apple Developer Console совпадает с `APPLE_CLIENT_ID` на backend
- Убедитесь, что Service ID правильно настроен

### Ошибка при генерации client_secret
- Проверьте, что приватный ключ (.p8) правильно загружен
- Проверьте, что Key ID совпадает с тем, что в Apple Developer Console

## Проверка статуса

```bash
# В контейнере
docker exec fashion_backend python3 /app/test_apple_auth.py

# Ожидаемый результат:
# ✅ ALL TESTS PASSED - Apple Sign In is READY!
```

## Итог

✅ **Apple Sign In полностью настроен и готов к использованию!**

- Все креды загружены и валидны
- JWT client_secret генерируется успешно  
- Endpoints работают корректно
- Можно начинать интеграцию в Flutter приложение

Для вопросов смотрите логи:
```bash
docker logs fashion_backend -f | grep APPLE
```
