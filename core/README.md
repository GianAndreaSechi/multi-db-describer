# Multi-DB Connector Core

## Introduction

The `core` component of the Multi-DB Connector project provides the fundamental logic for connecting to and interacting with various database systems. It acts as an abstraction layer, allowing the API and other potential consumers to work with different databases through a unified interface without needing to know the underlying database-specific implementations.

## Technical Details

The `core` component is written in Python and is designed to be highly modular and extensible. Key aspects include:

-   **`db_connector` package**: This package contains the core logic for database connectivity.
    -   **`manager.py`**: Manages the creation and retrieval of database connector instances. It acts as a central point for accessing different database types.
    -   **`interface.py`**: Defines the `BaseConnector` abstract base class, which all specific database connectors must implement. This ensures a consistent API across different database types.
    -   **`connectors/`**: This directory contains concrete implementations of the `BaseConnector` interface for various database systems (e.g., `mysql.py`, `sqlite.py`, `duckdb.py`).
    -   **`models/`**: Defines Pydantic models for representing database metadata such as `Instance`, `Schema`, `Table`, `Column`, and `TableDescription`. These models ensure type-safe and consistent data structures across the application.
    -   **`cache_manager.py`**: Manages Redis caching operations for database introspection results. It handles connecting to Redis, setting/getting cached data, and applying a project-specific prefix to cache keys.

-   **Caching with Redis**: The `core` library integrates with Redis to cache database introspection results, improving performance.
    *   **Cache Key Prefix**: All cache keys are prefixed with `multi-db-connector` (configurable via `CACHE_KEY_PREFIX` environment variable) to prevent collisions in a shared Redis instance.
    *   **Time-to-Live (TTL)**: Cached data has a default TTL of 1 day (configurable via `REDIS_TTL_SECONDS` environment variable).
    *   **Bypassing Cache**: Caching can be bypassed by passing `no_cache=True` to the relevant methods in the `BaseConnector` interface.

-   **Extensibility**: The design allows for easy addition of new database connectors by simply implementing the `BaseConnector` interface and registering it with the `ConnectorManager`.

## Connectors
### Available
- MySQL/MariaDB
- DuckeBD
- SQLite

### To be implemented
- Postgres
- Apache Presto/Athena
- ...others

## Docker

The `core` component is a library. While it doesn't run as a standalone application, a `docker-compose.yml` file is provided in the `core/` directory to facilitate development, testing, and isolated usage of the `core` library with its Redis caching capabilities.

To use the `core` library with its Redis caching in a Dockerized environment:

1.  **Navigate to the `core/` directory:**
    ```bash
    cd core/
    ```

2.  **Build and run the Docker Compose setup:**
    ```bash
    docker-compose build
    docker-compose up
    ```
    This will start a Redis server and a `core` container. The `core` container will remain running (due to `CMD ["tail", "-f", "/dev/null"]` in its Dockerfile), allowing you to `exec` into it.

3.  **Interact with the `core` library (e.g., run tests or Python scripts):**
    ```bash
    docker-compose exec core bash
    # Inside the container, you can run Python scripts or tests
    # For example: python -c "from db_connector.manager import ConnectorManager; from db_connector.cache_manager import CacheManager; cm = CacheManager(); mgr = ConnectorManager(cm); print(mgr.get_available_connectors())"
    ```

4.  **Environment Variables for Redis:**
    The `core` service in `docker-compose.yml` sets environment variables for Redis connection: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_TTL_SECONDS`, and `CACHE_KEY_PREFIX`. These can be adjusted as needed.