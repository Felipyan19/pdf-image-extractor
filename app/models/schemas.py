from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class URLExtractionRequest(BaseModel):
    """Request model for extracting images from a URL"""
    url: str = Field(
        ...,
        description="Public URL of the PDF file to extract images from",
        examples=[
            "http://example.com/document.pdf",
            "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        ]
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "url": "http://example.com/document.pdf"
                },
                {
                    "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
                }
            ]
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
    status: str = Field(..., description="Service health status", examples=["healthy"])
    app_name: str = Field(..., description="Application name", examples=["PDF Image Extractor"])
    version: str = Field(..., description="Application version", examples=["1.0.0"])
    timestamp: datetime = Field(default_factory=datetime.now, description="Current server timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "app_name": "PDF Image Extractor",
                "version": "1.0.0",
                "timestamp": "2026-01-22T02:00:00.000000"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message describing what went wrong")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "detail": "Only PDF files are allowed"
                },
                {
                    "detail": "File size (75.5MB) exceeds maximum allowed size (50MB)"
                },
                {
                    "detail": "Failed to download PDF from URL: 404 Client Error"
                }
            ]
        }
