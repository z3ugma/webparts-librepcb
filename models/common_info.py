"""
Defines common, shared Pydantic models used by both SearchResult and LibraryPart.
"""

from typing import Optional

from pydantic import BaseModel


class ImageInfo(BaseModel):
    url: Optional[str] = None
    # Path is no longer stored, it will be derived at runtime.


class SymbolInfo(BaseModel):
    uuid: Optional[str] = None
    png_path: Optional[str] = None
    svg_path: Optional[str] = None
    rendered_png_path: Optional[str] = None


class FootprintInfo(BaseModel):
    uuid: Optional[str] = None
    package_type: Optional[str] = None
    png_path: Optional[str] = None
    svg_path: Optional[str] = None
    rendered_png_path: Optional[str] = None


class ComponentInfo(BaseModel):
    uuid: Optional[str] = None


class DeviceInfo(BaseModel):
    uuid: Optional[str] = None
