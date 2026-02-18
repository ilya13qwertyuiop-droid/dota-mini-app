# Dota Mini App - Контекст проекта

## 🎯 Описание проекта

Telegram Mini App для подбора позиции и героев в Dota 2 на основе квизов.

### Основные функции:
1. **Position Quiz** — определяет подходящую игровую позицию (керри, мид, оффлейн, роумер, саппорт)
2. **Hero Quiz** — подбирает топ-5 героев для выбранной позиции с процентом совпадения
3. **Профиль** — отображает последнюю позицию и героев пользователя
4. **Интеграция Telegram** — авторизация через бота, отображение данных профиля

### Планы развития:
- Интеграция OpenDota API для статистики игрока
- Интеграция Stratz API для анализа матчей (требуется API ключ с особыми условиями)
- Расширенная аналитика игр пользователей

---

## 🏗️ Архитектура

### Технологический стек
- **Frontend**: SPA на чистом HTML/CSS/JS (Vanilla JavaScript)
- **Backend**: Python, FastAPI (Uvicorn), порт 8000
- **БД**: SQLite (`backend/dota_bot.db`)
- **Telegram Bot**: aiogram (polling)
- **Веб-сервер**: nginx + Let's Encrypt (HTTPS)
- **Домен**: dotaquiz.blog (Porkbun, A-записи на VPS)

### Инфраструктура
- **VPS**: Contabo, Ubuntu
- **IP**: 62.171.144.53
- **Пользователь**: zafer
- **Путь**: /home/zafer/dota-mini-app
- **Python**: venv в /home/zafer/dota-mini-app/venv

---

## 📁 Структура проекта

```
dota-mini-app/
├── backend/
│   ├── api.py              # FastAPI эндпоинты
│   ├── bot.py              # Telegram bot (aiogram)
│   ├── db.py               # Работа с SQLite
│   └── dota_bot.db         # База данных
├
│──script.js           # Основная логика приложения
│──styles.css          # Стили
│ # Данные героев по позициям
│──heroes-carry.js
│──heroes-mid.js
│──heroes-offlane.js
│──heroes-pos45.js  # Общий для роумера и саппорта
│──index.html          # Главная страница (SPA)
│
├── venv/                   # Python virtual environment
├── .env                    # Переменные окружения (не в git)
├── .gitignore
└── PROJECT_CONTEXT.md      # Этот файл
```

---

## 🗄️ База данных

### Таблицы

#### user_profiles
```sql
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY,
    favorite_heroes JSON,  -- ["Hero1", "Hero2", ...]
    settings JSON          -- {username, first_name, last_name, photo_url}
);
```

#### quiz_results
```sql
CREATE TABLE quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    result JSON NOT NULL,  -- См. структуру ниже
    updated_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id)
);
```

#### tokens
```sql
CREATE TABLE tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL
);
```

### Структура result (JSON в quiz_results)

**Новый формат** (после обновления):
```json
{
  "position_quiz": {
    "type": "position_quiz",
    "position": "Pos 1 — Керри",
    "posShort": "Керри",
    "positionIndex": 0,
    "date": "18.02.2026",
    "isPure": false,
    "extraPos": "pos2"
  },
  "hero_quiz_by_position": {
    "0": {
      "type": "hero_quiz",
      "heroPositionIndex": 0,
      "topHeroes": [
        {"name": "Anti-Mage", "score": 8.5, "matchPercent": 95},
        {"name": "Juggernaut", "score": 7.2, "matchPercent": 82},
        ...
      ]
    },
    "2": {
      "type": "hero_quiz",
      "heroPositionIndex": 2,
      "topHeroes": [...]
    }
  }
}
```

**Старый формат** (обратная совместимость):
```json
{
  "type": "position_quiz",
  "position": "Pos 1 — Керри",
  "positionIndex": 0,
  "hero_quiz": {
    "type": "hero_quiz",
    "heroPositionIndex": 0,
    "topHeroes": [...]
  }
}
```

---

## 🎮 Индексы позиций

| Позиция | Название в игре | mainPos | positionIndex | heroPositionIndex |
|---------|----------------|---------|---------------|-------------------|
| Pos 1 | Керри (Carry) | pos1 | 0 | 0 |
| Pos 2 | Мид (Mid) | pos2 | 1 | 1 |
| Pos 3 | Оффлейн (Offlane) | pos3 | 2 | 2 |
| Pos 4 | Роумер (Roamer) | pos4 | 3 | 3 |
| Pos 5 | Саппорт (Support) | pos5 | 4 | 4 |

**Важно**: 
- `positionIndex` рассчитывается как `parseInt(mainPos.replace('pos', '')) - 1`
- Позиции 4 и 5 используют **общий файл** `heroes-pos45.js` с одинаковым списком героев

---

## 🔌 API Эндпоинты

### POST /api/save_result
Сохраняет результат квиза (позиции или героев).

**Request:**
```json
{
  "token": "abc123xyz",
  "result": {
    "type": "position_quiz" | "hero_quiz",
    "positionIndex": 0,
    "heroPositionIndex": 0,
    "topHeroes": [...]
  }
}
```

**Response:** `{"success": true}`

### GET /api/profile_full?token=...
Полный профиль пользователя с историей квизов.

**Response:**
```json
{
  "user_id": 556944111,
  "username": "username",
  "first_name": "Иван",
  "photo_url": "https://...",
  "total_quizzes": 5,
  "last_quiz_date": "2026-02-18T10:30:00",
  "quiz_history": [
    {
      "date": "2026-02-18T10:30:00",
      "result": {
        "position_quiz": {...},
        "hero_quiz_by_position": {...}
      }
    }
  ]
}
```

### GET /api/get_result?token=...
Только последний результат квиза.

**Response:** `{"result": {...}}` или `{"result": null}`

### POST /api/check-subscription
Проверяет подписку пользователя на канал.

### POST /api/save_telegram_data
Сохраняет данные профиля из Telegram (имя, username, фото).

---

## 🤖 Telegram Bot

### Команды
- `/start` — генерирует токен, проверяет подписку, открывает Mini App
- `/help` — справка по использованию

### Процесс авторизации
1. Пользователь нажимает `/start`
2. Бот проверяет подписку на канал (CHECK_CHAT_ID: -1001982934939)
3. Генерируется токен через `create_token_for_user(user_id)`
4. Токен передаётся в URL: `https://dotaquiz.blog/?token=abc123xyz`
5. Frontend извлекает токен из URL: `const USER_TOKEN = getTokenFromUrl()`
6. Токен используется во всех API запросах

### Конфигурация
- **BOT_TOKEN**: 
- **MINI_APP_URL**: https://dotaquiz.blog/
- **CHECK_CHAT_ID**: -1001982934939 (канал @kasumi_tt)
- **Режим**: Polling (не webhook)

---

## 🚀 Deployment

### SSH доступ
```bash
ssh zafer@62.171.144.53
cd ~/dota-mini-app
```

### Процесс деплоя
```bash
# 1. Подключиться к серверу
ssh zafer@62.171.144.53

# 2. Перейти в проект
cd ~/dota-mini-app

# 3. Обновить код
git pull

# 4. Перезапустить сервисы
sudo systemctl restart dota-api.service
sudo systemctl restart dota-bot.service

# 5. Проверить статус
sudo systemctl status dota-api.service
sudo systemctl status dota-bot.service
```

### Systemd Services

#### dota-api.service
```ini
[Unit]
Description=Dota Mini App FastAPI backend
After=network.target

[Service]
User=zafer
WorkingDirectory=/home/zafer/dota-mini-app
Environment="BOT_TOKEN=8576767518:AAFeAqIesgJX4V67WX8H_MbmcG334PMUsdE"
Environment="CHECK_CHAT_ID=-1001982934939"
ExecStart=/home/zafer/dota-mini-app/venv/bin/python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --log-level debug
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### dota-bot.service
```ini
[Unit]
Description=Dota Telegram Bot
After=network.target

[Service]
User=zafer
WorkingDirectory=/home/zafer/dota-mini-app/backend
Environment="BOT_TOKEN=8576767518:AAFeAqIesgJX4V67WX8H_MbmcG334PMUsdE"
Environment="MINI_APP_URL=https://dotaquiz.blog/"
Environment="CHECK_CHAT_ID=-1001982934939"
ExecStart=/home/zafer/dota-mini-app/venv/bin/python /home/zafer/dota-mini-app/backend/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx конфигурация
**Файл**: `/etc/nginx/sites-available/default`

```nginx
server {
    root /home/zafer/dota-mini-app;
    index index.html index.htm;
    server_name dotaquiz.blog www.dotaquiz.blog;

    # Статические файлы и мини-апп
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Прокси на FastAPI (uvicorn backend.api:app на 8000 порту)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/dotaquiz.blog/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dotaquiz.blog/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = www.dotaquiz.blog) {
        return 301 https://$host$request_uri;
    }
    
    if ($host = dotaquiz.blog) {
        return 301 https://$host$request_uri;
    }

    listen 80 default_server;
    listen [::]:80 default_server;
    server_name dotaquiz.blog www.dotaquiz.blog;
    return 404;
}
```

---

## 🔐 Переменные окружения

### Локальная разработка
Файл `.env` в корне проекта (не в git, настроен `.gitignore`):
```env
BOT_TOKEN=8576767518:AAFeAqIesgJX4V67WX8H_MbmcG334PMUsdE
MINI_APP_URL=https://dotaquiz.blog/
CHECK_CHAT_ID=-1001982934939
```

### Продакшн
Переменные прописаны напрямую в systemd services (см. секцию Deployment).

**Примечание**: `.env` файл существует на сервере, но его использование не подтверждено. Переменные берутся из `Environment=` в systemd конфигах.

---

## 🛠️ Команды для работы

### База данных
```bash
# Подключиться к БД
sqlite3 /home/zafer/dota-mini-app/backend/dota_bot.db

# Внутри sqlite:
.tables                                          # Список таблиц
.schema quiz_results                            # Структура таблицы
.mode line                                      # Удобный формат
SELECT * FROM quiz_results WHERE user_id = 556944111;
.quit
```

### Логи
```bash
# Логи FastAPI
sudo journalctl -u dota-api.service -f

# Логи бота
sudo journalctl -u dota-bot.service -f

# Логи nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Управление сервисами
```bash
sudo systemctl status dota-api.service
sudo systemctl restart dota-api.service
sudo systemctl stop dota-api.service

sudo systemctl status dota-bot.service
sudo systemctl restart dota-bot.service

# Перезагрузка nginx
sudo systemctl reload nginx
```

### Зависимости проекта
```bash
# Активировать виртуальное окружение
source /home/zafer/dota-mini-app/venv/bin/activate

# Установить зависимости (если requirements.txt обновлён)
pip install -r backend/requirements.txt

# Основные зависимости:
# - fastapi
# - uvicorn
# - aiogram
# - sqlite3 (встроен в Python)
```

---

## ⚠️ Известные проблемы

### 1. Герои не всегда показываются в профиле
**Симптомы**: После прохождения hero_quiz герои не появляются в блоке "Твои герои". Проблема проявляется периодически, не связана конкретно с позициями 4-5.

**Возможные причины**:
- `hero_quiz_by_position[positionIndex]` не содержит данных для текущей позиции
- Несовпадение индексов между `position_quiz` и `hero_quiz`
- Данные не сохраняются на бэкенде корректно
- Проблема в логике записи/чтения из БД

**Диагностика**:
```sql
-- Проверить данные в БД
SELECT result FROM quiz_results WHERE user_id = 556944111;
```

**Статус**: В разработке. Требуется добавить debug-логи и проверить весь путь: Frontend → Backend → БД → Frontend.

### 2. Старые данные (hero_quiz vs hero_quiz_by_position)
**Проблема**: В БД могут быть записи старого формата без `hero_quiz_by_position`. Миграция не проводилась, так как приложение тестируется только одним пользователем.

**Решение**: Добавить fallback во фронтенде:
```javascript
// Сначала проверяем новый формат
if (res.hero_quiz_by_position && res.hero_quiz_by_position[positionIndex]) {
    heroData = res.hero_quiz_by_position[positionIndex];
}
// Fallback на старый формат
else if (res.hero_quiz && res.hero_quiz.heroPositionIndex === positionIndex) {
    heroData = res.hero_quiz;
}
```

**Статус**: Опционально. Можно реализовать для подстраховки.

### 3. DNS сервер
**Статус**: ✅ Решено. Проблема была одноразовая, больше не воспроизводится.

### 4. Картинки героев
**Статус**: ✅ Решено. Загружаются корректно.

---

## 📊 Тестовые данные

- **Основной user_id**: 556944111
- **Тестовый канал**: @dota2_quiz_blog (ID: -1001982934939)
- **Позиции**: Тестируются все (керри, мид, оффлейн, роумер, саппорт)
- **Других тестовых аккаунтов нет** — все тесты проводятся на основном аккаунте

---

## 📚 Полезные ссылки

- **GitHub**: https://github.com/ilya13qwertyuiop-droid/dota-mini-app
- **Домен**: https://dotaquiz.blog
- **Dota 2 Pro Tracker**: https://www.dota2protracker.com/hero/{hero_name}
- **OpenDota API**: https://docs.opendota.com/
- **Stratz API**: https://stratz.com/api (требуется особый API ключ)

---

## 🎯 Для нового треда с AI-помощником

Скопируй это в новый тред с Perplexity/Claude:

```
Проект: Dota Mini App (Telegram WebApp для подбора героев Dota 2)
Repo: github.com/ilya13qwertyuiop-droid/dota-mini-app
Stack: FastAPI + SQLite + Vanilla JS + aiogram
Сервер: zafer@62.171.144.53, ~/dota-mini-app
User ID: 556944111

Изучи PROJECT_CONTEXT.md из репозитория и помоги с [описание проблемы].
```

---

**Последнее обновление**: 18.02.2026, 16:12 +03:00