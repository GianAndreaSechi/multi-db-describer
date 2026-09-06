from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import Instance, Schema, Table, Column, TableDescription
from .cache_manager import CacheManager # Import CacheManager

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
    def __init__(self, connection_params: Dict[str, Any], cache_manager: CacheManager): # Add cache_manager
        """
        Initializes the connector with necessary connection parameters.
        
        Args:
            connection_params: A dictionary with credentials and connection details.
            cache_manager: An instance of CacheManager for caching operations.
        """
        self.connection_params = connection_params
        self.cache_manager = cache_manager # Store cache_manager

    @abstractmethod
    def list_instances(self, no_cache: bool = False) -> List[Instance]: # Add no_cache
        """
        Lists all accessible database instances/servers.
        For many DBs, this might be a single instance configuration.
        """
        raise NotImplementedError

    @abstractmethod
    def list_schemas(self, instance_name: str, no_cache: bool = False) -> List[Schema]: # Add no_cache
        """
        Lists all schemas or databases within a given instance.
        
        Args:
            instance_name: The name of the instance to inspect.
            no_cache: If True, bypass the cache and fetch directly from the database.
        """
        raise NotImplementedError

    @abstractmethod
    def list_tables(self, instance_name: str, schema_name: str, limit: Optional[int] = None, offset: Optional[int] = None, no_cache: bool = False) -> List[Table]: # Add no_cache
        """
        Lists all tables within a given schema/database.
        
        Args:
            instance_name: The name of the instance.
            schema_name: The name of the schema/database to inspect.
            limit: Optional. The maximum number of tables to return.
            offset: Optional. The number of tables to skip before starting to return results.
            no_cache: If True, bypass the cache and fetch directly from the database.
        """
        raise NotImplementedError

    @abstractmethod
    def describe_table(self, instance_name: str, schema_name: str, table_name: str, no_cache: bool = False) -> TableDescription:
        """
        Describes the columns of a specific table.
        
        Args:
            instance_name: The name of the instance.
            schema_name: The name of the schema.
            table_name: The name of the table to describe.
            no_cache: If True, bypass the cache and fetch directly from the database.
        
        Returns:
            A TableDescription object with columns, keys, and indexes.
        """
        raise NotImplementedError
