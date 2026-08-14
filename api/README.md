# API

FastAPI service exposing database introspection over HTTP. Provides synchronous point-in-time endpoints and async scan job enqueueing. Depends only on **core**.

---

## Endpoints

### Synchronous Introspection

| Method | Path | Body Parameters | Description |
|---|---|---|---|
| `GET` | `/configurations` | — | List all currently active database configurations |
| `POST` | `/connect` | `config_name` | Test database connection |
| `POST` | `/instances` | `config_name?` | List database instances. Omit `config_name` to list all active configurations |
| `POST` | `/schemas` | `config_name?`, `instance_name?` | List schemas/databases. Omitted fields expand the scope |
| `POST` | `/tables` | `config_name?`, `instance_name?`, `schema_name?`, `limit?`, `offset?` | List tables. Omitted scope fields expand the query |
| `POST` | `/describe` | `config_name?`, `instance_name?`, `schema_name?`, `table_name?`, `generate_ai_docs?`, `save_metadata?` | Describe table structure and optional AI documentation |

- **Bypass Redis Cache**: Send header `no-cache: true`.
- **TOON Payload Format**: Send header `Accept: application/toon` for LLM token reduction.
- **AI Documentation**: Send `generate_ai_docs: true` to include `ai_documentation`, `ai_generation_status`, and `ai_generation_error` in described tables. If `save_metadata: true`, the same AI documentation is persisted in metadata storage.

### Async Table Scan Jobs

| Method | Path | Description |
|---|---|---|
| `POST` | `/scan` | Enqueue an async scan job — returns `job_id` immediately (HTTP 202 Accepted) |
| `GET` | `/scan/{job_id}` | Retrieve job status; add `?include_results=true` for full `TableDescription` list |
| `GET` | `/scans?limit=50` | List recent scan jobs (newest first, lightweight metadata) |

Scan status values are `pending`, `running`, `completed`, `partial`, and `failed`.

Scan scope & AI doc options (all optional):
```json
{
  "config_name": "sales_mysql",
  "instance_name": "db1.company.com",
  "schema_name": "production",
  "generate_ai_docs": true,
  "save_metadata": true
}
```


---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis host (must match Worker) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |
| `REDIS_TTL_SECONDS` | `86400` | Introspection cache TTL (1 day) |
| `CACHE_KEY_PREFIX` | `multi-db-connector` | Redis key prefix (must match Worker) |
| `DB_CONFIG_FILE` | *(none)* | Optional explicit path to `.env` file for Docker container |
| `DB_TARGETS` | *(none)* | Comma-separated list of named DB targets |
| `SCAN_RESULTS_TTL_SECONDS` | `604800` | Scan job/result retention in Redis (7 days) |
| `STORAGE_METADATA_DIR` | `storage/metadata` | Metadata JSON output directory |
| `LITELLM_MODEL` | `gpt-4o-mini` | LLM model for AI doc generation |
| `LITELLM_API_KEY` | *(none)* | Optional LiteLLM API key override |
| `LITELLM_API_BASE` | *(none)* | Optional LiteLLM API base URL |

DB target variables — see [root README](../README.md#db-configuration--activation).

---

## Running

### Docker Compose

```bash
# Start shared Redis first
docker compose -f ../infra/docker-compose.infra.yml up -d

# Start API
docker compose up -d
```

### Local Development

```bash
pip install -r requirements.txt
uvicorn api.src.main:app --host 0.0.0.0 --port 8000 --reload
```
