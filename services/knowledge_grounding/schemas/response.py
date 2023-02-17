from typing import Tuple, Union
from pydantic import BaseModel


class ResponsesSchema(BaseModel):
    responses: Tuple = []
