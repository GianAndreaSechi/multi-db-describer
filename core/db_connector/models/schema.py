from pydantic import BaseModel
from typing import Optional

class Schema(BaseModel):
    """Represents a schema or a database within an instance."""
    name: str
    owner: Optional[str] = None
