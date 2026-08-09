# multi-db-describer

A unified, asynchronous database introspection layer designed to help LLMs and applications extract, summarize, and understand schemas across heterogeneous data stores.

---

## 🌟 Overview

When building AI agents or data tools across multiple databases, a primary challenge is providing accurate, low-overhead schema context. Without proper grounding, LLMs frequently hallucinate column names, infer non-existent relationships, or generate invalid SQL/NoSQL queries.

`multi-db-describer` acts as a **context provider layer** that:
- Introspects diverse SQL, NoSQL, and cloud analytics databases.
- Normalizes schemas, tables, columns, indexes, and primary/foreign keys into structured Pydantic models.
- Provides synchronous HTTP/MCP endpoints and asynchronous table scanning via **Redis Streams**.
- Optimizes payload size for LLMs using lightweight serialization ([TOON](https://github.com/toon-format/toon)).

---

## 🏗️ Architecture Overview

The system is split into microservices connected via Docker networks and Redis Streams:

```
                  ┌────────────────────────┐
                  │    MCP Client / LLM    │
                  └───────────┬────────────┘
                              │ HTTP / TOON
                              ▼
                       ┌─────────────┐
                       │  MCP Server │
                       └──────┬──────┘
                              │ HTTP
                              ▼
┌─────────────┐         ┌─────────────┐         ┌────────────────┐
│   Worker    │ ◄────── │ Redis Stream│ ◄────── │   FastAPI      │
│  (Consumer) │         │ (scan:queue)│         │   (Producer)   │
└──────┬──────┘         └─────────────┘         └───────┬────────┘
       │                                                │
       └───────────────────┬────────────────────────────┘
                           ▼
                  ┌─────────────────┐
                  │   Core Library  │
                  └────────┬────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ MySQL / PG   │    │ Dynamo / Mongo│   │ Athena/Trino │
└──────────────┘    └──────────────┘    └──────────────┘
```

- **`core/`**: Shared Python library providing connector abstractions, models, caching, configuration loaders, and Redis `JobStore`.
- **`infra/`**: Shared Redis container and `multi-db-net` Docker network.
- **`api/`**: FastAPI web service for synchronous introspection and async job enqueueing.
- **`worker/`**: Async task consumer executing background scans and storing results in Redis.
- **`mcp/`**: FastMCP server exposing introspection tools directly to AI assistants.

---

## 🔌 Supported Database Connectors

| Database | Connector Type | Activation Environment Var | Config Type |
|---|---|---|---|
| **MySQL / MariaDB** | `mysql` | `MYSQL_DB1_HOST` / `MYSQL_DB2_HOST` | Multi-host |
| **PostgreSQL** | `postgres` | `POSTGRES_HOST` | Single connection |
| **Amazon Athena** | `athena` | `ATHENA_REGION` | Flat / Remote discovery |
| **Amazon DynamoDB** | `dynamodb` | `DYNAMODB_REGION` | Flat / Remote discovery |
| **MongoDB** | `mongodb` | `MONGODB_HOST` | Single connection |
| **Trino** | `trino` | `TRINO_HOST` | Flat / Remote discovery |
| **Presto** | `presto` | `PRESTO_HOST` | Flat / Remote discovery |
| **SQLite** | `sqlite` | *(built-in / file-based)* | Single connection |
| **DuckDB** | `duckdb` | *(built-in / file-based)* | Single connection |

---

## 🔑 DB Configuration & Activation

Configurations are dynamically activated based on environment variables. A database target is included **only if its activation variable is present and non-empty**.

### Environment Variables Matrix

| Database Target | Primary Activation Var | Additional Connection Variables |
|---|---|---|
| **MySQL** | `MYSQL_DB1_HOST`, `MYSQL_DB2_HOST` | `MYSQL_DB1_USER`, `MYSQL_DB1_PASSWORD`, `MYSQL_DB1_PORT` |
| **PostgreSQL** | `POSTGRES_HOST` | `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_POOL_SIZE` |
| **Athena** | `ATHENA_REGION` | `ATHENA_CATALOG`, `ATHENA_S3_OUTPUT`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` |
| **Trino** | `TRINO_HOST` | `TRINO_PORT`, `TRINO_USER`, `TRINO_PASSWORD`, `TRINO_HTTP_SCHEME` |
| **Presto** | `PRESTO_HOST` | `PRESTO_PORT`, `PRESTO_USER`, `PRESTO_PASSWORD`, `PRESTO_HTTP_SCHEME` |
| **DynamoDB** | `DYNAMODB_REGION` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `DYNAMODB_ENDPOINT_URL` |
| **MongoDB** | `MONGODB_HOST` | `MONGODB_PORT`, `MONGODB_USER`, `MONGODB_PASSWORD`, `MONGODB_AUTH_SOURCE`, `MONGODB_TLS` |
| **Container Config** | `DB_CONFIG_FILE` | *(Optional path to an explicit `.env` file for Docker containers, e.g. `/app/api/.env`)* |

---

## 🚀 Quick Start with Docker Compose

1. **Start Shared Infrastructure (Redis)**:
   ```bash
   docker compose -f infra/docker-compose.infra.yml up -d
   ```

2. **Start API and Worker Services**:
   ```bash
   docker compose -f api/docker-compose.yml up -d
   docker compose -f worker/docker-compose.yml up -d
   ```

3. **Or Start Full MCP Pipeline**:
   ```bash
   docker compose -f mcp/docker-compose.yml up -d
   ```

---

## 💻 Python Core Usage Example

```python
from core.db_connector.cache_manager import CacheManager
from core.db_connector.manager import ConnectorManager
from core.db_connector.config_service import ConfigService

# 1. Initialize Redis Cache & Connector Manager
cache = CacheManager(host="localhost", port=6379, prefix="multi-db-connector")
manager = ConnectorManager(cache_manager=cache)

# 2. Initialize ConfigService (loads active DBs from environment)
config_service = ConfigService(connector_manager=manager)

# 3. List active database instances (handles both multi-host and flat connectors)
instances = config_service.list_instances(config_name="mysql_dev")
for inst in instances:
    print(f"Found instance: {inst.name}")

# 4. Perform direct table introspection
connector = config_service._get_connector_for_host("mysql_dev", instances[0].name)
tables = connector.list_tables(instance_name=instances[0].name, schema_name="public")
table_desc = connector.describe_table(instance_name=instances[0].name, schema_name="public", table_name=tables[0].name)

for col in table_desc.columns:
    print(f"{col.name}: {col.type} (PK={col.is_primary_key})")
```

---

## 🏷️ Status & Roadmap

- **Status**: Active Alpha 🚀
- **Features**:
  - [x] Redis Stream async scanner & dead worker consumer recovery
  - [x] TOON format output for LLM context reduction
  - [x] MCP Server integration for Claude / Gemini / Cursor
  - [x] Unified host and flat instance resolution
  - [ ] Automatic semantic documentation & LLM-generated table descriptions

