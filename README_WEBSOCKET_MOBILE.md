# 🚀 WebSocket Real-Time Notifications для Мобильного Приложения

## ✅ Готово к использованию!

Ваш бэкенд теперь поддерживает **real-time уведомления** о новых одобренных товарах через WebSocket. Когда администратор одобряет товар, все подключенные пользователи (включая мобильное приложение) мгновенно получают уведомление.

---

## 🎯 Что было сделано

### 1. Обновлен файл `app/api/admin.py`
- **Функция `approve_product()`**: Добавлена рассылка события `product.approved` всем пользователям
- **Функция `bulk_approve_products()`**: Добавлена рассылка для массового одобрения товаров

### 2. Существующая инфраструктура (уже была)
- ✅ WebSocket Manager (`app/core/websocket.py`)
- ✅ WebSocket Endpoint (`/ws/{client_type}`)
- ✅ JWT аутентификация
- ✅ Event schemas (`app/schemas/webhook.py`)

### 3. Документация
- 📄 `WEBSOCKET_PRODUCTS_GUIDE.md` - Полное руководство с примерами кода
- 📄 `CHANGES_SUMMARY.md` - Детальное описание изменений
- 🧪 `test_websocket_client.py` - Тестовый клиент для проверки

---

## 📱 Быстрый старт для мобильного приложения

### Шаг 1: Подключение к WebSocket

```javascript
// React Native / JavaScript
const token = await AsyncStorage.getItem('jwt_token');
const ws = new WebSocket(`ws://YOUR_BACKEND_URL/ws/user?token=${token}`);

ws.onopen = () => {
  console.log('✅ Подключено к WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'product.approved') {
    // 🎉 Новый товар одобрен!
    const product = data.data;
    showNotification(`Новый товар: ${product.product_name}`);
    refreshProductsList();
  }
};

ws.onerror = (error) => {
  console.error('❌ WebSocket ошибка:', error);
};

ws.onclose = () => {
  console.log('🔌 WebSocket отключен');
  // Переподключение через 5 секунд
  setTimeout(() => reconnectWebSocket(), 5000);
};
```

### Шаг 2: Получение событий

Когда админ одобряет товар, ваше приложение получит:

```json
{
  "event": "product.approved",
  "timestamp": "2024-01-01T12:00:00Z",
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

---

## 🧪 Тестирование

### Вариант 1: Используйте тестовый скрипт

```bash
# 1. Получите JWT токен (замените email и password)
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# 2. Запустите тестовый клиент
python3 test_websocket_client.py $TOKEN

# 3. В другом терминале одобрите товар как админ
# (см. инструкции в CHANGES_SUMMARY.md)
```

### Вариант 2: Используйте wscat (Node.js)

```bash
# Установите wscat
npm install -g wscat

# Подключитесь к WebSocket
wscat -c "ws://localhost:8000/ws/user?token=YOUR_JWT_TOKEN"
```

### Вариант 3: Проверьте статистику

```bash
curl http://localhost:8000/ws/stats
```

Ответ покажет активные соединения:
```json
{
  "total": 5,
  "by_type": {
    "user": 3,
    "shop": 1,
    "admin": 1
  },
  "rooms": 0
}
```

---

## 📊 Архитектура

```
┌─────────────────┐
│ Mobile App      │
│ (User Client)   │
└────────┬────────┘
         │ ws://backend/ws/user?token=JWT
         │
         ├──────────────────────────────┐
         │                              │
┌────────▼────────┐          ┌─────────▼──────────┐
│ WebSocket       │          │ Shop/Admin         │
│ Manager         │◄─────────│ Clients            │
└────────┬────────┘          └────────────────────┘
         │
         │ broadcast_to_type("user")
         │
┌────────▼────────────────────────────┐
│ Admin approves product              │
│ → Event created: product.approved   │
│ → Broadcast to:                     │
│   ✓ Shop (send_to_client)          │
│   ✓ ALL Users (broadcast_to_type)  │ ← NEW
│   ✓ Admins (moderation queue)      │
└─────────────────────────────────────┘
```

---

## 🔑 Основные endpoint'ы

### WebSocket
- **URL**: `ws://YOUR_BACKEND_URL/ws/user?token=JWT_TOKEN`
- **Протокол**: WebSocket (ws:// или wss:// для HTTPS)
- **Аутентификация**: JWT токен в query параметре

### REST API (для справки)
- **Получить товары**: `GET /api/v1/products?status=approved`
- **Статистика WebSocket**: `GET /ws/stats`
- **Health check**: `GET /health`

---

## 📋 События (Event Types)

| Event Type | Описание | Когда отправляется |
|-----------|----------|-------------------|
| `product.approved` | Товар одобрен | После одобрения админом |
| `product.rejected` | Товар отклонен | После отклонения админом |
| `settings.updated` | Настройки обновлены | При изменении настроек платформы |
| `connected` | Подключение установлено | При первом подключении |

---

## ⚙️ Настройки и рекомендации

### 1. Переподключение
Реализуйте автоматическое переподключение при обрыве соединения:

```javascript
function connectWebSocket(retryCount = 0) {
  const ws = new WebSocket(`ws://YOUR_URL/ws/user?token=${token}`);
  
  ws.onclose = () => {
    if (retryCount < 5) {
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
      setTimeout(() => connectWebSocket(retryCount + 1), delay);
    }
  };
}
```

### 2. Ping/Pong (Keep-Alive)
Отправляйте ping каждые 30 секунд для поддержания соединения:

```javascript
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'ping',
      timestamp: new Date().toISOString()
    }));
  }
}, 30000);
```

### 3. Управление состоянием
```javascript
// React Native пример
const [wsConnected, setWsConnected] = useState(false);
const [newProductsCount, setNewProductsCount] = useState(0);

ws.onopen = () => setWsConnected(true);
ws.onclose = () => setWsConnected(false);

// Показывать индикатор подключения в UI
<StatusBar 
  backgroundColor={wsConnected ? 'green' : 'red'}
  text={wsConnected ? 'Online' : 'Offline'}
/>
```

### 4. Фоновый режим
На iOS/Android WebSocket может быть закрыт при переходе в фоновый режим. Переподключайтесь при возвращении:

```javascript
import { AppState } from 'react-native';

AppState.addEventListener('change', (nextAppState) => {
  if (nextAppState === 'active') {
    // Приложение вернулось на передний план
    reconnectWebSocket();
  }
});
```

---

## 🔒 Безопасность

✅ **Реализовано:**
- JWT токен проверяется при подключении
- CORS origin валидация
- Автоматическое закрытие при невалидном токене
- Только авторизованные пользователи могут подключиться

⚠️ **Рекомендации:**
- Используйте `wss://` (WebSocket Secure) в продакшене
- Обновляйте JWT токен периодически
- Не сохраняйте токен в незащищенном виде

---

## 🐛 Устранение проблем

### Проблема: WebSocket не подключается
```bash
# 1. Проверьте доступность сервера
curl http://YOUR_BACKEND_URL/health

# 2. Проверьте JWT токен
echo $TOKEN | cut -d'.' -f2 | base64 -d

# 3. Проверьте логи backend
docker logs backend-container
```

### Проблема: События не приходят
```bash
# 1. Проверьте активные соединения
curl http://YOUR_BACKEND_URL/ws/stats

# 2. Подключитесь с тестовым клиентом
python3 test_websocket_client.py $TOKEN

# 3. Одобрите товар и проверьте логи
```

### Проблема: Connection timeout
- Увеличьте timeout в nginx/proxy
- Проверьте firewall правила
- Используйте keep-alive (ping/pong)

---

## 📚 Дополнительные ресурсы

- **Полное руководство**: `WEBSOCKET_PRODUCTS_GUIDE.md`
- **Детали реализации**: `CHANGES_SUMMARY.md`
- **Тестовый клиент**: `test_websocket_client.py`
- **WebSocket Manager код**: `app/core/websocket.py`
- **Event schemas**: `app/schemas/webhook.py`

---

## 🎉 Готово!

Теперь ваше мобильное приложение может получать real-time уведомления о новых товарах!

### Следующие шаги:
1. ✅ Интегрируйте WebSocket в мобильное приложение
2. ✅ Протестируйте с помощью `test_websocket_client.py`
3. ✅ Реализуйте переподключение и keep-alive
4. ✅ Добавьте UI индикатор подключения
5. 🚀 Деплой и наслаждайтесь real-time обновлениями!

---

## 💡 Вопросы?

Если что-то не работает, проверьте:
- Правильность JWT токена
- Доступность WebSocket endpoint (`/ws/user`)
- Логи backend сервера
- CORS настройки

Успехов! 🎊
