from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import Instance, Schema, Table
from api.src.services.config_service import ConfigService
from api.src.services.instance_service import InstanceService
from api.src.services.schema_service import SchemaService # New import

class TableService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager, instance_service: InstanceService, schema_service: SchemaService):
        self.config_service = config_service
        self.connector_manager = connector_manager
        self.instance_service = instance_service
        self.schema_service = schema_service

    def list_tables(self, config_name: Optional[str] = None, instance_name: Optional[str] = None, schema_name: Optional[str] = None) -> List[Table]:
        all_tables = []
        config_names_to_process = [config_name] if config_name else self.config_service.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self.config_service._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    instances_for_config = self.instance_service.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    schemas_to_process = []
                    if schema_name:
                        schemas_to_process.append(Schema(name=schema_name))
                    else:
                        schemas_for_instance = self.schema_service.list_schemas(config_name=c_name, instance_name=inst.name)
                        schemas_to_process.extend(schemas_for_instance)

                    for sch in schemas_to_process:
                        logger.info(f"TableService: Listing tables for config: {c_name}, instance: {inst.name}, schema: {sch.name}")
                        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                        tables = connector.list_tables(instance_name=inst.name, schema_name=sch.name)
                        all_tables.extend(tables)
                        logger.info(f"TableService: Found {len(tables)} tables for schema: {sch.name}")
            except Exception as e:
                logger.warning(f"TableService: Could not list tables for configuration {c_name}, instance {instance_name if instance_name else 'all'}, schema {schema_name if schema_name else 'all'}: {e}")
        return all_tables
