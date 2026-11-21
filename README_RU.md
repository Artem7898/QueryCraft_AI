# QueryCraft AI

[English](README.md) · **Русский**

QueryCraft AI превращает описание на русском или английском в черновик запроса для PostgreSQL, MySQL, SQLite или MongoDB. API возвращает текст запроса, пояснение и метаданные генерации. Приложение не подключается к СУБД и не выполняет запросы. Перед использованием сверьте результат со схемой данных и требованиями задачи.

[Руководство по проекту](Docs/README_RU.md) · [Техническое руководство](Docs/technical_RU.md)

## Архитектура

```mermaid
flowchart LR
    UI["Статический веб-интерфейс"] --> API["FastAPI · POST /api/v1/generate"]
    API -->|"Демо-режим"| Demo["Локальные примеры"]
    API -->|"Ключ Bytez задан"| Bytez["Bytez · HTTPX"]
```

- **API** проверяет входные данные через Pydantic v2, ограничивает размер и частоту запросов. Асинхронный клиент HTTPX и пул соединений живут в пределах одного процесса FastAPI.
- **Генерация** отправляет описание и необязательный контекст схемы в Bytez, затем проверяет синтаксис результата для выбранной СУБД. Готовые примеры доступны в явно включённом деморежиме.
- **Веб-интерфейс** работает на HTML, CSS и JavaScript без этапа сборки. Подсветка отображает ответ провайдера как текст в DOM.

## Локальный запуск

Требуется Python 3.12 или 3.13. Node.js и npm нужны для проверок фронтенда. Команды ниже рассчитаны на Bash.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Задайте `BYTEZ_API_KEY` в окружении или в `backend/.env`, затем запустите API из каталога `backend/`. По умолчанию сервис генерирует запросы через Bytez.

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Чтобы попробовать интерфейс без ключа, добавьте перед командой `GENERATION_MODE=demo`. Интерфейс помечает такие ответы как примеры.

Во втором терминале из корня репозитория запустите статический сервер.

```bash
python3 -m http.server --bind 127.0.0.1 --directory frontend/public 3000
```

Откройте страницу на `http://localhost:3000`. Браузер обращается к API на `http://localhost:8000/api/v1`. Для полной отрисовки стилей, шрифтов и карусели странице нужен доступ к CDN Tailwind, Swiper и Google Fonts.

## HTTP API

| Маршрут | Назначение |
| --- | --- |
| `POST /api/v1/generate` | Генерация черновика запроса |
| `GET /health` | Проверка доступности API |
| `GET /api/v1/health` | Состояние API и имя модели. Маршрут работает без запроса к Bytez |
| `GET /api/docs` | Swagger UI |
| `GET /api/redoc` | ReDoc |
| `GET /openapi.json` | Схема OpenAPI |

### Запрос генерации

```bash
curl --fail-with-body --silent --show-error http://127.0.0.1:8000/api/v1/generate \
  -H 'Content-Type: application/json' \
  --data '{"text":"Show active users older than 25","db_type":"postgresql","complexity":"simple","language":"en","schema_context":"users(id, username, email, age, status, created_at)"}'
```

| Поле | Допустимые значения | По умолчанию |
| --- | --- | --- |
| `text` | Строка из 3–1000 символов после удаления пробелов по краям | Обязательное поле |
| `db_type` | `postgresql`, `mysql`, `sqlite`, `mongodb` | `postgresql` |
| `complexity` | `simple`, `medium`, `advanced` | `medium` |
| `language` | `ru`, `en` | `ru` |
| `schema_context` | Необязательное описание схемы с таблицами или коллекциями, полями и связями, до 3000 символов | Отсутствует |

Пример ответа в демо-режиме:

```json
{
  "query": "SELECT id, username, email, age, status, created_at\nFROM users\nWHERE status = 'active' AND age > 25\nORDER BY created_at DESC\nLIMIT 100;",
  "explanation": "Selects active users older than 25",
  "executed_in": 0.0,
  "tokens_used": 150,
  "model": "Qwen/Qwen2-7B-Instruct (тестовый режим)",
  "source": "demo"
}
```

`executed_in` измеряется в секундах. Поле `source` принимает `live` для сгенерированного запроса или `demo` для готового примера. В деморежиме `tokens_used` содержит условное значение.

| Статус | Причина |
| --- | --- |
| `413` | Тело запроса превышает 64 КиБ |
| `422` | Некорректный JSON или ошибка валидации полей |
| `429` | Исчерпан лимит генерации. Время ожидания указано в `Retry-After` |
| `502` | Ошибка провайдера, некорректный формат ответа или синтаксис, который отклонил парсер выбранного диалекта |
| `503` | Выбрана генерация через Bytez и отсутствует ключ |
| `504` | Истёк тайм-аут обращения к провайдеру |

## Конфигурация

Приложение читает переменные окружения и файл `.env` из рабочей директории процесса. При запуске из `backend/` используйте `backend/.env`. Переменные окружения имеют приоритет.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `GENERATION_MODE` | `live` | Значение `demo` включает готовые примеры в среде разработки |
| `BYTEZ_API_KEY` | Не задана | Ключ для генерации через Bytez. Прежнее значение `your_api_key_here` явно включает деморежим |
| `BYTEZ_API_URL` | `https://api.bytez.com/models/v2/openai/v1` | Базовый HTTPS-адрес провайдера |
| `MODEL_NAME` | `Qwen/Qwen2-7B-Instruct` | Идентификатор модели |
| `API_TIMEOUT` | `30` | Общий тайм-аут обращения к Bytez в секундах, диапазон 5–120 |
| `ALLOWED_ORIGINS` | Локальные источники на портах 3000 и 8000 | Разрешённые источники CORS в формате JSON-массива или списка через запятую |
| `MAX_QUERY_LENGTH` | `1000` | Максимальная длина описания, диапазон 3–1000 |
| `MAX_REQUESTS_PER_MINUTE` | `60` | Общий лимит запросов генерации в минуту на процесс |
| `ENVIRONMENT` | `development` | В production требуются `live`, ключ Bytez и `DEBUG=false` |
| `DEBUG` | `false` | Флаг конфигурации для разработки |
| `APP_NAME` | `QueryCraft AI` | Имя приложения в заголовке документации API |

При генерации через Bytez сервис отправляет провайдеру описание и переданный контекст схемы. Храните ключ вне Git. В качестве контекста указывайте структуру таблиц и полей, оставляйте учётные данные и персональные записи за пределами описания.

Веб-интерфейс настроен на локальный API. При сетевом развёртывании настройте во фронтенде доступный браузеру адрес API и разрешите соответствующий источник через `ALLOWED_ORIGINS`. При нескольких воркерах применяйте общий лимит и контроль доступа на шлюзе. [Техническое руководство](Docs/technical_RU.md)

## Проверки

Из корня репозитория в активированном Python-окружении:

```bash
python -m pytest -q
ruff check backend
ruff format --check backend
mypy
```

При запущенном API в демо-режиме команда `python backend/cors_test.py` проверяет CORS и генерацию по HTTP. Тесты обращений к Bytez используют подставной HTTP-транспорт и выполняются без реального ключа.

Проверки фронтенда:

```bash
cd frontend
npm install
npm run lint
npm test -- --runInBand
```

## Структура репозитория

| Путь | Назначение |
| --- | --- |
| [`backend/app/main.py`](backend/app/main.py) | Фабрика FastAPI и жизненный цикл приложения |
| [`backend/app/api/v1/endpoints/query.py`](backend/app/api/v1/endpoints/query.py) | Генерация, диагностика и ограничения входящих запросов |
| [`backend/app/config.py`](backend/app/config.py) | Настройки и их валидация |
| [`backend/app/models/schemas.py`](backend/app/models/schemas.py) | Схемы запросов и ответов |
| [`backend/app/services/ai_service.py`](backend/app/services/ai_service.py) | Интеграция с Bytez и локальные примеры |
| [`backend/tests/`](backend/tests/) | Тесты API, конфигурации и провайдера |
| [`frontend/public/`](frontend/public/) | Статические ресурсы |
| [`frontend/tests/`](frontend/tests/) | Тесты браузерного JavaScript |

## Разработчик

Разработчик проекта — [Artem7898](https://github.com/Artem7898).
