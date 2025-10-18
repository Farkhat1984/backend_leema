#!/usr/bin/env python3
"""
Simple WebSocket client to test product approval notifications
Usage: python3 test_websocket_client.py <JWT_TOKEN>
"""

import asyncio
import websockets
import json
import sys

async def test_websocket(token: str, base_url: str = "ws://localhost:8000"):
    """Connect to WebSocket and listen for events"""
    uri = f"{base_url}/ws/user?token={token}"
    
    print(f"Подключаемся к {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Подключено к WebSocket!")
            print("Ожидание событий... (Ctrl+C для выхода)\n")
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                event_type = data.get('event')
                
                print(f"\n{'='*60}")
                print(f"📨 Получено событие: {event_type}")
                print(f"{'='*60}")
                
                if event_type == 'connected':
                    print(f"✅ Успешное подключение!")
                    print(f"   Client Type: {data.get('client_type')}")
                    print(f"   Client ID: {data.get('client_id')}")
                    print(f"   Timestamp: {data.get('timestamp')}")
                    
                elif event_type == 'product.approved':
                    product_data = data.get('data', {})
                    print(f"🎉 Новый товар одобрен!")
                    print(f"   ID товара: {product_data.get('product_id')}")
                    print(f"   Название: {product_data.get('product_name')}")
                    print(f"   Магазин: {product_data.get('shop_name')} (ID: {product_data.get('shop_id')})")
                    print(f"   Статус: {product_data.get('moderation_status')}")
                    if product_data.get('moderation_notes'):
                        print(f"   Заметки: {product_data.get('moderation_notes')}")
                    print(f"   Комиссия за одобрение: ${product_data.get('approval_fee', 0)}")
                    
                elif event_type == 'product.rejected':
                    product_data = data.get('data', {})
                    print(f"❌ Товар отклонен")
                    print(f"   ID товара: {product_data.get('product_id')}")
                    print(f"   Название: {product_data.get('product_name')}")
                    print(f"   Магазин: {product_data.get('shop_name')} (ID: {product_data.get('shop_id')})")
                    print(f"   Причина: {product_data.get('moderation_notes', 'Не указана')}")
                    
                elif event_type == 'settings.updated':
                    settings_data = data.get('data', {})
                    print(f"⚙️ Настройки обновлены")
                    print(f"   Ключ: {settings_data.get('key')}")
                    print(f"   Старое значение: {settings_data.get('old_value')}")
                    print(f"   Новое значение: {settings_data.get('new_value')}")
                    
                else:
                    print(f"📦 Другое событие")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                
                print(f"{'='*60}\n")
                
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ Ошибка WebSocket: {e}")
    except KeyboardInterrupt:
        print("\n\n👋 Отключение...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    if len(sys.argv) < 2:
        print("❌ Использование: python3 test_websocket_client.py <JWT_TOKEN> [WS_URL]")
        print("Пример: python3 test_websocket_client.py eyJhbGc...")
        print("        python3 test_websocket_client.py eyJhbGc... ws://192.168.1.100:8000")
        sys.exit(1)
    
    token = sys.argv[1]
    base_url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:8000"
    
    print("🚀 WebSocket Test Client для тестирования уведомлений о товарах")
    print(f"🔗 URL: {base_url}")
    print(f"🔑 Token: {token[:20]}...\n")
    
    try:
        asyncio.run(test_websocket(token, base_url))
    except KeyboardInterrupt:
        print("\n👋 Пока!")

if __name__ == "__main__":
    main()
