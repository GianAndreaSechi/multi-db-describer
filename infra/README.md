# Infra — Shared Infrastructure

Provides the shared Redis instance and Docker network (`irides-net`) used by the **API** (introspection cache + job producer), the **Worker** (job consumer + result writer), and the **MCP Server**.

> ⚠️ Redis must be started **before** launching the API, Worker, or MCP services.

---

## Why a Shared Infrastructure

The API writes scan jobs to a Redis Stream (`scan:queue`), while the Worker reads from that stream. Placing Redis and the services in a shared Docker network (`irides-net`) guarantees seamless service discovery (`REDIS_HOST=redis`) across containers.

---

## Docker Compose Setup

```bash
# From the project root
docker compose -f infra/docker-compose.infra.yml up -d
```

This starts:
- Redis container listening on port `6379`.
- Docker bridge network `irides-net`. All other component `docker-compose.yml` files declare `external: true` for this network.

To verify status:
```bash
docker compose -f infra/docker-compose.infra.yml ps
redis-cli -h localhost ping   # Returns PONG
```

---

## Redis Key Architecture & Retention

All keys are namespaced using `CACHE_KEY_PREFIX` (default: `irides`).

| Key Pattern | Redis Data Type | Purpose & Lifecycle |
|---|---|---|
| `{prefix}:{connector}_*` | String | Introspection Cache (TTL: `REDIS_TTL_SECONDS`, default 1 day) |
| `{prefix}:scan:queue` | Stream | Job Queue (consumed by `scan-workers` consumer group) |
| `{prefix}:scan:job:{id}` | Hash | Scan Job Metadata (TTL: `SCAN_RESULTS_TTL_SECONDS`, default 7 days) |
| `{prefix}:scan:results:{id}` | List | Scanned `TableDescription` Payloads (TTL: `SCAN_RESULTS_TTL_SECONDS`, default 7 days) |
| `{prefix}:scan:jobs` | Sorted Set | Job Index ordered by creation timestamp (auto-pruned via `zremrangebyscore`) |

