"""
Defines the canonical data model for a component search result.
"""
from typing import Optional, Dict
from pydantic import BaseModel, Field
from .common_info import (
    ImageInfo, SymbolInfo, FootprintInfo, ComponentInfo, DeviceInfo
)

class SearchResult(BaseModel):
    # Core identifying information
    uuid: Optional[str] = Field(None)
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

    # --- Transient, UI-specific fields ---
    # These hold temporary cache paths for the UI and are excluded from any serialization.
    hero_image_cache_path: Optional[str] = Field(None, exclude=True)
    symbol_png_cache_path: Optional[str] = Field(None, exclude=True)
    footprint_png_cache_path: Optional[str] = Field(None, exclude=True)
    footprint_svg_cache_path: Optional[str] = Field(None, exclude=True)
    
    # --- Raw Data (for processing, not for saving) ---
    raw_cad_data: Optional[Dict] = Field(None, exclude=True)
    has_3d_model: bool = Field(False, exclude=True)

    def to_dict(self):
        return self.model_dump(exclude_none=True)
