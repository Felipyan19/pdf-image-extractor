from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import requests
from urllib.parse import urlparse, unquote
from uuid import uuid4
import tempfile
import os

from app.config import settings
from app.models.schemas import HealthResponse, ErrorResponse, URLExtractionRequest
from app.services.image_extractor import PDFImageExtractor


router = APIRouter()
extractor = PDFImageExtractor()


def _cleanup_paths(*paths: Path) -> None:
    """Clean up temporary files and directories."""
    for path in paths:
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
        except Exception:
            pass


@router.post(
    "/extract",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/zip": {}}},
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Extract images from PDF",
    description="Upload a PDF file, extract embedded images and render pages, then return a ZIP with all images."
)
async def extract_images(
    file: UploadFile = File(..., description="PDF file to extract images from")
):
    """
    Extract all images from an uploaded PDF file.

    - **file**: PDF file to process (required)
    """
    # Validate file extension
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Create temporary file for PDF
    pdf_fd, pdf_temp_path = tempfile.mkstemp(suffix='.pdf', prefix='upload_')
    os.close(pdf_fd)
    pdf_path = Path(pdf_temp_path)

    output_dir = None
    zip_path = None

    try:
        # Save uploaded file to temp location
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Check file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size}MB)"
            )

        # Extract images
        output_subdir = f"{Path(file.filename).stem}_{uuid4().hex[:8]}"
        output_dir, zip_path, render_count, total_files, extraction_time = (
            extractor.extract_images_and_renders(
                str(pdf_path),
                output_subdir=output_subdir
            )
        )

        # Read ZIP into memory
        with open(zip_path, 'rb') as f:
            zip_content = f.read()

        # Create temporary file for response
        zip_fd, zip_temp_path = tempfile.mkstemp(suffix='.zip', prefix='response_')
        os.close(zip_fd)
        with open(zip_temp_path, 'wb') as f:
            f.write(zip_content)

        # Clean up extraction artifacts immediately
        _cleanup_paths(output_dir, zip_path)

        return FileResponse(
            path=zip_temp_path,
            media_type="application/zip",
            filename=f"{Path(file.filename).stem}_images.zip",
            background=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting images: {str(e)}"
        )
    finally:
        # Clean up uploaded PDF
        _cleanup_paths(pdf_path)
        # Clean up any remaining extraction artifacts
        if output_dir:
            _cleanup_paths(output_dir)
        if zip_path:
            _cleanup_paths(zip_path)


@router.post(
    "/extract-from-url",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/zip": {}}},
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Extract images from PDF URL",
    description="Download a PDF from a public URL, extract images and renders, then return a ZIP."
)
async def extract_images_from_url(
    request: URLExtractionRequest = Body(..., description="URL extraction request")
):
    """
    Extract all images from a PDF file accessible via public URL.

    - **url**: Public URL of the PDF file (required)
    """
    pdf_url = request.url

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

    # Create temporary file for downloaded PDF
    pdf_fd, pdf_temp_path = tempfile.mkstemp(suffix='.pdf', prefix='download_')
    os.close(pdf_fd)
    pdf_path = Path(pdf_temp_path)

    output_dir = None
    zip_path = None

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

        # Save downloaded file to temp location
        with open(pdf_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"PDF downloaded successfully to temp file")

        # Check file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size}MB)"
            )

        # Extract images
        output_subdir = f"{Path(filename).stem}_{uuid4().hex[:8]}"
        output_dir, zip_path, render_count, total_files, extraction_time = (
            extractor.extract_images_and_renders(
                str(pdf_path),
                output_subdir=output_subdir
            )
        )

        # Read ZIP into memory
        with open(zip_path, 'rb') as f:
            zip_content = f.read()

        # Create temporary file for response
        zip_fd, zip_temp_path = tempfile.mkstemp(suffix='.zip', prefix='response_')
        os.close(zip_fd)
        with open(zip_temp_path, 'wb') as f:
            f.write(zip_content)

        # Clean up extraction artifacts immediately
        _cleanup_paths(output_dir, zip_path)

        return FileResponse(
            path=zip_temp_path,
            media_type="application/zip",
            filename=f"{Path(filename).stem}_images.zip",
            background=None
        )

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )
    finally:
        # Clean up downloaded PDF
        _cleanup_paths(pdf_path)
        # Clean up any remaining extraction artifacts
        if output_dir:
            _cleanup_paths(output_dir)
        if zip_path:
            _cleanup_paths(zip_path)


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
