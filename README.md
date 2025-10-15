# FastAPI WebSocket Server з Graceful Shutdown

## 📋 Опис проекту

Цей проект реалізує повнофункціональний WebSocket сервер на базі FastAPI з розширеним механізмом graceful shutdown. Сервер підтримує множинні WebSocket з'єднання, broadcasting повідомлень та коректне завершення роботи при отриманні системних сигналів.

### ✨ Основні можливості

- ✅ **WebSocket з'єднання** - endpoint `/ws` для підключення клієнтів
- ✅ **Connection Management** - відстеження активних з'єднань, автоматичне видалення при відключенні
- ✅ **Broadcasting** - розсилка повідомлень всім активним клієнтам
- ✅ **Periodic Messages** - автоматична розсилка повідомлень кожні 10 секунд
- ✅ **Graceful Shutdown** - коректне завершення роботи при SIGTERM/SIGINT
- ✅ **Timeout механізм** - примусове завершення через 30 хвилин при shutdown
- ✅ **Детальне логування** - прогрес shutdown, кількість з'єднань, час що залишився
- ✅ **HTML тестовий клієнт** - вбудований інтерфейс для тестування
- ✅ **Health Check** - endpoint для моніторингу стану сервера

## 🚀 Швидкий старт

### Вимоги

- Python 3.8 або вище
- pip (Python package manager)

### Встановлення

1. **Клонуйте репозиторій або створіть директорію проекту:**
```bash
cd dev/join_to_it/test_task
```

2. **Створіть віртуальне оточення (рекомендовано):**
```bash
python3 -m venv venv
source venv/bin/activate  # Для Linux/Mac
# або
venv\Scripts\activate  # Для Windows
```

3. **Встановіть залежності:**
```bash
pip install -r requirements.txt
```

### Запуск сервера

**Базовий запуск (рекомендовано для graceful shutdown):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

**Або через Python:**
```bash
python main.py
```

**Запуск з автоматичним перезавантаженням (для розробки):**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

⚠️ **ВАЖЛИВО**: Для коректної роботи graceful shutdown використовуйте `--workers 1`. При використанні кількох workers кожен буде мати свій окремий ConnectionManager, що ускладнить процес graceful shutdown.

## 🧪 Тестування

### Метод 1: Вбудований HTML клієнт (найпростіший)

1. Запустіть сервер
2. Відкрийте браузер та перейдіть на: `http://localhost:8000`
3. Натисніть кнопку "Підключитися"
4. Спостерігайте за автоматичними повідомленнями кожні 10 секунд
5. Надсилайте власні повідомлення через форму
6. Відкрийте кілька вкладок для тестування broadcasting

### Метод 2: Python клієнт

Створіть файл `test_client.py`:

```python
import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws/test_client_1"
    
    async with websockets.connect(uri) as websocket:
        print(f"Підключено до {uri}")
        
        # Отримуємо привітальне повідомлення
        greeting = await websocket.recv()
        print(f"Отримано: {greeting}")
        
        # Надсилаємо тестове повідомлення
        await websocket.send("Привіт з Python клієнта!")
        
        # Слухаємо повідомлення протягом 60 секунд
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                print(f"Повідомлення від сервера: {message}")
        except asyncio.TimeoutError:
            print("Таймаут очікування")

if __name__ == "__main__":
    asyncio.run(test_websocket())
```

Запустіть клієнт:
```bash
python test_client.py
```

### Метод 3: wscat (командний рядок)

Встановіть wscat:
```bash
npm install -g wscat
```

Підключіться до сервера:
```bash
wscat -c ws://localhost:8000/ws/my_client_id
```

### Метод 4: curl (для HTTP endpoints)

**Health check:**
```bash
curl http://localhost:8000/health
```

Відповідь:
```json
{
  "status": "healthy",
  "active_connections": 2,
  "shutdown_in_progress": false,
  "timestamp": "2025-10-15T14:30:00.123456"
}
```

## 🛑 Тестування Graceful Shutdown

### Сценарій 1: Нормальний shutdown з відключенням клієнтів

1. **Запустіть сервер:**
```bash
uvicorn main:app --workers 1
```

2. **Підключіть кілька клієнтів** (наприклад, відкрийте 3-4 вкладки браузера з `http://localhost:8000`)

3. **Надішліть сигнал SIGTERM або SIGINT:**
```bash
# Натисніть Ctrl+C в терміналі де запущено сервер
# АБО знайдіть PID процесу та надішліть сигнал:
ps aux | grep uvicorn
kill -SIGTERM <PID>
```

4. **Очікуваний результат:**
   - Всі клієнти отримають попереджувальне повідомлення
   - Сервер почне логувати прогрес кожні 10 секунд
   - Після відключення всіх клієнтів сервер коректно завершить роботу
   - В логах буде час який зайняв shutdown

**Приклад логів:**
```
INFO: Отримано сигнал SIGINT. Початок graceful shutdown...
INFO: Розпочато процес graceful shutdown
INFO: Відправка повідомлення про shutdown 3 клієнтам
INFO: Shutdown в процесі: активних з'єднань: 2, часу минуло: 10.50s, залишилось до таймауту: 1789.50s
INFO: Клієнт client_abc123 відключився. Залишилось активних з'єднань: 1
INFO: Клієнт client_def456 відключився. Залишилось активних з'єднань: 0
INFO: Всі клієнти відключилися. Graceful shutdown завершено за 15.32 секунд
```

### Сценарій 2: Shutdown з таймаутом

1. **Запустіть сервер**

2. **Підключіть клієнта але НЕ відключайте його**

3. **Надішліть SIGTERM/SIGINT**

4. **Очікуваний результат:**
   - Сервер буде логувати прогрес кожні 10 секунд
   - Через 30 хвилин (1800 секунд) сервер примусово закриє всі з'єднання
   - В логах буде повідомлення про досягнення таймауту

**Приклад логів:**
```
INFO: Shutdown в процесі: активних з'єднань: 1, часу минуло: 1790.00s, залишилось до таймауту: 10.00s
WARNING: Досягнуто таймауту 1800 секунд. Примусове завершення роботи. Активних з'єднань: 1
INFO: Закриття всіх активних з'єднань. Кількість: 1
```

### Сценарій 3: Тестування з кількома workers (показати проблему)

⚠️ **Це демонстраційний сценарій для розуміння обмежень:**

```bash
# НЕ рекомендовано для продакшену
uvicorn main:app --workers 4
```

**Проблема:** Кожен worker процес має свій окремий екземпляр `ConnectionManager` та `GracefulShutdownManager`. Це означає:
- WebSocket з'єднання розподілені між різними workers
- Кожен worker не знає про з'єднання інших workers
- Graceful shutdown працює незалежно в кожному worker
- Broadcasting не працює між workers

**Рішення:** Використовуйте `--workers 1` або реалізуйте централізоване сховище з'єднань (наприклад, через Redis).

## 📊 Архітектура та Логіка

### Компоненти системи

#### 1. ConnectionManager
Відповідальний за управління WebSocket з'єднаннями:

- **`active_connections`** - словник активних з'єднань {client_id: (websocket, connect_time)}
- **`connect()`** - додає нове з'єднання
- **`disconnect()`** - видаляє з'єднання
- **`broadcast()`** - розсилає повідомлення всім клієнтам
- **`close_all_connections()`** - закриває всі з'єднання (для shutdown)

**Thread-safety:** Використовує `asyncio.Lock()` для запобігання race conditions.

#### 2. GracefulShutdownManager
Керує процесом graceful shutdown:

- **`register_signals()`** - реєструє обробники SIGTERM/SIGINT
- **`wait_for_shutdown()`** - основна логіка shutdown процесу
- **Таймаут механізм** - примусове завершення через 30 хвилин
- **Логування** - прогрес кожні 10 секунд

#### 3. Periodic Broadcast Task
Background задача що виконується постійно:

- Запускається при старті додатку
- Відправляє повідомлення кожні 10 секунд
- Автоматично зупиняється при shutdown

### Процес Graceful Shutdown

```
1. Отримано SIGTERM/SIGINT сигнал
   ↓
2. Встановлюється shutdown_event
   ↓
3. Відправка попереджувального повідомлення всім клієнтам
   ↓
4. Початок циклу очікування:
   ├─ Перевірка: всі клієнти відключились? → Завершення
   ├─ Перевірка: таймаут досягнуто? → Примусове закриття
   └─ Логування прогресу кожні 10 секунд
   ↓
5. Завершення роботи сервера
```

### Обробка Edge Cases

Код враховує та обробляє наступні граничні випадки:

1. **Клієнт відключився під час відправки повідомлення**
   - Broadcasting ловить виключення та видаляє failed клієнтів

2. **Shutdown під час відсутності активних з'єднань**
   - Миттєве завершення без очікування

3. **Нове з'єднання під час shutdown**
   - Відхиляється з кодом 1001 (Going Away)

4. **Таймаут досягнуто з активними з'єднаннями**
   - Примусове закриття всіх з'єднань з повідомленням

5. **Помилки при закритті окремих з'єднань**
   - Логування помилки, продовження обробки інших

6. **Кілька workers**
   - Попередження в логах про необхідність використання `--workers 1`

7. **Concurrent доступ до active_connections**
   - Використання asyncio.Lock() для thread-safety

## 📁 Структура проекту

```
test_task/
├── main.py              # Основний файл з усім кодом
├── requirements.txt     # Залежності Python
└── README.md           # Ця документація
```

## 🔧 Налаштування

### Зміна таймауту shutdown

За замовчуванням таймаут = 30 хвилин (1800 секунд). Для зміни:

```python
# В main.py, рядок створення shutdown_manager
shutdown_manager = GracefulShutdownManager(
    manager, 
    timeout_seconds=3600  # 1 година
)
```

### Зміна інтервалу periodic broadcast

За замовчуванням = 10 секунд. Для зміни:

```python
# В main.py, функція periodic_broadcast_task
await asyncio.wait_for(
    shutdown_manager.shutdown_event.wait(),
    timeout=30.0  # 30 секунд
)
```

### Зміна інтервалу логування shutdown

За замовчуванням = 10 секунд. Для зміни:

```python
# В main.py, метод wait_for_shutdown
log_interval = 5  # Логувати кожні 5 секунд
```

## 🐛 Відладка

### Увімкнення DEBUG логування

```bash
uvicorn main:app --log-level debug
```

Або в коді:
```python
# В main.py, початок файлу
logging.basicConfig(
    level=logging.DEBUG,  # Було INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Перевірка стану сервера

```bash
# Перевірка health check
curl http://localhost:8000/health

# Перевірка логів в реальному часі
tail -f /var/log/uvicorn.log  # Якщо логи пишуться в файл
```

## 📈 Продакшн розгортання

### Systemd Service (Linux)

Створіть `/etc/systemd/system/websocket-server.service`:

```ini
[Unit]
Description=FastAPI WebSocket Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=dev/join_to_it/test_task
Environment="PATH=dev/join_to_it/test_task/venv/bin"
ExecStart=dev/join_to_it/test_task/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10

# Graceful shutdown
TimeoutStopSec=1900
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

Керування сервісом:
```bash
sudo systemctl enable websocket-server
sudo systemctl start websocket-server
sudo systemctl status websocket-server
sudo systemctl stop websocket-server  # Тригерить graceful shutdown
```

### Docker

Створіть `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000

# Важливо: workers=1 для graceful shutdown
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

Білд та запуск:
```bash
docker build -t websocket-server .
docker run -p 8000:8000 websocket-server
```

### Nginx як Reverse Proxy

```nginx
upstream websocket_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Важливо для довгих WebSocket з'єднань
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

## ❓ FAQ

**Q: Чому використовується workers=1?**
A: При використанні кількох workers кожен процес має свій окремий ConnectionManager. Це означає що broadcasting та graceful shutdown не працюють коректно між різними workers. Для масштабування використовуйте horizontal scaling (кілька інстансів) з load balancer + централізоване сховище (Redis).

**Q: Що станеться якщо клієнт не відключиться протягом 30 хвилин?**
A: Сервер примусово закриє всі з'єднання після досягнення таймауту та завершить роботу. Клієнт отримає повідомлення про закриття з'єднання.

**Q: Чи можна змінити таймаут?**
A: Так, передайте параметр `timeout_seconds` при створенні `GracefulShutdownManager`. Див. розділ "Налаштування".

**Q: Як протестувати на великій кількості клієнтів?**
A: Використайте інструменти для навантажувального тестування як `locust`, `Artillery` або напишіть скрипт що створює багато паралельних WebSocket з'єднань.

**Q: Чи підтримується SSL/TLS?**
A: Так, використовуйте uvicorn з параметрами `--ssl-keyfile` та `--ssl-certfile`, або розгорніть за Nginx з SSL.

## 📝 Технічний стек

- **FastAPI** 0.109.0 - Сучасний веб-фреймворк
- **Uvicorn** 0.27.0 - ASGI сервер
- **WebSockets** 12.0 - WebSocket протокол
- **Python** 3.8+ - Мова програмування
- **AsyncIO** - Асинхронне програмування

## 🎯 Виконані вимоги

✅ WebSocket Server з endpoint `/ws`
✅ Відстежування активних WebSocket з'єднань
✅ Розсилка повідомлень кожні 10 секунд
✅ Connection Management з автоматичним видаленням
✅ Broadcasting повідомлень всім клієнтам
✅ Graceful Shutdown при SIGTERM/SIGINT
✅ Таймаут 30 хвилин для примусового shutdown
✅ Детальне логування прогресу
✅ Обробка випадку з кількома workers
✅ Готовий до запуску проект
✅ Повна документація

## 📞 Контакти

Проект створено як тестове завдання для позиції Middle Python Engineer.

---

**Дякую за увагу! Успіхів в роботі! 🚀**

