from typing import Optional, List
from pydantic import BaseModel

class InstanceRequest(BaseModel):
    config_names: Optional[List[str]] = None
