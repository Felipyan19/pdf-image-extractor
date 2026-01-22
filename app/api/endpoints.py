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
        200: {
            "description": "ZIP file containing all extracted images and page renders",
            "content": {"application/zip": {}}
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid file format (only PDF allowed)"
        },
        413: {
            "model": ErrorResponse,
            "description": "File size exceeds maximum allowed limit"
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error during image extraction"
        }
    },
    summary="📤 Extract images from uploaded PDF",
    description="""
    Upload a PDF file and extract all embedded images plus page renders.

    **Returns:** A ZIP file containing:
    - Page renders (PNG at 200 DPI) - one per page
    - Embedded images (original format: JPEG, PNG, etc.)

    **Example:** Upload `document.pdf` → Get `document_images.zip`

    **Notes:**
    - Only PDF files are accepted
    - Files are processed in memory - nothing is stored
    - Automatic cleanup after download
    - Maximum file size: 50 MB (configurable)
    """
)
async def extract_images(
    file: UploadFile = File(..., description="PDF file to extract images from (max 50MB)")
):
    """
    Extract all images from an uploaded PDF file.

    The endpoint will:
    1. Validate the PDF file
    2. Extract embedded images in their original format
    3. Render each page as high-quality PNG
    4. Package everything into a ZIP file
    5. Clean up all temporary files automatically

    **Parameters:**
    - **file**: PDF file to process (required, max 50MB)

    **Returns:**
    - ZIP file with all extracted images and renders
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
        200: {
            "description": "ZIP file containing all extracted images and page renders",
            "content": {"application/zip": {}}
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid URL or URL does not point to a valid PDF"
        },
        408: {
            "model": ErrorResponse,
            "description": "Request timeout while downloading PDF"
        },
        413: {
            "model": ErrorResponse,
            "description": "Downloaded file size exceeds maximum allowed limit"
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error during PDF download or image extraction"
        }
    },
    summary="🔗 Extract images from PDF URL",
    description="""
    Download a PDF from a public URL and extract all embedded images plus page renders.

    **Returns:** A ZIP file containing:
    - Page renders (PNG at 200 DPI) - one per page
    - Embedded images (original format: JPEG, PNG, etc.)

    **Example Request:**
    ```json
    {
      "url": "http://example.com/document.pdf"
    }
    ```

    **Example Response:** `document_images.zip`

    **Requirements:**
    - URL must be publicly accessible (no authentication)
    - URL must point to a valid PDF file
    - File size must not exceed 50 MB

    **Notes:**
    - Files are downloaded to temporary storage
    - Automatic validation of PDF format
    - Complete cleanup after processing
    - 30 second timeout for downloads
    """
)
async def extract_images_from_url(
    request: URLExtractionRequest = Body(
        ...,
        description="URL extraction request",
        openapi_examples={
            "example1": {
                "summary": "Basic PDF URL",
                "description": "Extract from a simple PDF URL",
                "value": {
                    "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
                }
            },
            "example2": {
                "summary": "URL with encoding",
                "description": "Extract from URL with spaces (encoded)",
                "value": {
                    "url": "http://example.com/files/my%20document.pdf"
                }
            }
        }
    )
):
    """
    Extract all images from a PDF file accessible via public URL.

    The endpoint will:
    1. Download the PDF from the provided URL
    2. Validate it's a proper PDF file
    3. Extract embedded images in their original format
    4. Render each page as high-quality PNG
    5. Package everything into a ZIP file
    6. Clean up all temporary files automatically

    **Parameters:**
    - **url**: Public URL of the PDF file (required, must be accessible without auth)

    **Returns:**
    - ZIP file with all extracted images and renders

    **Error Cases:**
    - 400: Invalid URL format or not a PDF
    - 408: Download timeout (>30 seconds)
    - 413: File too large (>50 MB)
    - 500: Extraction or server error
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
    summary="🏥 Health check",
    description="""
    Verify the API service status and get basic information.

    **Returns:**
    ```json
    {
      "status": "healthy",
      "app_name": "PDF Image Extractor",
      "version": "1.0.0",
      "timestamp": "2026-01-22T02:00:00"
    }
    ```

    **Use this endpoint to:**
    - Monitor service availability
    - Verify API is responding
    - Check current version
    - Health check for load balancers/monitoring tools
    """,
    responses={
        200: {
            "description": "Service is healthy and running",
            "model": HealthResponse
        }
    }
)
async def health_check():
    """
    Health check endpoint to verify the service is running.

    **Returns:**
    - Service status (always "healthy" if responding)
    - Application name
    - Current version
    - Current timestamp
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version
    )
