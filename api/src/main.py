from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from loguru import logger
import os
import json # New import

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

# Define the path to the configuration file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "configurations", "db_configurations.json")

# Load database configurations
with open(CONFIG_FILE_PATH, 'r') as f:
    DB_CONFIGURATIONS = json.load(f)
logger.info(f"Loaded {len(DB_CONFIGURATIONS)} database configurations from {CONFIG_FILE_PATH}")

# Initialize ConnectorManager and DBService once
connector_manager = ConnectorManager()
db_service = DBService(connector_manager, DB_CONFIGURATIONS) # Pass configurations to DBService

# Pydantic models for request bodies
class ConnectionRequest(BaseModel):
    config_name: str

class InstanceRequest(BaseModel):
    config_names: Optional[List[str]] = None

class SchemaRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None

class TableRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
    schema_name: Optional[str] = None

class DescribeTableRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
    schema_name: Optional[str] = None
    table_name: Optional[str] = None


@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the Multi-DB Connector API!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    logger.info(f"Items endpoint accessed with item_id: {item_id}, q: {q}")
    return {"item_id": item_id, "q": q}

@app.get("/configurations", response_model=List[str])
async def get_available_configurations():
    """
    Get a list of all available database configurations.
    """
    logger.info("API: Fetching available configurations.")
    return db_service.get_available_configurations()

@app.post("/connect")
async def test_connection(request: ConnectionRequest):
    """
    Test a connection to a specified database configuration.
    """
    logger.info(f"API: Attempting to test connection for config: {request.config_name}")
    try:
        return db_service.test_connection(request.config_name)
    except ValueError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred during connection test for config: {request.config_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/instances", response_model=List[Instance])
async def list_instances_route(request: InstanceRequest):
    """
    List all instances (e.g., hosts for MySQL, database files for SQLite)
    for a given connector type. If no connector types are specified,
    instances for all available connector types will be returned.
    """
    logger.info(f"API: Listing instances for config names: {request.config_names if request.config_names else 'all available'}")
    try:
        return db_service.list_instances(request.config_names)
    except ValueError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing instances for config names: {request.config_names}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/schemas", response_model=List[Schema])
async def list_schemas_route(request: SchemaRequest):
    """
    List all schemas (databases) for a given instance and configuration.
    If config_name is not specified, lists schemas for all available configurations.
    If instance_name is not specified, lists schemas for all instances within the specified configuration(s).
    """
    logger.info(f"API: Listing schemas for config: {request.config_name if request.config_name else 'all'}, instance: {request.instance_name if request.instance_name else 'all'}")
    try:
        return db_service.list_schemas(request.config_name, request.instance_name)
    except ValueError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing schemas for config: {request.config_name}, instance: {request.instance_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/tables", response_model=List[Table])
async def list_tables_route(request: TableRequest):
    """
    List all tables for a given schema, instance, and configuration.
    If config_name is not specified, lists tables for all available configurations.
    If instance_name is not specified, lists tables for all instances within the specified configuration(s).
    If schema_name is not specified, lists tables for all schemas within the specified instance(s).
    """
    logger.info(f"API: Listing tables for config: {request.config_name if request.config_name else 'all'}, instance: {request.instance_name if request.instance_name else 'all'}, schema: {request.schema_name if request.schema_name else 'all'}")
    try:
        return db_service.list_tables(request.config_name, request.instance_name, request.schema_name)
    except ValueError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing tables for config: {request.config_name}, instance: {request.instance_name}, schema: {request.schema_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/describe", response_model=List[TableDescription])
async def describe_table_route(request: DescribeTableRequest):
    """
    Get a detailed description of a specific table, including columns,
    primary keys, foreign keys, and other indexes.
    If config_name is not specified, describes tables for all available configurations.
    If instance_name is not specified, describes tables for all instances within the specified configuration(s).
    If schema_name is not specified, describes tables for all schemas within the specified instance(s).
    If table_name is not specified, describes all tables within the specified schema(s).
    """
    logger.info(f"API: Describing table for config: {request.config_name if request.config_name else 'all'}, instance: {request.instance_name if request.instance_name else 'all'}, schema: {request.schema_name if request.schema_name else 'all'}, table: {request.table_name if request.table_name else 'all'}")
    try:
        return db_service.describe_table(
            request.config_name,
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
        logger.exception(f"API: An unexpected error occurred while describing table for config: {request.config_name}, instance: {request.instance_name}, schema: {request.schema_name}, table: {request.table_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")