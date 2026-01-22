from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class URLExtractionRequest(BaseModel):
    """Request model for extracting images from a URL"""
    url: str = Field(..., description="Public URL of the PDF file to extract images from")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "http://example.com/document.pdf"
            }
        }


class ImageInfo(BaseModel):
    """Information about an extracted image"""
    filename: str
    page_number: int
    width: int
    height: int
    format: str
    size_bytes: int
    color_space: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Response model for image extraction"""
    success: bool
    message: str
    total_pages: int
    total_images: int
    images: List[ImageInfo]
    extraction_time: float
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    app_name: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
