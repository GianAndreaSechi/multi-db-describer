# Core

Shared Python library used by both the **API** and the **Worker**. It provides database connector abstractions, Pydantic models, Redis cache management, configuration loading, and the async job store.

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
├── manager.py            # ConnectorManager (auto-discovers BaseConnector implementations)
├── cache_manager.py      # Redis cache (get/set with prefix + TTL)
├── config_service.py     # ConfigService — resolves configs & instances to connectors
├── configurations.py     # DB configuration loading from environment variables
└── job_store.py          # JobStore — Redis Stream queue + job metadata & result storage
```

---

## Key Modules

### `storage.py`
Provides metadata persistence abstractions via `BaseMetadataStore`:
- **`FileMetadataStore`** (default): Saves JSON documents to disk under `STORAGE_METADATA_DIR` (default: `storage/metadata/`).
- Structure preserves raw schema introspection in `schema_description` and LLM-generated documentation in `ai_documentation` as separate top-level fields, preventing data overwrites.

### `ai_service.py`
**`AIDocumentationService`**: Non-blocking integration with LiteLLM (`LITELLM_MODEL`, default `gpt-4o-mini`). Generates high-level business summaries and column descriptions. When requested, generated docs are attached to `TableDescription.ai_documentation` with `ai_generation_status`; failures also include `ai_generation_error`. If `litellm` is uninstalled, API keys are missing, or network errors occur, it logs a warning and returns no documentation without throwing exceptions.

### `configurations.py`
Reads database connection parameters from environment variables. `DB_TARGETS` supports any number of named targets for any connector.
- Supports `DB_CONFIG_FILE` environment variable to explicitly specify the path to a container `.env` file (e.g. `/app/api/.env`), falling back to default `load_dotenv()` discovery when unset.
- Target names from `DB_TARGETS` become API/MCP `config_name` values. Example: `DB_TARGETS=sales_mysql,analytics_pg` creates `sales_mysql` and `analytics_pg` configurations.
- Each target uses `DB_TARGET_<TARGET_KEY>_*` variables, where `<TARGET_KEY>` is the uppercased target name with non-alphanumeric characters replaced by underscores.
- Exact required and optional keys for each connector type are documented in the root README under **DB Configuration & Activation**.


### `config_service.py`
Wraps `ConnectorManager` and `configurations`.
- **`list_instances(config_name, no_cache)`**: Uniformly lists instances for both multi-host configurations (MySQL/MariaDB) and flat configurations (Athena, DynamoDB, Trino, MongoDB, SQLite).
- **`resolve_instance_names(config_name, instance_name, no_cache)`**: Returns `[instance_name]` if specified, or all discovered instances if `instance_name` is `None`.
- **`_get_connector_for_host(config_name, host)`**: Returns the connector for a specific host, falling back to flat connection parameters when static host definitions are omitted.

### `cache_manager.py`
Redis-backed cache for introspection results. All keys are prefixed with `CACHE_KEY_PREFIX`. Cache can be bypassed per-call with `no_cache=True`.

### `job_store.py`
Manages async scan jobs via Redis:
- **Stream** (`{prefix}:scan:queue`) — job queue for workers (`scan-workers` consumer group).
- **Hash** (`{prefix}:scan:job:{job_id}`) — job metadata, scope, and status.
- **List** (`{prefix}:scan:results:{job_id}`) — serialized `TableDescription` results with automatic TTL extensions on writes.
- **Sorted Set** (`{prefix}:scan:jobs`) — job index ordered by creation timestamp, automatically pruned of entries older than `RESULTS_TTL` via `zremrangebyscore` to prevent Redis memory leaks.

---

## Supported Databases

| Database | Connector Type | Configuration Style |
|---|---|---|---|
| MySQL / MariaDB | `mysql` | Named `DB_TARGETS` |
| PostgreSQL | `postgres` | Named `DB_TARGETS` |
| SQLite | `sqlite` | Named `DB_TARGETS` |
| DuckDB | `duckdb` | Named `DB_TARGETS` |
| Amazon DynamoDB | `dynamodb` | Named `DB_TARGETS` |
| Amazon Athena | `athena` | Named `DB_TARGETS` |
| MongoDB | `mongodb` | Named `DB_TARGETS` |
| Trino | `trino` | Named `DB_TARGETS` |
| Presto | `presto` | Named `DB_TARGETS` |

---

## Environment Variables

Copy `.env.example` to `.env` and configure as needed.

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |
| `REDIS_TTL_SECONDS` | `86400` | Introspection cache TTL (1 day) |
| `CACHE_KEY_PREFIX` | `multi-db-connector` | Prefix for all Redis keys |
| `SCAN_RESULTS_TTL_SECONDS` | `604800` | Scan result retention in Redis (7 days) |
| `DB_CONFIG_FILE` | *(none)* | Explicit path to `.env` configuration file |
| `DB_TARGETS` | *(none)* | Comma-separated list of named DB targets |
| `STORAGE_METADATA_DIR` | `storage/metadata` | Metadata JSON output directory |
| `LITELLM_MODEL` | `gpt-4o-mini` | LiteLLM model for AI documentation |
| `LITELLM_API_KEY` | *(none)* | Optional provider API key override |
| `LITELLM_API_BASE` | *(none)* | Optional custom LiteLLM API base URL |

DB activation vars — see [root README](../README.md#db-configuration--activation).

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

1. Create `core/db_connector/connectors/mydb.py` implementing `BaseConnector`.
2. Export it from `core/db_connector/connectors/__init__.py`.
3. Add its activation env var and config block to `core/db_connector/configurations.py`.

The `ConnectorManager` automatically discovers all classes that extend `BaseConnector`.
