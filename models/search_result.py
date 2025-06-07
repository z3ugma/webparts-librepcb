"""
Search result model for component search across different vendor APIs.
Simple implementation without external dependencies.
"""

from typing import Optional


class SearchResult:
    """
    Canonical data model for component search results.
    
    This model standardizes search results from different vendor APIs
    (EasyEDA, Digi-Key, Mouser, etc.) into a common format for the UI.
    """
    
    def __init__(
        self,
        vendor: str,
        part_name: str,
        lcsc_id: str,
        description: str,
        manufacturer: str,
        mfr_part_number: str,
        full_description: str,
        datasheet_url: Optional[str] = None,
        image_url: Optional[str] = None,
        stock_quantity: Optional[int] = None,
        unit_price: Optional[float] = None,
        package_type: Optional[str] = None,
    ):
        # Required fields
        self.vendor = self._validate_string(vendor, "vendor")
        self.part_name = self._validate_string(part_name, "part_name")
        self.lcsc_id = self._validate_string(lcsc_id, "lcsc_id")
        self.description = self._validate_string(description, "description")
        self.manufacturer = self._validate_string(manufacturer, "manufacturer")
        self.mfr_part_number = self._validate_string(mfr_part_number, "mfr_part_number")
        self.full_description = self._validate_string(full_description, "full_description")
        
        # Optional fields
        self.datasheet_url = datasheet_url
        self.image_url = image_url
        self.stock_quantity = stock_quantity
        self.unit_price = unit_price
        self.package_type = package_type
    
    def _validate_string(self, value: str, field_name: str) -> str:
        """Validate that required string fields are provided."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value)}")
        return value
    
    def dict(self) -> dict:
        """Convert to dictionary for backward compatibility with existing UI code."""
        return {
            "vendor": self.vendor,
            "part_name": self.part_name,
            "lcsc_id": self.lcsc_id,
            "description": self.description,
            "manufacturer": self.manufacturer,
            "mfr_part_number": self.mfr_part_number,
            "full_description": self.full_description,
            "datasheet_url": self.datasheet_url,
            "image_url": self.image_url,
            "stock_quantity": self.stock_quantity,
            "unit_price": self.unit_price,
            "package_type": self.package_type,
        }
    
    def get(self, key: str, default=None):
        """Provide dict-like .get() method for backward compatibility."""
        return getattr(self, key, default)
        
    def __str__(self) -> str:
        return f"<SearchResult {self.vendor}:{self.lcsc_id} - {self.part_name}>"
        
    def __repr__(self) -> str:
        return (
            f"SearchResult(vendor='{self.vendor}', part_name='{self.part_name}', "
            f"lcsc_id='{self.lcsc_id}', manufacturer='{self.manufacturer}')"
        )