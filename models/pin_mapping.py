from typing import Dict, List, Tuple
from pydantic import BaseModel, ConfigDict
from librepcb_parts_generator.entities.symbol import Pin


class PinMapping(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    """
    An auxiliary data structure to hold the full, unconsolidated pin information.
    """
    pins: List[Tuple[str, str, Pin]] = []
