"""
Defines the canonical data model for a component that has been saved
to the user's local library.
"""

from typing import Optional, Dict
from pathlib import Path
from pydantic import BaseModel, Field
from .common_info import ImageInfo, SymbolInfo, FootprintInfo, ComponentInfo, DeviceInfo
from .status import Status


class LibraryPart(BaseModel):
    """
    Represents a single, atomic component saved in the user's library.
    Its source of truth is the set of files within the .lplib directory.
    It does not store file paths, as they are derived at runtime based on convention.
    """

    # Core identifying information
    uuid: str = Field(description="Primary key for the part, equivalent to device_uuid")
    vendor: str
    part_name: str
    lcsc_id: str
    manufacturer: str
    mfr_part_number: str

    # Descriptive information
    description: str
    full_description: str

    # Metadata
    datasheet_url: Optional[str] = None
    stock_quantity: Optional[int] = None

    # --- Nested Part Information (from common models) ---
    image: ImageInfo = Field(default_factory=ImageInfo)
    symbol: SymbolInfo = Field(default_factory=SymbolInfo)
    footprint: FootprintInfo = Field(default_factory=FootprintInfo)
    component: ComponentInfo = Field(default_factory=ComponentInfo)
    device: DeviceInfo = Field(default_factory=DeviceInfo)

    # --- Approval Status (not serialized - read from individual element manifests) ---
    status: Status = Field(default_factory=Status, exclude=True)

    # --- Hydrated Fields ---
    has_3d_model: bool = Field(False)

    @property
    def hero_image_path(self) -> Optional[Path]:
        """
        Dynamically constructs the path to the hero image for this part.
        """
        from constants import WEBPARTS_DIR, WebPartsFilename
        from pathlib import Path

        if not self.uuid:
            return None
        return WEBPARTS_DIR / self.uuid / WebPartsFilename.HERO_IMAGE.value

    @property
    def manifest_path(self) -> Optional[Path]:
        """
        Dynamically constructs the path to the main part manifest file.
        """
        from constants import WEBPARTS_DIR, WebPartsFilename
        from pathlib import Path

        if not self.uuid:
            return None
        return WEBPARTS_DIR / self.uuid / WebPartsFilename.PART_MANIFEST.value

    @property
    def dir_path(self) -> Optional[Path]:
        """
        Dynamically constructs the path to the main part directory.
        """
        from constants import WEBPARTS_DIR
        from pathlib import Path

        if not self.uuid:
            return None
        return WEBPARTS_DIR / self.uuid

    def create_library_dirs(self):
        """
        Creates all necessary directories for this library part.
        """
        if self.dir_path:
            self.dir_path.mkdir(parents=True, exist_ok=True)
        if self.footprint and self.footprint.dir_path:
            self.footprint.dir_path.mkdir(parents=True, exist_ok=True)
        if self.symbol and self.symbol.dir_path:
            self.symbol.dir_path.mkdir(parents=True, exist_ok=True)
