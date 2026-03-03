from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .models import Instance, Schema, Table, Column

class BaseConnector(ABC):
    """
    Abstract Base Class for database connectors.
    Each connector must implement these methods to ensure a consistent interface
    for interacting with different database types.
    """

    @staticmethod
    @abstractmethod
    def get_type() -> str:
        """Returns the type of the database (e.g., 'postgres', 'mysql')."""
        raise NotImplementedError

    @abstractmethod
    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initializes the connector with necessary connection parameters.
        
        Args:
            connection_params: A dictionary with credentials and connection details.
        """
        self.connection_params = connection_params

    @abstractmethod
    def list_instances(self) -> List[Instance]:
        """
        Lists all accessible database instances/servers.
        For many DBs, this might be a single instance configuration.
        """
        raise NotImplementedError

    @abstractmethod
    def list_schemas(self, instance_name: str) -> List[Schema]:
        """
        Lists all schemas or databases within a given instance.
        
        Args:
            instance_name: The name of the instance to inspect.
        """
        raise NotImplementedError

    @abstractmethod
    def list_tables(self, instance_name: str, schema_name: str) -> List[Table]:
        """
        Lists all tables within a given schema/database.
        
        Args:
            instance_name: The name of the instance.
            schema_name: The name of the schema/database to inspect.
        """
        raise NotImplementedError

    @abstractmethod
    def describe_table(self, instance_name: str, schema_name: str, table_name: str) -> List[Column]:
        """
        Describes the columns of a specific table.
        
        Args:
            instance_name: The name of the instance.
            schema_name: The name of the schema.
            table_name: The name of the table to describe.
        
        Returns:
            A list of Column objects detailing each column in the table.
        """
        raise NotImplementedError
