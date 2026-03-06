# Multi-DB Connector API

## Introduction

This API serves as a versatile connector for various database systems, providing a unified interface for database introspection. It allows users to connect to different database types (e.g., MySQL, SQLite, DuckDB) and perform operations such as listing instances, schemas, tables, and describing table structures. The API is designed to be extensible, allowing for easy integration of new database connectors.

## Technical Details

The API is built using **FastAPI**, a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It leverages **Pydantic** for data validation and serialization, ensuring robust and type-safe data handling.

Key features include:
- **Database Abstraction**: Connects to multiple database types through a common interface.
- **Introspection Capabilities**: Provides endpoints to explore database metadata (instances, schemas, tables, column details).
- **Configurable Connections**: Database connection parameters are managed through configurations, allowing for flexible setup.
- **Logging**: Utilizes `loguru` for comprehensive and easy-to-read logging.
- **Custom Response Formats**: Supports both JSON and TOON (Tree-Oriented Object Notation) response formats, selectable via the `Accept` HTTP header.

## Docker

To run the API using Docker, follow these steps:

0. **Using docker-compose:**
    ```bash
    docker-compose build
    
    docker-compose up
    ```

1.  **Build the Docker image:**
    ```bash
    docker build -t multi-db-api .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -d --name multi-db-api -p 8000:8000 multi-db-api
    ```

3.  **Access the API:**
    The API will be available at `http://localhost:8000`. You can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

4.  **Stop the Docker container:**
    ```bash
    docker stop multi-db-api
    ```

5.  **Remove the Docker container:**
    ```bash
    docker rm multi-db-api
    ```

6.  **Remove the Docker image:**
    ```bash
    docker rmi multi-db-connector-api
    ```
