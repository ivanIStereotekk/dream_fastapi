from typing import Tuple
from pydantic import BaseModel


class Batch(BaseModel):
    checked_sentence: Tuple = None
    knowledge: Tuple = None
    text: str = None
    history: Tuple = None
