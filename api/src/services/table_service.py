from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import Instance, Schema, Table
from api.src.services.config_service import ConfigService

class TableService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager): # Removed instance_service, schema_service
        self.config_service = config_service
        self.connector_manager = connector_manager

    def list_tables(self, config_name: Optional[str] = None, instance_name: Optional[str] = None, schema_name: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None, no_cache: bool = False) -> List[Table]:
        all_tables = []
        config_names_to_process = [config_name] if config_name else self.config_service.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self.config_service._get_connector_details(c_name) # Get details once per config
                
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    # Directly get instances using ConfigService and ConnectorManager
                    connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                    instances_for_config = connector.list_instances(no_cache=no_cache)
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        # Directly get schemas using ConfigService and ConnectorManager
                        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                        schemas_for_instance = connector.list_schemas(instance_name=inst.name, no_cache=no_cache)
                        schemas_to_process.extend(schemas_for_instance)

                    for sch in schemas_to_process:
                        logger.info(f"TableService: Listing tables for config: {c_name}, instance: {inst.name}, schema: {sch.name}")
                        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                        tables = connector.list_tables(instance_name=inst.name, schema_name=sch.name, limit=limit, offset=offset, no_cache=no_cache)
                        all_tables.extend(tables)
                        logger.info(f"TableService: Found {len(tables)} tables for schema: {sch.name}")
            except Exception as e:
                logger.warning(f"TableService: Could not list tables for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}: {e}")
        return all_tables