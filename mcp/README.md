# MCP: Multi-DB Connector Control Plane

## Overview

The Multi-DB Connector Control Plane (MCP) is a component designed to expose the functionalities of the Multi-DB Connector API to Large Language Models (LLMs) and other AI agents. It acts as a bridge, translating the API's capabilities into a set of "tools" that an LLM can understand and execute.

Built with `fastmcp`, this control plane follows the Model Context Protocol, a standardized way to connect LLMs to external functionalities.

## Features

- **LLM Tool Integration:** Exposes database introspection capabilities as tools for LLMs.
- **Standardized Protocol:** Uses `fastmcp` to adhere to the Model Context Protocol.
- **Centralized API Communication:** All interactions with the backend API are handled through a centralized `ApiClient`.
- **Structured Data:** Uses Pydantic models for clear and validated request and response structures.
- **Flexible Response Formats:** Can request data from the API in either standard JSON or the compressed TOON format.

## Technical Overview

The MCP is a Python application that uses the `fastmcp` library to create a tool server. When the MCP server is running, it provides a set of tools that an LLM can call.

Each tool corresponds to an endpoint in the main Multi-DB Connector API. When an LLM calls a tool, the MCP server:

1.  Receives the tool call.
2.  Validates the incoming parameters using Pydantic models.
3.  Uses the `ApiClient` service to make a request to the corresponding endpoint on the main API. The `ApiClient` is configured to request responses in the efficient TOON format.
4.  The `ApiClient` receives the TOON response, decodes it, and returns the data to the tool.
5.  The tool then packages the data into a structured `GenericResponse` object and returns it.

This architecture decouples the LLM from the specifics of the main API, providing a clean and standardized interface.

## Available Tools

The following tools are exposed by the MCP:

- **`get_available_connectors(no_cache: bool = False)`**: Retrieves a list of all available database connector configurations.
- **`list_instances(request: InstanceRequest, no_cache: bool = False)`**: Lists all available instances for a given set of configurations.
  - `InstanceRequest`: `{ "config_names": ["list", "of", "strings"] }`
- **`list_schemas(request: SchemaRequest, no_cache: bool = False)`**: Lists all schemas (databases) for a specific instance.
  - `SchemaRequest`: `{ "config_name": "string", "instance_name": "string" }`
- **`list_tables(request: TableRequest, no_cache: bool = False)`**: Lists all tables within a specific schema.
  - `TableRequest`: `{ "config_name": "string", "instance_name": "string", "schema_name": "string" }`
- **`describe_table(request: DescribeTableRequest, no_cache: bool = False)`**: Provides a detailed description of a specific table, including columns and keys.
  - `DescribeTableRequest`: `{ "config_name": "string", "instance_name": "string", "schema_name": "string", "table_name": "string" }`

## Getting Started

### Prerequisites

- Python 3.8+
- An instance of the Multi-DB Connector API running.

### Installation

1.  Navigate to the `mcp` directory:
    ```bash
    cd /path/to/multi-db-connector/mcp
    ```
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server

To start the MCP server, run the following command from within the `mcp` directory:

```bash
python -m src.main
```

The server will start and be ready to accept tool calls from an LLM.

## LLM Configuration Example

To configure an LLM like Google's Gemini or Anthropic's Claude to use the MCP, you would typically provide the tool definitions and the server's endpoint to the LLM's API.

The exact implementation varies by provider, but here is a conceptual example.

### 1. Tool Definition

You would first define the tools in a format that the LLM provider's API understands. This is often a JSON or JSON Schema representation of the functions. `fastmcp` can automatically generate this for you. You can get the tool definition by running the MCP server and accessing the appropriate endpoint (usually `/tools.json` or similar, depending on the `fastmcp` version).

### 2. Example Configuration (Conceptual)

Here is a pseudo-code example of how you might configure a Gemini or Claude chat session to use the MCP tools.

Go into ``` /Users/<usernmae>/.gemini/settings.json ``` and put this into the existing configuration

```json
{
  ...
  "mcpServers": {
    "multi-db-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://0.0.0.0:8001/mcp"
      ]
    }
  },
  "general": {
    "sessionRetention": {
      "enabled": true,
      "maxAge": "30d",
      "warningAcknowledged": true
    }
  },
...
}
```
