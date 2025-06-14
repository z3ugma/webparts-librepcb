from enum import Enum
from pydantic import BaseModel, Field

class StatusValue(Enum):
    """An enumeration for the approval status of a library element."""

    def __new__(cls, value, icon):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        return obj

    APPROVED = ("approved", "✔")
    NEEDS_REVIEW = ("needs_review", "⏳")
    ERROR = ("error", "✘")
    UNAVAILABLE = ("unavailable", "❓")
    UNKNOWN = ("unknown", "❓")

class Status(BaseModel):
    """Holds the approval status for all elements of a library part."""
    footprint: StatusValue = Field(default=StatusValue.NEEDS_REVIEW, description="Approval status of the footprint")
    symbol: StatusValue = Field(default=StatusValue.NEEDS_REVIEW, description="Approval status of the symbol")
    component: StatusValue = Field(default=StatusValue.NEEDS_REVIEW, description="Approval status of the component")
    device: StatusValue = Field(default=StatusValue.NEEDS_REVIEW, description="Approval status of the device")
