from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import Instance, Schema
from api.src.services.config_service import ConfigService
from api.src.services.instance_service import InstanceService # New import

class SchemaService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager, instance_service: InstanceService):
        self.config_service = config_service
        self.connector_manager = connector_manager
        self.instance_service = instance_service

    def list_schemas(self, config_name: Optional[str] = None, instance_name: Optional[str] = None) -> List[Schema]:
        all_schemas = []
        config_names_to_process = [config_name] if config_name else self.config_service.get_available_configurations()

        for c_name in config_names_to_process:
            try:
                details = self.config_service._get_connector_details(c_name) # Get details once per config
                instances_to_process = []
                if instance_name:
                    # If a specific instance_name is provided, create a dummy Instance object
                    instances_to_process.append(Instance(name=instance_name, version=""))
                else:
                    # If no instance_name, get all instances for the current config
                    instances_for_config = self.instance_service.list_instances(config_names=[c_name])
                    instances_to_process.extend(instances_for_config)

                for inst in instances_to_process:
                    logger.info(f"SchemaService: Listing schemas for config: {c_name}, instance: {inst.name}")
                    connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
                    schemas = connector.list_schemas(instance_name=inst.name)
                    all_schemas.extend(schemas)
                    logger.info(f"SchemaService: Found {len(schemas)} schemas for instance: {inst.name}")
            except Exception as e:
                logger.warning(f"SchemaService: Could not list schemas for configuration {c_name} and instance {instance_name if instance_name else 'all'}: {e}")
        return all_schemas
