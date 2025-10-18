#!/usr/bin/env python3
"""
WebSocket Test Script for Mobile Integration

This script tests the WebSocket connection for mobile apps.

Usage:
    python test_websocket_mobile.py <token>

Example:
    python test_websocket_mobile.py eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime


async def test_websocket_mobile(token: str):
    """Test WebSocket connection with mobile parameters"""
    
    # Mobile WebSocket URL
    uri = f"wss://api.leema.kz/ws/products?token={token}&client_type=shop&platform=mobile"
    
    print(f"🔗 Connecting to WebSocket...")
    print(f"   URL: {uri[:80]}...")
    print()
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            print()
            
            # Wait for connection confirmation
            print("⏳ Waiting for connection confirmation...")
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✅ Received: {data}")
            print()
            
            # Test ping/pong
            print("📤 Sending ping...")
            timestamp = int(datetime.now().timestamp() * 1000)
            ping_message = {
                "type": "ping",
                "timestamp": timestamp
            }
            await websocket.send(json.dumps(ping_message))
            
            # Wait for pong
            print("⏳ Waiting for pong...")
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("type") == "pong":
                print(f"✅ Received pong: {data}")
                print()
            else:
                print(f"⚠️  Unexpected response: {data}")
                print()
            
            # Listen for events
            print("👂 Listening for events (press Ctrl+C to stop)...")
            print("   Create a product in the web UI to see events!")
            print()
            
            event_count = 0
            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=60)
                    data = json.loads(message)
                    event_count += 1
                    
                    event_type = data.get("event", data.get("type", "unknown"))
                    timestamp = data.get("timestamp", "N/A")
                    
                    print(f"\n🔔 Event #{event_count} received at {datetime.now().isoformat()}")
                    print(f"   Type: {event_type}")
                    
                    if "data" in data:
                        event_data = data["data"]
                        
                        # Show product info if present
                        if "product" in event_data and event_data["product"]:
                            product = event_data["product"]
                            print(f"   Product ID: {product.get('id')}")
                            print(f"   Product Name: {product.get('name')}")
                            print(f"   Price: ${product.get('price', 0):.2f}")
                            print(f"   Status: {product.get('moderation_status')}")
                            print(f"   Active: {product.get('is_active')}")
                            
                            # Check if product should be visible to users
                            if product.get('moderation_status') == 'approved' and product.get('is_active'):
                                print(f"   ✅ Should be VISIBLE to users")
                            else:
                                print(f"   ⚠️  Should be HIDDEN from users")
                        
                        elif "product_id" in event_data:
                            print(f"   Product ID: {event_data.get('product_id')}")
                            print(f"   Action: {event_data.get('action', 'N/A')}")
                    
                    print()
                    
                    # Send ping every 30 events to keep connection alive
                    if event_count % 30 == 0:
                        print("📤 Sending ping (keep-alive)...")
                        await websocket.send(json.dumps({
                            "type": "ping",
                            "timestamp": int(datetime.now().timestamp() * 1000)
                        }))
                
                except asyncio.TimeoutError:
                    # No message received in 60 seconds, send ping
                    print("⏰ 60 seconds timeout, sending ping...")
                    await websocket.send(json.dumps({
                        "type": "ping",
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }))
                
                except KeyboardInterrupt:
                    print("\n\n👋 Disconnecting...")
                    break
            
            print(f"\n📊 Total events received: {event_count}")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status code: {e.status_code}")
        if e.status_code == 403:
            print("   → Token might be invalid or expired")
        elif e.status_code == 404:
            print("   → WebSocket endpoint not found")
        print()
        
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        print()
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("❌ Error: Token required")
        print()
        print("Usage:")
        print(f"    python {sys.argv[0]} <token>")
        print()
        print("Example:")
        print(f"    python {sys.argv[0]} eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        print()
        print("Get your token from:")
        print("    1. Login to https://leema.kz")
        print("    2. Open browser DevTools (F12)")
        print("    3. Go to Application/Storage → Local Storage")
        print("    4. Copy the 'token' value")
        print()
        sys.exit(1)
    
    token = sys.argv[1]
    
    print("=" * 80)
    print("WebSocket Mobile Integration Test")
    print("=" * 80)
    print()
    
    try:
        asyncio.run(test_websocket_mobile(token))
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")


if __name__ == "__main__":
    main()
