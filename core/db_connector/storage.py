from abc import ABC, abstractmethod
import json
import math
import re
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger


def build_metadata_key(
    config_name: str, instance_name: str, schema_name: str, table_name: str
) -> str:
    """Build a composite unique metadata key."""
    return f"{config_name}::{instance_name}::{schema_name}::{table_name}"


class BaseMetadataStore(ABC):
    """Abstract Base Class for Metadata Storage (File System, MongoDB, Postgres, etc.)."""

    @abstractmethod
    def save_table_metadata(
        self,
        config_name: str,
        instance_name: str,
        schema_name: str,
        table_name: str,
        schema_description: Dict[str, Any],
        ai_documentation: Optional[Dict[str, Any]] = None,
        only_if_changed: bool = False,
        save_markdown: bool = False,
    ) -> Dict[str, Any]:
        """Save or update table metadata.

        Must preserve existing ai_documentation if ai_documentation is None.
        Must keep schema_description and ai_documentation in separate top-level fields.
        When ``save_markdown`` is true, implementations should persist an
        LLM-friendly Markdown representation alongside the metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def get_table_metadata(
        self,
        config_name: str,
        instance_name: str,
        schema_name: str,
        table_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve stored table metadata."""
        raise NotImplementedError

    @abstractmethod
    def list_instances(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all unique instance names across all configs, paginated."""
        raise NotImplementedError

    @abstractmethod
    def list_databases(self, instance_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all database/schema names for a given instance, paginated."""
        raise NotImplementedError

    @abstractmethod
    def list_tables_metadata(self, instance_name: str, database_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all table names for a given instance+database, paginated."""
        raise NotImplementedError

    @abstractmethod
    def find_table_metadata(self, instance_name: str, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Find table metadata by instance, database and table name (searches across all configs)."""
        raise NotImplementedError

    @abstractmethod
    def update_table_metadata(
        self, instance_name: str, database_name: str, table_name: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Merge payload into an existing metadata document.

        System identity fields are protected and cannot be overwritten.
        Returns the updated document, or None if the document does not exist.
        """
        raise NotImplementedError


class FileMetadataStore(BaseMetadataStore):
    """File System implementation storing metadata as JSON files."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.getenv("STORAGE_METADATA_DIR", "storage/metadata")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize(name: str) -> str:
        """Replace any character that is not alphanumeric, dot, hyphen, or underscore."""
        return re.sub(r"[^\w.\-]", "_", name)

    def _get_file_path(
        self, config_name: str, instance_name: str, schema_name: str, table_name: str
    ) -> Path:
        safe_config = self._sanitize(config_name)
        safe_instance = self._sanitize(instance_name)
        safe_schema = self._sanitize(schema_name)
        safe_table = self._sanitize(table_name)
        return self.base_dir / safe_config / safe_instance / safe_schema / f"{safe_table}.json"

    def _get_markdown_file_path(
        self, config_name: str, instance_name: str, schema_name: str, table_name: str
    ) -> Path:
        return self._get_file_path(config_name, instance_name, schema_name, table_name).with_suffix(".md")

    @staticmethod
    def _markdown_escape(value: Any) -> str:
        return str("" if value is None else value).replace("|", "\\|").replace("\n", " ")

    def _render_markdown(self, record: Dict[str, Any]) -> str:
        """Render a compact, self-contained schema document for LLM ingestion."""
        schema = record["schema_description"]
        lines = [
            f"# {record['schema_name']}.{record['table_name']}",
            "",
            "## Source",
            "",
            f"- Configuration: `{record['config_name']}`",
            f"- Instance: `{record['instance_name']}`",
            f"- Schema: `{record['schema_name']}`",
            f"- Table: `{record['table_name']}`",
            f"- Metadata updated: `{record['updated_at']}`",
        ]
        ai_doc = record.get("ai_documentation") or {}
        if ai_doc.get("summary"):
            lines.extend(["", "## AI documentation", "", ai_doc["summary"]])

        columns = schema.get("columns", [])
        if columns:
            lines.extend(["", "## Columns", "", "| Name | Type | Nullable | Description |", "| --- | --- | --- | --- |"])
            descriptions = ai_doc.get("column_descriptions", {})
            for column in columns:
                lines.append(
                    "| {name} | {data_type} | {nullable} | {description} |".format(
                        name=self._markdown_escape(column.get("name")),
                        data_type=self._markdown_escape(column.get("data_type")),
                        nullable=self._markdown_escape(column.get("is_nullable")),
                        description=self._markdown_escape(descriptions.get(column.get("name"))),
                    )
                )

        primary_key = schema.get("primary_key") or {}
        key_columns = primary_key.get("column_names", []) if isinstance(primary_key, dict) else []
        if key_columns:
            lines.extend(["", "## Primary key", "", ", ".join(f"`{column}`" for column in key_columns)])
        if schema.get("foreign_keys"):
            lines.extend(["", "## Foreign keys", ""])
            for key in schema["foreign_keys"]:
                lines.append(f"- `{key.get('column_name')}` → `{key.get('referenced_table')}.{key.get('referenced_column')}`")
        return "\n".join(lines) + "\n"

    def _save_markdown(self, record: Dict[str, Any]) -> None:
        path = self._get_markdown_file_path(record["config_name"], record["instance_name"], record["schema_name"], record["table_name"])
        path.write_text(self._render_markdown(record), encoding="utf-8")
        logger.info(f"FileMetadataStore: Saved Markdown metadata for {record['table_name']} -> {path}")

    def get_table_metadata(
        self,
        config_name: str,
        instance_name: str,
        schema_name: str,
        table_name: str,
    ) -> Optional[Dict[str, Any]]:
        file_path = self._get_file_path(config_name, instance_name, schema_name, table_name)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"FileMetadataStore: Error reading {file_path}: {e}")
            return None

    # Keys managed entirely by the system — never carried forward from existing data
    _SYSTEM_KEYS = frozenset({
        "metadata_key", "config_name", "instance_name", "schema_name",
        "table_name", "updated_at", "schema_description", "ai_documentation",
    })

    def save_table_metadata(
        self,
        config_name: str,
        instance_name: str,
        schema_name: str,
        table_name: str,
        schema_description: Dict[str, Any],
        ai_documentation: Optional[Dict[str, Any]] = None,
        only_if_changed: bool = False,
        save_markdown: bool = False,
    ) -> Dict[str, Any]:
        file_path = self._get_file_path(config_name, instance_name, schema_name, table_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data = self.get_table_metadata(config_name, instance_name, schema_name, table_name) or {}

        # Skip write if schema is unchanged (preserves updated_at and avoids noise)
        if only_if_changed and existing_data:
            if existing_data.get("schema_description") == schema_description:
                if save_markdown:
                    self._save_markdown(existing_data)
                logger.info(f"FileMetadataStore: No schema change for {table_name}, skipping write.")
                return {**existing_data, "_unchanged": True}

        # Preserve existing ai_documentation if not passed in this call
        final_ai_doc = (
            ai_documentation
            if ai_documentation is not None
            else existing_data.get("ai_documentation")
        )

        # Carry forward any custom fields added by humans (owner, tags, notes, etc.)
        custom_fields = {k: v for k, v in existing_data.items() if k not in self._SYSTEM_KEYS}

        metadata_record = {
            **custom_fields,
            "metadata_key": build_metadata_key(config_name, instance_name, schema_name, table_name),
            "config_name": config_name,
            "instance_name": instance_name,
            "schema_name": schema_name,
            "table_name": table_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "schema_description": schema_description,
            "ai_documentation": final_ai_doc,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metadata_record, f, indent=2, ensure_ascii=False)
            logger.info(f"FileMetadataStore: Saved table metadata for {table_name} -> {file_path}")
        except Exception as e:
            logger.error(f"FileMetadataStore: Failed to write {file_path}: {e}")

        if save_markdown:
            self._save_markdown(metadata_record)
        return metadata_record


    def _paginate(self, items: List[str], page: int, page_size: int) -> Dict[str, Any]:
        total = len(items)
        start = (page - 1) * page_size
        return {
            "items": items[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": math.ceil(total / page_size) if total > 0 else 0,
        }

    def list_instances(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        instances: set = set()
        if self.base_dir.exists():
            for config_dir in self.base_dir.iterdir():
                if config_dir.is_dir():
                    for instance_dir in config_dir.iterdir():
                        if instance_dir.is_dir():
                            instances.add(instance_dir.name)
        return self._paginate(sorted(instances), page, page_size)

    def list_databases(self, instance_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        sanitized = self._sanitize(instance_name)
        databases: set = set()
        if self.base_dir.exists():
            for config_dir in self.base_dir.iterdir():
                if config_dir.is_dir():
                    instance_dir = config_dir / sanitized
                    if instance_dir.is_dir():
                        for db_dir in instance_dir.iterdir():
                            if db_dir.is_dir():
                                databases.add(db_dir.name)
        return self._paginate(sorted(databases), page, page_size)

    def list_tables_metadata(self, instance_name: str, database_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        sanitized_instance = self._sanitize(instance_name)
        sanitized_db = self._sanitize(database_name)
        tables: set = set()
        if self.base_dir.exists():
            for config_dir in self.base_dir.iterdir():
                if config_dir.is_dir():
                    db_dir = config_dir / sanitized_instance / sanitized_db
                    if db_dir.is_dir():
                        for f in db_dir.iterdir():
                            if f.is_file() and f.suffix == ".json":
                                tables.add(f.stem)
        return self._paginate(sorted(tables), page, page_size)

    def find_table_metadata(self, instance_name: str, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        sanitized_instance = self._sanitize(instance_name)
        sanitized_db = self._sanitize(database_name)
        sanitized_table = self._sanitize(table_name)
        if self.base_dir.exists():
            for config_dir in self.base_dir.iterdir():
                if config_dir.is_dir():
                    file_path = config_dir / sanitized_instance / sanitized_db / f"{sanitized_table}.json"
                    if file_path.exists():
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                return json.load(f)
                        except Exception as e:
                            logger.warning(f"FileMetadataStore: Error reading {file_path}: {e}")
        return None

    def _find_file_path(self, instance_name: str, database_name: str, table_name: str) -> Optional[Path]:
        sanitized_instance = self._sanitize(instance_name)
        sanitized_db = self._sanitize(database_name)
        sanitized_table = self._sanitize(table_name)
        if self.base_dir.exists():
            for config_dir in self.base_dir.iterdir():
                if config_dir.is_dir():
                    candidate = config_dir / sanitized_instance / sanitized_db / f"{sanitized_table}.json"
                    if candidate.exists():
                        return candidate
        return None

    _PROTECTED_FIELDS = frozenset({"metadata_key", "config_name", "instance_name", "schema_name", "table_name", "updated_at"})

    def update_table_metadata(
        self, instance_name: str, database_name: str, table_name: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        file_path = self._find_file_path(instance_name, database_name, table_name)
        if file_path is None:
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            logger.warning(f"FileMetadataStore: Error reading {file_path}: {e}")
            return None

        for key, value in payload.items():
            if key not in self._PROTECTED_FIELDS:
                existing[key] = value
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            logger.info(f"FileMetadataStore: Updated metadata for {table_name} -> {file_path}")
        except Exception as e:
            logger.error(f"FileMetadataStore: Failed to write {file_path}: {e}")
            return None

        return existing


def get_metadata_store(store_type: Optional[str] = None) -> BaseMetadataStore:
    """Factory to get configured metadata store implementation."""
    store_type = store_type or os.getenv("METADATA_STORE_TYPE", "file")
    if store_type == "file":
        return FileMetadataStore()
    else:
        logger.warning(f"Unknown METADATA_STORE_TYPE '{store_type}', falling back to FileMetadataStore")
        return FileMetadataStore()
