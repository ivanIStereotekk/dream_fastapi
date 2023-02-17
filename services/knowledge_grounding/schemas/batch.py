from typing import Tuple, Union
from pydantic import BaseModel


class Batch(BaseModel):
    checked_sentence: str = None
    knowledge: str = None
    text: str = None
    history: str = None
