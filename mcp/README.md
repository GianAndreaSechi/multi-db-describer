## MCP — Multi-DB Describer Control Plane

MCP server built with `fastmcp` that exposes API and async scan capabilities as tools for LLM agents (Claude, Gemini, IDE assistants, etc.).

---

## Available Tools

### Introspection (synchronous, all parameters required)

| Tool | Parameters | Description |
|---|---|---|
| `get_available_connectors` | `no_cache?` | List active DB configurations |
| `list_instances` | `config_name`, `no_cache?` | List instances for a config |
| `list_schemas` | `config_name`, `instance_name`, `no_cache?` | List schemas |
| `list_tables` | `config_name`, `instance_name`, `schema_name`, `no_cache?` | List tables |
| `describe_table` | `config_name`, `instance_name`, `schema_name`, `table_name`, `no_cache?` | Describe a table |

All introspection tools return data in **TOON** format for LLM efficiency.

### Async Scan

| Tool | Parameters | Description |
|---|---|---|
| `enqueue_scan` | `config_name?`, `instance_name?`, `schema_name?` | Launch async scan, returns `job_id` |
| `get_scan_job` | `job_id`, `include_results?` | Job status; with `include_results=True` returns TableDescriptions in TOON |
| `list_scan_jobs` | `limit?` | List recent scan jobs |

Typical LLM flow:
1. Call `enqueue_scan` → get `job_id`
2. Poll `get_scan_job(job_id)` until `status == "completed"`
3. Call `get_scan_job(job_id, include_results=True)` to read results

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `http` | `http` or `stdio` |
| `MCP_HOST` | `0.0.0.0` | Listen address (http transport) |
| `MCP_PORT` | `8000` | Listen port (http transport) |
| `API_BASE_URL` | `http://localhost:8000` | URL of the running API service |

---

## Running

### Docker Compose

```bash
# Starts Redis + API + MCP
docker compose -f ../docker-compose.infra.yml up -d
docker compose up -d
```

### Local

```bash
pip install -r requirements.txt
python -m src.server
```

---

## LLM Configuration

### Claude / Gemini (via `mcp-remote`)

Add to your MCP client settings (e.g. `~/.gemini/settings.json` or Claude Desktop config):

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

Replace `<mcp-host>:<port>` with the address where the MCP server is running.

