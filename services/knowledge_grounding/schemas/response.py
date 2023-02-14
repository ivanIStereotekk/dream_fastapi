from typing import Optional
from pydantic import BaseModel


class ResponsesSchema(BaseModel):
    responses: Optional[dict] = {}
