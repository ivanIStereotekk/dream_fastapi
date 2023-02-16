from typing import Tuple, Union
from pydantic import BaseModel


class Batch(BaseModel):
    checked_sentence: Union[Tuple, str, dict] = None
    knowledge: Union[Tuple, str, dict] = None
    text: Union[Tuple, str, dict] = None
    history: Union[Tuple, str, dict] = None
