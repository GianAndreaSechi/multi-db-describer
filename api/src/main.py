from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import (
    Instance, Schema, Table,
    TableDescription # Only need TableDescription for response_model
)
from api.src.services.db_service import DBService # New import

app = FastAPI(
    title="Multi-DB Connector API",
    description="API for connecting to various databases and performing introspection.",
    version="0.1.0",
)

# Initialize ConnectorManager and DBService once
connector_manager = ConnectorManager()
db_service = DBService(connector_manager) # New instance of DBService

# Pydantic models for request bodies
class ConnectionRequest(BaseModel):
    connector_type: str
    connection_params: Dict[str, Any]

class InstanceRequest(ConnectionRequest):
    pass # Inherits connector_type and connection_params

class SchemaRequest(ConnectionRequest):
    instance_name: str

class TableRequest(SchemaRequest):
    schema_name: str

class DescribeTableRequest(TableRequest):
    table_name: str


@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the Multi-DB Connector API!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    logger.info(f"Items endpoint accessed with item_id: {item_id}, q: {q}")
    return {"item_id": item_id, "q": q}

@app.get("/connectors", response_model=List[str])
async def get_available_connectors():
    """
    Get a list of all available database connector types.
    """
    logger.info("API: Fetching available connectors.")
    return db_service.get_available_connectors()

@app.post("/connect")
async def test_connection(request: ConnectionRequest):
    """
    Test a connection to a specified database.
    """
    logger.info(f"API: Attempting to test connection for type: {request.connector_type}")
    try:
        return db_service.test_connection(request.connector_type, request.connection_params)
    except ValueError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred during connection test for type: {request.connector_type}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/instances", response_model=List[Instance])
async def list_instances_route(request: InstanceRequest):
    """
    List all instances (e.g., hosts for MySQL, database files for SQLite)
    for a given connector type.
    """
    logger.info(f"API: Listing instances for type: {request.connector_type}")
    try:
        return db_service.list_instances(request.connector_type, request.connection_params)
    except ValueError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing instances for type: {request.connector_type}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/schemas", response_model=List[Schema])
async def list_schemas_route(request: SchemaRequest):
    """
    List all schemas (databases) for a given instance.
    """
    logger.info(f"API: Listing schemas for type: {request.connector_type}, instance: {request.instance_name}")
    try:
        return db_service.list_schemas(request.connector_type, request.connection_params, request.instance_name)
    except ValueError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing schemas for instance: {request.instance_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/tables", response_model=List[Table])
async def list_tables_route(request: TableRequest):
    """
    List all tables for a given schema within an instance.
    """
    logger.info(f"API: Listing tables for type: {request.connector_type}, instance: {request.instance_name}, schema: {request.schema_name}")
    try:
        return db_service.list_tables(request.connector_type, request.connection_params, request.instance_name, request.schema_name)
    except ValueError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing tables for schema: {request.schema_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/describe", response_model=TableDescription)
async def describe_table_route(request: DescribeTableRequest):
    """
    Get a detailed description of a specific table, including columns,
    primary keys, foreign keys, and other indexes.
    """
    logger.info(f"API: Describing table: {request.table_name} in schema: {request.schema_name}, instance: {request.instance_name}, type: {request.connector_type}")
    try:
        return db_service.describe_table(
            request.connector_type,
            request.connection_params,
            request.instance_name,
            request.schema_name,
            request.table_name,
        )
    except ValueError as e:
        logger.error(f"API: Describing table failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Describing table failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while describing table: {request.table_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")