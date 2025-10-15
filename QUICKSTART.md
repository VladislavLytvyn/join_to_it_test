# 🚀 Швидкий старт

Ласкаво просимо! Цей гайд допоможе вам запустити WebSocket сервер за 5 хвилин.

## Крок 1: Встановлення залежностей (1 хвилина)

```bash
# Перейдіть в директорію проекту
cd dev/join_to_it/test_task

# Створіть віртуальне оточення (рекомендовано)
python3 -m venv venv
source venv/bin/activate

# Встановіть залежності
pip install -r requirements.txt
```

## Крок 2: Запуск сервера (30 секунд)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Ви побачите:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Крок 3: Тестування (3 хвилини)

### Варіант A: Через браузер (найпростіше)

1. Відкрийте браузер
2. Перейдіть на: http://localhost:8000
3. Натисніть "Підключитися"
4. Спостерігайте за автоматичними повідомленнями кожні 10 секунд
5. Надсилайте власні повідомлення

### Варіант B: Python клієнт

Відкрийте новий термінал:
```bash
python test_client.py
# Оберіть опцію 1 (інтерактивний режим)
```

### Варіант C: Перевірка health check

```bash
curl http://localhost:8000/health
```

## Крок 4: Тестування Graceful Shutdown (1 хвилина)

### Спосіб 1: Автоматичний тест

```bash
# У новому терміналі
./test_graceful_shutdown.sh
```

### Спосіб 2: Ручний тест

1. **Термінал 1**: Сервер вже запущено
2. **Термінал 2**: Запустіть клієнтів
   ```bash
   python test_client.py
   # Оберіть опцію 3
   ```
3. **Термінал 1**: Натисніть `Ctrl+C`
4. Спостерігайте за логами graceful shutdown

## 🎉 Готово!

Ваш WebSocket сервер працює! Що далі?

- 📖 Детальна документація: [README.md](README.md)
- 💡 Приклади використання: [EXAMPLES.md](EXAMPLES.md)
- 🔧 Налаштування для продакшн: [README.md#продакшн-розгортання](README.md#продакшн-розгортання)

## 🆘 Виникли проблеми?

### Помилка: "Address already in use"

```bash
# Знайдіть процес що використовує порт 8000
sudo lsof -i :8000
# Або
sudo netstat -tlnp | grep 8000

# Завершіть процес
kill -9 <PID>
```

### Помилка: "Module not found"

```bash
# Переконайтесь що ви в віртуальному оточенні
source venv/bin/activate

# Перевстановіть залежності
pip install -r requirements.txt
```

### Помилка: "Permission denied" для скрипта

```bash
chmod +x test_graceful_shutdown.sh
```

## 📊 Корисні команди

```bash
# Запуск з автоматичним перезавантаженням (розробка)
uvicorn main:app --reload

# Запуск з debug логами
uvicorn main:app --log-level debug

# Перевірка активних з'єднань
curl -s http://localhost:8000/health | python3 -m json.tool
```

---

**Успіхів! 🚀**

