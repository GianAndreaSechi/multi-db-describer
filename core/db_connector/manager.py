import importlib
import pkgutil
from typing import Dict, Type, Optional
from .interface import BaseConnector
from loguru import logger

class ConnectorManager:
    """
    Discovers and manages available database connectors.
    """
    def __init__(self):
        self.connectors: Dict[str, Type[BaseConnector]] = {}
        self._discover_connectors()

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

    def get_available_connectors(self) -> list[str]:
        """Returns a list of available connector types."""
        return list(self.connectors.keys())

    def get_connector(self, connector_type: str, connection_params: dict) -> Optional[BaseConnector]:
        """
        Initializes and returns a connector instance of the specified type.

        Args:
            connector_type: The type of the connector (e.g., 'postgres').
            connection_params: The parameters needed to initialize the connection.

        Returns:
            An instance of the requested connector, or None if not found.
        """
        connector_class = self.connectors.get(connector_type)
        if not connector_class:
            logger.error(f"Connector type '{connector_type}' not found.")
            raise ValueError(f"Connector type '{connector_type}' not found.")
        
        return connector_class(connection_params=connection_params)


