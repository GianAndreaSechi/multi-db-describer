from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from loguru import logger
import os
# Removed json import

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import (
    Instance, Schema, Table,
    TableDescription # Only need TableDescription for response_model
)
from api.src.services.config_service import ConfigService # Updated import
from api.src.services.instance_service import InstanceService # New import
from api.src.services.schema_service import SchemaService # New import
from api.src.services.table_service import TableService # New import
from api.src.services.describe_table_service import DescribeTableService # New import

from api.src.models.requests.connection_request import ConnectionRequest
from api.src.models.requests.instance_request import InstanceRequest
from api.src.models.requests.schema_request import SchemaRequest
from api.src.models.requests.table_request import TableRequest
from api.src.models.requests.describe_table_request import DescribeTableRequest

app = FastAPI(
    title="Multi-DB Connector API",
    description="API for connecting to various databases and performing introspection.",
    version="0.1.0",
)


# Initialize ConnectorManager and Services
connector_manager = ConnectorManager()
config_service = ConfigService(connector_manager)
instance_service = InstanceService(config_service, connector_manager)
schema_service = SchemaService(config_service, connector_manager, instance_service)
table_service = TableService(config_service, connector_manager, instance_service, schema_service)
describe_table_service = DescribeTableService(config_service, connector_manager, instance_service, schema_service, table_service)




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
    return config_service.get_available_configurations()

@app.post("/connect")
async def test_connection(request: ConnectionRequest):
    """
    Test a connection to a specified database configuration.
    """
    logger.info(f"API: Attempting to test connection for config: {request.config_name}")
    try:
        return config_service.test_connection(request.config_name)
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
        return instance_service.list_instances(request.config_names)
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
        return schema_service.list_schemas(request.config_name, request.instance_name)
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
        return table_service.list_tables(request.config_name, request.instance_name, request.schema_name)
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
        return describe_table_service.describe_table(
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