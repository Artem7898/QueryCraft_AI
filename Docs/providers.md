# Generation providers

**English** · [Русский](providers_RU.md)

Set `GENERATION_PROVIDER` on the backend and restart the API when switching providers. The form and query validation work the same way for all providers.

| Provider | Setting | Credential | Default model |
| --- | --- | --- | --- |
| Ollama | `ollama` | None for local inference | `qwen2.5-coder:1.5b` |
| OpenAI | `openai` | `QUERYCRAFT_OPENAI_API_KEY` or `OPENAI_API_KEY` | `gpt-4.1-mini` |
| Bytez | `bytez` (default) | `BYTEZ_API_KEY` | `Qwen/Qwen2-7B-Instruct` |

Set `MODEL_NAME` to override the model for the selected provider. Remove an old override when switching providers if it names a model specific to the previous provider.

## Ollama without an API key

Install Ollama on the machine that runs the QueryCraft API. Start its service with `ollama serve` if it is not already running. In another terminal, download the default model once.

```bash
ollama pull qwen2.5-coder:1.5b
```

With the QueryCraft Python environment active, start the API from the repository root:

```bash
cd backend
GENERATION_PROVIDER=ollama python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend posts to Ollama's OpenAI-compatible endpoint at `http://127.0.0.1:11434/v1/chat/completions`. After the model download, inference on the same machine can run without Internet access. The browser still uses CDNs for some interface assets. If the first request times out while the model loads, increase `API_TIMEOUT` up to 120 seconds. [Ollama installation](https://ollama.com/download) · [Ollama API compatibility](https://docs.ollama.com/api/openai-compatibility)

`OLLAMA_API_URL` is the base URL ending in `/v1`, without `/chat/completions`. Plain HTTP is accepted for loopback only. For remote Ollama, use an HTTPS endpoint you control. The backend sends no Authorization header to Ollama.

## OpenAI or Bytez

- For OpenAI, set `GENERATION_PROVIDER=openai` and supply `QUERYCRAFT_OPENAI_API_KEY` or `OPENAI_API_KEY` in the server environment. The scoped variable takes precedence if both are set. Requests go to `https://api.openai.com/v1/chat/completions`.
- For Bytez, set `GENERATION_PROVIDER=bytez` and supply `BYTEZ_API_KEY` in the server environment. The default base URL is `https://api.bytez.com/models/v2/openai/v1`.

Keep keys on the server. Hosted services receive the description and any schema context submitted in the form. In a managed cloud environment, allow egress to the selected cloud provider and store its credential in the environment's secret settings.

## Verify the selected provider

Start the frontend and submit a new description with the desired database dialect. A generated result reports `source: "live"`, the provider name, and the model. Each request goes to the configured provider. To test the interface with predefined examples, explicitly use `GENERATION_MODE=demo`. [Run the application and check the HTTP API](../README.md#run-locally)
