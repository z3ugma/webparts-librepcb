"""
Defines the data model for the approval status of library part elements.
"""
from pydantic import BaseModel, Field

class Status(BaseModel):
    """
    Holds the approval status for each element of a library part.
    """
    footprint: str = Field("needs_review", description="Approval status of the footprint")
    symbol: str = Field("needs_review", description="Approval status of the symbol")
    component: str = Field("needs_review", description="Approval status of the component")
    device: str = Field("needs_review", description="Approval status of the device")
