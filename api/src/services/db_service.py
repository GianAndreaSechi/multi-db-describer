from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import (
    Instance, Schema, Table, Column,
    TableDescription, PrimaryKey, ForeignKey, Index
)

class DBService:
    def __init__(self, connector_manager: ConnectorManager, db_configurations: Dict[str, Dict[str, Any]]):
        self.connector_manager = connector_manager
        self.db_configurations = db_configurations

    def get_available_configurations(self) -> List[str]:
        logger.info("Service: Fetching available configurations.")
        return list(self.db_configurations.keys())

    def _get_connector_details(self, config_name: str) -> Dict[str, Any]:
        config = self.db_configurations.get(config_name)
        if not config:
            logger.error(f"Configuration name '{config_name}' not found.")
            raise ValueError(f"Configuration name '{config_name}' not found.")
        
        connector_type = config.get("connector_type")
        connection_params = config.get("connection_params")

        if not connector_type or not connection_params:
            raise ValueError(f"Configuration '{config_name}' is missing 'connector_type' or 'connection_params'.")
        return {"connector_type": connector_type, "connection_params": connection_params}

    def test_connection(self, config_name: str):
        logger.info(f"Service: Attempting to test connection for config: {config_name}")
        details = self._get_connector_details(config_name)
        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
        # The connector's __init__ method already tests the connection
        logger.info(f"Service: Successfully tested connection for config: {config_name}")
        return {"message": f"Successfully connected to {config_name}."}

    def list_instances(self, config_names: Optional[List[str]] = None) -> List[Instance]:
        all_instances = []
        if not config_names:
            config_names = self.get_available_configurations()

        for c_name in config_names:
            logger.info(f"Service: Listing instances for config: {c_name}")
            try:
                details = self._get_connector_details(c_name)
                connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                instances = connector.list_instances()
                all_instances.extend(instances)
                logger.info(f"Service: Found {len(instances)} instances for config: {c_name}")
            except Exception as e:
                logger.warning(f"Service: Could not list instances for configuration {c_name}: {e}")
        return all_instances

    def list_schemas(self, config_name: Optional[str] = None, instance_name: Optional[str] = None) -> List[Schema]:
        all_schemas = []
        config_names_to_process = [config_name] if config_name else self.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    instances_for_config = self.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    logger.info(f"Service: Listing schemas for config: {c_name}, instance: {inst.name}")
                    connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                    schemas = connector.list_schemas(instance_name=inst.name)
                    all_schemas.extend(schemas)
                    logger.info(f"Service: Found {len(schemas)} schemas for instance: {inst.name}")
            except Exception as e:
                logger.warning(f"Service: Could not list schemas for configuration {c_name} and instance {instance_name if instance_name else 'all'}: {e}")
        return all_schemas

    def list_tables(self, config_name: Optional[str] = None, instance_name: Optional[str] = None, schema_name: Optional[str] = None) -> List[Table]:
        all_tables = []
        config_names_to_process = [config_name] if config_name else self.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    instances_for_config = self.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        schemas_for_instance = self.list_schemas(config_name=c_name, instance_name=inst.name)
                        schemas_to_process.extend(schemas_for_instance)

                    for sch in schemas_to_process:
                        logger.info(f"Service: Listing tables for config: {c_name}, instance: {inst.name}, schema: {sch.name}")
                        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                        tables = connector.list_tables(instance_name=inst.name, schema_name=sch.name)
                        all_tables.extend(tables)
                        logger.info(f"Service: Found {len(tables)} tables for schema: {sch.name}")
            except Exception as e:
                logger.warning(f"Service: Could not list tables for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}: {e}")
        return all_tables

    def describe_table(self, config_name: Optional[str] = None, instance_name: Optional[str] = None, schema_name: Optional[str] = None, table_name: Optional[str] = None) -> List[TableDescription]:
        all_table_descriptions = []
        config_names_to_process = [config_name] if config_name else self.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    instances_for_config = self.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        schemas_for_instance = self.list_schemas(config_name=c_name, instance_name=inst.name)
                        schemas_to_process.extend(schemas_for_instance)

                    for sch in schemas_to_process:
                        tables_to_process = []
                        if table_name:
                            tables_to_process.append(Table(name=table_name))
                        else:
                            tables_for_schema = self.list_tables(config_name=c_name, instance_name=inst.name, schema_name=sch.name)
                            tables_to_process.extend(tables_for_schema)

                        for tbl in tables_to_process:
                            logger.info(f"Service: Describing table: {tbl.name} in schema: {sch.name}, instance: {inst.name}, config: {c_name}")
                            connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                            table_description = connector.describe_table(
                                instance_name=inst.name,
                                schema_name=sch.name,
                                table_name=tbl.name,
                            )
                            all_table_descriptions.append(table_description)
                            logger.info(f"Service: Successfully described table: {tbl.name}")
            except Exception as e:
                logger.warning(f"Service: Could not describe table for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}, table {table_name if table_name else 'all'}: {e}")
        return all_table_descriptions
