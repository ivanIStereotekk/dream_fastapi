from pydantic import BaseModel
from typing_schemas.batch import Batch
from typing import Tuple


class BatchInputsSchema(BaseModel):
    batch: Batch
