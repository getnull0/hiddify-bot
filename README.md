# Hiddify Bot

Telegram-бот для управления [Hiddify](https://github.com/hiddify/Hiddify-Panel) VPN-панелью. Полноценный администраторский интерфейс + личный кабинет для пользователей.

## Возможности

### Для администратора

- **Управление пользователями** — создание, редактирование, удаление, поиск по имени / UUID / Telegram ID
- **Контроль трафика** — блокировка / разблокировка, сброс трафика, продление подписки, установка лимитов
- **Режимы сброса** — ежемесячно / еженедельно / ежедневно / без сброса
- **Мониторинг сервера** — CPU, RAM, диск, сеть, top-5 процессов, количество соединений и IP
- **Логи панели** — 8 типов лог-файлов с просмотром прямо в Telegram
- **Привязка Telegram ID** — для каждого пользователя можно указать Telegram ID

### Для пользователя

- **Личный кабинет** — остаток трафика, дней до окончания, режим сброса, последний онлайн
- **Ссылка подписки** — копирование одним нажатием
- **QR-код** — сканирование для быстрой настройки
- **Приложения** — прямые ссылки на Hiddify, v2rayNG, NekoBox, Streisand для всех платформ

## Быстрый старт

### Требования

- Python 3.12+
- Hiddify Panel (протестировано на v11)
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))

### Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/VoidrixLab/hiddify-bot.git
cd hiddify-bot
```

2. Создайте `.env` на основе `.env.example` и заполните значения:

```bash
cp .env.example .env
```

3. Запустите через Docker:

```bash
docker compose up -d --build
```

Или локально:

```bash
pip install -r requirements.txt
python bot.py
```

### Конфигурация

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `HIDDIFY_URL` | URL Hiddify панели (без trailing slash) |
| `HIDDIFY_PROXY_PATH` | Путь перед `/api/v2` |
| `HIDDIFY_USER_PATH` | Путь для построения URL подписок пользователей |
| `HIDDIFY_ADMIN_UUID` | Admin UUID панели (используется как API-ключ) |
| `ADMIN_IDS` | Telegram user IDs через запятую |
| `ADMIN_USERNAME` | Telegram username для поддержки (без @) |
| `HIDDIFY_VERIFY_SSL` | `true` для production (Let's Encrypt), `false` для self-signed |

## Разработка

### Установка dev-зависимостей

```bash
pip install -r requirements-dev.txt
pre-commit install
```

### Линтинг и форматирование

```bash
ruff check .
ruff format .
```

### Тесты

```bash
pytest -v
```

### CI

GitHub Actions (`.github/workflows/ci.yml`) запускается на push и PR:

- **lint** — ruff check + format check
- **test** — pytest
- **build** — сборка Docker-образа

## Архитектура

```
bot.py             → точка входа: Bot + Dispatcher, маршрутизация
handlers/          → aiogram Routers (common, users, server, account)
services/          → бизнес-логика, обёртки над API
api/hiddify.py     → HTTP-клиент Hiddify REST API (aiohttp)
keyboards/         → InlineKeyboard билдеры + навигация
formatters/        → pure functions: API dict → HTML string
filters/admin.py   → IsAdmin filter
middlewares/       → ThrottleMiddleware (rate limiting)
```

Подробности — в [AGENTS.md](AGENTS.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
