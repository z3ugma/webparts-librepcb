from __future__ import annotations
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from constants import LIBRARY_DIR

class LibrePCBElement(Enum):
    """Represents the core elements of a LibrePCB library."""

    def __new__(cls, value, dir_name, filename, webparts_name):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.dir = LIBRARY_DIR / dir_name
        obj.filename = filename
        obj.webparts_name = webparts_name
        return obj

    PACKAGE = ("package", "pkg", "package.lp", "footprint")
    SYMBOL = ("symbol", "sym", "symbol.lp", "symbol")
    COMPONENT = ("component", "cmp", "component.lp", "component")
    DEVICE = ("device", "dev", "device.lp", "device")

    def get_lp_path(self, uuid: str) -> Path:
        """Get the path to the main LibrePCB element file (.lp)."""
        return self.dir / uuid / self.filename

    def get_wp_path(self, uuid: str) -> Path:
        """Get the path to the WebParts manifest file (.wp)."""
        return self.dir / uuid / f"{uuid}.{self.webparts_name}.wp"

class BaseElement(BaseModel):
    """
    A base model for all library elements, containing common metadata.
    """
    uuid: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    author: Optional[str] = None
    version: Optional[str] = None
    created_at: Optional[datetime] = None
    generated_by: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
