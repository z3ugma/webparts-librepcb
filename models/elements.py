from __future__ import annotations
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4
import re

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

    def get_element_name(self, uuid: str) -> Optional[str]:
        """Extract the element name from the .lp file."""
        lp_path = self.get_lp_path(uuid)
        if not lp_path.exists():
            return None
        
        try:
            with open(lp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for (name "...") pattern in the S-expression
                match = re.search(r'\(name\s+"([^"]+)"\)', content)
                if match:
                    return match.group(1)
        except Exception:
            # Silently fail - logging should be done at the caller level
            pass
        
        return None

    def get_element_dir_absolute(self, uuid: str) -> Optional[Path]:
        """Get the absolute path to an element's directory if it exists."""
        if not uuid:
            return None
        
        element_dir = self.dir / uuid
        if element_dir.exists():
            return element_dir.resolve()
        
        return None


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
