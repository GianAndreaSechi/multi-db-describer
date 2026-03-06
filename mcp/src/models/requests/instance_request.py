from pydantic import BaseModel
from typing import List

class InstanceRequest(BaseModel):
    config_names: List[str]
