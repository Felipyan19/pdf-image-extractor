from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


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
