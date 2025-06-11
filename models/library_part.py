"""
Defines the canonical data model for a component that has been saved
to the user's local library.
"""
from typing import Optional, Dict
from pydantic import BaseModel, Field
from .common_info import (
    ImageInfo, SymbolInfo, FootprintInfo, ComponentInfo, DeviceInfo
)

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

    # --- Hydrated Fields ---
    has_3d_model: bool = Field(False)
