from pydantic import BaseModel

class SchemaRequest(BaseModel):
    config_name: str
    instance_name: str
