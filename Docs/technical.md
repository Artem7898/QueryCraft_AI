# QueryCraft AI technical reference

**English** · [Русский](technical_RU.md)

[Project guide](README.md) · [Generation providers](providers.md) · [Quick start and HTTP API](../README.md)

## Runtime

The web interface is a static HTML, CSS, and JavaScript application served from
`frontend/public/`. Uvicorn serves the FastAPI application on Python 3.12 or 3.13.
Local development uses port 3000 for the frontend and port 8000 for the API. Node.js and
npm support development checks. The browser loads the application directly.
[Frontend entry point](../frontend/public/index.html)

`create_app()` builds the application and accepts settings and an optional
outbound HTTP transport for testing. Each ASGI lifespan owns an asynchronous
HTTPX client with a connection pool, a generation rate limiter, and the effective
description length limit. The pool allows up to 20 connections and 10 keep-alive
connections. Each maximum is capped by `MAX_REQUESTS_PER_MINUTE`. Shutdown closes
the client and its connections. [Application factory](../backend/app/main.py)
[Runtime state](../backend/app/runtime.py)

## Generation request lifecycle

1. The browser sends a JSON description, optional schema context, and the selected
   dialect, complexity, and language to `POST /api/v1/generate`. The CORS middleware handles
   preflight and controls which origins can read the response in a browser.
   [Browser request handling](../frontend/public/assets/js/main.js)
2. The route reserves a generation slot in the worker's fixed 60-second window.
   It counts request bytes as it reads the body and rejects bodies over 64 KiB
   before JSON parsing. A malformed or oversized generation request consumes a
   slot once reserved. [Generation route](../backend/app/api/v1/endpoints/query.py)
3. Pydantic trims surrounding whitespace, checks the input fields, and rejects
   unexpected fields. The handler applies the configured
   description limit after schema validation.
   [Request and response schemas](../backend/app/models/schemas.py)
4. Demo mode selects an example for users, orders, or a generic description.
   Live mode sends the description and any supplied schema context in the user
   message. The selected dialect, complexity, and explanation instructions go
   in the system message. HTTPX posts
   the resulting payload to the selected provider's OpenAI-compatible
   `/chat/completions` endpoint. OpenAI uses `max_completion_tokens`, while
   Bytez and Ollama use `max_tokens`.
   [Generation service](../backend/app/services/ai_service.py)
5. The service extracts the first completion and checks its syntax with SQLGlot
   for PostgreSQL, MySQL, and SQLite, or with the JavaScript parser and a MongoDB
   shell structure check for MongoDB. The response includes `source` (`live`
   or `demo`) and the provider name for generated results. The browser renders
   query tokens and the explanation as text.
   [Generation service](../backend/app/services/ai_service.py)
   [Dialect validation](../backend/app/services/query_validation.py)
   [Output rendering](../frontend/public/assets/js/main.js)

## Settings and limits

Settings come from case-sensitive environment variables and the `.env` in the
API process's working directory. Environment variables take precedence. Use
`backend/.env` for a server started from `backend/`.
[Settings](../backend/app/config.py)

| Setting or limit | Default | Behavior |
| --- | --- | --- |
| `GENERATION_MODE` | `live` | Developers can explicitly select `demo` for local examples. |
| `GENERATION_PROVIDER` | `bytez` | Set to `bytez`, `openai`, or `ollama`. |
| `BYTEZ_API_KEY` | Unset | Key for Bytez. The legacy value `your_api_key_here` selects demo mode when Bytez is configured. |
| `QUERYCRAFT_OPENAI_API_KEY` / `OPENAI_API_KEY` | Unset | Key for OpenAI. The scoped variable takes precedence. |
| `BYTEZ_API_URL` | `https://api.bytez.com/models/v2/openai/v1` | Requires HTTPS with a host. Embedded credentials, query strings, and fragments are rejected. |
| `OLLAMA_API_URL` | `http://127.0.0.1:11434/v1` | HTTP allowed for loopback only. Remote hosts require HTTPS. |
| `MODEL_NAME` | Provider default | Model identifier sent to the selected provider and reported by the API. |
| `API_TIMEOUT` | 30 seconds | Accepts 5–120 seconds. Covers the outbound request and reading the response. |
| `ALLOWED_ORIGINS` | Local origins on ports 3000 and 8000 | Accepts a JSON array or comma-separated origins. Each entry includes a scheme and host, plus a port when needed. |
| `MAX_QUERY_LENGTH` | 1,000 characters | Allows a maximum from 3 to 1,000 characters after trimming whitespace. |
| `MAX_REQUESTS_PER_MINUTE` | 60 | Shared by all generation callers in each worker. Health routes and CORS preflight bypass this quota. |
| `ENVIRONMENT` / `DEBUG` | `development` / `false` | Production requires live generation and disabled debug configuration. Bytez and OpenAI require keys. |
| `APP_NAME` | `QueryCraft AI` | Prefix used in the OpenAPI title. |
| Schema context | Optional | Up to 3,000 characters after trimming whitespace. |
| Inbound generation body | 64 KiB | Fixed cap on bytes seen by the generation route. |
| Provider response body | 256 KiB | Fixed cap on the streamed body. The client requests identity encoding. |

## Errors and application boundaries

| Status | Condition | Check |
| --- | --- | --- |
| `413` | The generation body exceeded its byte limit. | Reduce the JSON payload. |
| `422` | JSON or a field failed validation. | Check the returned field location and the OpenAPI schema. |
| `429` | The worker's generation window is full. | Use the `Retry-After` value before retrying. |
| `502` | The provider failed, or the response format or generated syntax was invalid. | Check the selected service and model. With Ollama, confirm the service is running and the model is installed. |
| `503` | The selected cloud provider's key is missing. | Configure its key in the server environment and restart the API. |
| `504` | The outbound provider deadline expired. | Check connectivity and `API_TIMEOUT`, especially on first use of a local model. |

Public validation errors omit input values. Provider failures use fixed
messages, and the versioned health response reports the configured model and
API readiness without contacting the provider. The client sends the description
and supplied schema context to the selected provider. Authorization is sent
only to the selected cloud provider. Loopback Ollama connections ignore proxy
settings from the environment. A parser checks syntax without a database
connection. The API returns query text,
and reviewing it against the intended schema remains the caller's responsibility.
[Error responses and health](../backend/app/main.py)
[Provider request](../backend/app/services/ai_service.py)

CORS controls which origins can read API responses in a browser. A hosted
deployment needs its own access control, and deployments with several workers
need a shared limit at the gateway if they require one quota across workers.
[Runtime state](../backend/app/runtime.py)

## Frontend

`main.js` handles the form, the API health check, SQL highlighting, and copying
the draft. The browser stores language and theme preferences in `localStorage`.
The service worker registers and claims clients. The interface and API use
network responses. The page loads Tailwind, Swiper, and Google Fonts
from external CDNs. [Main script](../frontend/public/assets/js/main.js)
[Service worker](../frontend/public/service-worker.js)
[External assets](../frontend/public/index.html)

## Verification and troubleshooting

Run the backend tests, Ruff lint and format checks, mypy, and the frontend Jest
and ESLint checks using the commands in the quick start. The backend suite
covers strict validation, CORS, request size and rate limiting under concurrent
calls. Mock transport tests cover provider selection, authorization, timeouts,
malformed output, and response-size limits. For an integration check, run a
local model or configure credentials and egress for a cloud service.
[Development commands](../README.md#development-checks)
[Backend tests](../backend/tests/)
[Frontend tests](../frontend/tests/)

- If the browser cannot reach the API, check `GET /api/v1/health` from the same
  machine that runs the browser and verify the API URL shown in DevTools. For
  hosted use, configure the API base in `main.js` and the connection check in
  `app-state.js` if that check is used.
  [Main script](../frontend/public/assets/js/main.js)
  [State helper](../frontend/public/assets/js/app-state.js)
- If a browser request fails but a direct HTTP request succeeds, compare its
  `Origin` header to `ALLOWED_ORIGINS` and check the browser's `OPTIONS` preflight.
  [HTTP CORS probe](../backend/cors_test.py)
- If the page loads without styling or the carousel, inspect the CDN requests
  in DevTools and verify that the browser can reach the required hosts.
  [External assets](../frontend/public/index.html)
- If the form shows a demo example, check `GENERATION_MODE` and any legacy
  Bytez demo key. Restart after selecting the intended provider. If production
  startup fails, check the generation mode, debug configuration, and any
  required cloud key.
  [Configuration](../README.md#configuration)
