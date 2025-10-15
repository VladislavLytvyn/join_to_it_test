import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manager for managing active WebSocket connections

    Responsible for:
    - Adding/removing clients
    - Broadcasting messages to all clients
    - Tracking the number of active connections
    """
    
    def __init__(self):
        self.active_connections: Dict[str, tuple[WebSocket, float]] = {}
        self._lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Adds a new WebSocket connection to the list of active ones

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = (websocket, time.time())
            logger.info(f"Клієнт {client_id} підключився. Всього активних з'єднань: {len(self.active_connections)}")
    
    async def disconnect(self, client_id: str) -> None:
        """
        Removes WebSocket connections from the list of active ones
        
        Args:
            client_id: Client ID to delete
        """
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                logger.info(f"Клієнт {client_id} відключився. Залишилось активних з'єднань: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """
        Sends a personal message to a specific customer
        
        Args:
            message: Message text
            websocket: WebSocket client connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Помилка відправки персонального повідомлення: {e}")
    
    async def broadcast(self, message: str, exclude_ids: Set[str] = None) -> None:
        """
        Sends messages to all active customers
        
        Args:
            message: Message text for the newsletter
            exclude_ids: Set of customer IDs to exclude from the mailing list
        """
        if exclude_ids is None:
            exclude_ids = set()
            
        async with self._lock:
            client_ids = list(self.active_connections.keys())
        
        failed_clients = []
        for client_id in client_ids:
            if client_id in exclude_ids:
                continue
                
            async with self._lock:
                if client_id not in self.active_connections:
                    continue
                websocket, _ = self.active_connections[client_id]
            
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Помилка відправки повідомлення клієнту {client_id}: {e}")
                failed_clients.append(client_id)
        
        for client_id in failed_clients:
            await self.disconnect(client_id)
    
    def get_active_count(self) -> int:
        """Returns the number of active connections"""
        return len(self.active_connections)
    
    async def close_all_connections(self) -> None:
        """
        Closes all active WebSocket connections
        Used for graceful shutdown
        """
        async with self._lock:
            client_ids = list(self.active_connections.keys())
        
        logger.info(f"Закриття всіх активних з'єднань. Кількість: {len(client_ids)}")
        
        for client_id in client_ids:
            try:
                async with self._lock:
                    if client_id in self.active_connections:
                        websocket, _ = self.active_connections[client_id]
                
                await websocket.send_text("Сервер завершує роботу. З'єднання буде закрито.")
                await websocket.close()
                
            except Exception as e:
                logger.error(f"Помилка при закритті з'єднання {client_id}: {e}")
            finally:
                await self.disconnect(client_id)


class GracefulShutdownManager:
    """
    Manager for graceful server shutdown

    Handles SIGTERM/SIGINT signals and manages the shutdown process:
    - Waits for all clients to disconnect
    - Force shutdown after timeout (30 minutes)
    - Logs progress
    """
    
    def __init__(self, connection_manager: ConnectionManager, timeout_seconds: int = 20):
        """
        Args:
            connection_manager: Connection Manager
            timeout_seconds: Maximum wait time in seconds (default 1800 seconds)
        """
        self.connection_manager = connection_manager
        self.timeout_seconds = timeout_seconds
        self.shutdown_event = asyncio.Event()
        self._shutdown_started = False
        
    def signal_handler(self):
        """
        SIGTERM/SIGINT signal handler (asyncio version)
        """
        if not self._shutdown_started:
            self._shutdown_started = True
            logger.info("Отримано сигнал SIGTERM/SIGINT. Початок graceful shutdown...")
            self.shutdown_event.set()
        else:
            logger.warning("Отримано повторний сигнал. Примусове завершення...")
            os._exit(1)
    
    def register_signals(self):
        """Registers handlers for SIGTERM and SIGINT signals"""
        loop = asyncio.get_running_loop()
        
        loop.add_signal_handler(signal.SIGTERM, self.signal_handler)
        loop.add_signal_handler(signal.SIGINT, self.signal_handler)
        
        logger.info("Signal handlers for SIGTERM and SIGINT registered")
    
    async def wait_for_shutdown(self):
        """
        Waits for shutdown signal and manages the shutdown process

        Logic:
        1. Waits for shutdown signal
        2. If no clients - shutdown immediately  
        3. If clients exist - wait timeout_seconds allowing them to continue working
        4. After timeout - force close all connections
        5. Server stops
        """
        logger.info("Shutdown task запущено. Очікування сигналу...")
        await self.shutdown_event.wait()
        
        logger.info("=== Розпочато процес graceful shutdown ===")
        
        active_count = self.connection_manager.get_active_count()
        
        if active_count == 0:
            logger.info("Немає активних з'єднань. Зупинка сервера.")
            logger.info("Завершення роботи сервера...")
            os.kill(os.getpid(), signal.SIGTERM)
            return
        
        logger.info(
            f"Активних клієнтів: {active_count}. "
            f"Сервер зупиниться через {self.timeout_seconds} секунд. "
            f"Клієнти можуть продовжувати працювати до завершення таймауту."
        )
        
        await self.connection_manager.broadcast(
            "⚠️ УВАГА: Сервер розпочинає процес завершення роботи.\n"
            "Робота сервера буде завершена через 30 хвилин.\n"
            "Будь ласка, збережіть вашу роботу та відключіться."
        )
        
        start_time = time.time()
        log_interval = 5
        last_log_time = time.time()
        
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            if elapsed_time >= self.timeout_seconds:
                active_count = self.connection_manager.get_active_count()
                logger.warning(
                    f"Таймаут {self.timeout_seconds} секунд досягнуто. "
                    f"Примусове закриття {active_count} активних з'єднань."
                )
                await self.connection_manager.close_all_connections()
                
                logger.info("Всі з'єднання закрито. Завершення роботи сервера...")
                
                await asyncio.sleep(0.5)
                os._exit(0)
            
            if current_time - last_log_time >= log_interval:
                remaining_time = self.timeout_seconds - elapsed_time
                active_count = self.connection_manager.get_active_count()
                logger.info(
                    f"Shutdown через {remaining_time:.1f}s. "
                    f"Активних з'єднань: {active_count}. "
                    f"Клієнти можуть продовжувати працювати."
                )
                last_log_time = current_time
            
            await asyncio.sleep(1)
        
        logger.info("Graceful shutdown процес завершено. Сервер зупиняється.")


manager = ConnectionManager()
shutdown_manager = GracefulShutdownManager(manager)


async def periodic_broadcast_task():
    """
    Background task for periodic sending of messages to all clients
    Sends a message every 10 seconds
    """
    logger.info("Starting periodic broadcast task")
    
    while not shutdown_manager.shutdown_event.is_set():
        try:
            await asyncio.wait_for(
                shutdown_manager.shutdown_event.wait(),
                timeout=10.0
            )
            break
        except asyncio.TimeoutError:
            pass
        
        active_count = manager.get_active_count()
        if active_count > 0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"📢 Periodic broadcast [{timestamp}]: Активних клієнтів: {active_count}"
            logger.info(f"Відправка periodic broadcast повідомлення. Клієнтів: {active_count}")
            await manager.broadcast(message)
    
    logger.info("Periodic broadcast task завершено")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application lifecycle management

    Launches:
    - Signal handler registration
    - Background task for periodic broadcast
    - Graceful shutdown process
    """
    logger.info("FastAPI application is starting up...")
    
    shutdown_manager.register_signals()
    
    broadcast_task = asyncio.create_task(periodic_broadcast_task())
    
    # ВАЖЛИВО: Запускаємо wait_for_shutdown як окрему задачу в startup phase
    # Інакше вона не викличеться, бо ми перехопили SIGTERM/SIGINT
    shutdown_task = asyncio.create_task(shutdown_manager.wait_for_shutdown())
    
    logger.info("FastAPI application started successfully")
    
    yield
    
    logger.info("FastAPI application is closing down...")
    
    # Якщо shutdown task ще виконується - чекаємо
    if not shutdown_task.done():
        # Тригеруємо shutdown якщо ще не тригернуто
        if not shutdown_manager.shutdown_event.is_set():
            shutdown_manager.shutdown_event.set()
        
        try:
            await asyncio.wait_for(shutdown_task, timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning("Shutdown task не завершився вчасно")
    
    if not broadcast_task.done():
        broadcast_task.cancel()
        try:
            await broadcast_task
        except asyncio.CancelledError:
            pass
    
    logger.info("FastAPI the application has stopped completely")


app = FastAPI(
    title="WebSocket Server with Graceful Shutdown",
    description="WebSocket сервер з підтримкою graceful shutdown",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    """
    Home page with HTML client for WebSocket testing
    """
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>WebSocket Test Client</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .status {
                    padding: 10px;
                    margin: 20px 0;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                }
                .connected {
                    background-color: #d4edda;
                    color: #155724;
                }
                .disconnected {
                    background-color: #f8d7da;
                    color: #721c24;
                }
                button {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    margin: 5px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                }
                button:hover {
                    background-color: #0056b3;
                }
                button:disabled {
                    background-color: #ccc;
                    cursor: not-allowed;
                }
                .disconnect-btn {
                    background-color: #dc3545;
                }
                .disconnect-btn:hover {
                    background-color: #c82333;
                }
                #messages {
                    border: 1px solid #ddd;
                    height: 400px;
                    overflow-y: auto;
                    padding: 15px;
                    margin: 20px 0;
                    background-color: #fafafa;
                    border-radius: 5px;
                }
                .message {
                    margin: 5px 0;
                    padding: 8px;
                    border-left: 3px solid #007bff;
                    background-color: white;
                }
                .system-message {
                    border-left-color: #ffc107;
                    background-color: #fff3cd;
                }
                .error-message {
                    border-left-color: #dc3545;
                    background-color: #f8d7da;
                }
                .input-group {
                    display: flex;
                    gap: 10px;
                    margin: 20px 0;
                }
                #messageInput {
                    flex: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    font-size: 14px;
                }
                .button-group {
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔌 WebSocket Test Client</h1>
                
                <div id="status" class="status disconnected">
                    Відключено
                </div>
                
                <div class="button-group">
                    <button id="connectBtn" onclick="connect()">Підключитися</button>
                    <button id="disconnectBtn" onclick="disconnect()" disabled class="disconnect-btn">Відключитися</button>
                </div>
                
                <div id="messages"></div>
                
                <div class="input-group">
                    <input type="text" id="messageInput" placeholder="Введіть повідомлення..." disabled>
                    <button id="sendBtn" onclick="sendMessage()" disabled>Відправити</button>
                </div>
                
                <div style="text-align: center; color: #666; margin-top: 20px;">
                    <small>Сервер автоматично надсилає повідомлення кожні 10 секунд</small>
                </div>
            </div>
            
            <script>
                let ws = null;
                const messagesDiv = document.getElementById('messages');
                const statusDiv = document.getElementById('status');
                const connectBtn = document.getElementById('connectBtn');
                const disconnectBtn = document.getElementById('disconnectBtn');
                const messageInput = document.getElementById('messageInput');
                const sendBtn = document.getElementById('sendBtn');
                
                function addMessage(text, type = 'normal') {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message';
                    if (type === 'system') {
                        messageDiv.classList.add('system-message');
                    } else if (type === 'error') {
                        messageDiv.classList.add('error-message');
                    }
                    
                    const timestamp = new Date().toLocaleTimeString('uk-UA');
                    messageDiv.innerHTML = `<small>[${timestamp}]</small> ${text}`;
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
                
                function updateStatus(connected) {
                    if (connected) {
                        statusDiv.textContent = '✅ Підключено';
                        statusDiv.className = 'status connected';
                        connectBtn.disabled = true;
                        disconnectBtn.disabled = false;
                        messageInput.disabled = false;
                        sendBtn.disabled = false;
                    } else {
                        statusDiv.textContent = '❌ Відключено';
                        statusDiv.className = 'status disconnected';
                        connectBtn.disabled = false;
                        disconnectBtn.disabled = true;
                        messageInput.disabled = true;
                        sendBtn.disabled = true;
                    }
                }
                
                function connect() {
                    const clientId = 'client_' + Math.random().toString(36).substr(2, 9);
                    const wsUrl = `ws://${window.location.host}/ws/${clientId}`;
                    
                    addMessage(`Підключення до ${wsUrl}...`, 'system');
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function(event) {
                        addMessage("WebSocket з'єднання встановлено!", 'system');
                        updateStatus(true);
                    };
                    
                    ws.onmessage = function(event) {
                        addMessage(`📨 ${event.data}`);
                    };
                    
                    ws.onerror = function(error) {
                        addMessage("❌ Помилка WebSocket з'єднання", 'error');
                        console.error('WebSocket error:', error);
                    };
                    
                    ws.onclose = function(event) {
                        addMessage("WebSocket з'єднання закрито", 'system');
                        updateStatus(false);
                        ws = null;
                    };
                }
                
                function disconnect() {
                    if (ws) {
                        ws.close();
                    }
                }
                
                function sendMessage() {
                    const message = messageInput.value.trim();
                    if (message && ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(message);
                        addMessage(`📤 Ви: ${message}`, 'system');
                        messageInput.value = '';
                    }
                }
                
                // Відправка повідомлення по Enter
                messageInput.addEventListener('keypress', function(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring server status
    """
    return {
        "status": "healthy",
        "active_connections": manager.get_active_count(),
        "shutdown_in_progress": shutdown_manager.shutdown_event.is_set(),
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for handling connections

    Args:
    websocket: WebSocket connection
    client_id: Unique client identifier

    Logic:
    1. Accept connection and add client to manager
    2. Send welcome message
    3. Handle incoming messages from client
    4. Auto-delete on disconnection
    """
    if shutdown_manager.shutdown_event.is_set():
        logger.warning(f"Відхилено з'єднання від {client_id}: сервер в процесі shutdown")
        await websocket.close(code=1001, reason="Сервер завершує роботу")
        return
    
    await manager.connect(websocket, client_id)
    
    try:
        await manager.send_personal_message(
            f"👋 Вітаємо, {client_id}! Ви успішно підключені до WebSocket сервера.",
            websocket
        )
        
        await manager.broadcast(
            f"ℹ️ Клієнт {client_id} приєднався. Всього активних: {manager.get_active_count()}",
            exclude_ids={client_id}
        )
        
        while True:
            data = await websocket.receive_text()
            
            logger.info(f"Отримано повідомлення від {client_id}: {data}")
            
            await manager.send_personal_message(
                f"✅ Ваше повідомлення отримано: {data}",
                websocket
            )
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await manager.broadcast(
                f"💬 [{timestamp}] {client_id}: {data}",
                exclude_ids={client_id}
            )
            
    except WebSocketDisconnect:
        logger.info(f"Клієнт {client_id} відключився (WebSocketDisconnect)")
        
    except Exception as e:
        logger.error(f"Помилка при обробці WebSocket з'єднання {client_id}: {e}", exc_info=True)
        
    finally:
        await manager.disconnect(client_id)
        
        if manager.get_active_count() > 0:
            await manager.broadcast(
                f"ℹ️ Клієнт {client_id} відключився. Залишилось активних: {manager.get_active_count()}"
            )


if __name__ == "__main__":
    import uvicorn
    
    logger.warning(
        "ATTENTION: For graceful shutdown to work correctly, use:"
        "uvicorn main:app --workers 1"
    )
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

