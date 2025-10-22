# Изменения для Web Frontend (Admin & Shop панели)

## Дата: 2025-10-22

---

## 📋 Общая информация

### Что меняется
Backend рефакторинг для улучшения разделения ролей и добавления функции "Гардероб пользователя".

### Затронутые части
- ✅ **Admin Panel** - небольшие уточнения
- ✅ **Shop Panel** - небольшие изменения
- ❌ **User Panel** - НЕ ЗАТРОНУТО (у пользователей нет веб интерфейса)

---

## 🔐 Архитектура Authentication (уточнения)

### Текущая схема (остается без изменений)

#### 1. Admin Panel
- **Пользователь**: User с ролью `ADMIN`
- **Токен**: `{user_id, role: "admin", platform: "web", account_type: "user"}`
- **Доступ**: только через Web
- **Endpoints**: `/api/v1/admin/*`

```javascript
// Login для админа
POST /api/v1/auth/google/login
Body: {
  code: "google_auth_code",
  account_type: "user",  // ВАЖНО: user, не admin!
  platform: "web"
}

// Response содержит user.role = "admin"
Response: {
  access_token: "...",
  refresh_token: "...",
  user: {
    id: 1,
    email: "admin@example.com",
    role: "admin",  // Проверяйте это поле!
    ...
  },
  account_type: "user",
  platform: "web"
}
```

**⚠️ ВАЖНО**: 
- Admin это НЕ отдельный account_type
- Admin это User с `role: "admin"`
- При логине указывайте `account_type: "user"`
- Проверяйте `user.role === "admin"` для доступа к админ панели

#### 2. Shop Panel
- **Пользователь**: Shop (отдельная сущность)
- **Токен**: `{shop_id, role: "shop", platform: "web", account_type: "shop"}`
- **Доступ**: только через Web
- **Endpoints**: `/api/v1/shops/me/*`, `/api/v1/products/*`

```javascript
// Login для магазина
POST /api/v1/auth/google/login
Body: {
  code: "google_auth_code",
  account_type: "shop",  // Для магазина
  platform: "web"
}

Response: {
  access_token: "...",
  refresh_token: "...",
  shop: {
    id: 1,
    shop_name: "My Fashion Store",
    email: "shop@example.com",
    is_approved: true,
    ...
  },
  account_type: "shop",
  platform: "web"
}
```

---

## 🛠️ Изменения в API

### 1. Admin Panel - БЕЗ ИЗМЕНЕНИЙ

Все существующие endpoints остаются без изменений:
- `GET /api/v1/admin/users` - список пользователей
- `GET /api/v1/admin/shops` - список магазинов
- `POST /api/v1/admin/shops/{id}/approve` - одобрение магазина
- `GET /api/v1/admin/products/moderation` - модерация товаров
- И т.д.

**Действия**: Ничего не нужно менять ✅

### 2. Shop Panel - НОВАЯ СТРУКТУРА UPLOADS

#### 2.1 Upload товаров магазина

**Было:**
```
POST /api/v1/products
Content-Type: multipart/form-data

files: [File, File, ...]
name: "Product name"
price: 1000
...

→ Файлы сохранялись в: /uploads/products/{random_uuid}.jpg
```

**Стало:**
```
POST /api/v1/products
Content-Type: multipart/form-data

files: [File, File, ...]
name: "Product name"
price: 1000
...

→ Файлы сохраняются в: /uploads/shops/{shop_id}/products/{product_id}/image_{index}.jpg
```

**Что это значит:**
- URL изображений изменится с `/uploads/products/xxx.jpg` на `/uploads/shops/1/products/123/image_0.jpg`
- Изображения организованы по магазинам и товарам
- Каждый товар имеет свою папку

#### 2.2 Изменения в Product Response

**Было:**
```json
{
  "id": 123,
  "name": "Dress",
  "images": [
    "/uploads/products/abc123.jpg",
    "/uploads/products/def456.jpg"
  ]
}
```

**Стало:**
```json
{
  "id": 123,
  "name": "Dress",
  "images": [
    "/uploads/shops/5/products/123/image_0.jpg",
    "/uploads/shops/5/products/123/image_1.jpg"
  ]
}
```

**Действия для Frontend:**
1. ✅ Используйте полные URL из API (не конструируйте сами)
2. ✅ Обновите тесты если там hardcoded пути к изображениям
3. ✅ При миграции старые URL будут работать (backward compatibility)

---

## 📁 File Upload - Лучшие практики

### Загрузка изображений товаров

```javascript
// React пример
const uploadProduct = async (formData) => {
  const form = new FormData();
  
  // Добавить файлы
  files.forEach((file) => {
    form.append('files', file);
  });
  
  // Добавить данные
  form.append('name', productName);
  form.append('price', price);
  form.append('description', description);
  
  const response = await fetch('/api/v1/products', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      // НЕ ДОБАВЛЯЙТЕ Content-Type - браузер сам установит для multipart
    },
    body: form
  });
  
  const product = await response.json();
  
  // Используйте URLs из response
  console.log('Product images:', product.images);
};
```

### Отображение изображений

```javascript
// Правильно - используйте URL из API
<img src={product.images[0]} alt={product.name} />

// НЕПРАВИЛЬНО - не конструируйте URL сами
<img src={`/uploads/products/${product.id}/image.jpg`} />
```

---

## 🚨 Breaking Changes

### ❌ НЕТ BREAKING CHANGES для Web Frontend

Все изменения обратно совместимы:
- Существующие endpoints работают
- Формат запросов не изменился
- Формат ответов расширен (новые поля добавлены, старые не удалены)
- Старые URL изображений продолжат работать через редирект

---

## 🧪 Тестирование

### Что протестировать в Admin Panel

1. **Авторизация админа**
   - [ ] Login через Google работает
   - [ ] Токен содержит `user.role = "admin"`
   - [ ] Редирект на админ панель после успешного логина

2. **Управление магазинами**
   - [ ] Список магазинов загружается
   - [ ] Одобрение/отклонение магазина работает
   - [ ] WebSocket уведомления о новых магазинах приходят

3. **Модерация товаров**
   - [ ] Очередь модерации загружается
   - [ ] Одобрение/отклонение товара работает
   - [ ] Изображения товаров отображаются корректно

### Что протестировать в Shop Panel

1. **Авторизация магазина**
   - [ ] Login через Google работает
   - [ ] Токен содержит `shop` объект
   - [ ] Редирект на панель магазина после логина

2. **Управление товарами**
   - [ ] Создание товара с загрузкой изображений
   - [ ] Изображения отображаются по новым URL
   - [ ] Редактирование товара работает
   - [ ] Удаление товара работает

3. **Статистика**
   - [ ] Dashboard загружается
   - [ ] Графики отображаются
   - [ ] Экспорт данных работает

---

## 🆕 Новые возможности (опционально)

### 1. Admin может видеть товары пользователей в гардеробе

Новый endpoint для админа:
```
GET /api/v1/admin/wardrobe
→ Список всех товаров в гардеробах пользователей

GET /api/v1/admin/users/{user_id}/wardrobe
→ Гардероб конкретного пользователя
```

**Зачем**: Для модерации контента, загруженного пользователями

**UI идеи**:
- Вкладка "User Wardrobe" в админ панели
- Фильтры: по пользователю, по источнику (generated/uploaded/shop)
- Возможность удалять неподходящий контент

### 2. Просмотр истории копирования товаров

Новый endpoint:
```
GET /api/v1/shops/me/analytics/copied-to-wardrobe
→ Статистика: сколько раз товары магазина копировались в гардероб
```

**Зачем**: Магазин видит популярность своих товаров среди пользователей

**UI идеи**:
- График "Добавлено в гардероб" на странице товара
- Топ товаров по копированию в гардероб

---

## 📞 API Reference (Quick Guide)

### Admin Endpoints (без изменений)
```
GET    /api/v1/admin/dashboard          - Статистика платформы
GET    /api/v1/admin/users               - Список пользователей
GET    /api/v1/admin/shops               - Список магазинов
POST   /api/v1/admin/shops/{id}/approve  - Одобрить магазин
POST   /api/v1/admin/shops/{id}/reject   - Отклонить магазин
GET    /api/v1/admin/products/moderation - Очередь модерации товаров
POST   /api/v1/admin/products/{id}/approve - Одобрить товар
POST   /api/v1/admin/products/{id}/reject  - Отклонить товар
GET    /api/v1/admin/settings            - Настройки платформы
PUT    /api/v1/admin/settings            - Обновить настройки
```

### Shop Endpoints (без изменений)
```
GET    /api/v1/shops/me                  - Профиль магазина
PUT    /api/v1/shops/me                  - Обновить профиль
GET    /api/v1/shops/me/analytics        - Аналитика магазина
GET    /api/v1/products                  - Список товаров магазина
POST   /api/v1/products                  - Создать товар
GET    /api/v1/products/{id}             - Детали товара
PUT    /api/v1/products/{id}             - Обновить товар
DELETE /api/v1/products/{id}             - Удалить товар
```

---

## ✅ Checklist для внедрения

### До развертывания
- [ ] Изучить новую структуру Auth (admin = user с role)
- [ ] Убедиться что используете URL изображений из API, а не конструируете сами
- [ ] Обновить тесты если есть hardcoded пути

### После развертывания
- [ ] Протестировать логин админа
- [ ] Протестировать логин магазина
- [ ] Протестировать загрузку изображений товаров
- [ ] Проверить что старые изображения отображаются

### Мониторинг
- [ ] Проверить логи на ошибки 403/401 (проблемы авторизации)
- [ ] Проверить что изображения загружаются (нет 404)
- [ ] Мониторить размер папки uploads

---

## 🆘 Troubleshooting

### Проблема: Admin не может войти
**Решение**: Убедитесь что:
- При логине указываете `account_type: "user"`, а не "admin"
- Проверяете `response.user.role === "admin"` для редиректа
- В токене есть `user_id` (не `shop_id`)

### Проблема: Изображения не загружаются (404)
**Решение**:
- Используйте полный URL из `product.images` массива
- Не конструируйте URL самостоятельно
- Проверьте что backend доступен (CORS настроен)

### Проблема: Shop не может загрузить товар
**Решение**:
- Проверьте что shop одобрен (`is_approved: true`)
- Проверьте размер файлов (макс 10MB на файл)
- Убедитесь что используете `multipart/form-data`

---

## 📧 Контакты

При возникновении вопросов:
- Backend документация: `/var/www/backend/BACKEND_REFACTORING_TODOLIST.md`
- API документация: `https://api.leema.kz/docs` (только в dev режиме)
- Swagger UI: `https://api.leema.kz/redoc` (только в dev режиме)

---

**Дата последнего обновления**: 2025-10-22
**Версия Backend API**: v1
**Статус**: ✅ Ready for implementation
