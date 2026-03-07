from pydantic import BaseModel
from typing import List, Optional

class InstanceRequest(BaseModel):
    config_names: Optional[List[str]] = None
