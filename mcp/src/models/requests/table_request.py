from pydantic import BaseModel

class TableRequest(BaseModel):
    config_name: str
    instance_name: str
    schema_name: str
