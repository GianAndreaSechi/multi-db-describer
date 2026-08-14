from abc import ABC, abstractmethod
import json
import re
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, Any, Optional
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
    ) -> Dict[str, Any]:
        """Save or update table metadata.

        Must preserve existing ai_documentation if ai_documentation is None.
        Must keep schema_description and ai_documentation in separate top-level fields.
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

    def save_table_metadata(
        self,
        config_name: str,
        instance_name: str,
        schema_name: str,
        table_name: str,
        schema_description: Dict[str, Any],
        ai_documentation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        file_path = self._get_file_path(config_name, instance_name, schema_name, table_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data = self.get_table_metadata(config_name, instance_name, schema_name, table_name) or {}

        # Preserve existing ai_documentation if not passed in this call
        final_ai_doc = (
            ai_documentation
            if ai_documentation is not None
            else existing_data.get("ai_documentation")
        )

        metadata_record = {
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

        return metadata_record


def get_metadata_store(store_type: Optional[str] = None) -> BaseMetadataStore:
    """Factory to get configured metadata store implementation."""
    store_type = store_type or os.getenv("METADATA_STORE_TYPE", "file")
    if store_type == "file":
        return FileMetadataStore()
    else:
        logger.warning(f"Unknown METADATA_STORE_TYPE '{store_type}', falling back to FileMetadataStore")
        return FileMetadataStore()
