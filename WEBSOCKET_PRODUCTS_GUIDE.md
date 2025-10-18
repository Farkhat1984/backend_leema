# WebSocket для получения обновлений товаров в реальном времени

## Обзор

Когда администратор одобряет товары (approve by admin), все подключенные пользователи (включая мобильное приложение) получают уведомления через WebSocket в реальном времени.

## Подключение WebSocket из мобильного приложения

### Endpoint
```
ws://YOUR_BACKEND_URL/ws/user?token=YOUR_JWT_TOKEN
```

или для HTTPS:
```
wss://YOUR_BACKEND_URL/ws/user?token=YOUR_JWT_TOKEN
```

### Параметры
- **client_type**: `user` (для мобильного приложения)
- **token**: JWT токен доступа пользователя (получается при логине)

## События, которые вы получите

### 1. Событие подключения (connection confirmation)
```json
{
  "event": "connected",
  "client_type": "user",
  "client_id": 123,
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### 2. Товар одобрен администратором
```json
{
  "event": "product.approved",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "product_id": 456,
    "product_name": "Красное платье",
    "shop_id": 10,
    "shop_name": "Fashion Store",
    "moderation_status": "approved",
    "moderation_notes": "Отличный товар!",
    "admin_id": 1,
    "approval_fee": 5.0
  }
}
```

### 3. Товар отклонен администратором
```json
{
  "event": "product.rejected",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "product_id": 457,
    "product_name": "Синяя куртка",
    "shop_id": 11,
    "shop_name": "Winter Store",
    "moderation_status": "rejected",
    "moderation_notes": "Не соответствует требованиям",
    "admin_id": 1
  }
}
```

### 4. Обновление настроек платформы
```json
{
  "event": "settings.updated",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "key": "shop_approval_fee",
    "old_value": "5.0",
    "new_value": "7.0",
    "description": "Fee charged for product approval",
    "updated_by": 1
  }
}
```

## Пример кода для React Native / JavaScript

```javascript
// Подключение к WebSocket
const token = 'YOUR_JWT_TOKEN'; // Получить из localStorage или AsyncStorage
const ws = new WebSocket(`ws://YOUR_BACKEND_URL/ws/user?token=${token}`);

ws.onopen = () => {
  console.log('WebSocket подключен');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Получено событие:', data);
  
  switch(data.event) {
    case 'connected':
      console.log('Успешно подключились к WebSocket');
      break;
      
    case 'product.approved':
      // Новый товар одобрен - обновить список товаров
      const newProduct = data.data;
      console.log('Новый товар:', newProduct.product_name);
      // Обновить UI или fetch новый список товаров
      fetchProducts(); // Ваша функция для обновления списка
      break;
      
    case 'product.rejected':
      console.log('Товар отклонен:', data.data.product_name);
      break;
      
    case 'settings.updated':
      console.log('Настройки обновлены:', data.data.key);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket ошибка:', error);
};

ws.onclose = () => {
  console.log('WebSocket отключен');
  // Можно реализовать автоматическое переподключение
  setTimeout(() => {
    connectWebSocket(); // Функция для переподключения
  }, 5000);
};

// Отправка ping для поддержания соединения
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'ping',
      timestamp: new Date().toISOString()
    }));
  }
}, 30000); // Каждые 30 секунд
```

## Пример для Flutter / Dart

```dart
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

class WebSocketService {
  WebSocketChannel? _channel;
  
  void connect(String token) {
    final wsUrl = Uri.parse('ws://YOUR_BACKEND_URL/ws/user?token=$token');
    _channel = WebSocketChannel.connect(wsUrl);
    
    _channel!.stream.listen(
      (message) {
        final data = jsonDecode(message);
        print('Получено событие: ${data['event']}');
        
        switch(data['event']) {
          case 'connected':
            print('Успешно подключились к WebSocket');
            break;
            
          case 'product.approved':
            final productData = data['data'];
            print('Новый товар: ${productData['product_name']}');
            // Обновить список товаров
            _refreshProducts();
            break;
            
          case 'product.rejected':
            print('Товар отклонен: ${data['data']['product_name']}');
            break;
        }
      },
      onError: (error) {
        print('WebSocket ошибка: $error');
      },
      onDone: () {
        print('WebSocket отключен');
        // Переподключение через 5 секунд
        Future.delayed(Duration(seconds: 5), () {
          connect(token);
        });
      },
    );
  }
  
  void sendPing() {
    if (_channel != null) {
      _channel!.sink.add(jsonEncode({
        'type': 'ping',
        'timestamp': DateTime.now().toIso8601String(),
      }));
    }
  }
  
  void dispose() {
    _channel?.sink.close();
  }
  
  void _refreshProducts() {
    // Ваш код для обновления списка товаров
  }
}
```

## Рекомендации

1. **Автоматическое переподключение**: Реализуйте логику переподключения при разрыве соединения
2. **Ping/Pong**: Отправляйте ping каждые 30-60 секунд для поддержания соединения
3. **Обработка ошибок**: Обрабатывайте ошибки подключения и показывайте пользователю статус подключения
4. **Фоновый режим**: На мобильных устройствах учитывайте, что WebSocket может быть отключен при переходе приложения в фоновый режим
5. **Батарея**: WebSocket соединение потребляет батарею, поэтому можно добавить опцию отключения в настройках

## Альтернатива: HTTP Polling (если WebSocket не работает)

Если WebSocket подключение не работает, можно использовать polling:

```javascript
// Опросить API каждые 30 секунд
setInterval(async () => {
  const response = await fetch('http://YOUR_BACKEND_URL/api/v1/products?status=approved&limit=10&offset=0');
  const data = await response.json();
  // Обновить список товаров
}, 30000);
```

## Проверка работоспособности

### 1. Проверить статистику WebSocket соединений
```bash
curl http://YOUR_BACKEND_URL/ws/stats
```

Ответ:
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

### 2. Проверить health check
```bash
curl http://YOUR_BACKEND_URL/health
```

## Типы событий (WebhookEventType)

- `product.created` - Товар создан
- `product.updated` - Товар обновлен
- `product.deleted` - Товар удален
- `product.approved` - **Товар одобрен (это главное событие для мобильного приложения)**
- `product.rejected` - Товар отклонен
- `balance.updated` - Баланс обновлен
- `transaction.completed` - Транзакция завершена
- `transaction.failed` - Транзакция провалилась
- `settings.updated` - Настройки обновлены
- `moderation.queue_updated` - Очередь модерации обновлена (только для админов)

## Безопасность

- JWT токен проверяется при подключении
- Проверяется CORS origin
- Только авторизованные пользователи могут подключиться
- Соединение автоматически разрывается при невалидном токене
