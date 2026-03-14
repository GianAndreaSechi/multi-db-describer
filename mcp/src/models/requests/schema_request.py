from pydantic import BaseModel
from typing import Optional

class SchemaRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
