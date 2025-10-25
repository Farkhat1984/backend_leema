# API Changes - Authorization Update (Apple Sign In Added)

## Дата: 2025-10-25
## Версия: 2.0.0

---

## 🚨 CRITICAL - Authorization Changes

### Что изменилось:

1. **Добавлена авторизация через Apple Sign In** (iOS/macOS)
2. **Изменена структура запросов авторизации** - теперь требуется `platform` и `account_type`
3. **Google авторизация обновлена** - исправлены проблемы с входом

---

## 📱 Новые Endpoints - Apple Sign In

### POST /api/auth/apple/login

Авторизация через Apple Sign In (аналог Google).

**Request Body:**
```json
{
  "id_token": "eyJraWQiOiJXNldjT0tC...",
  "account_type": "user",
  "platform": "mobile",
  "user_data": {
    "name": {
      "firstName": "John",
      "lastName": "Doe"
    }
  }
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "email": "john@privaterelay.appleid.com",
    "name": "John Doe",
    "avatar_url": null,
    "role": "user",
    "balance": 0.0,
    "free_generations_left": 3,
    "free_try_ons_left": 5
  },
  "account_type": "user",
  "platform": "mobile"
}
```

**Важно:** Apple предоставляет имя пользователя (`user_data`) **только один раз** при первом входе! Обязательно сохраните его.

---

## 🔄 Изменения в Google авторизации

### POST /api/auth/google/login

**ЧТО ИЗМЕНИЛОСЬ:**
- Теперь **обязательно** нужно передать `platform` и `account_type`
- Исправлена проблема с верификацией токенов

**Старый запрос (НЕ РАБОТАЕТ):**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Новый запрос (ПРАВИЛЬНО):**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "account_type": "user",
  "platform": "mobile"
}
```

**Параметры:**
- `id_token` (string, required) - Google ID token из Firebase Auth
- `account_type` (enum, required) - `"user"` или `"shop"`
- `platform` (enum, required) - `"mobile"` или `"web"`

---

## 📝 Обновление Flutter кода

### 1. Установите пакет для Apple Sign In

```yaml
# pubspec.yaml
dependencies:
  sign_in_with_apple: ^5.0.0
  google_sign_in: ^6.1.5
  firebase_auth: ^4.15.0
```

### 2. Обновите Google Sign In

**Старый код:**
```dart
// ❌ НЕ РАБОТАЕТ
Future<void> signInWithGoogle() async {
  final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
  final GoogleSignInAuthentication googleAuth = await googleUser!.authentication;
  
  final response = await dio.post('/api/auth/google/login', data: {
    'id_token': googleAuth.idToken,  // ❌ Не хватает полей
  });
}
```

**Новый код:**
```dart
// ✅ ПРАВИЛЬНО
Future<void> signInWithGoogle() async {
  final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
  if (googleUser == null) return;
  
  final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
  
  final response = await dio.post('/api/auth/google/login', data: {
    'id_token': googleAuth.idToken,
    'account_type': 'user',      // ✅ Обязательно!
    'platform': 'mobile',        // ✅ Обязательно!
  });
  
  if (response.statusCode == 200) {
    final data = response.data;
    // Сохраняем токены
    await storage.write(key: 'access_token', value: data['access_token']);
    await storage.write(key: 'refresh_token', value: data['refresh_token']);
    await storage.write(key: 'user', value: jsonEncode(data['user']));
  }
}
```

### 3. Добавьте Apple Sign In

```dart
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

Future<void> signInWithApple() async {
  try {
    // Проверяем доступность Apple Sign In
    final isAvailable = await SignInWithApple.isAvailable();
    if (!isAvailable) {
      throw Exception('Apple Sign In not available on this device');
    }
    
    // Запрашиваем авторизацию
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );
    
    // Отправляем на бэкенд
    final response = await dio.post('/api/auth/apple/login', data: {
      'id_token': credential.identityToken,
      'account_type': 'user',
      'platform': 'mobile',
      'user_data': {
        'name': {
          'firstName': credential.givenName,
          'lastName': credential.familyName,
        }
      }
    });
    
    if (response.statusCode == 200) {
      final data = response.data;
      // Сохраняем токены
      await storage.write(key: 'access_token', value: data['access_token']);
      await storage.write(key: 'refresh_token', value: data['refresh_token']);
      await storage.write(key: 'user', value: jsonEncode(data['user']));
      
      // Сохраняем тип авторизации
      await storage.write(key: 'auth_provider', value: 'apple');
    }
  } on SignInWithAppleAuthorizationException catch (e) {
    switch (e.code) {
      case AuthorizationErrorCode.canceled:
        print('User canceled Apple Sign In');
        break;
      case AuthorizationErrorCode.failed:
        print('Apple Sign In failed');
        break;
      case AuthorizationErrorCode.invalidResponse:
        print('Invalid response from Apple');
        break;
      case AuthorizationErrorCode.notHandled:
        print('Apple Sign In not handled');
        break;
      case AuthorizationErrorCode.unknown:
        print('Unknown error occurred');
        break;
    }
  } catch (e) {
    print('Error during Apple Sign In: $e');
  }
}
```

### 4. Создайте единый AuthService

```dart
class AuthService {
  final Dio dio;
  final FlutterSecureStorage storage;
  
  AuthService({required this.dio, required this.storage});
  
  /// Вход через Google
  Future<Map<String, dynamic>?> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) return null;
      
      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      
      return await _authenticate(
        endpoint: '/api/auth/google/login',
        data: {
          'id_token': googleAuth.idToken,
          'account_type': 'user',
          'platform': 'mobile',
        },
        provider: 'google',
      );
    } catch (e) {
      print('Google Sign In error: $e');
      return null;
    }
  }
  
  /// Вход через Apple
  Future<Map<String, dynamic>?> signInWithApple() async {
    try {
      if (!await SignInWithApple.isAvailable()) {
        throw Exception('Apple Sign In not available');
      }
      
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );
      
      return await _authenticate(
        endpoint: '/api/auth/apple/login',
        data: {
          'id_token': credential.identityToken,
          'account_type': 'user',
          'platform': 'mobile',
          'user_data': {
            'name': {
              'firstName': credential.givenName,
              'lastName': credential.familyName,
            }
          }
        },
        provider: 'apple',
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      print('Apple Sign In canceled or failed: ${e.code}');
      return null;
    } catch (e) {
      print('Apple Sign In error: $e');
      return null;
    }
  }
  
  /// Общий метод авторизации
  Future<Map<String, dynamic>?> _authenticate({
    required String endpoint,
    required Map<String, dynamic> data,
    required String provider,
  }) async {
    try {
      final response = await dio.post(endpoint, data: data);
      
      if (response.statusCode == 200) {
        final responseData = response.data;
        
        // Сохраняем токены
        await storage.write(key: 'access_token', value: responseData['access_token']);
        await storage.write(key: 'refresh_token', value: responseData['refresh_token']);
        await storage.write(key: 'user', value: jsonEncode(responseData['user']));
        await storage.write(key: 'auth_provider', value: provider);
        
        return responseData;
      }
      
      return null;
    } catch (e) {
      print('Authentication error: $e');
      return null;
    }
  }
  
  /// Выход
  Future<void> signOut() async {
    try {
      final refreshToken = await storage.read(key: 'refresh_token');
      final provider = await storage.read(key: 'auth_provider');
      
      // Отправляем logout запрос
      if (refreshToken != null) {
        await dio.post('/api/auth/logout', data: {
          'refresh_token': refreshToken,
        });
      }
      
      // Выходим из провайдеров
      if (provider == 'google') {
        await GoogleSignIn().signOut();
      }
      // Apple не требует дополнительного logout
      
      // Очищаем хранилище
      await storage.deleteAll();
    } catch (e) {
      print('Sign out error: $e');
      // В любом случае очищаем локальное хранилище
      await storage.deleteAll();
    }
  }
  
  /// Обновление токена
  Future<bool> refreshToken() async {
    try {
      final refreshToken = await storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;
      
      final response = await dio.post('/api/auth/refresh', data: {
        'refresh_token': refreshToken,
      });
      
      if (response.statusCode == 200) {
        final data = response.data;
        await storage.write(key: 'access_token', value: data['access_token']);
        return true;
      }
      
      return false;
    } catch (e) {
      print('Refresh token error: $e');
      return false;
    }
  }
}
```

### 5. Обновите UI экрана входа

```dart
class LoginScreen extends StatelessWidget {
  final AuthService authService;
  
  const LoginScreen({required this.authService});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Google Sign In кнопка
            ElevatedButton.icon(
              icon: Image.asset('assets/google_logo.png', height: 24),
              label: Text('Sign in with Google'),
              style: ElevatedButton.styleFrom(
                padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
              onPressed: () async {
                final result = await authService.signInWithGoogle();
                if (result != null) {
                  // Успешный вход
                  Navigator.pushReplacementNamed(context, '/home');
                } else {
                  // Ошибка
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Google Sign In failed')),
                  );
                }
              },
            ),
            
            SizedBox(height: 16),
            
            // Apple Sign In кнопка (только на iOS/macOS)
            if (Platform.isIOS || Platform.isMacOS)
              SignInWithAppleButton(
                onPressed: () async {
                  final result = await authService.signInWithApple();
                  if (result != null) {
                    // Успешный вход
                    Navigator.pushReplacementNamed(context, '/home');
                  } else {
                    // Ошибка
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Apple Sign In failed')),
                    );
                  }
                },
              ),
          ],
        ),
      ),
    );
  }
}
```

---

## 🔧 Настройка Apple Sign In

### iOS Setup

1. **Xcode Project Settings:**
   - Откройте `ios/Runner.xcworkspace`
   - Выберите `Runner` target
   - Перейдите в `Signing & Capabilities`
   - Нажмите `+ Capability`
   - Добавьте `Sign in with Apple`

2. **Info.plist:**
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>your-app-bundle-id</string>
    </array>
  </dict>
</array>
```

### Android Setup

Apple Sign In на Android работает через веб-поток. Дополнительная настройка не требуется, но доступно только на Android 6.0+.

---

## ⚠️ Важные замечания

### Apple Sign In особенности:

1. **Имя пользователя** - Apple предоставляет только **один раз** при первом входе. После этого `givenName` и `familyName` будут `null`. Обязательно сохраните на бэкенде.

2. **Email** - Пользователь может выбрать "Hide My Email", тогда будет использоваться приватный email типа `xyz123@privaterelay.appleid.com`

3. **Аватар** - Apple **не предоставляет** аватар пользователя, `avatar_url` всегда `null`

4. **Обязательность** - Если ваше приложение использует Google/Facebook Sign In, Apple требует также добавить Apple Sign In (App Store guideline 4.8)

### Google Sign In исправления:

1. **Теперь работает** множественная верификация с разными Client ID (web, android, iOS)
2. **Обязательные поля** `platform` и `account_type` предотвращают ошибки
3. **Улучшена обработка ошибок** в backend

---

## 📊 Сравнение провайдеров

| Функция | Google | Apple |
|---------|--------|-------|
| Email | ✅ Всегда настоящий | ⚠️ Может быть приватный relay |
| Имя | ✅ Всегда доступно | ⚠️ Только при первом входе |
| Аватар | ✅ Предоставляется | ❌ Не предоставляется |
| Платформы | Android, iOS, Web | iOS, macOS, (Android через web) |
| Обязательность в App Store | Нет | Да, если есть другие соц. входы |

---

## 🧪 Тестирование

### Тестовые сценарии:

1. **Первый вход через Google** → создается новый пользователь
2. **Повторный вход через Google** → вход в существующий аккаунт
3. **Первый вход через Apple** → создается новый пользователь (имя сохраняется)
4. **Повторный вход через Apple** → вход в существующий аккаунт (имя не обновляется)
5. **Вход через Google, затем через Apple с тем же email** → два разных аккаунта
6. **Logout** → токен попадает в blacklist, refresh не работает
7. **Refresh token** → получение нового access token

---

## 📝 Checklist для Flutter разработчика

- [ ] Добавить зависимость `sign_in_with_apple: ^5.0.0`
- [ ] Обновить код Google Sign In (добавить `platform` и `account_type`)
- [ ] Реализовать Apple Sign In (метод `signInWithApple()`)
- [ ] Создать единый `AuthService`
- [ ] Обновить UI экрана входа (добавить Apple кнопку)
- [ ] Настроить Xcode capabilities для Apple Sign In
- [ ] Сохранять `user_data.name` при первом Apple Sign In
- [ ] Обработать приватный email от Apple
- [ ] Протестировать оба метода авторизации
- [ ] Протестировать logout и refresh token
- [ ] Добавить обработку ошибок
- [ ] Обновить документацию в коде

---

## 🆘 Troubleshooting

**Проблема:** Google Sign In не работает, ошибка 401
**Решение:** Добавьте `platform: 'mobile'` и `account_type: 'user'` в запрос

**Проблема:** Apple Sign In доступен только на iOS
**Решение:** Используйте `Platform.isIOS || Platform.isMacOS` для условного отображения кнопки

**Проблема:** При повторном Apple Sign In имя пользователя `null`
**Решение:** Это нормально, Apple дает имя только 1 раз. Backend уже сохранил его.

**Проблема:** Пользователь получил приватный Apple email
**Решение:** Это нормально, используйте его как обычный email. Письма будут пересылаться.

---

# API Changes - Image Management Update (Previous Version)

## Дата: 2025-10-25
## Версия: 1.1.0

---

## 📋 Краткое описание изменений

Исправлено управление изображениями в системе. Теперь изображения корректно удаляются при удалении из wardrobe и добавлен новый endpoint для удаления AI генераций.

---

## 🆕 Новые API Endpoints

### DELETE /api/generations/{generation_id}

**Описание:** Удаление AI генерации вместе с изображениями.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `generation_id` (integer, required) - ID генерации для удаления

**Query Parameters:**
- `delete_files` (boolean, optional, default: true) - Удалять ли файлы изображений

**Response 200 (Success):**
```json
{
  "message": "Generation deleted successfully",
  "id": 123
}
```

**Response 404 (Not Found):**
```json
{
  "detail": "Generation not found"
}
```

**Response 409 (Conflict - в использовании):**
```json
{
  "detail": "Cannot delete: generation is saved in 2 wardrobe item(s). Remove from wardrobe first."
}
```

**Пример использования (Dart/Flutter):**
```dart
Future<void> deleteGeneration(int generationId, {bool deleteFiles = true}) async {
  final response = await dio.delete(
    '/api/generations/$generationId',
    queryParameters: {'delete_files': deleteFiles},
    options: Options(
      headers: {'Authorization': 'Bearer $token'},
    ),
  );
  
  if (response.statusCode == 200) {
    print('Generation deleted successfully');
  } else if (response.statusCode == 409) {
    // Генерация используется в wardrobe, сначала нужно удалить из wardrobe
    showError('Remove from wardrobe first');
  }
}
```

---

## 🔄 Изменения в существующих Endpoints

### DELETE /api/wardrobe/{wardrobe_id}

**Что изменилось:** Улучшена логика удаления файлов в зависимости от источника item'а.

**Новое поведение:**

1. **UPLOADED items** (загружено пользователем):
   - ✅ Файлы удаляются из `uploads/users/{user_id}/wardrobe/{wardrobe_id}/`
   - Поведение не изменилось

2. **SHOP_PRODUCT items** (из магазина):
   - ✅ Если `copy_files=true` был использован при добавлении, скопированные файлы теперь удаляются
   - Если `copy_files=false`, ссылки на оригинальные файлы товара остаются (правильно)

3. **GENERATED items** (AI генерация):
   - ⚠️ Файлы НЕ удаляются при удалении из wardrobe
   - Файлы принадлежат Generation записи
   - Для удаления файлов используйте новый endpoint `DELETE /api/generations/{id}`

**Запрос не изменился:**
```dart
Future<void> deleteWardrobeItem(int wardrobeId, {bool deleteFiles = true}) async {
  final response = await dio.delete(
    '/api/wardrobe/$wardrobeId',
    queryParameters: {'delete_files': deleteFiles},
  );
}
```

---

## 🎯 Рекомендуемые изменения в Flutter приложении

### 1. Добавить UI для удаления генераций

Добавьте возможность удалять старые AI генерации из истории пользователя:

```dart
class GenerationHistoryScreen extends StatelessWidget {
  Future<void> _deleteGeneration(BuildContext context, int generationId) async {
    // Показываем подтверждение
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete Generation'),
        content: Text('This will permanently delete the generated image. Continue?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    
    if (confirm != true) return;
    
    try {
      await apiService.deleteGeneration(generationId);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Generation deleted successfully')),
      );
      // Обновить список
      setState(() {
        _loadGenerations();
      });
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) {
        // Генерация в wardrobe
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Remove from wardrobe first'),
            action: SnackBarAction(
              label: 'Open Wardrobe',
              onPressed: () => Navigator.pushNamed(context, '/wardrobe'),
            ),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.message}')),
        );
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemBuilder: (context, index) {
        final generation = generations[index];
        return ListTile(
          leading: Image.network(generation.imageUrl),
          title: Text('Generation #${generation.id}'),
          trailing: IconButton(
            icon: Icon(Icons.delete, color: Colors.red),
            onPressed: () => _deleteGeneration(context, generation.id),
          ),
        );
      },
    );
  }
}
```

### 2. Обновить API Service

Добавьте новый метод в ваш API service:

```dart
class ApiService {
  final Dio dio;
  
  // ... existing methods
  
  /// Удалить AI генерацию
  Future<void> deleteGeneration(
    int generationId, {
    bool deleteFiles = true,
  }) async {
    final response = await dio.delete(
      '/api/generations/$generationId',
      queryParameters: {'delete_files': deleteFiles},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to delete generation');
    }
  }
  
  /// Удалить wardrobe item
  Future<void> deleteWardrobeItem(
    int wardrobeId, {
    bool deleteFiles = true,
  }) async {
    final response = await dio.delete(
      '/api/wardrobe/$wardrobeId',
      queryParameters: {'delete_files': deleteFiles},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to delete wardrobe item');
    }
  }
}
```

### 3. Улучшить UX при удалении из Wardrobe

При удалении GENERATED item'а из wardrobe, показывайте пользователю информацию:

```dart
Future<void> _deleteFromWardrobe(WardrobeItem item) async {
  String message = 'Delete this item from wardrobe?';
  String submessage = '';
  
  // Разное сообщение в зависимости от источника
  switch (item.source) {
    case 'uploaded':
      submessage = 'Image files will be permanently deleted.';
      break;
    case 'generated':
      submessage = 'Generated image will remain in your history.';
      break;
    case 'shop_product':
      submessage = 'Product will remain in the shop.';
      break;
  }
  
  final confirm = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Delete Item'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(message),
          SizedBox(height: 8),
          Text(
            submessage,
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text('Delete', style: TextStyle(color: Colors.red)),
        ),
      ],
    ),
  );
  
  if (confirm == true) {
    await apiService.deleteWardrobeItem(item.id);
    // Обновить UI
  }
}
```

---

## 📊 Логика управления изображениями

### Жизненный цикл изображений по источникам:

| Источник | Где хранится | Удаляется при удалении из Wardrobe | Как удалить файл |
|----------|--------------|-----------------------------------|------------------|
| **UPLOADED** | `uploads/users/{user_id}/wardrobe/{wardrobe_id}/` | ✅ Да | Автоматически при `DELETE /api/wardrobe/{id}` |
| **SHOP_PRODUCT** (copy_files=false) | `uploads/shops/{shop_id}/products/{product_id}/` | ❌ Нет (ссылка) | Удаляется только при удалении товара |
| **SHOP_PRODUCT** (copy_files=true) | `uploads/users/{user_id}/wardrobe/{wardrobe_id}/` | ✅ Да | Автоматически при `DELETE /api/wardrobe/{id}` |
| **GENERATED** | `uploads/generations/{user_id}/{generation_id}_*.jpg` | ❌ Нет | `DELETE /api/generations/{id}` |

### Последовательность удаления GENERATED item:

1. Пользователь удаляет из wardrobe → запись удаляется, файл остается
2. Пользователь удаляет генерацию → файл удаляется

Если пользователь пытается удалить генерацию, которая еще в wardrobe:
- API вернет 409 Conflict
- Нужно сначала удалить из wardrobe, потом удалить генерацию

---

## 🧪 Тестовые сценарии

### Сценарий 1: Удаление загруженного item
```
1. Загрузить фото → создать wardrobe item (source: UPLOADED)
2. Удалить item из wardrobe
3. ✅ Проверить: файлы удалены из uploads/users/{user_id}/wardrobe/{wardrobe_id}/
```

### Сценарий 2: Удаление сгенерированного item
```
1. Создать AI генерацию
2. Сохранить в wardrobe (source: GENERATED)
3. Удалить из wardrobe
4. ✅ Проверить: файл остался в uploads/generations/{user_id}/
5. Попытаться удалить генерацию через API
6. ❌ Получить 409 (еще в wardrobe - если не удалили на шаге 3)
   ИЛИ
   ✅ Успешно удалить (если удалили на шаге 3)
7. ✅ Проверить: файл удален из uploads/generations/{user_id}/
```

### Сценарий 3: Удаление товара из магазина
```
1. Добавить товар в wardrobe с copy_files=true
2. Удалить из wardrobe
3. ✅ Проверить: скопированные файлы удалены из uploads/users/{user_id}/wardrobe/{wardrobe_id}/
4. ✅ Проверить: оригинальные файлы товара остались
```

---

## 🔧 Миграция данных

**Не требуется.** Изменения касаются только логики удаления файлов.

Существующие записи в базе данных остаются без изменений.

---

## ⚠️ Breaking Changes

**Нет breaking changes.**

Все существующие endpoints работают так же, только улучшена логика удаления файлов.

---

## 📝 Checklist для Flutter разработчика

- [ ] Добавить метод `deleteGeneration()` в API service
- [ ] Добавить UI для удаления генераций (иконка delete в истории генераций)
- [ ] Обработать ошибку 409 при попытке удалить генерацию, которая в wardrobe
- [ ] Обновить UI подтверждения удаления из wardrobe (показать разные сообщения для разных источников)
- [ ] Протестировать все сценарии удаления
- [ ] Обновить документацию API в коде (если есть)

---

## 🆘 Поддержка

При возникновении вопросов обращайтесь к backend разработчику или создавайте issue в репозитории.

---

## 📚 Дополнительные ресурсы

- [Wardrobe API Documentation](./app/api/wardrobe.py)
- [Generation API Documentation](./app/api/generations.py)
- [File Upload Documentation](./app/core/file_upload.py)
