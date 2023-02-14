from pydantic import BaseModel
from typing_schemas.batch import Batch


class BatchInputsSchema(BaseModel):
    batch: list[Batch]
