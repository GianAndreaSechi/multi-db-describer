# API

FastAPI service exposing database introspection over HTTP. Provides synchronous point-in-time endpoints and async scan job enqueueing. Depends only on **core**.

---

## Endpoints

### Synchronous — all parameters required (no implicit bulk operations)

| Method | Path | Required body |
|---|---|---|
| `GET` | `/configurations` | — |
| `POST` | `/connect` | `config_name` |
| `POST` | `/instances` | `config_name` |
| `POST` | `/schemas` | `config_name`, `instance_name` |
| `POST` | `/tables` | `config_name`, `instance_name`, `schema_name` |
| `POST` | `/describe` | `config_name`, `instance_name`, `schema_name`, `table_name` |

All endpoints accept the optional header `no-cache: true` to bypass Redis caching.  
Response format can be switched to TOON via `Accept: application/toon`.

### Async Scan

| Method | Path | Description |
|---|---|---|
| `POST` | `/scan` | Enqueue a scan job — returns `job_id` immediately (HTTP 202) |
| `GET` | `/scan/{job_id}` | Job status; add `?include_results=true` for full `TableDescription` list |
| `GET` | `/scans?limit=50` | List recent jobs (newest first, no result payloads) |

Scan scope parameters (all optional — omit to scan everything):
```json
{ "config_name": "mysql_dev", "instance_name": "host", "schema_name": "mydb" }
```

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Must match Worker's Redis |
| `REDIS_PORT` | `6379` | |
| `REDIS_DB` | `0` | |
| `REDIS_TTL_SECONDS` | `86400` | Introspection cache TTL |
| `CACHE_KEY_PREFIX` | `multi-db-connector` | Must match Worker's prefix |

DB connection vars — see [root README](../README.md#db-configuration-activation).

---

## Running

### Docker Compose

```bash
# Start shared Redis first
docker compose -f ../docker-compose.infra.yml up -d

# Start API
docker compose up -d
```

### Local

```bash
pip install -r requirements.txt
uvicorn api.src.main:app --host 0.0.0.0 --port 8000 --reload
```