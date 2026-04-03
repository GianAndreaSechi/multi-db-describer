# Core

Shared Python library used by both the **API** and the **Worker**. It provides all database connectors, Pydantic models, Redis cache management, configuration loading, and the async job store.

---

## Package Structure

```
core/db_connector/
├── connectors/           # DB-specific connector implementations
│   ├── mysql.py
│   ├── postgres.py
│   ├── sqlite.py
│   ├── duckdb.py
│   ├── dynamodb.py
│   ├── mongodb.py
│   ├── athena.py
│   ├── trino.py
│   └── presto.py
├── models/               # Pydantic data models
│   ├── instance.py
│   ├── schema.py
│   ├── table.py
│   ├── column.py
│   ├── table_details.py  # TableDescription, PrimaryKey, ForeignKey, Index, Partition
│   └── scan_job.py       # ScanJob, ScanScope, ScanStatus
├── interface.py          # BaseConnector abstract class
├── manager.py            # ConnectorManager (auto-discovers connectors)
├── cache_manager.py      # Redis cache (get/set with prefix + TTL)
├── config_service.py     # ConfigService — resolves configs to connectors
├── configurations.py     # DB configuration loading from env vars
└── job_store.py          # JobStore — Redis Stream queue + job metadata
```

---

## Key Modules

### `configurations.py`
Reads database connection parameters from environment variables. A configuration is included **only if its activation env var is set** — no code changes needed to enable/disable a database.

### `config_service.py`
Wraps `ConnectorManager` and `configurations`. Resolves a config name + host to a ready-to-use connector instance.

### `cache_manager.py`
Redis-backed cache for introspection results. All keys are prefixed with `CACHE_KEY_PREFIX`. Cache can be bypassed per-call with `no_cache=True`.

### `job_store.py`
Manages async scan jobs via Redis:
- **Stream** (`{prefix}:scan:queue`) — job queue for workers
- **Hash** (`{prefix}:scan:job:{job_id}`) — job metadata and status
- **List** (`{prefix}:scan:results:{job_id}`) — TableDescription results
- **Sorted Set** (`{prefix}:scan:jobs`) — index of jobs by creation time

---

## Supported Databases

| Database | Connector type |
|---|---|
| MySQL / MariaDB | `mysql` |
| PostgreSQL | `postgres` |
| SQLite | `sqlite` |
| DuckDB | `duckdb` |
| Amazon DynamoDB | `dynamodb` |
| Amazon Athena | `athena` |
| MongoDB | `mongodb` |
| Trino | `trino` |
| Presto | `presto` |

---

## Environment Variables

Copy `.env.example` to `.env` and configure as needed.

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |
| `REDIS_TTL_SECONDS` | `86400` | Cache TTL (1 day) |
| `CACHE_KEY_PREFIX` | `multi-db-connector` | Prefix for all Redis keys |
| `SCAN_RESULTS_TTL_SECONDS` | `604800` | Scan result retention (7 days) |

DB activation vars — see [root README](../README.md#db-configuration-activation).

---

## Installation

The core package is installed in editable mode by the API and Worker:

```bash
pip install -e /path/to/core
# or via requirements.txt:
pip install -r requirements.txt
```

---

## Adding a New Connector

1. Create `core/db_connector/connectors/mydb.py` implementing `BaseConnector`
2. Export it from `core/db_connector/connectors/__init__.py`
3. Add its activation env var and config block to `core/db_connector/configurations.py`

The `ConnectorManager` auto-discovers all classes that extend `BaseConnector`.