from fastmcp import Context
from loguru import logger
from typing import Optional
from ..services.api_client import api_client
from ..models.requests.instance_request import InstanceRequest
from ..models.requests.schema_request import SchemaRequest
from ..models.requests.table_request import TableRequest
from ..models.requests.describe_table_request import DescribeTableRequest
from ..models.responses.generic_response import GenericResponse
from ..constants import TOON_RESPONSE_FORMAT

def register_tools(mcp):
    """Register all car_data tools for the MCP Server"""

    @mcp.tool()
    async def get_available_connectors(no_cache: Optional[bool] = False) -> GenericResponse:
        """
        Get a list of all available database connector types from the API service.
        """
        logger.info("MCP: Fetching available connector types from API service.")
        api_response = await api_client.get("/configurations", no_cache=no_cache, response_format=TOON_RESPONSE_FORMAT)
        if "error" in api_response:
            return GenericResponse(message=api_response["error"])
        return GenericResponse(message="Available connector types retrieved successfully from API.", data=api_response.get("data"))

    @mcp.tool()
    async def list_instances(request: InstanceRequest, no_cache: Optional[bool] = False) -> GenericResponse:
        """
        List instances for specific configurations by calling the API service.
        """
        logger.info(f"MCP: Listing instances for configs: {request.config_names} via API service.")
        api_response = await api_client.post("/instances", payload=request.model_dump(), no_cache=no_cache, response_format=TOON_RESPONSE_FORMAT)
        if "error" in api_response:
            return GenericResponse(message=api_response["error"])
        return GenericResponse(message=f"Instances for {request.config_names} retrieved successfully from API.", data=api_response.get("data"))

    @mcp.tool()
    async def list_schemas(request: SchemaRequest, no_cache: Optional[bool] = False) -> GenericResponse:
        """
        List schemas for a specific instance by calling the API service.
        """
        logger.info(f"MCP: Listing schemas for instance '{request.instance_name}' in config '{request.config_name}' via API.")
        api_response = await api_client.post("/schemas", payload=request.model_dump(), no_cache=no_cache, response_format=TOON_RESPONSE_FORMAT)
        if "error" in api_response:
            return GenericResponse(message=api_response["error"])
        return GenericResponse(message=f"Schemas for instance '{request.instance_name}' retrieved successfully from API.", data=api_response.get("data"))

    @mcp.tool()
    async def list_tables(request: TableRequest, no_cache: Optional[bool] = False) -> GenericResponse:
        """
        List tables for a specific schema by calling the API service.
        """
        logger.info(f"MCP: Listing tables for schema '{request.schema_name}' in instance '{request.instance_name}' via API.")
        api_response = await api_client.post("/tables", payload=request.model_dump(), no_cache=no_cache, response_format=TOON_RESPONSE_FORMAT)
        if "error" in api_response:
            return GenericResponse(message=api_response["error"])
        return GenericResponse(message=f"Tables for schema '{request.schema_name}' retrieved successfully from API.", data=api_response.get("data"))

    @mcp.tool()
    async def describe_table(request: DescribeTableRequest, no_cache: Optional[bool] = False) -> GenericResponse:
        """
        Describe a specific table by calling the API service.
        """
        logger.info(f"MCP: Describing table '{request.table_name}' in schema '{request.schema_name}' via API.")
        api_response = await api_client.post("/describe", payload=request.model_dump(), no_cache=no_cache, response_format=TOON_RESPONSE_FORMAT)
        if "error" in api_response:
            return GenericResponse(message=api_response["error"])
        return GenericResponse(message=f"Description for table '{request.table_name}' retrieved successfully from API.", data=api_response.get("data"))

    