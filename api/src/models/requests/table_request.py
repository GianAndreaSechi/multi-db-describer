from typing import Optional
from pydantic import BaseModel

class TableRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
    schema_name: Optional[str] = None
