# Infra — Shared Infrastructure

Provides the shared Redis instance used by both the **API** (cache + scan job queue) and the **Worker** (job queue consumer + result storage).

> Redis must be started **before** the API and the Worker.

---

## Why a Shared Redis

The API writes scan jobs to a Redis Stream. The Worker reads from the same stream. If they use separate Redis instances they can never communicate. This component ensures a single, shared Redis is available to all services.

---

## Docker Compose

```bash
# From the project root
docker compose -f infra/docker-compose.infra.yml up -d
```

This creates a Redis container and a Docker network `multi-db-net`. All other `docker-compose.yml` files reference this network as `external: true` and set `REDIS_HOST=redis`.

To verify:
```bash
docker compose -f infra/docker-compose.infra.yml ps
redis-cli -h localhost ping   # PONG
```

---

## Redis Key Structure

All keys use the prefix defined by `CACHE_KEY_PREFIX` (default: `multi-db-connector`).

| Key pattern | Type | Used by |
|---|---|---|
| `{prefix}:{connector}_*` | String | Cache (API → core) |
| `{prefix}:scan:queue` | Stream | Queue (API writes, Worker reads) |
| `{prefix}:scan:job:{id}` | Hash | Job metadata (API + Worker) |
| `{prefix}:scan:results:{id}` | List | Scan results (Worker writes, API reads) |
| `{prefix}:scan:jobs` | Sorted Set | Job index by timestamp |
