from fastapi import FastAPI, HTTPException, Request, Header, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from loguru import logger
import os

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import (
    Instance, Schema, Table,
    TableDescription
)
from core.db_connector.cache_manager import CacheManager
from api.src.services.config_service import ConfigService
from api.src.services.instance_service import InstanceService
from api.src.services.schema_service import SchemaService
from api.src.services.table_service import TableService
from api.src.services.describe_table_service import DescribeTableService

from api.src.models.requests.connection_request import ConnectionRequest
from api.src.models.requests.instance_request import InstanceRequest
from api.src.models.requests.schema_request import SchemaRequest
from api.src.models.requests.table_request import TableRequest
from api.src.models.requests.describe_table_request import DescribeTableRequest
from api.src.services.response_service import api_response

app = FastAPI(
    title="Multi DB Describer API",
    description="API for connecting to various databases and performing introspection.",
    version="0.1.0",
)

# Initialize CacheManager
cache_manager = CacheManager(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    ttl_seconds=int(os.getenv("REDIS_TTL_SECONDS", 86400)) # Default 1 day
)

# Initialize ConnectorManager and Services
connector_manager = ConnectorManager(cache_manager)
config_service = ConfigService(connector_manager)
instance_service = InstanceService(config_service, connector_manager)
schema_service = SchemaService(config_service, connector_manager)
table_service = TableService(config_service, connector_manager)
describe_table_service = DescribeTableService(config_service, connector_manager)

# Helper to extract no_cache header
def get_no_cache_header(no_cache: Optional[str] = Header(None)) -> bool:
    return no_cache is not None and no_cache.lower() == "true"

#start routing
@app.get("/")
async def read_root(http_request: Request):
    logger.info("Root endpoint accessed.")
    return api_response(http_request, "Welcome to the Multi-DB Connector API!", None)

@app.get("/ping")
async def ping(http_request: Request):
    logger.info("Ping endpoint accessed.")
    return api_response(http_request, "Pong!", {"status": "success", "timestamp": str(os.times())})

@app.get("/configurations")
async def get_available_configurations(http_request: Request, no_cache: bool = Depends(get_no_cache_header)): # Add no_cache
    """
    Get a list of all available database configurations.
    """
    logger.info("API: Fetching available configurations.")
    # Caching for configurations is not implemented in core, so no_cache is not passed here
    data = config_service.get_available_configurations()
    return api_response(http_request, "Available configurations retrieved successfully.", data)

@app.post("/connect")
async def test_connection(req: ConnectionRequest, http_request: Request):
    """
    Test a connection to a specified database configuration.
    """
    logger.info(f"API: Attempting to test connection for config: {req.config_name}")
    try:
        data = config_service.test_connection(req.config_name)
        return api_response(http_request, "Connection test successful.", data)
    except ValueError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred during connection test for config: {req.config_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/instances")
async def list_instances_route(req: InstanceRequest, http_request: Request, no_cache: bool = Depends(get_no_cache_header)): # Add no_cache
    """
    List all instances (e.g., hosts for MySQL, database files for SQLite)
    for a given connector type. If no connector types are specified,
    instances for all available connector types will be returned.
    """
    logger.info(f"API: Listing instances for config names: {req.config_names if req.config_names else 'all available'}")
    try:
        data = instance_service.list_instances(req.config_names, no_cache=no_cache) # Pass no_cache
        return api_response(http_request, "Instances retrieved successfully.", data)
    except ValueError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing instances failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing instances for config names: {req.config_names}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/schemas")
async def list_schemas_route(req: SchemaRequest, http_request: Request, no_cache: bool = Depends(get_no_cache_header)): # Add no_cache
    """
    List all schemas (databases) for a given instance and configuration.
    If config_name is not specified, lists schemas for all available configurations.
    If instance_name is not specified, lists schemas for all instances within the specified configuration(s).
    """
    logger.info(f"API: Listing schemas for config: {req.config_name if req.config_name else 'all'}, instance: {req.instance_name if req.instance_name else 'all'}")
    try:
        data = schema_service.list_schemas(req.config_name, req.instance_name, no_cache=no_cache) # Pass no_cache
        return api_response(http_request, "Schemas retrieved successfully.", data)
    except ValueError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing schemas failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing schemas for config: {req.config_name}, instance: {req.instance_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/tables")
async def list_tables_route(req: TableRequest, http_request: Request, no_cache: bool = Depends(get_no_cache_header)): # Add no_cache
    """
    List all tables for a given schema, instance, and configuration.
    If config_name is not specified, lists tables for all available configurations.
    If instance_name is not specified, lists tables for all instances within the specified configuration(s).
    If schema_name is not specified, lists tables for all schemas within the specified instance(s).
    """
    logger.info(f"API: Listing tables for config: {req.config_name if req.config_name else 'all'}, instance: {req.instance_name if req.instance_name else 'all'}, schema: {req.schema_name if req.schema_name else 'all'}, limit: {req.limit if req.limit else 'none'}, offset: {req.offset if req.offset else 'none'}")
    try:
        data = table_service.list_tables(req.config_name, req.instance_name, req.schema_name, req.limit, req.offset, no_cache=no_cache) # Pass no_cache
        return api_response(http_request, "Tables retrieved successfully.", data)
    except ValueError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Listing tables failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while listing tables for config: {req.config_name}, instance: {req.instance_name}, schema: {req.schema_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/describe")
async def describe_table_route(req: DescribeTableRequest, http_request: Request, no_cache: bool = Depends(get_no_cache_header)): # Add no_cache
    """
    Get a detailed description of a specific table, including columns,
    primary keys, foreign keys, and other indexes.
    If config_name is not specified, describes tables for all available configurations.
    If instance_name is not specified, describes tables for all instances within the specified configuration(s).
    If schema_name is not specified, describes tables for all schemas within the specified instance(s).
    If table_name is not specified, describes all tables within the specified schema(s).
    """
    logger.info(f"API: Describing table for config: {req.config_name if req.config_name else 'all'}, instance: {req.instance_name if req.instance_name else 'all'}, schema: {req.schema_name if req.schema_name else 'all'}, table: {req.table_name if req.table_name else 'all'}")
    try:
        data = describe_table_service.describe_table(
            req.config_name,
            req.instance_name,
            req.schema_name,
            req.table_name,
            no_cache=no_cache # Pass no_cache
        )
        return api_response(http_request, "Table description retrieved successfully.", data)
    except ValueError as e:
        logger.error(f"API: Describing table failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"API: Describing table failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {e}")
    except Exception as e:
        logger.exception(f"API: An unexpected error occurred while describing table for config: {req.config_name}, instance: {req.instance_name}, schema: {req.schema_name}, table: {req.table_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.src.main:app", host="0.0.0.0", port=8000)