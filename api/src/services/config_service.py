from typing import Dict, Any, List, Optional
from loguru import logger
import json
import os

from core.db_connector.manager import ConnectorManager

class ConfigService:
    # Define a default path relative to the service file
    DEFAULT_CONFIG_FILE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "configurations", "db_configurations.json"
    )

    def __init__(self, connector_manager: ConnectorManager, config_file_path: Optional[str] = None):
        self.connector_manager = connector_manager
        self.config_file_path = config_file_path if config_file_path else self.DEFAULT_CONFIG_FILE_PATH
        self.db_configurations: Dict[str, Dict[str, Any]] = {}
        self._load_configurations()

    def _load_configurations(self):
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file_path}")
        
        with open(self.config_file_path, 'r') as f:
            self.db_configurations = json.load(f)
        logger.info(f"ConfigService: Loaded {len(self.db_configurations)} database configurations from {self.config_file_path}")

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