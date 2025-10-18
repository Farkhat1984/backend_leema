# Изменения: Добавлена поддержка WebSocket для мобильного приложения

## Проблема
Мобильное приложение не получало уведомления о новых одобренных администратором товарах в реальном времени. WebSocket события отправлялись только магазинам и администраторам, но не обычным пользователям.

## Решение
Добавлена широковещательная рассылка (broadcast) событий одобрения товаров всем подключенным пользователям через WebSocket.

## Изменения в коде

### 1. Файл: `app/api/admin.py`

#### Функция `approve_product()` (строки ~242-265)
**До:**
```python
# Send webhook to shop
await connection_manager.send_to_client(event.model_dump(mode="json"), "shop", product.shop_id)

# Update moderation queue for admins
await connection_manager.broadcast_to_type(queue_event.model_dump(mode="json"), "admin")
```

**После:**
```python
# Send webhook to shop
await connection_manager.send_to_client(event.model_dump(mode="json"), "shop", product.shop_id)

# Broadcast to all users (mobile app users)
await connection_manager.broadcast_to_type(event.model_dump(mode="json"), "user")

# Update moderation queue for admins
await connection_manager.broadcast_to_type(queue_event.model_dump(mode="json"), "admin")
```

**Что добавлено:**
- Одна строка: `await connection_manager.broadcast_to_type(event.model_dump(mode="json"), "user")`
- Теперь все подключенные пользователи получают событие `product.approved`

#### Функция `bulk_approve_products()` (строки ~589-622)
**Обновлено:**
- Добавлены WebSocket уведомления для каждого одобренного товара
- Добавлена рассылка всем пользователям: `broadcast_to_type(..., "user")`
- Улучшена обработка ошибок при отправке email уведомлений
- Добавлено обновление очереди модерации для администраторов

## Как это работает

### Архитектура

1. **WebSocket Manager** (`app/core/websocket.py`):
   - Управляет всеми активными WebSocket соединениями
   - Поддерживает три типа клиентов: `user`, `shop`, `admin`
   - Предоставляет методы для отправки сообщений конкретным клиентам или broadcast

2. **WebSocket Endpoint** (`app/main.py` - `/ws/{client_type}`):
   - Принимает подключения от клиентов
   - Аутентифицирует через JWT токен
   - Поддерживает соединение активным
   - Обрабатывает ping/pong и подписки на комнаты

3. **Event Broadcasting** (обновлено в `app/api/admin.py`):
   - При одобрении товара создается событие `product.approved`
   - Событие отправляется:
     - Конкретному магазину (shop)
     - **ВСЕМ пользователям (user)** ← НОВОЕ
     - Всем администраторам (admin) с обновлением очереди

### Поток событий

```
Админ одобряет товар
    ↓
approve_product() вызывается
    ↓
Создается WebSocket событие с типом "product.approved"
    ↓
Рассылается по трем каналам:
    ├─→ send_to_client(event, "shop", shop_id)     [конкретному магазину]
    ├─→ broadcast_to_type(event, "user")           [ВСЕМ пользователям] ← НОВОЕ
    └─→ broadcast_to_type(queue_event, "admin")    [всем администраторам]
    ↓
Все подключенные клиенты получают событие в реальном времени
```

## Использование в мобильном приложении

### Подключение
```javascript
const ws = new WebSocket(`ws://YOUR_BACKEND_URL/ws/user?token=${jwtToken}`);
```

### Обработка событий
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'product.approved') {
    // Новый товар одобрен!
    const product = data.data;
    console.log(`Новый товар: ${product.product_name}`);
    // Обновить список товаров в приложении
    refreshProductsList();
  }
};
```

## Структура события

### Событие `product.approved`
```json
{
  "event": "product.approved",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "product_id": 123,
    "product_name": "Красное платье",
    "shop_id": 10,
    "shop_name": "Fashion Store",
    "moderation_status": "approved",
    "moderation_notes": "Отличный товар",
    "admin_id": 1,
    "approval_fee": 5.0
  }
}
```

## Преимущества

1. **Мгновенные обновления**: Пользователи видят новые товары сразу после одобрения
2. **Нет polling**: Не нужно постоянно опрашивать API
3. **Меньше нагрузки на сервер**: WebSocket эффективнее чем HTTP polling
4. **Лучший UX**: Пользователи получают real-time опыт
5. **Экономия трафика**: Одно постоянное соединение вместо множества HTTP запросов

## Тестирование

### 1. Проверить WebSocket статистику
```bash
curl http://YOUR_BACKEND_URL/ws/stats
```

### 2. Подключиться через WebSocket (с токеном)
```bash
# Получить токен при логине
TOKEN=$(curl -X POST http://YOUR_BACKEND_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' | jq -r '.access_token')

# Подключиться к WebSocket (требуется wscat: npm install -g wscat)
wscat -c "ws://YOUR_BACKEND_URL/ws/user?token=$TOKEN"
```

### 3. Одобрить товар как админ (в другом терминале)
```bash
# Получить админский токен
ADMIN_TOKEN=$(curl -X POST http://YOUR_BACKEND_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"adminpass"}' | jq -r '.access_token')

# Одобрить товар
curl -X POST http://YOUR_BACKEND_URL/api/v1/admin/moderation/PRODUCT_ID/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Approved for testing"}'
```

### 4. Проверить, что WebSocket клиент получил событие
В первом терминале (wscat) вы должны увидеть:
```json
{
  "event": "product.approved",
  "timestamp": "...",
  "data": { ... }
}
```

## Обратная совместимость

✅ Изменения **полностью обратно совместимы**:
- Существующие клиенты (магазины, админы) продолжают работать как раньше
- Добавлена только новая функциональность для пользователей
- Не изменились API endpoints или структуры данных
- Не требуется миграция базы данных

## Безопасность

✅ Безопасность не нарушена:
- JWT токен проверяется при подключении
- CORS origin валидируется
- Только авторизованные пользователи могут подключиться
- Каждый клиент видит только те события, которые ему предназначены

## Дополнительные файлы

- **WEBSOCKET_PRODUCTS_GUIDE.md** - Полное руководство по использованию WebSocket API
  - Примеры кода для JavaScript/React Native
  - Примеры кода для Flutter/Dart
  - Описание всех типов событий
  - Рекомендации по реализации

## Следующие шаги

1. **Протестировать** изменения на dev окружении
2. **Обновить мобильное приложение** для использования WebSocket
3. **Добавить reconnection logic** в мобильное приложение
4. **Настроить monitoring** для отслеживания WebSocket соединений
5. **Опционально**: Добавить события для других операций (product.updated, product.deleted)

## Альтернативные решения (не реализованы)

1. **Создать отдельный endpoint `/ws/products`**
   - Минусы: Дублирование кода, больше endpoints для поддержки
   - Плюсы: Более явная семантика

2. **Использовать Server-Sent Events (SSE)**
   - Минусы: Только односторонняя связь (server → client)
   - Плюсы: Проще реализация

3. **Polling**
   - Минусы: Неэффективно, задержки, высокая нагрузка
   - Плюсы: Проще для debugging

Выбранное решение (broadcast через существующий WebSocket) является оптимальным балансом между простотой и эффективностью.
