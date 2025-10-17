# Google OAuth Configuration Guide

## Ваши Client IDs

✅ **Web Client ID**: `YOUR-CLIENT-ID.apps.googleusercontent.com`
✅ **Android Client ID**: `YOUR-ANDROID-CLIENT-ID.apps.googleusercontent.com`

---

## 🔧 Настройка Web Client (YOUR-CLIENT-ID)

### Шаг 1: Откройте Google Cloud Console
1. Перейдите: https://console.cloud.google.com/apis/credentials
2. Выберите правильный проект
3. Найдите OAuth 2.0 Client ID с ID: **YOUR-CLIENT-ID**
4. Нажмите на него для редактирования

### Шаг 2: Добавьте Authorized Redirect URIs

**ВАЖНО:** Добавьте ВСЕ эти URI в раздел "Authorized redirect URIs":

```
https://api.leema.kz/api/v1/auth/google/callback
https://www.leema.kz/public/auth/callback.html
http://localhost:8000/api/v1/auth/google/callback
```

### Шаг 3: Добавьте Authorized JavaScript Origins

**ВАЖНО:** Добавьте ВСЕ эти origins в раздел "Authorized JavaScript origins":

```
https://api.leema.kz
https://www.leema.kz
https://leema.kz
http://localhost:8000
http://localhost:3000
```

### Шаг 4: Сохраните изменения
- Нажмите кнопку "SAVE" внизу страницы
- Подождите 5-10 минут для распространения изменений

---

## 🔧 Настройка Android Client (YOUR-ANDROID-CLIENT-ID)

Для Android клиента redirect URIs не требуются, так как используется ID token flow.

**Проверьте:**
1. SHA-1 fingerprint вашего Android приложения добавлен
2. Package name правильно указан

---

## 📝 Текущая конфигурация Backend

Ваши `.env` настройки:
```bash
GOOGLE_CLIENT_ID=YOUR-CLIENT-ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR-CLIENT-SECRET
GOOGLE_REDIRECT_URI=https://www.leema.kz/public/auth/callback.html

# Mobile
GOOGLE_MOBILE_CLIENT_ID=YOUR-CLIENT-ID.apps.googleusercontent.com
GOOGLE_MOBILE_CLIENT_SECRET=YOUR-CLIENT-SECRET
GOOGLE_ANDROID_CLIENT_ID=YOUR-ANDROID-CLIENT-ID.apps.googleusercontent.com
```

✅ Эти настройки правильные!

---

## 🧪 Тестирование

### Тест 1: Получить OAuth URL
```bash
curl "https://api.leema.kz/api/v1/auth/google/url?account_type=shop&platform=web"
```

Ожидаемый результат:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "account_type": "shop",
  "platform": "web"
}
```

### Тест 2: Проверка callback endpoint
```bash
curl -I "https://api.leema.kz/api/v1/auth/google/callback"
```

Должен вернуть `302` или `400`, НЕ `404`

### Тест 3: Полный OAuth flow
1. Откройте в браузере URL из Теста 1
2. Войдите через Google
3. Проверьте что вас перенаправило на `callback.html`
4. Проверьте консоль браузера на ошибки

---

## 🚨 Распространенные ошибки

### Ошибка: "redirect_uri_mismatch" или 404
**Причина:** URI в коде не совпадает с настройками в Google Console

**Решение:**
1. Убедитесь что в Google Console добавлены ВСЕ redirect URIs из Шага 2
2. Проверьте что нет опечаток (http vs https, trailing slash и т.д.)
3. Подождите 5-10 минут после сохранения в Google Console

### Ошибка: "origin_mismatch"
**Причина:** JavaScript origin не авторизован

**Решение:**
1. Добавьте все origins из Шага 3
2. Убедитесь что не добавляете trailing slash к origins (неправильно: `https://api.leema.kz/`)

### Ошибка: "invalid_client"
**Причина:** Неверный Client ID или Secret

**Решение:**
1. Убедитесь что используете Web Client ID, а не Android
2. Проверьте что Client Secret правильно скопирован (без пробелов)
3. Убедитесь что выбран правильный проект в Google Console

---

## 🔄 Что делать после изменения настроек

1. ✅ Сохранить изменения в Google Console
2. ⏰ Подождать 5-10 минут
3. 🧹 Очистить кэш браузера и cookies
4. 🔄 Перезапустить backend (если нужно): `docker-compose restart backend`
5. 🧪 Протестировать OAuth flow заново

---

## 📞 Проверка что настройки применились

Перейдите в Google Console и проверьте визуально:
1. Раздел "Authorized redirect URIs" содержит минимум 2 URI:
   - `https://api.leema.kz/api/v1/auth/google/callback`
   - `https://www.leema.kz/public/auth/callback.html`

2. Раздел "Authorized JavaScript origins" содержит минимум 3 origins:
   - `https://api.leema.kz`
   - `https://www.leema.kz`
   - `https://leema.kz`

---

## ✅ Checklist

- [ ] Web Client ID настроен в Google Console
- [ ] Добавлены все Authorized Redirect URIs
- [ ] Добавлены все Authorized JavaScript Origins
- [ ] Сохранены изменения в Google Console
- [ ] Прошло 5-10 минут после сохранения
- [ ] Очищен кэш браузера
- [ ] Протестирован OAuth flow
- [ ] Backend перезапущен (если были изменения в .env)

---

## 🆘 Если всё ещё не работает

Проверьте логи backend:
```bash
docker logs fashion-backend --tail 100 | grep -i google
```

Или запустите диагностический скрипт:
```bash
python3 check_google_auth.py
```
