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

- Python 3.12+ (или Docker)
- Hiddify Panel (API сверен с исходниками v14.0.0b5; ранее бот работал на v11)
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- UUID и proxy path администратора панели (см. ниже, откуда их взять)

### Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/getnull0/hiddify-bot.git
cd hiddify-bot
```

2. Создайте `.env` на основе `.env.example` и заполните значения:

```bash
cp .env.example .env
```

3. Запустите через Docker (при старте бот проверяет доступ к панели и пишет подсказку в лог, если что-то не так):

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
| `ADMIN_IDS` | Telegram user IDs администраторов через запятую |
| `HIDDIFY_URL` | URL панели с `https://`, без слеша в конце |
| `HIDDIFY_PROXY_PATH` | **Админский** proxy path: первый сегмент админской ссылки `https://домен/<PROXY_PATH>/<ADMIN_UUID>/admin/` |
| `HIDDIFY_ADMIN_UUID` | UUID администратора: второй сегмент той же ссылки (используется как API-ключ) |
| `HIDDIFY_USER_PATH` | **Клиентский** proxy path: первый сегмент ссылки подписки любого пользователя `https://домен/<USER_PATH>/<uuid>/` |
| `HIDDIFY_VERIFY_SSL` | `true` — проверять сертификат (Let's Encrypt), иначе без проверки (self-signed, sslip.io) |
| `ADMIN_USERNAME` | Telegram username поддержки без `@` (необязательно) |
| `QR_API_URL` | Свой сервис QR-кодов (необязательно) |

Админский и клиентский proxy path в Hiddify разные. Если перепутать, панель ответит 403/404, и бот покажет подсказку.

## Разработка

### Файлы зависимостей

| Файл | Что это |
|---|---|
| `requirements.in` | то, что нужно самому боту (3 пакета), правится вручную |
| `requirements.txt` | полный закреплённый список с хешами, ставится в Docker-образ |
| `requirements-dev.in` / `.txt` | инструменты разработки и CI (ruff, mypy, pytest, bandit...), в образ бота не попадают |

Закреплённые `.txt` не правят руками: меняете `.in` и запускаете `make lock`.

### Установка dev-зависимостей

```bash
pip install -r requirements-dev.txt
pre-commit install
```

### Все проверки одной командой

```bash
make check
```

Отдельно: `make lint`, `typecheck`, `deadcode`, `security`, `audit`, `comments`, `test`. Тесты не требуют ни `.env`, ни настоящей панели: в них поднимается фейковая панель Hiddify и фейковый Telegram, поэтому нажатия кнопок проверяются от обновления до ответа панели.

### CI

GitHub Actions (`.github/workflows/ci.yml`) запускает параллельные джобы, итоговая `gate` падает, если упала любая:

- **lint** — ruff (расширенный набор правил)
- **typecheck** — mypy `--strict`
- **quality** — vulture (мёртвый код) и проверка комментариев (английский, не больше 2 строк)
- **security** — bandit и pip-audit
- **test** — pytest с порогом покрытия
- **build** — сборка Docker-образа

Зависимости зафиксированы с хешами (`requirements*.txt`); обновляйте через `make lock`.

## Архитектура

```
bot.py             → точка входа: create_dispatcher() и main()
config.py          → Settings: валидация окружения
api/client.py      → HiddifyClient: HTTP-клиент панели, ошибки, кэш пользователей
handlers/          → aiogram Routers: common, account, server, users/ (пакет), errors
services/          → бизнес-логика поверх клиента
keyboards/         → InlineKeyboard билдеры + навигация
formatters/        → pure functions: dict панели → HTML
middlewares/       → ThrottleMiddleware (rate limiting)
utils/             → esc, типизированный доступ к полям Telegram, валидация, статус пользователя
tests/             → unit + end-to-end тесты с фейковой панелью и фейковым Telegram
```

Подробности: [docs/architecture.md](docs/architecture.md) (устройство), [docs/hiddify-api.md](docs/hiddify-api.md) (что бот берёт от API панели), [AGENTS.md](AGENTS.md) (правила для AI-агентов).

## Лицензия

MIT — см. [LICENSE](LICENSE).
