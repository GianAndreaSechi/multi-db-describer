from pydantic import BaseModel
from typing import Optional, Any

class Column(BaseModel):
    """Represents a column of a table."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[Any] = None
    comment: Optional[str] = None
