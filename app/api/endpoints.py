from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pathlib import Path
import os
import shutil
from typing import Optional

from app.config import settings
from app.models.schemas import ExtractionResponse, HealthResponse, ErrorResponse
from app.services.image_extractor import PDFImageExtractor


router = APIRouter()
extractor = PDFImageExtractor()


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Extract images from PDF",
    description="Upload a PDF file and extract all images from it. Images will be saved in the specified format."
)
async def extract_images(
    file: UploadFile = File(..., description="PDF file to extract images from"),
    output_format: Optional[str] = None
):
    """
    Extract all images from an uploaded PDF file.

    - **file**: PDF file to process (required)
    - **output_format**: Desired output format (png, jpg, jpeg) - defaults to settings
    """
    # Validate file extension
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    file_path = upload_dir / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > settings.max_file_size:
        file_path.unlink()  # Delete the file
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size}MB)"
        )

    # Set output format if provided
    if output_format:
        original_format = extractor.output_format
        extractor.output_format = output_format.lower()

    try:
        # Get PDF info
        pdf_info = extractor.get_pdf_info(str(file_path))

        # Extract images
        images_info, extraction_time = extractor.extract_images(
            str(file_path),
            output_subdir=Path(file.filename).stem
        )

        # Create response
        response = ExtractionResponse(
            success=True,
            message="Images extracted successfully",
            total_pages=pdf_info["page_count"],
            total_images=len(images_info),
            images=images_info,
            extraction_time=extraction_time
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting images: {str(e)}"
        )

    finally:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()

        # Restore original format if it was changed
        if output_format:
            extractor.output_format = original_format


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is running and get basic information"
)
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version
    )
