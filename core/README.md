# Multi-DB Connector Core

## Introduction

The `core` component of the Multi-DB Connector project provides the fundamental logic for connecting to and interacting with various database systems. It acts as an abstraction layer, allowing the API and other potential consumers to work with different databases through a unified interface without needing to know the underlying database-specific implementations.

## Technical Details

The `core` component is written in Python and is designed to be highly modular and extensible. Key aspects include:

-   **`db_connector` package**: This package contains the core logic for database connectivity.
    -   **`manager.py`**: Manages the creation and retrieval of database connector instances. It acts as a central point for accessing different database types.
    -   **`interface.py`**: Defines the `DBConnector` abstract base class, which all specific database connectors must implement. This ensures a consistent API across different database types.
    -   **`connectors/`**: This directory contains concrete implementations of the `DBConnector` interface for various database systems (e.g., `mysql.py`, `sqlite.py`, `duckdb.py`).
    -   **`models/`**: Defines Pydantic models for representing database metadata such as `Instance`, `Schema`, `Table`, `Column`, and `TableDescription`. These models ensure type-safe and consistent data structures across the application.
    -   **`caching.py`**: (If implemented) Provides caching mechanisms to improve performance for frequently accessed metadata.

-   **Extensibility**: The design allows for easy addition of new database connectors by simply implementing the `DBConnector` interface and registering it with the `ConnectorManager`.

## Docker

The `core` component itself is a library and does not typically run as a standalone Docker container. It is designed to be integrated into other applications, such as the `api` component, which can then be containerized.

If you are developing or testing the `core` component in isolation, you might use a Docker container to set up a consistent Python environment. For example, to run tests within a Docker container:

1.  **Build the Docker image for the core environment (if a Dockerfile exists for core):**
    ```bash
    docker build -t multi-db-core-env -f core/Dockerfile .
    ```
    *(Note: A `core/Dockerfile` might be used for setting up a development/testing environment, not for running a service.)*

2.  **Run tests in a temporary container:**
    ```bash
    docker run --rm multi-db-core-env pytest
    ```
    *(This assumes `pytest` is installed in the Docker image and tests are configured to run.)*
