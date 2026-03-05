import importlib
import pkgutil
import json
import os
from typing import Dict, Type, Optional, Any
from .interface import BaseConnector
from loguru import logger

class ConnectorManager:
    """
    Discovers and manages available database connectors and their configurations.
    """
    def __init__(self, config_file_path: Optional[str] = None):
        self.connectors: Dict[str, Type[BaseConnector]] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._discover_connectors()
        if config_file_path:
            self.load_configurations(config_file_path)

    def _discover_connectors(self):
        """
        Dynamically imports all connector modules from the 'connectors' package
        and registers the connector classes.
        """
        import core.db_connector.connectors as connectors_package
        
        for _, name, _ in pkgutil.iter_modules(connectors_package.__path__):
            module = importlib.import_module(f"{connectors_package.__name__}.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                        issubclass(attr, BaseConnector) and
                        attr is not BaseConnector):
                    # Register the connector class by its type name
                    connector_type = attr.get_type()
                    if connector_type in self.connectors:
                        logger.warning(f"Duplicate connector type '{connector_type}' found. Overwriting.")
                    self.connectors[connector_type] = attr

    def load_configurations(self, config_file_path: str):
        """
        Loads database connection configurations from a JSON file.
        """
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
        
        with open(config_file_path, 'r') as f:
            self._configurations = json.load(f)
        logger.info(f"Loaded {len(self._configurations)} database configurations from {config_file_path}")

    def get_available_configurations(self) -> list[str]:
        """Returns a list of available configuration names."""
        return list(self._configurations.keys())

    def get_connector(self, config_name: str) -> BaseConnector:
        """
        Initializes and returns a connector instance based on a named configuration.

        Args:
            config_name: The name of the configuration (e.g., 'mysql_dev').

        Returns:
            An instance of the requested connector.

        Raises:
            ValueError: If the configuration name is not found or if the
                        connector type specified in the configuration is unknown.
        """
        config = self._configurations.get(config_name)
        if not config:
            logger.error(f"Configuration name '{config_name}' not found.")
            raise ValueError(f"Configuration name '{config_name}' not found.")
        
        connector_type = config.get("connector_type")
        connection_params = config.get("connection_params")

        if not connector_type or not connection_params:
            raise ValueError(f"Configuration '{config_name}' is missing 'connector_type' or 'connection_params'.")

        connector_class = self.connectors.get(connector_type)
        if not connector_class:
            logger.error(f"Connector type '{connector_type}' specified in configuration '{config_name}' not found.")
            raise ValueError(f"Connector type '{connector_type}' not found for configuration '{config_name}'.")
        
        return connector_class(connection_params=connection_params)


