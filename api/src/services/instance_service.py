from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.models import Instance
from api.src.services.config_service import ConfigService # New import

class InstanceService:
    def __init__(self, config_service: ConfigService, connector_manager: ConnectorManager):
        self.config_service = config_service
        self.connector_manager = connector_manager

    def list_instances(self, config_names: Optional[List[str]] = None, no_cache: bool = False) -> List[Instance]:
        all_instances = []
        if not config_names:
            config_names = self.config_service.get_available_configurations()

        for c_name in config_names:
            logger.info(f"InstanceService: Listing instances for config: {c_name}")
            for host in self.config_service._get_hosts(c_name):
                try:
                    connector = self.config_service._get_connector_for_host(c_name, host)
                    instances = connector.list_instances(no_cache=no_cache)
                    all_instances.extend(instances)
                    logger.info(f"InstanceService: Found {len(instances)} instances for host: {host}, config: {c_name}")
                except Exception as e:
                    logger.warning(f"InstanceService: Could not list instances for host {host} in config {c_name}: {e}")
        return all_instances
