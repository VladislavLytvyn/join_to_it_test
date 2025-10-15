# 🏗️ Архітектура проекту

Детальний опис архітектури WebSocket сервера з graceful shutdown.

## 📐 Загальна структура

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌──────────────────────────────┐    │
│  │ HTTP Endpoints  │    │  WebSocket Endpoint (/ws)    │    │
│  │  - GET /        │    │  - Accept connections        │    │
│  │  - GET /health  │    │  - Handle messages           │    │
│  └─────────────────┘    │  - Manage lifecycle          │    │
│                         └──────────────────────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Connection Manager                        │   │
│  │  - Track active connections                          │   │
│  │  - Broadcasting mechanism                            │   │
│  │  - Thread-safe operations (asyncio.Lock)             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Graceful Shutdown Manager                    │   │
│  │  - Signal handlers (SIGTERM/SIGINT)                  │   │
│  │  - Shutdown orchestration                            │   │
│  │  - Timeout enforcement (30 min)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Background Tasks                             │   │
│  │  - Periodic broadcast (every 10s)                    │   │
│  │  - Shutdown monitoring                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Компоненти

### 1. ConnectionManager

**Призначення**: Централізоване управління WebSocket з'єднаннями

**Структура даних**:
```python
active_connections: Dict[str, tuple[WebSocket, float]]
# Ключ: client_id (унікальний ідентифікатор)
# Значення: (websocket, connect_time)
```

**Методи**:
- `connect()` - додає нове з'єднання
- `disconnect()` - видаляє з'єднання
- `broadcast()` - розсилає повідомлення всім
- `send_personal_message()` - відправляє персональне повідомлення
- `get_active_count()` - повертає кількість активних з'єднань
- `close_all_connections()` - закриває всі з'єднання

**Thread Safety**:
```python
self._lock = asyncio.Lock()

async with self._lock:
    # Критична секція
    self.active_connections[client_id] = (websocket, time.time())
```

### 2. GracefulShutdownManager

**Призначення**: Управління процесом коректного завершення роботи

**Основні властивості**:
```python
shutdown_event: asyncio.Event()  # Сигнал для початку shutdown
timeout_seconds: int = 1800      # 30 хвилин
_shutdown_started: bool          # Прапорець для уникнення повторного виклику
```

**Методи**:
- `register_signals()` - реєструє SIGTERM/SIGINT обробники
- `signal_handler()` - обробляє отримані сигнали
- `wait_for_shutdown()` - основна логіка shutdown

**Алгоритм shutdown**:
```
1. Отримано сигнал → встановити shutdown_event
2. Відправити попередження всім клієнтам
3. LOOP:
   a. Перевірити: всі відключилися? → EXIT
   b. Перевірити: таймаут досягнуто? → примусове закриття → EXIT
   c. Логувати прогрес (кожні 10s)
   d. Чекати 1 секунду
4. Завершити роботу
```

### 3. WebSocket Endpoint

**Lifecycle**:
```
┌──────────────┐
│  New Request │
└──────┬───────┘
       │
       ├─── Перевірка shutdown_in_progress
       │    └─── якщо ТАК → відхилити (код 1001)
       │
       ├─── ConnectionManager.connect()
       │    └─── accept() + додати до active_connections
       │
       ├─── Відправити привітання
       │
       ├─── Повідомити інших про нове підключення
       │
       ├─── LOOP: Обробка вхідних повідомлень
       │    ├─── websocket.receive_text()
       │    ├─── Обробка повідомлення
       │    └─── Broadcasting іншим клієнтам
       │
       ├─── Exception handling:
       │    ├─── WebSocketDisconnect → нормальне відключення
       │    └─── Exception → логування помилки
       │
       └─── FINALLY:
            ├─── ConnectionManager.disconnect()
            └─── Повідомити інших про відключення
```

### 4. Periodic Broadcast Task

**Призначення**: Автоматична розсилка повідомлень для підтримки активності

```python
while not shutdown_event.is_set():
    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=10.0)
        break  # Shutdown отримано
    except asyncio.TimeoutError:
        # 10 секунд пройшло - надішліть повідомлення
        await manager.broadcast(periodic_message)
```

## 🔄 Потік даних

### Нормальна операція

```
Client A          Server              Client B
   │                 │                   │
   ├─── connect ────>│                   │
   │<── welcome ─────┤                   │
   │                 │<─── connect ──────┤
   │<── broadcast ───┤──── welcome ─────>│
   │                 │                   │
   ├─── message ────>│                   │
   │<── ack ─────────┤                   │
   │                 ├── broadcast ─────>│
   │                 │                   │
   │<─ periodic ─────┤─── periodic ─────>│
   │                 │                   │
```

### Graceful Shutdown

```
Client A          Server              Client B
   │                 │                   │
   │    [SIGTERM received]               │
   │                 │                   │
   │<── warning ─────┤──── warning ─────>│
   │                 │                   │
   │                 │ [waiting...]      │
   │                 │                   │
   ├─── close ──────>│                   │
   │                 │ [1 connection]    │
   │                 │                   │
   │                 │<──── close ───────┤
   │                 │ [0 connections]   │
   │                 │                   │
   │              [shutdown]              │
```

## 🛡️ Edge Cases та Обробка помилок

### 1. Клієнт відключився під час broadcast

```python
failed_clients = []
for client_id, (websocket, _) in active_connections.items():
    try:
        await websocket.send_text(message)
    except Exception:
        failed_clients.append(client_id)

# Очистка
for client_id in failed_clients:
    await self.disconnect(client_id)
```

### 2. Race condition при одночасному доступі

```python
# ❌ НЕБЕЗПЕЧНО
active_count = len(self.active_connections)  # Читання
del self.active_connections[client_id]       # Запис

# ✅ БЕЗПЕЧНО
async with self._lock:
    active_count = len(self.active_connections)
    del self.active_connections[client_id]
```

### 3. Нове з'єднання під час shutdown

```python
if shutdown_manager.shutdown_event.is_set():
    await websocket.close(code=1001, reason="Сервер завершує роботу")
    return
```

### 4. Таймаут досягнуто з активними клієнтами

```python
if elapsed_time >= self.timeout_seconds:
    logger.warning("Таймаут досягнуто. Примусове закриття...")
    await self.connection_manager.close_all_connections()
    break
```

## ⚙️ Конфігурація та Налаштування

### Environment Variables (опціонально)

```python
import os

SHUTDOWN_TIMEOUT = int(os.getenv("SHUTDOWN_TIMEOUT", 1800))
BROADCAST_INTERVAL = int(os.getenv("BROADCAST_INTERVAL", 10))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

### Параметри Uvicorn

```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \              # ⚠️ Обов'язково 1!
  --timeout-keep-alive 3600 \ # Для довгих з'єднань
  --limit-concurrency 1000    # Максимум з'єднань
```

## 📊 Performance Considerations

### Масштабування

**Вертикальне масштабування** (workers=1):
```
✅ Простота реалізації
✅ Працює graceful shutdown
❌ Обмежена продуктивність (1 процес)
```

**Горизонтальне масштабування** (кілька інстансів):
```
✅ Висока продуктивність
✅ Fault tolerance
⚠️ Потребує централізоване сховище (Redis/RabbitMQ)
```

### Memory Usage

```python
# Приблизна оцінка пам'яті на з'єднання
per_connection = (
    WebSocket object: ~2KB +
    Buffers: ~8KB +
    Connection metadata: ~1KB
) ≈ 11KB

# Для 10,000 з'єднань:
10,000 * 11KB ≈ 110MB
```

### CPU Usage

- **Idle**: ~0-1% (лише periodic tasks)
- **Broadcasting**: O(n) де n = кількість клієнтів
- **Shutdown**: O(n) для закриття всіх з'єднань

## 🔐 Безпека

### Рекомендації

1. **Аутентифікація**:
```python
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: str):
    if not verify_token(token):
        await websocket.close(code=1008, reason="Unauthorized")
        return
```

2. **Rate Limiting**:
```python
# Обмеження повідомлень від клієнта
MAX_MESSAGES_PER_MINUTE = 60
```

3. **Input Validation**:
```python
# Валідація client_id
import re
if not re.match(r'^[a-zA-Z0-9_-]+$', client_id):
    await websocket.close(code=1003, reason="Invalid client ID")
    return
```

## 🧪 Тестування

### Unit Tests

```python
import pytest
from main import ConnectionManager

@pytest.mark.asyncio
async def test_connection_manager():
    manager = ConnectionManager()
    # Mock WebSocket
    ws = MockWebSocket()
    
    await manager.connect(ws, "test_client")
    assert manager.get_active_count() == 1
    
    await manager.disconnect("test_client")
    assert manager.get_active_count() == 0
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from main import app

def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws/test") as websocket:
        data = websocket.receive_text()
        assert "Вітаємо" in data
```

## 📈 Моніторинг та Метрики

### Ключові метрики

1. **active_connections** - поточна кількість з'єднань
2. **total_messages_sent** - всього відправлено повідомлень
3. **shutdown_duration** - час на graceful shutdown
4. **failed_broadcasts** - невдалі спроби broadcast

### Логування

```python
# Структуроване логування
logger.info(
    "Connection event",
    extra={
        "client_id": client_id,
        "event": "connect",
        "total_connections": manager.get_active_count()
    }
)
```

---

**Ця архітектура забезпечує надійну, масштабовану та легко підтримувану систему WebSocket комунікації.** 🚀

