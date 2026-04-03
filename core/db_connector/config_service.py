from typing import Dict, Any, List, Optional
from loguru import logger

from core.db_connector.manager import ConnectorManager
from core.db_connector.configurations import DB_CONFIGURATIONS


class ConfigService:
    def __init__(self, connector_manager: ConnectorManager):
        self.connector_manager = connector_manager
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
            raise ValueError(
                f"ConfigService: Configuration '{config_name}' is missing "
                "'connector_type' or 'connection_params'."
            )
        return {"connector_type": connector_type, "connection_params": connection_params}

    def _get_hosts(self, config_name: str) -> List[str]:
        details = self._get_connector_details(config_name)
        return [h["host"] for h in details["connection_params"].get("hosts", [])]

    def _get_connector_for_host(self, config_name: str, host: str):
        details = self._get_connector_details(config_name)
        host_params = next(
            (h for h in details["connection_params"].get("hosts", []) if h["host"] == host),
            None,
        )
        if not host_params:
            raise ValueError(f"Host '{host}' not found in config '{config_name}'")
        return self.connector_manager.get_connector(details["connector_type"], host_params)

    def test_connection(self, config_name: str):
        logger.info(f"ConfigService: Attempting to test connection for config: {config_name}")
        hosts = self._get_hosts(config_name)
        for host in hosts:
            self._get_connector_for_host(config_name, host)
            logger.info(f"ConfigService: Successfully tested connection to {host} for config: {config_name}")
        return {"message": f"Successfully connected to all hosts in {config_name}."}
