# ✅ GOOGLE OAUTH - ЧЕКЛИСТ ИСПРАВЛЕНИЙ

## 🔴 Найденные проблемы

### 1. Старый Google Client ID в frontend
❌ **Было:** `222819809615-cb4p93ej04cr6ur9cf5o1jjk9n6dmvuj.apps.googleusercontent.com`
✅ **Стало:** `YOUR-CLIENT-ID.apps.googleusercontent.com`

### 2. Неправильный API URL в frontend
❌ **Было:** `https://www.api.leema.kz` (лишний www)
✅ **Стало:** `https://api.leema.kz`

---

## ✅ Применённые исправления

### Файл: `/var/www/frontend_leema/assets/js/core/config.js`

```javascript
// До:
production: 'https://www.api.leema.kz'
GOOGLE_CLIENT_ID: '222819809615-cb4p93ej04cr6ur9cf5o1jjk9n6dmvuj.apps.googleusercontent.com'

// После:
production: 'https://api.leema.kz'
GOOGLE_CLIENT_ID: 'YOUR-CLIENT-ID.apps.googleusercontent.com'
```

---

## 📋 ЧТО НУЖНО СДЕЛАТЬ СЕЙЧАС

### Шаг 1: Очистить кэш браузера 🧹
- [ ] Открыть Chrome/Firefox DevTools (F12)
- [ ] Правый клик на кнопке "Обновить" → "Очистить кэш и жесткая перезагрузка"
- [ ] Или: Ctrl+Shift+Delete → Очистить "Кэшированные изображения и файлы"

### Шаг 2: Настроить Google Cloud Console ⚙️

**URL:** https://console.cloud.google.com/apis/credentials

1. Выберите ваш проект
2. Найдите OAuth 2.0 Client ID: `YOUR-CLIENT-ID`
3. Нажмите на него для редактирования

#### Добавьте Authorized Redirect URIs:
- [ ] `https://www.leema.kz/public/auth/callback.html`
- [ ] `https://api.leema.kz/api/v1/auth/google/callback`
- [ ] `http://localhost:8000/api/v1/auth/google/callback` (опционально, для локальной разработки)

#### Добавьте Authorized JavaScript Origins:
- [ ] `https://www.leema.kz`
- [ ] `https://api.leema.kz`
- [ ] `https://leema.kz`
- [ ] `http://localhost:8000` (опционально, для локальной разработки)

4. **💾 СОХРАНИТЕ** изменения!

### Шаг 3: Подождите ⏰
- [ ] Подождите 5-10 минут для распространения изменений Google

### Шаг 4: Тестирование 🧪
- [ ] Откройте https://www.leema.kz/public/index.html
- [ ] Нажмите "Войти через Google" (для магазина или пользователя)
- [ ] Проверьте что перенаправление работает без ошибки 404

---

## 📊 Текущий статус конфигурации

### Backend (✅ Правильно настроен)
```bash
GOOGLE_CLIENT_ID=YOUR-CLIENT-ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR-CLIENT-SECRET
GOOGLE_REDIRECT_URI=https://www.leema.kz/public/auth/callback.html
GOOGLE_MOBILE_CLIENT_ID=YOUR-CLIENT-ID.apps.googleusercontent.com
GOOGLE_ANDROID_CLIENT_ID=YOUR-ANDROID-CLIENT-ID.apps.googleusercontent.com
```

### Frontend (✅ Исправлено)
```javascript
apiUrls: {
    production: 'https://api.leema.kz'  // Без www!
}
GOOGLE_CLIENT_ID: 'YOUR-CLIENT-ID.apps.googleusercontent.com'
```

### API Endpoints (✅ Работают)
- `GET https://api.leema.kz/api/v1/auth/google/url` - генерация OAuth URL
- `GET https://api.leema.kz/api/v1/auth/google/callback` - обработка callback
- `POST https://api.leema.kz/api/v1/auth/google/login` - вход через Google

---

## 🔍 Диагностика и тестирование

### Тест 1: Проверка OAuth URL
```bash
curl "https://api.leema.kz/api/v1/auth/google/url?account_type=shop&platform=web"
```

Должен вернуть JSON с `authorization_url`.

### Тест 2: Проверка callback endpoint
```bash
curl -I "https://api.leema.kz/api/v1/auth/google/callback"
```

Должен вернуть `302` или `422`, НЕ `404`.

### Тест 3: Проверка frontend config
Откройте в браузере: https://www.leema.kz/assets/js/core/config.js
Проверьте что там правильный Client ID и API URL.

---

## ⚠️ Распространённые ошибки

### Ошибка 404 от Google
**Причина:** Redirect URI не добавлен в Google Console или есть опечатка  
**Решение:** Проверьте что добавлены ТОЧНЫЕ URIs (с https://, без trailing slash)

### Ошибка "redirect_uri_mismatch"
**Причина:** URI в коде не совпадает с настройками в Google Console  
**Решение:** Убедитесь что URI идентичны (включая протокол, домен, путь)

### Ошибка "origin_mismatch"
**Причина:** JavaScript origin не авторизован  
**Решение:** Добавьте все необходимые origins в Google Console

### Старый Client ID все еще используется
**Причина:** Кэш браузера  
**Решение:** Жесткая перезагрузка (Ctrl+Shift+R) или очистка кэша

---

## 📞 Дополнительные ресурсы

- **Полная инструкция:** `GOOGLE_OAUTH_SETUP.md`
- **Диагностический скрипт:** `python3 check_google_auth.py`
- **Тестовый скрипт:** `./test_oauth.sh`

---

## ✨ После выполнения всех шагов

Если вы выполнили все шаги выше и все еще видите ошибку 404:

1. Проверьте логи backend:
   ```bash
   docker logs fashion_backend --tail 50 | grep -i google
   ```

2. Проверьте консоль браузера (F12) на наличие ошибок JavaScript

3. Убедитесь что сохранили изменения в Google Console и прошло 5-10 минут

4. Попробуйте в режиме инкогнито (чтобы исключить проблемы с кэшем)

---

**Дата исправления:** 2025-10-17  
**Исправленные файлы:** `/var/www/frontend_leema/assets/js/core/config.js`
