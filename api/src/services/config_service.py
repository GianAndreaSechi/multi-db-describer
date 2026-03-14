from typing import Dict, Any, List, Optional
from loguru import logger
import os

from core.db_connector.manager import ConnectorManager
# Importiamo le configurazioni dal nuovo file Python
from api.src.configurations.db_configurations import DB_CONFIGURATIONS

class ConfigService:
    def __init__(self, connector_manager: ConnectorManager):
        self.connector_manager = connector_manager
        # Utilizziamo direttamente il dizionario importato
        self.db_configurations: Dict[str, Dict[str, Any]] = DB_CONFIGURATIONS
        logger.info(f"ConfigService: Initialized with {len(self.db_configurations)} database configurations.")

    def get_available_configurations(self) -> List[str]:
        logger.info("ConfigService: Fetching available configurations.")
        return list(self.db_configurations.keys())

    def _get_connector_details(self, config_name: str) -> Dict[str, Any]:
        config = self.db_configurations.get(config_name)
        if not config:
            logger.error(f"ConfigService: Configuration name '{config_name}' not found.")
            raise ValueError(f"Configuration name '{config_name}' not found.")
        
        connector_type = config.get("connector_type")
        connection_params = config.get("connection_params")

        if not connector_type or not connection_params:
            raise ValueError(f"ConfigService: Configuration '{config_name}' is missing 'connector_type' or 'connection_params'.")
        return {"connector_type": connector_type, "connection_params": connection_params}

    def test_connection(self, config_name: str):
        logger.info(f"ConfigService: Attempting to test connection for config: {config_name}")
        details = self._get_connector_details(config_name)
        connector = self.connector_manager.get_connector(details["connector_type"], details["connection_params"])
        logger.info(f"ConfigService: Successfully tested connection for config: {config_name}")
        return {"message": f"Successfully connected to {config_name}."}
