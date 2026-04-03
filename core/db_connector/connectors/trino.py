import trino
from typing import List, Dict, Any, Optional
from core.db_connector.interface import BaseConnector
from core.db_connector.models import Instance, Schema, Table, Column, TableDescription
from core.db_connector.models.table_details import Partition
from loguru import logger
from ..cache_manager import CacheManager


class TrinoConnector(BaseConnector):
    """
    A database connector for Apache Trino and Presto (PrestoSQL).

    Hierarchy mapping:
        instance  = Trino/Presto catalog  (e.g. "hive", "iceberg")
        schema    = schema / database inside the catalog
        table     = table

    Connection params:
        - host (str): coordinator hostname (required).
        - port (int): coordinator port. Default: 8080.
        - user (str): username (required).
        - http_scheme (str): "http" or "https". Default: "http".
        - password (str): optional, enables BasicAuthentication.
        - session_properties (dict): optional Trino/Presto session properties.

    Foreign keys and primary keys are not enforced and are always empty.
    Partition keys are detected via information_schema.columns.extra_info.
    """

    @staticmethod
    def get_type() -> str:
        return "trino"

    def __init__(self, connection_params: Dict[str, Any], cache_manager: CacheManager):
        super().__init__(connection_params, cache_manager)

        self.host = connection_params.get("host")
        if not self.host:
            raise ValueError("Trino connector requires 'host' in connection_params.")

        self.port = int(connection_params.get("port", 8080))
        self.user = connection_params.get("user", "trino")
        self.http_scheme = connection_params.get("http_scheme", "http")
        self.password = connection_params.get("password")
        self.session_properties = connection_params.get("session_properties", {})

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            conn.close()
            logger.info(f"Successfully connected to Trino at {self.host}:{self.port}")
        except Exception as e:
            logger.exception("Failed to connect to Trino.")
            raise ConnectionError(f"Failed to connect to Trino at {self.host}:{self.port}: {e}")

    def _get_connection(self, catalog: Optional[str] = None, schema: Optional[str] = None):
        auth = (
            trino.auth.BasicAuthentication(self.user, self.password)
            if self.password
            else None
        )
        kwargs: Dict[str, Any] = dict(
            host=self.host,
            port=self.port,
            user=self.user,
            http_scheme=self.http_scheme,
            session_properties=self.session_properties,
        )
        if auth:
            kwargs["auth"] = auth
        if catalog:
            kwargs["catalog"] = catalog
        if schema:
            kwargs["schema"] = schema
        return trino.dbapi.connect(**kwargs)

    def _execute_query(self, query: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = self._get_connection(catalog=catalog, schema=schema)
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.exception(f"Trino query failed: {query}")
            raise RuntimeError(f"Trino query failed: {e} — Query: {query}")
        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------------
    # list_instances  →  Trino catalogs
    # ------------------------------------------------------------------

    def list_instances(self, no_cache: bool = False) -> List[Instance]:
        cache_key = f"trino_instances:{self.host}:{self.port}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Instance(**d) for d in cached_data]

        version_rows = self._execute_query(
            "SELECT node_version FROM system.runtime.nodes WHERE coordinator = true LIMIT 1"
        )
        version = version_rows[0]["node_version"] if version_rows else None

        rows = self._execute_query("SHOW CATALOGS")
        col = rows[0] and list(rows[0].keys())[0] if rows else "Catalog"
        instances = [Instance(name=row[col], version=version) for row in rows]

        self.cache_manager.set_cached_data(cache_key, [i.model_dump() for i in instances])
        return instances

    # ------------------------------------------------------------------
    # list_schemas  →  schemas inside a catalog
    # ------------------------------------------------------------------

    def list_schemas(self, instance_name: str, no_cache: bool = False) -> List[Schema]:
        cache_key = f"trino_schemas:{self.host}:{self.port}:{instance_name}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Schema(**d) for d in cached_data]

        rows = self._execute_query(f"SHOW SCHEMAS FROM {instance_name}")
        col = list(rows[0].keys())[0] if rows else "Schema"
        schemas = [Schema(name=row[col]) for row in rows]

        self.cache_manager.set_cached_data(cache_key, [s.model_dump() for s in schemas])
        return schemas

    # ------------------------------------------------------------------
    # list_tables
    # ------------------------------------------------------------------

    def list_tables(
        self,
        instance_name: str,
        schema_name: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_cache: bool = False,
    ) -> List[Table]:
        cache_key = f"trino_tables:{self.host}:{self.port}:{instance_name}:{schema_name}:{limit}:{offset}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Table(**d) for d in cached_data]

        query = f"""
            SELECT table_name
            FROM {instance_name}.information_schema.tables
            WHERE table_schema = '{schema_name}'
            ORDER BY table_name
        """
        if offset is not None:
            query += f" OFFSET {offset} ROWS"
        if limit is not None:
            query += f" FETCH FIRST {limit} ROWS ONLY"

        rows = self._execute_query(query)
        tables = [Table(name=row["table_name"], schema_name=schema_name) for row in rows]

        self.cache_manager.set_cached_data(cache_key, [t.model_dump() for t in tables])
        return tables

    # ------------------------------------------------------------------
    # describe_table  →  columns + partition keys via information_schema
    # ------------------------------------------------------------------

    def describe_table(
        self,
        instance_name: str,
        schema_name: str,
        table_name: str,
        no_cache: bool = False,
    ) -> TableDescription:
        cache_key = f"trino_describe_table:{self.host}:{self.port}:{instance_name}:{schema_name}:{table_name}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return TableDescription(**cached_data)

        query = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                comment,
                extra_info
            FROM {instance_name}.information_schema.columns
            WHERE table_schema = '{schema_name}'
              AND table_name   = '{table_name}'
            ORDER BY ordinal_position
        """
        rows = self._execute_query(query)

        columns: List[Column] = []
        partitions: List[Partition] = []

        for row in rows:
            is_partition = (row.get("extra_info") or "").lower() == "partition key"
            col = Column(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=(row.get("is_nullable", "YES").upper() == "YES"),
                default_value=row.get("column_default"),
                comment=row.get("comment") or None,
            )
            if is_partition:
                partitions.append(
                    Partition(
                        column_name=row["column_name"],
                        data_type=row["data_type"],
                        comment=row.get("comment") or None,
                    )
                )
            else:
                columns.append(col)

        table_description = TableDescription(
            instance_name=instance_name,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
            primary_key=None,   # not enforced in Trino/Presto
            foreign_keys=[],    # not supported
            indexes=[],         # no traditional indexes
            partitions=partitions,
        )
        self.cache_manager.set_cached_data(cache_key, table_description.model_dump())
        return table_description


class PrestoConnector(TrinoConnector):
    """
    Thin alias of TrinoConnector registered under the type 'presto'.
    Points at a Presto (PrestoSQL) coordinator using the same trino Python client.
    Default port is 8080.
    """

    @staticmethod
    def get_type() -> str:
        return "presto"
