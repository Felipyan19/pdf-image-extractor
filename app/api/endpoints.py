from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body
from pathlib import Path
import os
import shutil
import requests
from typing import Optional
from urllib.parse import urlparse, unquote

from app.config import settings
from app.models.schemas import ExtractionResponse, HealthResponse, ErrorResponse, URLExtractionRequest
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


@router.post(
    "/extract-from-url",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Extract images from PDF URL",
    description="Download a PDF from a public URL and extract all images from it."
)
async def extract_images_from_url(
    request: URLExtractionRequest = Body(..., description="URL extraction request")
):
    """
    Extract all images from a PDF file accessible via public URL.

    - **url**: Public URL of the PDF file (required)
    - **output_format**: Desired output format (png, jpg, jpeg) - defaults to settings
    """
    pdf_url = request.url
    output_format = request.output_format

    # Validate URL format
    try:
        parsed_url = urlparse(pdf_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {str(e)}"
        )

    # Extract filename from URL
    url_path = unquote(parsed_url.path)
    filename = Path(url_path).name
    if not filename.lower().endswith('.pdf'):
        filename = f"{filename}.pdf" if filename else "downloaded.pdf"

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename

    try:
        # Download PDF from URL
        print(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' not in content_type and not filename.lower().endswith('.pdf'):
            # Try to detect if it's actually a PDF by checking magic bytes
            first_bytes = response.content[:4]
            if first_bytes != b'%PDF':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL does not point to a valid PDF file"
                )

        # Save downloaded file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"PDF downloaded successfully: {file_path}")

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout while downloading PDF"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download PDF from URL: {str(e)}"
        )
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )

    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > settings.max_file_size:
        file_path.unlink()
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
            output_subdir=Path(filename).stem
        )

        # Create response
        response = ExtractionResponse(
            success=True,
            message=f"Images extracted successfully from URL",
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
        # Clean up downloaded file
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
