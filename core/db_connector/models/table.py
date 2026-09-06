from pydantic import BaseModel
from typing import Optional

class Table(BaseModel):
    """Represents a table within a schema."""
    name: str
    schema_name: str
    row_count: Optional[int] = None
