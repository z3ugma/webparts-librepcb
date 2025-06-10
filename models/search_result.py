from typing import Optional
from pydantic import BaseModel, Field

class SearchResult(BaseModel):
    """
    Canonical data model for a component search result.
    
    This model standardizes search results and will be hydrated with
    additional data as the user interacts with it.
    """
    # Core identifying information
    vendor: str
    part_name: str
    lcsc_id: str
    manufacturer: str
    mfr_part_number: str
    
    # Descriptive information
    description: str
    full_description: str
    
    # Optional metadata
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    stock_quantity: Optional[int] = None
    unit_price: Optional[float] = None
    package_type: Optional[str] = None
    
    # --- Hydrated Fields ---
    # These fields are populated after the initial search, on-demand.
    footprint_png_path: Optional[str] = Field(None, description="Absolute path to the cached footprint PNG")
    symbol_png_path: Optional[str] = Field(None, description="Absolute path to the cached symbol PNG")

    def __str__(self) -> str:
        return f"<SearchResult {self.vendor}:{self.lcsc_id} - {self.part_name}>"
        
    def __repr__(self) -> str:
        return (
            f"SearchResult(vendor='{self.vendor}', part_name='{self.part_name}', "
            f"lcsc_id='{self.lcsc_id}', manufacturer='{self.manufacturer}')"
        )
