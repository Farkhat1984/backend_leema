# Исправление: Google Sign In с iOS

## Проблема
Backend отклонял Google ID токены от iOS приложения с ошибкой `401 Unauthorized: Invalid Google authentication credentials`.

## Причина
При валидации JWT токенов backend проверял только Web и Android Client IDs, но не iOS Client ID. Токены от iOS содержали `aud` (audience) с iOS Client ID, который не был в списке разрешенных.

## Решение

### 1. Добавлен iOS Client ID в конфигурацию

**Файл: `.env`**
```env
GOOGLE_IOS_CLIENT_ID=236011762515-cp9drtdpjvmg9ddhoc1l4pnnkc26bt2c.apps.googleusercontent.com
```

**Файл: `app/config.py`**
```python
GOOGLE_IOS_CLIENT_ID: str = ""  # Optional - iOS-specific client ID
```

### 2. Обновлена логика верификации токенов

**Файл: `app/core/google_auth.py`**

Теперь метод `verify_id_token()` проверяет токены в следующем порядке:
1. iOS Client ID (для iOS приложения)
2. Android Client ID (для Android приложения)
3. Mobile/Web Client ID (для веб-приложения)
4. Main Client ID (запасной вариант)

Добавлены отладочные логи для диагностики:
```python
print(f"[AUTH DEBUG] Token verified successfully with client_id: {client_id[:50]}...")
print(f"[AUTH DEBUG] Failed to verify with client_id {client_id[:50]}...: {str(e)[:100]}")
```

### 3. Обновлена документация

**Файл: `.env.example`**
```env
GOOGLE_IOS_CLIENT_ID=your-ios-client-id.apps.googleusercontent.com
```

## Список всех Client IDs проекта

| Платформа | Client ID |
|-----------|-----------|
| Web | 236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com |
| iOS | 236011762515-cp9drtdpjvmg9ddhoc1l4pnnkc26bt2c.apps.googleusercontent.com |
| Android | 236011762515-ocf56786ddancro84gtb9cfeo1oc046q.apps.googleusercontent.com |

## Тестирование

Теперь iOS приложение может успешно авторизоваться через Google Sign In:

**Запрос:**
```json
POST /api/v1/auth/google/login
{
  "account_type": "user",
  "platform": "mobile",
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg4NDg5MjEyMmUyOTM5ZmQxZjMxMzc1YjJiMzYzZWM4MTU3MjNiYmIiLCJ0eXAiOiJKV1QifQ..."
}
```

**Ожидаемый результат:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {...},
  "account_type": "user",
  "platform": "mobile"
}
```

## Google Project Info
- **Project ID:** virtual-try-on-61143
- **Bundle ID (iOS):** com.leema.app
- **Package Name (Android):** com.leema.app

## Файлы изменены
- `.env` - добавлен GOOGLE_IOS_CLIENT_ID
- `.env.example` - добавлен GOOGLE_IOS_CLIENT_ID
- `app/config.py` - добавлено поле GOOGLE_IOS_CLIENT_ID
- `app/core/google_auth.py` - обновлена логика verify_id_token() с поддержкой iOS Client ID
