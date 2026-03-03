import mysql.connector
from typing import List, Dict, Any
from core.db_connector.interface import BaseConnector
from core.db_connector.models import Instance, Schema, Table, Column
from core.db_connector.caching import cache_result

class MySQLConnector(BaseConnector):
    """
    A database connector for MySQL.
    """

    @staticmethod
    def get_type() -> str:
        return "mysql"

    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__(connection_params)
        self.host = connection_params.get("host")
        self.user = connection_params.get("user")
        self.password = connection_params.get("password")
        self.port = connection_params.get("port", 3306)
        
        if not all([self.host, self.user, self.password]):
            raise ValueError("MySQL connector requires 'host', 'user', and 'password' in connection_params.")
        
        # Test connection
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port
            )
            conn.close()
        except mysql.connector.Error as e:
            raise ConnectionError(f"Failed to connect to MySQL database at {self.host}:{self.port}: {e}")

    def _get_connection(self, database: Optional[str] = None):
        """Helper to get a database connection."""
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=database
        )

    def _execute_query(self, query: str, params: tuple = (), database: Optional[str] = None) -> List[Dict[str, Any]]:
        """Helper to execute a query and return results as list of dicts."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection(database=database)
            cursor = conn.cursor(dictionary=True) # Return rows as dicts
            cursor.execute(query, params)
            return cursor.fetchall()
        except mysql.connector.Error as e:
            raise RuntimeError(f"MySQL query failed: {e} - Query: {query}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @cache_result(ttl=3600)
    def list_instances(self) -> List[Instance]:
        # For MySQL, the instance is the host. We can get the version.
        query = "SELECT VERSION();"
        result = self._execute_query(query)
        version = result[0]['VERSION()'] if result else None
        return [Instance(name=self.host, version=version)]

    @cache_result(ttl=3600)
    def list_schemas(self, instance_name: str) -> List[Schema]:
        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")
        
        query = "SHOW DATABASES;"
        rows = self._execute_query(query)
        return [Schema(name=row["Database"]) for row in rows if row["Database"] not in ["information_schema", "mysql", "performance_schema", "sys"]]

    @cache_result(ttl=3600)
    def list_tables(self, instance_name: str, schema_name: str) -> List[Table]:
        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")
        
        query = f"SHOW TABLES FROM `{schema_name}`;"
        rows = self._execute_query(query, database=schema_name)
        # The key in the dict will be like 'Tables_in_your_db_name'
        table_key = f"Tables_in_{schema_name}"
        return [Table(name=row[table_key], schema_name=schema_name) for row in rows]

    @cache_result(ttl=3600)
    def describe_table(self, instance_name: str, schema_name: str, table_name: str) -> List[Column]:
        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")
        
        query = f"SHOW COLUMNS FROM `{schema_name}`.`{table_name}`;"
        rows = self._execute_query(query, database=schema_name)
        
        columns = []
        for row in rows:
            columns.append(
                Column(
                    name=row["Field"],
                    data_type=row["Type"],
                    is_nullable=row["Null"] == "YES",
                    default_value=row["Default"],
                    comment=None # MySQL SHOW COLUMNS does not provide column comments directly
                )
            )
        return columns
