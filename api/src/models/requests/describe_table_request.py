from typing import Optional
from pydantic import BaseModel

class DescribeTableRequest(BaseModel):
    config_name: Optional[str] = None
    instance_name: Optional[str] = None
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
