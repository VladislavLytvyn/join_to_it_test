"""
Тестовий WebSocket клієнт для перевірки функціональності сервера

Використання:
    python test_client.py
"""

import asyncio
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("❌ Помилка: websockets не встановлено")
    print("Встановіть: pip install websockets")
    sys.exit(1)


async def test_websocket_client(client_id: str, duration: int = 60):
    """
    Тестовий WebSocket клієнт
    
    Args:
        client_id: Унікальний ідентифікатор клієнта
        duration: Тривалість роботи в секундах
    """
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    print(f"🔌 [{client_id}] Підключення до {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ [{client_id}] Успішно підключено!")
            
            # Отримуємо привітальне повідомлення
            greeting = await websocket.recv()
            print(f"📨 [{client_id}] {greeting}")
            
            # Надсилаємо тестове повідомлення
            test_message = f"Привіт з тестового клієнта {client_id}!"
            await websocket.send(test_message)
            print(f"📤 [{client_id}] Відправлено: {test_message}")
            
            # Слухаємо повідомлення протягом вказаного часу
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Розраховуємо залишковий час
                    elapsed = asyncio.get_event_loop().time() - start_time
                    remaining = duration - elapsed
                    
                    if remaining <= 0:
                        print(f"⏰ [{client_id}] Час роботи ({duration}s) вичерпано")
                        break
                    
                    # Очікуємо повідомлення з таймаутом
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=min(remaining, 5.0)
                    )
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"📨 [{client_id}] [{timestamp}] {message}")
                    
                except asyncio.TimeoutError:
                    # Таймаут - це нормально, продовжуємо слухати
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    print(f"🔌 [{client_id}] З'єднання закрито сервером")
                    break
                    
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ [{client_id}] WebSocket помилка: {e}")
    except Exception as e:
        print(f"❌ [{client_id}] Неочікувана помилка: {e}")
    finally:
        print(f"👋 [{client_id}] Відключено")


async def test_multiple_clients(num_clients: int = 3, duration: int = 60):
    """
    Запускає кілька клієнтів одночасно для тестування broadcasting
    
    Args:
        num_clients: Кількість клієнтів
        duration: Тривалість роботи кожного клієнта в секундах
    """
    print(f"🚀 Запуск {num_clients} тестових клієнтів...")
    print(f"⏱️  Тривалість роботи: {duration} секунд")
    print("=" * 60)
    
    # Створюємо задачі для кожного клієнта
    tasks = []
    for i in range(num_clients):
        client_id = f"test_client_{i+1}"
        task = asyncio.create_task(test_websocket_client(client_id, duration))
        tasks.append(task)
        
        # Невелика затримка між підключеннями
        await asyncio.sleep(0.5)
    
    # Чекаємо завершення всіх клієнтів
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print("=" * 60)
    print(f"✅ Всі {num_clients} клієнтів завершили роботу")


async def interactive_client():
    """
    Інтерактивний клієнт з можливістю відправки повідомлень
    """
    client_id = f"interactive_client_{datetime.now().strftime('%H%M%S')}"
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    print(f"🔌 Підключення до {uri}...")
    print("💡 Введіть 'quit' для виходу")
    print("=" * 60)
    
    async with websockets.connect(uri) as websocket:
        print(f"✅ Підключено як {client_id}")
        
        # Отримуємо привітальне повідомлення
        greeting = await websocket.recv()
        print(f"📨 {greeting}\n")
        
        async def receive_messages():
            """Фонова задача для отримання повідомлень"""
            try:
                while True:
                    message = await websocket.recv()
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n📨 [{timestamp}] {message}")
                    print("Ваше повідомлення: ", end="", flush=True)
            except websockets.exceptions.ConnectionClosed:
                print("\n🔌 З'єднання закрито")
        
        # Запускаємо фонову задачу для отримання повідомлень
        receive_task = asyncio.create_task(receive_messages())
        
        try:
            # Головний цикл для відправки повідомлень
            while True:
                # Читаємо ввід користувача в окремому потоці
                message = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    input, 
                    "Ваше повідомлення: "
                )
                
                if message.strip().lower() == 'quit':
                    print("👋 Вихід...")
                    break
                
                if message.strip():
                    await websocket.send(message)
                    
        except KeyboardInterrupt:
            print("\n👋 Перервано користувачем")
        finally:
            receive_task.cancel()


def main():
    """Головна функція з меню вибору режиму"""
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "WebSocket Тестовий Клієнт" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print("Оберіть режим тестування:")
    print("  1. Інтерактивний клієнт (можна відправляти повідомлення)")
    print("  2. Один тестовий клієнт (60 секунд)")
    print("  3. Три тестових клієнти одночасно (60 секунд)")
    print("  4. П'ять тестових клієнтів одночасно (120 секунд)")
    print("  5. Stress test: 10 клієнтів (300 секунд)")
    print()
    
    choice = input("Ваш вибір (1-5): ").strip()
    
    try:
        if choice == "1":
            asyncio.run(interactive_client())
        elif choice == "2":
            asyncio.run(test_websocket_client("test_client_1", duration=60))
        elif choice == "3":
            asyncio.run(test_multiple_clients(num_clients=3, duration=60))
        elif choice == "4":
            asyncio.run(test_multiple_clients(num_clients=5, duration=120))
        elif choice == "5":
            print("\n⚠️  STRESS TEST: 10 клієнтів протягом 5 хвилин")
            confirm = input("Продовжити? (y/n): ").strip().lower()
            if confirm == 'y':
                asyncio.run(test_multiple_clients(num_clients=10, duration=300))
            else:
                print("Скасовано")
        else:
            print("❌ Невірний вибір")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Перервано користувачем")
    except Exception as e:
        print(f"\n❌ Помилка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

