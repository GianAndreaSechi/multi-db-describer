from typing import List, Optional
from pydantic import BaseModel

# Assuming core.db_connector.models.column.Column already exists
from .column import Column

class PrimaryKey(BaseModel):
    """Represents a primary key constraint."""
    column_names: List[str]

class ForeignKey(BaseModel):
    """Represents a foreign key constraint."""
    column_name: str
    referenced_table: str
    referenced_column: str
    constraint_name: Optional[str] = None

class Index(BaseModel):
    """Represents an index on a table."""
    name: str
    column_names: List[str]
    is_unique: bool
    is_primary: bool # True if this index is also the primary key
    type: Optional[str] = None # e.g., 'BTREE', 'HASH'

class TableDescription(BaseModel):
    """
    A comprehensive description of a database table, including columns,
    primary keys, foreign keys, and other indexes.
    """
    instance_name: str
    schema_name: str
    table_name: str
    columns: List[Column]
    primary_key: Optional[PrimaryKey] = None
    foreign_keys: List[ForeignKey] = []
    indexes: List[Index] = []
