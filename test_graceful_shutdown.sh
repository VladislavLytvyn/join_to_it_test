#!/bin/bash

# Скрипт для тестування graceful shutdown механізму
# Використання: ./test_graceful_shutdown.sh

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Тест Graceful Shutdown для WebSocket сервера             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Перевірка чи встановлено необхідні залежності
echo -e "${BLUE}[1/5]${NC} Перевірка залежностей..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не знайдено${NC}"
    exit 1
fi

if ! command -v uvicorn &> /dev/null; then
    echo -e "${YELLOW}⚠️  Uvicorn не знайдено. Встановлення...${NC}"
    pip install -r requirements.txt
fi

echo -e "${GREEN}✅ Залежності в порядку${NC}"
echo ""

# Запуск сервера
echo -e "${BLUE}[2/5]${NC} Запуск WebSocket сервера..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &
SERVER_PID=$!

echo -e "${GREEN}✅ Сервер запущено (PID: $SERVER_PID)${NC}"
echo ""

# Чекаємо поки сервер запуститься
echo -e "${BLUE}[3/5]${NC} Очікування запуску сервера..."
sleep 3

# Перевірка чи сервер запущено
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}❌ Помилка запуску сервера${NC}"
    exit 1
fi

# Перевірка доступності через curl
if command -v curl &> /dev/null; then
    HEALTH_CHECK=$(curl -s http://localhost:8000/health || echo "failed")
    if [[ $HEALTH_CHECK == *"healthy"* ]]; then
        echo -e "${GREEN}✅ Сервер відповідає на health check${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check не пройдено, але сервер працює${NC}"
    fi
fi
echo ""

# Запуск тестових клієнтів
echo -e "${BLUE}[4/5]${NC} Запуск тестових WebSocket клієнтів..."
echo -e "${YELLOW}    Клієнти будуть працювати 120 секунд${NC}"
python3 test_client.py <<EOF &
3
EOF
CLIENTS_PID=$!

sleep 5
echo -e "${GREEN}✅ Тестові клієнти запущено${NC}"
echo ""

# Тестування graceful shutdown
echo -e "${BLUE}[5/5]${NC} Тестування graceful shutdown..."
echo -e "${YELLOW}    Чекаємо 10 секунд перед відправкою SIGTERM...${NC}"
sleep 10

echo ""
echo -e "${YELLOW}⚠️  Відправка SIGTERM сигналу серверу (PID: $SERVER_PID)...${NC}"
kill -SIGTERM $SERVER_PID

echo -e "${BLUE}ℹ️  Сервер отримав SIGTERM. Очікуємо graceful shutdown...${NC}"
echo -e "${BLUE}ℹ️  Спостерігайте за логами вище для деталей процесу${NC}"
echo ""

# Чекаємо завершення сервера (максимум 60 секунд для тесту)
WAIT_TIME=0
MAX_WAIT=60

while kill -0 $SERVER_PID 2>/dev/null && [ $WAIT_TIME -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
    
    # Показуємо прогрес кожні 5 секунд
    if [ $((WAIT_TIME % 5)) -eq 0 ]; then
        echo -e "${BLUE}ℹ️  Graceful shutdown в процесі... (${WAIT_TIME}s / ${MAX_WAIT}s)${NC}"
    fi
done

echo ""

# Перевірка результату
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}❌ Сервер все ще працює після ${MAX_WAIT} секунд${NC}"
    echo -e "${YELLOW}   Примусове завершення...${NC}"
    kill -9 $SERVER_PID 2>/dev/null || true
    EXIT_CODE=1
else
    echo -e "${GREEN}✅ Graceful shutdown успішно завершено за ${WAIT_TIME} секунд!${NC}"
    EXIT_CODE=0
fi

# Очищення
kill $CLIENTS_PID 2>/dev/null || true
wait 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Тест завершено                          ║"
echo "╚════════════════════════════════════════════════════════════╝"

exit $EXIT_CODE

