"""
Defines common, shared Pydantic models used by both SearchResult and LibraryPart.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from constants import WebPartsFilename

from .elements import LibrePCBElement


class ImageInfo(BaseModel):
    url: Optional[str] = None


class SymbolInfo(BaseModel):
    uuid: Optional[str] = None
    name: Optional[str] = None

    @property
    def dir_path(self) -> Optional[Path]:
        if not self.uuid:
            return None
        return LibrePCBElement.SYMBOL.dir / self.uuid

    @property
    def png_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.SYMBOL_PNG.value

    @property
    def svg_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.SYMBOL_SVG.value

    @property
    def rendered_png_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.RENDERED_PNG.value


class FootprintInfo(BaseModel):
    uuid: Optional[str] = None
    name: Optional[str] = None
    package_type: Optional[str] = None
    model_3d_uuid: Optional[str] = None

    @property
    def dir_path(self) -> Optional[Path]:
        if not self.uuid:
            return None
        return LibrePCBElement.PACKAGE.dir / self.uuid

    @property
    def png_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.FOOTPRINT_PNG.value

    @property
    def svg_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.FOOTPRINT_SVG.value

    @property
    def rendered_png_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        return self.dir_path / WebPartsFilename.RENDERED_PNG.value

    @property
    def model_3d_path(self) -> Optional[Path]:
        if not self.model_3d_uuid:
            return None
        return LibrePCBElement.PACKAGE.dir / f"{self.model_3d_uuid}.step"

    @property
    def alignment_settings_path(self) -> Optional[Path]:
        if not self.dir_path:
            return None
        # Note: This file is not stored in the pkg directory anymore,
        # but in the backgrounds cache. This property constructs the path
        # to where LibrePCB expects it.
        from constants import BACKGROUNDS_DIR

        return BACKGROUNDS_DIR / self.uuid / "settings.lp"


class ComponentInfo(BaseModel):
    uuid: Optional[str] = None

    @property
    def dir_path(self) -> Optional[Path]:
        if not self.uuid:
            return None
        return LibrePCBElement.COMPONENT.dir / self.uuid


class DeviceInfo(BaseModel):
    uuid: Optional[str] = None

    @property
    def dir_path(self) -> Optional[Path]:
        if not self.uuid:
            return None
        return LibrePCBElement.DEVICE.dir / self.uuid
