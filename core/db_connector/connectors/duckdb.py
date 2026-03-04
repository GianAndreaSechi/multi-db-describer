import duckdb
from typing import List, Dict, Any, Optional
from core.db_connector.interface import BaseConnector
from core.db_connector.models import Instance, Schema, Table, Column
from core.db_connector.caching import cache_result
from loguru import logger

class DuckDBConnector(BaseConnector):
    """
    A database connector for DuckDB.
    """

    @staticmethod
    def get_type() -> str:
        return "duckdb"

    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.database = connection_params.get("database", ":memory:") # Default to in-memory

        # Test connection
        try:
            conn = self._get_connection()
            conn.close()
            logger.info(f"Successfully connected to DuckDB database at {self.database}")
        except Exception as e:
            logger.exception(f"Failed to connect to DuckDB database at {self.database}")
            raise ConnectionError(f"Failed to connect to DuckDB database at {self.database}: {e}")

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Helper to get a database connection."""
        return duckdb.connect(database=self.database, read_only=False)

    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Helper to execute a query and return results as list of dicts."""
        conn = None
        try:
            conn = self._get_connection()
            if params:
                result = conn.execute(query, params).fetchall()
            else:
                result = conn.execute(query).fetchall()
            
            # DuckDB fetchall returns a list of tuples, need to convert to list of dicts
            # Get column names from cursor description
            columns = [desc[0] for desc in conn.description]
            
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.exception(f"DuckDB query failed: {e} - Query: {query}")
            raise RuntimeError(f"DuckDB query failed: {e} - Query: {query}")
        finally:
            if conn:
                conn.close()

    @cache_result(ttl=3600)
    def list_instances(self) -> List[Instance]:
        # For DuckDB, the instance is the database file itself or :memory:
        return [Instance(name=self.database, version=duckdb.__version__)]

    @cache_result(ttl=3600)
    def list_schemas(self, instance_name: str) -> List[Schema]:
        if instance_name != self.database:
            logger.error(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
            raise ValueError(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
        
        # DuckDB typically uses 'main' as the default schema
        # We can list attached databases, which can act as schemas
        rows = self._execute_query("PRAGMA database_list;")
        schemas = []
        for row in rows:
            # The 'name' column in PRAGMA database_list is the schema name
            schemas.append(Schema(name=row["database_name"]))
        return schemas

    @cache_result(ttl=3600)
    def list_tables(self, instance_name: str, schema_name: str) -> List[Table]:
        if instance_name != self.database:
            logger.error(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
            raise ValueError(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
        
        # Use PRAGMA show_tables to list tables in a specific schema
        # DuckDB's PRAGMA show_tables doesn't directly filter by schema in a simple way
        # A more robust way is to query information_schema or similar if available,
        # but for simplicity, we'll assume tables are within the main database for now.
        # For more complex schema handling, one might need to adjust the connection or query.
        
        # DuckDB's information_schema.tables provides schema_name
        query = f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = '{schema_name}';
        """
        rows = self._execute_query(query)
        return [Table(name=row["table_name"], schema_name=schema_name) for row in rows]

    @cache_result(ttl=3600)
    def describe_table(self, instance_name: str, schema_name: str, table_name: str) -> List[Column]:
        if instance_name != self.database:
            logger.error(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
            raise ValueError(f"Instance name '{instance_name}' does not match connected database '{self.database}'")
        
        # Use PRAGMA table_info to get column details
        query = f"PRAGMA table_info('{schema_name}.{table_name}');"
        rows = self._execute_query(query)
        
        columns = []
        for row in rows:
            columns.append(
                Column(
                    name=row["name"],
                    data_type=row["type"],
                    is_nullable=not row["notnull"],
                    default_value=row["dflt_value"],
                    comment=None # DuckDB PRAGMA table_info does not provide column comments directly
                )
            )
        return columns
