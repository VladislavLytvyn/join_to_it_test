# Приклади використання WebSocket сервера

Цей документ містить практичні приклади використання та тестування WebSocket сервера.

## 📚 Зміст

1. [Базове використання](#базове-використання)
2. [Тестування з Python](#тестування-з-python)
3. [Тестування з JavaScript](#тестування-з-javascript)
4. [Тестування Graceful Shutdown](#тестування-graceful-shutdown)
5. [Продвинуті сценарії](#продвинуті-сценарії)

---

## Базове використання

### Запуск сервера

```bash
# Простий запуск
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# З автоматичним перезавантаженням (для розробки)
uvicorn main:app --reload

# З налагодженням
uvicorn main:app --log-level debug
```

### Перевірка health check

```bash
curl http://localhost:8000/health
```

Очікувана відповідь:
```json
{
  "status": "healthy",
  "active_connections": 0,
  "shutdown_in_progress": false,
  "timestamp": "2025-10-15T14:30:00.123456"
}
```

---

## Тестування з Python

### Простий клієнт

```python
import asyncio
import websockets

async def simple_client():
    uri = "ws://localhost:8000/ws/my_client"
    
    async with websockets.connect(uri) as websocket:
        # Отримати привітання
        greeting = await websocket.recv()
        print(f"Сервер: {greeting}")
        
        # Відправити повідомлення
        await websocket.send("Привіт, сервере!")
        
        # Отримати відповідь
        response = await websocket.recv()
        print(f"Сервер: {response}")

asyncio.run(simple_client())
```

### Використання готового тестового клієнта

```bash
# Запуск інтерактивного режиму
python test_client.py
# Оберіть опцію 1

# Або запустіть багато клієнтів одночасно
python test_client.py
# Оберіть опцію 3 або 4
```

### Клієнт з обробкою помилок

```python
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed

async def robust_client():
    uri = "ws://localhost:8000/ws/robust_client"
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            async with websockets.connect(uri) as websocket:
                print(f"✅ Підключено (спроба {attempt + 1})")
                
                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=30.0
                        )
                        print(f"📨 {message}")
                        
                    except asyncio.TimeoutError:
                        # Ping для перевірки з'єднання
                        await websocket.ping()
                        
        except ConnectionClosed:
            print(f"⚠️ З'єднання закрито")
            if attempt < max_retries - 1:
                print(f"🔄 Повторна спроба через {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print("❌ Вичерпано спроби підключення")
                
        except Exception as e:
            print(f"❌ Помилка: {e}")
            break

asyncio.run(robust_client())
```

---

## Тестування з JavaScript

### Node.js клієнт

```javascript
// Встановіть: npm install ws

const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/nodejs_client');

ws.on('open', () => {
    console.log('✅ Підключено до сервера');
    ws.send('Привіт з Node.js!');
});

ws.on('message', (data) => {
    console.log(`📨 Отримано: ${data}`);
});

ws.on('close', () => {
    console.log('👋 З\'єднання закрито');
});

ws.on('error', (error) => {
    console.error(`❌ Помилка: ${error.message}`);
});
```

### Browser JavaScript (через DevTools Console)

```javascript
// Відкрийте консоль браузера на http://localhost:8000
const ws = new WebSocket('ws://localhost:8000/ws/browser_client');

ws.onopen = () => {
    console.log('✅ Підключено');
    ws.send('Привіт з браузера!');
};

ws.onmessage = (event) => {
    console.log('📨 Повідомлення:', event.data);
};

ws.onclose = () => {
    console.log('👋 Відключено');
};

ws.onerror = (error) => {
    console.error('❌ Помилка:', error);
};
```

### React Hook для WebSocket

```javascript
import { useEffect, useState, useRef } from 'react';

function useWebSocket(url) {
    const [messages, setMessages] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef(null);

    useEffect(() => {
        ws.current = new WebSocket(url);

        ws.current.onopen = () => {
            setIsConnected(true);
            console.log('WebSocket підключено');
        };

        ws.current.onmessage = (event) => {
            setMessages(prev => [...prev, event.data]);
        };

        ws.current.onclose = () => {
            setIsConnected(false);
            console.log('WebSocket відключено');
        };

        return () => {
            ws.current?.close();
        };
    }, [url]);

    const sendMessage = (message) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(message);
        }
    };

    return { messages, isConnected, sendMessage };
}

// Використання
function App() {
    const { messages, isConnected, sendMessage } = 
        useWebSocket('ws://localhost:8000/ws/react_client');

    return (
        <div>
            <div>Статус: {isConnected ? '✅ Підключено' : '❌ Відключено'}</div>
            <button onClick={() => sendMessage('Привіт!')}>
                Надіслати
            </button>
            <ul>
                {messages.map((msg, i) => <li key={i}>{msg}</li>)}
            </ul>
        </div>
    );
}
```

---

## Тестування Graceful Shutdown

### Автоматичний тест

```bash
# Використайте готовий скрипт
./test_graceful_shutdown.sh
```

### Ручне тестування

**Термінал 1 - Запуск сервера:**
```bash
uvicorn main:app --workers 1
```

**Термінал 2 - Підключення клієнтів:**
```bash
# Запустіть 3 клієнти
python test_client.py
# Оберіть опцію 3
```

**Термінал 3 - Моніторинг:**
```bash
# Спостерігайте за активними з'єднаннями
watch -n 1 'curl -s http://localhost:8000/health | jq'
```

**Термінал 1 - Ініціація shutdown:**
```bash
# Натисніть Ctrl+C в терміналі де запущено сервер
# АБО
kill -SIGTERM $(pgrep -f "uvicorn main:app")
```

**Очікувані логи:**

```
INFO: Отримано сигнал SIGINT. Початок graceful shutdown...
INFO: Розпочато процес graceful shutdown
INFO: Відправка повідомлення про shutdown 3 клієнтам
INFO: Shutdown в процесі: активних з'єднань: 3, часу минуло: 0.50s, залишилось до таймауту: 1799.50s
INFO: Клієнт test_client_1 відключився. Залишилось активних з'єднань: 2
INFO: Shutdown в процесі: активних з'єднань: 2, часу минуло: 10.50s, залишилось до таймауту: 1789.50s
INFO: Клієнт test_client_2 відключився. Залишилось активних з'єднань: 1
INFO: Клієнт test_client_3 відключився. Залишилось активних з'єднань: 0
INFO: Всі клієнти відключилися. Graceful shutdown завершено за 23.45 секунд
```

### Тест з таймаутом

Щоб протестувати примусовий shutdown при досягненні таймауту, змініть таймаут на меншу величину:

```python
# В main.py, змініть:
shutdown_manager = GracefulShutdownManager(manager, timeout_seconds=30)
# Таймаут тепер 30 секунд замість 30 хвилин
```

Потім:
1. Запустіть сервер
2. Підключіть клієнта
3. Надішліть SIGTERM
4. НЕ відключайте клієнта
5. Через 30 секунд сервер примусово закриє з'єднання

---

## Продвинуті сценарії

### Load Testing з Locust

Створіть `locustfile.py`:

```python
from locust import User, task, between
import websocket
import time

class WebSocketUser(User):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Підключення при старті"""
        self.ws_url = f"ws://localhost:8000/ws/locust_{id(self)}"
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
        # Запуск в окремому потоці
        import threading
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        time.sleep(1)  # Чекаємо підключення
    
    def on_open(self, ws):
        print(f"WebSocket підключено: {self.ws_url}")
    
    def on_message(self, ws, message):
        print(f"Отримано: {message}")
    
    def on_error(self, ws, error):
        print(f"Помилка: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket закрито")
    
    @task
    def send_message(self):
        """Відправка повідомлення"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send(f"Test message at {time.time()}")
    
    def on_stop(self):
        """Відключення при зупинці"""
        if self.ws:
            self.ws.close()
```

Запуск:
```bash
pip install locust websocket-client
locust -f locustfile.py --host=http://localhost:8000
# Відкрийте http://localhost:8089 в браузері
```

### Моніторинг з Prometheus

Додайте metrics endpoint в `main.py`:

```python
from prometheus_client import Counter, Gauge, generate_latest
from fastapi.responses import Response

# Метрики
active_connections_gauge = Gauge(
    'websocket_active_connections', 
    'Кількість активних WebSocket з\'єднань'
)
messages_sent_counter = Counter(
    'websocket_messages_sent_total', 
    'Всього відправлено повідомлень'
)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    active_connections_gauge.set(manager.get_active_count())
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Docker Compose з Redis для масштабування

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  websocket-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 3
```

### Інтеграція з Nginx для load balancing

```nginx
upstream websocket_backend {
    ip_hash;  # Важливо для WebSocket
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

Запуск кількох інстансів:
```bash
uvicorn main:app --port 8001 --workers 1 &
uvicorn main:app --port 8002 --workers 1 &
uvicorn main:app --port 8003 --workers 1 &
```

---

## 🔍 Корисні команди для діагностики

```bash
# Перевірка відкритих портів
sudo netstat -tlnp | grep 8000

# Перегляд процесів uvicorn
ps aux | grep uvicorn

# Моніторинг логів в реальному часі
tail -f ~/.pm2/logs/websocket-server-out.log

# Перевірка кількості активних WebSocket з'єднань
curl -s http://localhost:8000/health | jq '.active_connections'

# Відправка SIGTERM
kill -SIGTERM $(pgrep -f "uvicorn main:app")

# Відправка SIGINT (те саме що Ctrl+C)
kill -SIGINT $(pgrep -f "uvicorn main:app")
```

---

## 📊 Приклади відповідей API

### Health Check (нормальний стан)
```json
{
  "status": "healthy",
  "active_connections": 5,
  "shutdown_in_progress": false,
  "timestamp": "2025-10-15T14:30:00.123456"
}
```

### Health Check (під час shutdown)
```json
{
  "status": "healthy",
  "active_connections": 2,
  "shutdown_in_progress": true,
  "timestamp": "2025-10-15T14:35:30.789012"
}
```

---

**Готово! Ці приклади допоможуть вам повністю протестувати функціональність WebSocket сервера.** 🚀

