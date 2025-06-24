# models/status.py
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class StatusValue(str, Enum):
    """Represents the approval status of a library element."""

    def __new__(cls, value, icon):
        obj = str.__new__(cls, value)
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

    footprint: StatusValue = Field(
        default=StatusValue.NEEDS_REVIEW, description="Approval status of the footprint"
    )
    symbol: StatusValue = Field(
        default=StatusValue.NEEDS_REVIEW, description="Approval status of the symbol"
    )
    component: StatusValue = Field(
        default=StatusValue.NEEDS_REVIEW, description="Approval status of the component"
    )
    device: StatusValue = Field(
        default=StatusValue.NEEDS_REVIEW, description="Approval status of the device"
    )


class ValidationSeverity(str, Enum):
    """Represents the severity of a validation message."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    HINT = "HINT"


class ValidationMessage(BaseModel):
    """Represents a single validation message from the checker."""

    message: str
    severity: ValidationSeverity
    count: int = 1
    is_approved: bool = False


class ElementManifest(BaseModel):
    """
    Represents the complete structure of a .wp manifest file.
    """

    version: int = 1
    status: StatusValue = StatusValue.NEEDS_REVIEW
    validation: List[ValidationMessage] = []
