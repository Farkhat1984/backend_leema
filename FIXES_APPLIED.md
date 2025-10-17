# Исправления Google OAuth

## Проблемы найдены:

1. ❌ Старый GOOGLE_CLIENT_ID в config.js (222819809615...)
2. ❌ Неправильный API URL (www.api.leema.kz вместо api.leema.kz)

## Исправления применены:

### 1. Обновлен `/var/www/frontend_leema/assets/js/core/config.js`

**Было:**
```javascript
production: 'https://www.api.leema.kz'
GOOGLE_CLIENT_ID: '222819809615-cb4p93ej04cr6ur9cf5o1jjk9n6dmvuj.apps.googleusercontent.com'
```

**Стало:**
```javascript
production: 'https://api.leema.kz'
GOOGLE_CLIENT_ID: '236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com'
```

## ✅ Что нужно сделать СЕЙЧАС:

### 1. Очистить кэш браузера
- Нажмите Ctrl+Shift+Delete (или Cmd+Shift+Delete на Mac)
- Выберите "Кэшированные изображения и файлы"
- Или откройте страницу с Ctrl+Shift+R (hard refresh)

### 2. Настроить Google Cloud Console

Откройте: https://console.cloud.google.com/apis/credentials

Для Client ID: `236011762515-q48adtqtgd72na7lp861339offh3b9k3`

**Добавьте Authorized Redirect URIs:**
```
https://www.leema.kz/public/auth/callback.html
https://api.leema.kz/api/v1/auth/google/callback
http://localhost:8000/api/v1/auth/google/callback
```

**Добавьте Authorized JavaScript Origins:**
```
https://www.leema.kz
https://api.leema.kz
https://leema.kz
http://localhost:8000
```

### 3. Подождите 5-10 минут
Google нужно время для распространения изменений.

### 4. Проверьте
Откройте: https://www.leema.kz/public/index.html
Попробуйте войти через Google.

## 🔍 Проверка настроек

Backend правильно настроен ✅:
```bash
GOOGLE_CLIENT_ID=236011762515-q48adtqtgd72na7lp861339offh3b9k3.apps.googleusercontent.com
GOOGLE_REDIRECT_URI=https://www.leema.kz/public/auth/callback.html
```

Frontend теперь тоже правильно настроен ✅

## 📝 Тестовый URL

Попробуйте открыть этот URL для тестирования OAuth:
https://api.leema.kz/api/v1/auth/google/url?account_type=shop&platform=web

Скопируйте authorization_url из ответа и откройте в браузере.

## ⚠️ Если все еще 404

Проверьте в Google Cloud Console что добавлены ВСЕ redirect URIs выше.
Ошибка 404 от Google означает "redirect_uri_mismatch" - URI не совпадает.
