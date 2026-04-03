from pydantic import BaseModel


class DescribeTableRequest(BaseModel):
    config_name: str
    instance_name: str
    schema_name: str
    table_name: str
