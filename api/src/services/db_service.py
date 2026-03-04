from typing import Dict, Any, List
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import (
    Instance, Schema, Table, Column,
    TableDescription, PrimaryKey, ForeignKey, Index
)

class DBService:
    def __init__(self, connector_manager: ConnectorManager):
        self.connector_manager = connector_manager

    def get_available_connectors(self) -> List[str]:
        logger.info("Service: Fetching available connectors.")
        return self.connector_manager.get_available_connectors()

    def test_connection(self, connector_type: str, connection_params: Dict[str, Any]):
        logger.info(f"Service: Attempting to test connection for type: {connector_type}")
        connector = self.connector_manager.get_connector(connector_type, connection_params)
        # The connector's __init__ method already tests the connection
        logger.info(f"Service: Successfully tested connection for type: {connector_type}")
        return {"message": f"Successfully connected to {connector_type}."}

    def list_instances(self, connector_type: str, connection_params: Dict[str, Any]) -> List[Instance]:
        logger.info(f"Service: Listing instances for type: {connector_type}")
        connector = self.connector_manager.get_connector(connector_type, connection_params)
        instances = connector.list_instances()
        logger.info(f"Service: Found {len(instances)} instances for type: {connector_type}")
        return instances

    def list_schemas(self, connector_type: str, connection_params: Dict[str, Any], instance_name: str) -> List[Schema]:
        logger.info(f"Service: Listing schemas for type: {connector_type}, instance: {instance_name}")
        connector = self.connector_manager.get_connector(connector_type, connection_params)
        schemas = connector.list_schemas(instance_name=instance_name)
        logger.info(f"Service: Found {len(schemas)} schemas for instance: {instance_name}")
        return schemas

    def list_tables(self, connector_type: str, connection_params: Dict[str, Any], instance_name: str, schema_name: str) -> List[Table]:
        logger.info(f"Service: Listing tables for type: {connector_type}, instance: {instance_name}, schema: {schema_name}")
        connector = self.connector_manager.get_connector(connector_type, connection_params)
        tables = connector.list_tables(instance_name=instance_name, schema_name=schema_name)
        logger.info(f"Service: Found {len(tables)} tables for schema: {schema_name}")
        return tables

    def describe_table(self, connector_type: str, connection_params: Dict[str, Any], instance_name: str, schema_name: str, table_name: str) -> TableDescription:
        logger.info(f"Service: Describing table: {table_name} in schema: {schema_name}, instance: {instance_name}, type: {connector_type}")
        connector = self.connector_manager.get_connector(connector_type, connection_params)
        table_description = connector.describe_table(
            instance_name=instance_name,
            schema_name=schema_name,
            table_name=table_name,
        )
        logger.info(f"Service: Successfully described table: {table_name}")
        return table_description
