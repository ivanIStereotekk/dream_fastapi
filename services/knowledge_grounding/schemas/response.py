from typing import Optional, Tuple
from pydantic import BaseModel


class ResponsesSchema(BaseModel):
    responses: Optional[Tuple] = None
