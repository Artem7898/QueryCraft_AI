# QueryCraft AI technical reference

**English** · [Русский](technical_RU.md)

[Project guide](README.md) · [Quick start and HTTP API](../README.md)

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

1. The browser sends a JSON description and the selected dialect, complexity,
   and language to `POST /api/v1/generate`. The CORS middleware handles
   preflight and controls which origins can read the response in a browser.
   [Browser request handling](../frontend/public/assets/js/main.js)
2. The route reserves a generation slot in the worker's fixed 60-second window.
   It counts request bytes as it reads the body and rejects bodies over 16 KiB
   before JSON parsing. A malformed or oversized generation request consumes a
   slot once reserved. [Generation route](../backend/app/api/v1/endpoints/query.py)
3. Pydantic trims surrounding whitespace and checks the description, enums,
   language, and unexpected fields. The handler applies the configured
   description limit after schema validation.
   [Request and response schemas](../backend/app/models/schemas.py)
4. Demo mode selects an example for users, orders, or a generic description.
   Live mode sends the description as the user message and the dialect,
   complexity, and explanation instructions as the system message. HTTPX posts
   the resulting payload to `/chat/completions` under the configured Bytez base URL.
   [Generation service](../backend/app/services/ai_service.py)
5. The service validates the provider envelope and extracts the first
   completion, its explanation, and token count when available. The response
   carries the draft, explanation, elapsed seconds, token metadata, and model
   name. The browser renders query tokens and the explanation as text.
   [Generation service](../backend/app/services/ai_service.py)
   [Output rendering](../frontend/public/assets/js/main.js)

## Settings and limits

Settings come from case-sensitive environment variables and the `.env` in the
API process's working directory. Environment variables take precedence. Use
`backend/.env` for a server started from `backend/`.
[Settings](../backend/app/config.py)

| Setting or limit | Default | Behavior |
| --- | --- | --- |
| `BYTEZ_API_KEY` | Unset | An unset or empty key, or the literal `your_api_key_here`, selects local examples in development. Production requires a key and `DEBUG=false`. |
| `BYTEZ_API_URL` | `https://api.bytez.com/models/v2/openai/v1` | Requires HTTPS with a host. Embedded credentials, query strings, and fragments are rejected. |
| `MODEL_NAME` | `Qwen/Qwen2-7B-Instruct` | The model identifier sent to Bytez and reported by the API. |
| `API_TIMEOUT` | 30 seconds | Accepts 5–120 seconds. Covers the outbound request and reading the response. |
| `ALLOWED_ORIGINS` | Local origins on ports 3000 and 8000 | Accepts a JSON array or comma-separated origins. Each entry includes a scheme and host, plus a port when needed. |
| `MAX_QUERY_LENGTH` | 1,000 characters | Allows a maximum from 3 to 1,000 characters after trimming whitespace. |
| `MAX_REQUESTS_PER_MINUTE` | 60 | Shared by all generation callers in each worker. Health routes and CORS preflight bypass this quota. |
| `ENVIRONMENT` / `DEBUG` | `development` / `false` | Startup validation requires a live credential and disables debug configuration in production. |
| `APP_NAME` | `QueryCraft AI` | Prefix used in the OpenAPI title. |
| Inbound generation body | 16 KiB | Fixed cap on bytes seen by the generation route. |
| Bytez response body | 256 KiB | Fixed cap on the streamed body. Bytez receives a request for identity encoding. |

## Errors and application boundaries

| Status | Condition | Check |
| --- | --- | --- |
| `413` | The generation body exceeded its byte limit. | Reduce the JSON payload. |
| `422` | JSON or a field failed validation. | Check the returned field location and the OpenAPI schema. |
| `429` | The worker's generation window is full. | Use the `Retry-After` value before retrying. |
| `502` | An upstream connection or HTTP request failed, or Bytez returned an invalid response. | Check the configured endpoint and the provider status. Reproduce with a synthetic description. |
| `504` | A Bytez timeout or the outbound deadline expired. | Check connectivity and `API_TIMEOUT`. |

Public validation errors omit input values. Provider failures use fixed
messages, and the versioned health response reports the configured model and
API readiness without testing Bytez. The key stays on the backend. Live
generation sends description text to Bytez. The API ends at returning a draft,
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
calls. Mock transport tests cover Bytez success, timeout, malformed output, and
response-size limits. A live Bytez check requires a configured credential and
network access. [Development commands](../README.md#development-checks)
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
- If live mode returns demo output, remove any startup override with the demo
  key and restart the process after loading the intended credential. If the API
  cannot start in production, check the credential and debug settings.
  [Configuration](../README.md#configuration)
