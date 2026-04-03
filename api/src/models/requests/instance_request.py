from pydantic import BaseModel


class InstanceRequest(BaseModel):
    config_name: str
