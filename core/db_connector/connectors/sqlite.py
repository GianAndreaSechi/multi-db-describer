import sqlite3
from typing import List, Dict, Any
from core.db_connector.interface import BaseConnector
from core.db_connector.models import Instance, Schema, Table, Column
from core.db_connector.caching import cache_result
from loguru import logger # New import

class SQLiteConnector(BaseConnector):
    """
    A database connector for SQLite.
    """

    @staticmethod
    def get_type() -> str:
        return "sqlite"

    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.db_path = connection_params.get("database")
        if not self.db_path:
            logger.error("SQLite connector requires 'database' path in connection_params.")
            raise ValueError("SQLite connector requires 'database' path in connection_params.")
        
        # Test connection
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
            logger.info(f"Successfully connected to SQLite database at {self.db_path}")
        except sqlite3.Error as e:
            logger.exception(f"Failed to connect to SQLite database at {self.db_path}")
            raise ConnectionError(f"Failed to connect to SQLite database at {self.db_path}: {e}")

    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Helper to execute a query and return results as list of dicts."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row # Return rows as dict-like objects
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.exception(f"SQLite query failed: {e} - Query: {query}")
            raise RuntimeError(f"SQLite query failed: {e} - Query: {query}")
        finally:
            if conn:
                conn.close()

    @cache_result(ttl=3600)
    def list_instances(self) -> List[Instance]:
        # For SQLite, the instance is the database file itself
        return [Instance(name=self.db_path, version=sqlite3.sqlite_version)]

    @cache_result(ttl=3600)
    def list_schemas(self, instance_name: str) -> List[Schema]:
        # SQLite typically has a single 'main' schema
        if instance_name != self.db_path:
            logger.error(f"Instance name '{instance_name}' does not match connected database '{self.db_path}'")
            raise ValueError(f"Instance name '{instance_name}' does not match connected database '{self.db_path}'")
        return [Schema(name="main")]

    @cache_result(ttl=3600)
    def list_tables(self, instance_name: str, schema_name: str) -> List[Table]:
        if instance_name != self.db_path or schema_name != "main":
            logger.error("Invalid instance or schema for SQLite.")
            raise ValueError("Invalid instance or schema for SQLite.")
        
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        rows = self._execute_query(query)
        return [Table(name=row["name"], schema_name=schema_name) for row in rows]

    @cache_result(ttl=3600)
    def describe_table(self, instance_name: str, schema_name: str, table_name: str) -> List[Column]:
        if instance_name != self.db_path or schema_name != "main":
            logger.error("Invalid instance or schema for SQLite.")
            raise ValueError("Invalid instance or schema for SQLite.")
        
        query = f"PRAGMA table_info('{table_name}');"
        rows = self._execute_query(query)
        
        columns = []
        for row in rows:
            columns.append(
                Column(
                    name=row["name"],
                    data_type=row["type"],
                    is_nullable=bool(not row["notnull"]), # 0 for NOT NULL, 1 for NULL
                    default_value=row["dflt_value"],
                    comment=None # SQLite PRAGMA does not provide column comments directly
                )
            )
        return columns
