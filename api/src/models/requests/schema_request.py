from typing import Optional
from pydantic import BaseModel

class SchemaRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
