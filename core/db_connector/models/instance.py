from pydantic import BaseModel
from typing import Optional

class Instance(BaseModel):
    """Represents a database instance/server."""
    name: str
    version: Optional[str] = None
