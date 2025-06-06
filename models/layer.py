# Global imports
# footprint.py
# Global imports
from enum import Enum
from typing import Annotated, Dict, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field, model_validator


class LayerType(str, Enum):
    """Types for PCB layers."""

    TOP_COPPER = "top_copper"
    BOTTOM_COPPER = "bottom_copper"
    INNER_COPPER = "inner_copper"  # indexed
    TOP_SOLDER_MASK = "top_solder_mask"
    BOTTOM_SOLDER_MASK = "bottom_solder_mask"
    TOP_PASTE_MASK = "top_paste_mask"
    BOTTOM_PASTE_MASK = "bottom_paste_mask"
    TOP_SILKSCREEN = "top_silkscreen"
    BOTTOM_SILKSCREEN = "bottom_silkscreen"
    BOARD_OUTLINE = "board_outline"
    COURTYARD_TOP = "courtyard_top"
    COURTYARD_BOTTOM = "courtyard_bottom"
    FABRICATION_TOP = "fabrication_top"
    FABRICATION_BOTTOM = "fabrication_bottom"
    ASSEMBLY_TOP = "assembly_top"
    ASSEMBLY_BOTTOM = "assembly_bottom"
    DOCUMENTATION = "documentation"
    MECHANICAL = "mechanical"  # indexed
    ADHESIVE_TOP = "adhesive_top"
    ADHESIVE_BOTTOM = "adhesive_bottom"
    USER_NON_PLATED_HOLES = "user_non_plated_holes"
    MULTI_LAYER = "multi_layer"  # spans start/end layers


# --- Layer Reference ---


class LayerRef(BaseModel):
    type: LayerType
    index: Optional[int] = Field(
        None, ge=1, description="1-based index for INNER_COPPER or MECHANICAL layers"
    )

    @model_validator(mode="after")
    def _check_index(cls, m):
        req = {LayerType.INNER_COPPER, LayerType.MECHANICAL}
        if m.type in req and m.index is None:
            raise ValueError(f"Layer '{m.type}' requires an index")
        if m.index is not None and m.type not in req:
            raise ValueError(f"Layer '{m.type}' must not have an index")
        return m

    def __str__(self):
        return f"{self.type.value}_{self.index}" if self.index else self.type.value


LayerInput = Union[LayerType, LayerRef, Dict]


def _validate_layer(v: LayerInput) -> LayerRef:
    if isinstance(v, LayerRef):
        return v
    if isinstance(v, LayerType):
        if v in (LayerType.INNER_COPPER, LayerType.MECHANICAL):
            raise ValueError(f"Layer '{v}' requires index; use LayerRef")
        return LayerRef(type=v)
    if isinstance(v, dict):
        return LayerRef(**v)
    raise TypeError("Invalid Layer input")


Layer = Annotated[
    LayerRef, BeforeValidator(_validate_layer), Field(validate_default=False)
]
