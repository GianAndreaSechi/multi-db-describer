from typing import Optional
from pydantic import BaseModel


class DescribeTableRequest(BaseModel):
    config_name: str
    instance_name: str
    schema_name: str
    table_name: str
    generate_ai_docs: bool = False
    save_metadata: bool = True

