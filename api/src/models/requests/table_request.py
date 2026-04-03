from typing import Optional
from pydantic import BaseModel


class TableRequest(BaseModel):
    config_name: str
    instance_name: str
    schema_name: str
    limit: Optional[int] = None
    offset: Optional[int] = None
