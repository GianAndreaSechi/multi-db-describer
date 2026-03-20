# multi-db-describer

A lightweight layer to help LLMs and applications understand database structures across heterogeneous data stores.

## Overview

When working with multiple databases, one of the main challenges—especially with LLMs—is providing reliable, structured context about what data actually exists.

`multi-db-describer` is an experimental project that aims to:
- introspect multiple databases
- expose their structure in a consistent format
- make this information accessible to applications and AI systems

## Features

- Python core library (embeddable)
- API layer + MCP interface
- Multi-database support:
  - MySQL
  - DuckDB
  - SQLite
- Table discovery and schema description (`describe`)
- Redis caching for performance optimization

## Why this project

LLMs are powerful, but without proper grounding they tend to:
- hallucinate tables or columns
- generate invalid queries
- lack awareness of real data structures

This project acts as a **context provider layer**, enabling:
- better prompt grounding
- safer query generation
- improved data exploration workflows

## Future direction

A key next step is to:
- feed database metadata into AI models
- generate enriched context (descriptions, inferred relationships, usage hints)
- persist this knowledge over time

This would allow building a **self-improving semantic layer** on top of raw database structures.

This part is still experimental and requires further design and iteration.

## Current status

⚠️ Alpha

Limitations:
- limited database connectors
- basic iteration logic when parameters are missing
- cache strategy can be improved
- packaging not finalized yet (PyPI planned)

## Installation

_(coming soon – packaging in progress)_

## Example (Service usage)

The library is organized into specialized services that handle orchestration across multiple database configurations.

```python
from core.db_connector.manager import ConnectorManager
from core.db_connector.cache_manager import CacheManager
from api.src.services.config_service import ConfigService
from api.src.services.table_service import TableService
from api.src.services.describe_table_service import DescribeTableService

# 1. Setup the core managers
cache = CacheManager(host="localhost", port=6379)
manager = ConnectorManager(cache)

# 2. Initialize the configuration service (loads from db_configurations.py)
config = ConfigService(manager)

# 3. Use specialized services for introspection
table_service = TableService(config, manager)
describe_service = DescribeTableService(config, manager)

# List tables for a specific configuration
tables = table_service.list_tables(config_name="my_mysql_db")

# Describe a specific table
details = describe_service.describe_table(
    config_name="my_mysql_db", 
    table_name="users"
)

for col in details[0].columns:
    print(f"{col.name}: {col.type}")
```
