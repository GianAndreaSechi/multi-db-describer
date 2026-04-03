from pymongo import MongoClient
from pymongo.errors import PyMongoError, OperationFailure
from typing import List, Dict, Any, Optional
from core.db_connector.interface import BaseConnector
from core.db_connector.models import Instance, Schema, Table, Column, TableDescription
from core.db_connector.models.table_details import Index, Partition
from loguru import logger
from ..cache_manager import CacheManager

# MongoDB databases that are always present and should be hidden
_SYSTEM_DBS = {"admin", "local", "config"}

# BSON type → readable name (subset of most common types)
_BSON_TYPES: Dict[str, str] = {
    "string":     "string",
    "int":        "int32",
    "long":       "int64",
    "double":     "double",
    "decimal":    "decimal128",
    "bool":       "boolean",
    "date":       "date",
    "timestamp":  "timestamp",
    "objectId":   "ObjectId",
    "array":      "array",
    "object":     "object",
    "binData":    "binary",
    "null":       "null",
}


class MongoDBConnector(BaseConnector):
    """
    A database connector for MongoDB.

    Hierarchy mapping:
        instance   = host
        schema     = MongoDB database
        table      = MongoDB collection

    ── Schema inference policy ──────────────────────────────────────────────
    describe_table() relies **exclusively** on the collection's $jsonSchema
    validator (set via db.createCollection / db.runCommand collMod with a
    validator).  If no $jsonSchema validator is found the method raises a
    SchemaNotDefinedError with a clear message explaining how to define one.

    No sampling or field inference is performed — the behaviour is intentional
    to avoid returning partial or misleading schema information.
    ─────────────────────────────────────────────────────────────────────────

    What is returned when $jsonSchema is present:
        - columns      : properties defined in $jsonSchema.properties,
                         nullable = field not listed in $jsonSchema.required.
        - primary_key  : None (MongoDB _id is implicit and not enumerated as PK).
        - foreign_keys : always empty (not enforced by MongoDB).
        - indexes      : all collection indexes via index_information().
        - partitions   : shard key fields, if the collection is sharded and the
                         connector has read access to config.collections.
                         Silently empty if not sharded or access is denied.

    Connection params:
        - host (str): required, e.g. "localhost" or a full mongodb:// URI.
        - port (int): default 27017. Ignored when host is a URI.
        - username (str): optional.
        - password (str): optional.
        - authSource (str): default "admin".
        - tls (bool): default False.
        - tlsAllowInvalidCertificates (bool): default False.
    """

    @staticmethod
    def get_type() -> str:
        return "mongodb"

    def __init__(self, connection_params: Dict[str, Any], cache_manager: CacheManager):
        super().__init__(connection_params, cache_manager)

        self.host = connection_params.get("host")
        if not self.host:
            raise ValueError("MongoDB connector requires 'host' in connection_params.")

        self.port = int(connection_params.get("port", 27017))
        client_kwargs: Dict[str, Any] = {}

        if connection_params.get("username"):
            client_kwargs["username"] = connection_params["username"]
            client_kwargs["password"] = connection_params.get("password", "")
            client_kwargs["authSource"] = connection_params.get("authSource", "admin")
        if connection_params.get("tls"):
            client_kwargs["tls"] = True
            client_kwargs["tlsAllowInvalidCertificates"] = connection_params.get(
                "tlsAllowInvalidCertificates", False
            )

        try:
            # Use host as URI directly if it starts with "mongodb"
            if self.host.startswith("mongodb"):
                self._client = MongoClient(self.host, **client_kwargs)
            else:
                self._client = MongoClient(self.host, self.port, **client_kwargs)

            self._client.admin.command("ping")
            logger.info(f"Successfully connected to MongoDB at {self.host}:{self.port}")
        except PyMongoError as e:
            logger.exception("Failed to connect to MongoDB.")
            raise ConnectionError(f"Failed to connect to MongoDB at {self.host}: {e}")

    # ------------------------------------------------------------------
    # list_instances  →  the server host + version
    # ------------------------------------------------------------------

    def list_instances(self, no_cache: bool = False) -> List[Instance]:
        cache_key = f"mongodb_instances:{self.host}:{self.port}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Instance(**d) for d in cached_data]

        try:
            info = self._client.server_info()
            version = info.get("version")
        except PyMongoError:
            version = None

        instances = [Instance(name=self.host, version=version)]
        self.cache_manager.set_cached_data(cache_key, [i.model_dump() for i in instances])
        return instances

    # ------------------------------------------------------------------
    # list_schemas  →  MongoDB databases
    # ------------------------------------------------------------------

    def list_schemas(self, instance_name: str, no_cache: bool = False) -> List[Schema]:
        cache_key = f"mongodb_schemas:{self.host}:{self.port}:{instance_name}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Schema(**d) for d in cached_data]

        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")

        try:
            names = self._client.list_database_names()
        except PyMongoError as e:
            logger.exception("Failed to list MongoDB databases.")
            raise RuntimeError(f"Failed to list MongoDB databases: {e}")

        schemas = [Schema(name=n) for n in names if n not in _SYSTEM_DBS]
        self.cache_manager.set_cached_data(cache_key, [s.model_dump() for s in schemas])
        return schemas

    # ------------------------------------------------------------------
    # list_tables  →  MongoDB collections
    # ------------------------------------------------------------------

    def list_tables(
        self,
        instance_name: str,
        schema_name: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_cache: bool = False,
    ) -> List[Table]:
        cache_key = f"mongodb_tables:{self.host}:{self.port}:{instance_name}:{schema_name}:{limit}:{offset}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return [Table(**d) for d in cached_data]

        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")

        try:
            names = self._client[schema_name].list_collection_names()
        except PyMongoError as e:
            logger.exception(f"Failed to list collections for database '{schema_name}'.")
            raise RuntimeError(f"Failed to list collections for database '{schema_name}': {e}")

        start = offset or 0
        end = (start + limit) if limit is not None else None
        tables = [Table(name=n, schema_name=schema_name) for n in sorted(names)[start:end]]

        self.cache_manager.set_cached_data(cache_key, [t.model_dump() for t in tables])
        return tables

    # ------------------------------------------------------------------
    # describe_table  →  $jsonSchema only
    # ------------------------------------------------------------------

    def describe_table(
        self,
        instance_name: str,
        schema_name: str,
        table_name: str,
        no_cache: bool = False,
    ) -> TableDescription:
        cache_key = f"mongodb_describe_table:{self.host}:{self.port}:{instance_name}:{schema_name}:{table_name}"
        cached_data = self.cache_manager.get_cached_data(cache_key, no_cache)
        if cached_data:
            return TableDescription(**cached_data)

        if instance_name != self.host:
            raise ValueError(f"Instance name '{instance_name}' does not match connected host '{self.host}'")

        json_schema = self._get_json_schema(schema_name, table_name)

        if json_schema is None:
            raise SchemaNotDefinedError(
                f"Collection '{schema_name}.{table_name}' has no $jsonSchema validator. "
                "Schema description is only available for collections with an explicit "
                "$jsonSchema validator. To define one, run:\n\n"
                f"  db.runCommand({{\n"
                f"    collMod: '{table_name}',\n"
                f"    validator: {{\n"
                f"      $jsonSchema: {{\n"
                f"        bsonType: 'object',\n"
                f"        required: ['field1', 'field2'],\n"
                f"        properties: {{\n"
                f"          field1: {{ bsonType: 'string', description: '...' }},\n"
                f"          field2: {{ bsonType: 'int' }}\n"
                f"        }}\n"
                f"      }}\n"
                f"    }},\n"
                f"    validationLevel: 'moderate'\n"
                f"  }})"
            )

        columns = self._columns_from_json_schema(json_schema)
        indexes = self._get_index_details(schema_name, table_name)
        partitions = self._get_shard_key(schema_name, table_name)

        table_description = TableDescription(
            instance_name=instance_name,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
            primary_key=None,    # _id is implicit; not modelled as a relational PK
            sort_key=None,
            foreign_keys=[],
            indexes=indexes,
            partitions=partitions,
        )
        self.cache_manager.set_cached_data(cache_key, table_description.model_dump())
        return table_description

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _get_json_schema(self, db_name: str, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Returns the $jsonSchema object from the collection validator, or None
        if no $jsonSchema validator is defined.
        """
        try:
            result = self._client[db_name].command(
                "listCollections", filter={"name": collection_name}
            )
            collections = list(result.get("cursor", {}).get("firstBatch", []))
            if not collections:
                return None
            validator = collections[0].get("options", {}).get("validator", {})
            return validator.get("$jsonSchema")
        except PyMongoError as e:
            logger.exception(f"Failed to retrieve validator for '{db_name}.{collection_name}'.")
            raise RuntimeError(f"Failed to retrieve validator for '{db_name}.{collection_name}': {e}")

    @staticmethod
    def _columns_from_json_schema(json_schema: Dict[str, Any]) -> List[Column]:
        """Parses $jsonSchema.properties into Column objects."""
        properties: Dict[str, Any] = json_schema.get("properties", {})
        required_fields: List[str] = json_schema.get("required", [])

        columns: List[Column] = []
        for field_name, field_def in properties.items():
            bson_type = field_def.get("bsonType") or field_def.get("type", "unknown")
            if isinstance(bson_type, list):
                # e.g. ["string", "null"] — pick the non-null type
                bson_type = next((t for t in bson_type if t != "null"), bson_type[0])
            data_type = _BSON_TYPES.get(bson_type, bson_type)
            columns.append(Column(
                name=field_name,
                data_type=data_type,
                is_nullable=(field_name not in required_fields),
                default_value=None,
                comment=field_def.get("description") or field_def.get("title") or None,
            ))
        return columns

    def _get_index_details(self, db_name: str, collection_name: str) -> List[Index]:
        try:
            index_info: Dict[str, Any] = self._client[db_name][collection_name].index_information()
        except PyMongoError as e:
            logger.warning(f"Could not retrieve indexes for '{db_name}.{collection_name}': {e}")
            return []

        indexes: List[Index] = []
        for idx_name, idx_def in index_info.items():
            col_names = [k for k, _ in idx_def.get("key", [])]
            is_unique = bool(idx_def.get("unique", False))
            is_primary = idx_name == "_id_"
            indexes.append(Index(
                name=idx_name,
                column_names=col_names,
                is_unique=is_unique or is_primary,
                is_primary=is_primary,
                type=None,
            ))
        return indexes

    def _get_shard_key(self, db_name: str, collection_name: str) -> List[Partition]:
        """
        Returns shard key fields as Partition objects.
        Requires read access to the config database (available on mongos routers).
        Returns an empty list silently if the collection is not sharded or
        if the connector lacks the necessary permissions.
        """
        try:
            config_db = self._client["config"]
            ns = f"{db_name}.{collection_name}"
            doc = config_db["collections"].find_one({"_id": ns, "dropped": {"$ne": True}})
            if not doc or "key" not in doc:
                return []
            return [
                Partition(column_name=field, data_type="unknown")
                for field in doc["key"]
            ]
        except (PyMongoError, OperationFailure) as e:
            logger.debug(f"Shard key not accessible for '{db_name}.{collection_name}': {e}")
            return []


class SchemaNotDefinedError(ValueError):
    """
    Raised by MongoDBConnector.describe_table() when the target collection
    has no $jsonSchema validator and schema description is therefore impossible.
    """
    pass
