# MCP — Multi-DB Describer Control Plane

Model Context Protocol (MCP) server built with `fastmcp` that exposes API introspection and async scan capabilities as tools for LLM agents (Claude, Gemini, Cursor, IDE assistants, etc.).

---

## Available Tools

### Introspection Tools (Synchronous)

| Tool | Parameters | Description |
|---|---|---|
| `get_available_connectors` | `no_cache?` | List all active database configurations |
| `list_instances` | `config_name`, `no_cache?` | List database instances (works for multi-host and flat connectors) |
| `list_schemas` | `config_name`, `instance_name`, `no_cache?` | List schemas/databases within an instance |
| `list_tables` | `config_name`, `instance_name`, `schema_name`, `no_cache?` | List tables within a schema |
| `describe_table` | `config_name`, `instance_name`, `schema_name`, `table_name`, `no_cache?` | Describe a table (columns, primary keys, foreign keys, indexes) |

> 💡 **LLM Optimization**: All introspection tools automatically request data in **TOON** format (`Accept: application/toon`), drastically reducing token consumption compared to verbose JSON.

### Async Table Scan Tools

| Tool | Parameters | Description |
|---|---|---|
| `enqueue_scan` | `config_name?`, `instance_name?`, `schema_name?` | Launch an async background scan job — returns `job_id` |
| `get_scan_job` | `job_id`, `include_results?` | Check job status; set `include_results=True` to fetch full `TableDescription` list |
| `list_scan_jobs` | `limit?` | List recent scan jobs (newest first) |

Typical LLM agent workflow:
1. Call `enqueue_scan(config_name="mysql_dev")` → receive `job_id`
2. Poll `get_scan_job(job_id)` until `status == "completed"`
3. Call `get_scan_job(job_id, include_results=True)` to read scanned schemas

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `http` | Transport protocol (`http` or `stdio`) |
| `MCP_HOST` | `0.0.0.0` | Listen address for HTTP transport |
| `MCP_PORT` | `8000` | Listen port for HTTP transport |
| `API_BASE_URL` | `http://localhost:8000` | Address of the running `multi-db-api` service |
| `DB_CONFIG_FILE` | `/app/api/.env` | Path to container environment configuration file |

---

## Running

### Docker Compose

Starting MCP via Docker Compose automatically provisions the **API**, the **MCP Server**, and the **Worker** (which consumes background scan jobs):

```bash
# 1. Start shared Redis infrastructure
docker compose -f ../infra/docker-compose.infra.yml up -d

# 2. Start API + MCP Server + Background Worker
docker compose up -d
```

### Local Development

```bash
pip install -r requirements.txt
python -m src.server
```

---

## LLM Client Configuration

### Claude Desktop / Gemini CLI (via `mcp-remote`)

Add to your client configuration (e.g. `~/.gemini/settings.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "multi-db-describer": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "http://<mcp-host>:<port>/mcp"]
    }
  }
}
```

Replace `<mcp-host>:<port>` with your MCP server address (e.g. `http://localhost:8000/mcp`).

