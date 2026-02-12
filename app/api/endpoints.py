from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body, Path as PathParam, Request
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import requests
from urllib.parse import urlparse, unquote
from uuid import uuid4
import tempfile
import os
import re
import mimetypes
from typing import Optional

from app.config import settings
from app.models.schemas import HealthResponse, ErrorResponse, URLExtractionRequest, HtmlExtractionResponse, AssetUrl
from app.services.image_extractor import PDFImageExtractor
from app.services.layout_extractor import extract_layout
from app.services.html_renderer import render_html, render_html_exact
from app.services.structured_extractor import extract_structured


router = APIRouter()
extractor = PDFImageExtractor()

# Session manager will be initialized in main.py
session_manager = None


def set_session_manager(manager):
    """Set the global session manager instance."""
    global session_manager
    session_manager = manager


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format (32-character hex string)."""
    return bool(re.match(r'^[a-f0-9]{32}$', session_id))


def validate_filename(filename: str) -> bool:
    """Validate filename to prevent path traversal attacks."""
    # Reject paths containing '..' or path separators
    if any(char in filename for char in ['/', '\\', '..', '\0']):
        return False
    # Must have valid image extension
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    return any(filename.lower().endswith(ext) for ext in valid_extensions)


def get_base_url(request: Request) -> str:
    """Get base URL from settings or auto-detect from request."""
    if settings.base_url:
        return settings.base_url.rstrip('/')
    # Auto-detect from request
    return f"{request.url.scheme}://{request.url.netloc}"


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


@router.get(
    "/images/{session_id}/{filename}",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Image file",
            "content": {"image/*": {}}
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid session ID or filename"
        },
        404: {
            "model": ErrorResponse,
            "description": "Session or image not found"
        },
        410: {
            "model": ErrorResponse,
            "description": "Session has expired"
        }
    },
    summary="🖼️ Get extracted image",
    description="""
    Retrieve a specific extracted image from a temporary session.

    **Usage:**
    1. Extract images from PDF using `/extract` or `/extract-from-url`
    2. Get session_id from response headers (X-Session-ID)
    3. Open metadata.json from the ZIP to get image URLs
    4. Access images directly via this endpoint

    **Example:**
    ```
    GET /api/v1/images/abc123def456.../page001_img01_xref12.png
    ```

    **Session Expiry:**
    - Sessions expire after {ttl_hours} hour(s)
    - After expiry, images are automatically deleted
    - Returns 410 Gone if session has expired

    **Security:**
    - Session IDs are validated (32-character hex)
    - Filenames are validated to prevent path traversal
    - Only image files can be accessed
    """.format(ttl_hours=settings.session_ttl_hours)
)
async def get_session_image(
    session_id: str = PathParam(..., description="Session ID from extraction (32-char hex string)"),
    filename: str = PathParam(..., description="Image filename (e.g., page001_img01_xref12.png)")
):
    """
    Retrieve a specific extracted image from a session.

    **Parameters:**
    - **session_id**: Unique session identifier (UUID hex format)
    - **filename**: Name of the image file to retrieve

    **Returns:**
    - Image file with appropriate content-type

    **Error Cases:**
    - 400: Invalid session ID format or filename
    - 404: Session or file not found
    - 410: Session has expired
    """
    # Check if public URLs feature is enabled
    if not settings.enable_public_urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public URLs feature is not enabled"
        )

    # Check if session manager is initialized
    if session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session manager not initialized"
        )

    # Validate session ID format
    if not validate_session_id(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )

    # Validate filename
    if not validate_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filename: {filename}"
        )

    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    # Check if session has expired
    if session_manager.is_session_expired(session_id):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Session has expired at {session.expires_at.isoformat()}"
        )

    # Construct file path
    file_path = session.output_dir / filename

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {filename}"
        )

    # Determine content type
    content_type, _ = mimetypes.guess_type(filename)
    if content_type is None:
        content_type = "application/octet-stream"

    # Return image file
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename
    )


@router.post(
    "/extract",
    response_class=FileResponse,
    name="extract_images_from_upload",
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
    request: Request,
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
        if settings.enable_public_urls and session_manager:
            # New flow: Create session, keep files
            session_id = session_manager.create_session(file.filename)
            session = session_manager.get_session(session_id)
            base_url = get_base_url(request)

            output_subdir = f"sessions/{session_id}"
            output_dir, zip_path, render_count, total_files, extraction_time = (
                extractor.extract_images_and_renders(
                    str(pdf_path),
                    output_subdir=output_subdir,
                    session_id=session_id,
                    base_url=base_url,
                    enable_urls=True
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

            # Clean up only the ZIP file, keep extracted files for session
            _cleanup_paths(zip_path)

            # Return with session headers
            return FileResponse(
                path=zip_temp_path,
                media_type="application/zip",
                filename=f"{Path(file.filename).stem}_images.zip",
                headers={
                    "X-Session-ID": session_id,
                    "X-Session-Expires": session.expires_at.isoformat()
                },
                background=None
            )
        else:
            # Original flow: Extract, send, delete everything
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
        # Clean up extraction artifacts only if not using sessions
        if not settings.enable_public_urls:
            if output_dir:
                _cleanup_paths(output_dir)
        # Always clean up the ZIP file itself (content is in temp file)
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
    request_obj: Request,
    url_request: URLExtractionRequest = Body(
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
    pdf_url = url_request.url

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
        if settings.enable_public_urls and session_manager:
            # New flow: Create session, keep files
            session_id = session_manager.create_session(filename)
            session = session_manager.get_session(session_id)
            base_url = get_base_url(request_obj)

            output_subdir = f"sessions/{session_id}"
            output_dir, zip_path, render_count, total_files, extraction_time = (
                extractor.extract_images_and_renders(
                    str(pdf_path),
                    output_subdir=output_subdir,
                    session_id=session_id,
                    base_url=base_url,
                    enable_urls=True
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

            # Clean up only the ZIP file, keep extracted files for session
            _cleanup_paths(zip_path)

            # Return with session headers
            return FileResponse(
                path=zip_temp_path,
                media_type="application/zip",
                filename=f"{Path(filename).stem}_images.zip",
                headers={
                    "X-Session-ID": session_id,
                    "X-Session-Expires": session.expires_at.isoformat()
                },
                background=None
            )
        else:
            # Original flow: Extract, send, delete everything
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
        # Clean up extraction artifacts only if not using sessions
        if not settings.enable_public_urls:
            if output_dir:
                _cleanup_paths(output_dir)
        # Always clean up the ZIP file itself (content is in temp file)
        if zip_path:
            _cleanup_paths(zip_path)


@router.post(
    "/extract-html",
    response_model=HtmlExtractionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format (only PDF allowed)"},
        413: {"model": ErrorResponse, "description": "File size exceeds maximum allowed limit"},
        500: {"model": ErrorResponse, "description": "Server error during extraction"},
    },
    summary="📄 Extract PDF layout and generate editable HTML",
    description="""
    Upload a PDF and receive:
    - **html**: Complete editable HTML page (images use public HTTPS URLs)
    - **layout**: Full layout JSON with text spans, bboxes, fonts, colors — feed this to an AI to improve the HTML
    - **assets**: List of extracted images with their public URLs
    - **session_id / session_expires**: Session info (images available for TTL hours)

    **Requires** `ENABLE_PUBLIC_URLS=true` in server configuration.
    """,
)
async def extract_html(
    request: Request,
    file: Optional[UploadFile] = File(None, description="PDF file (max 50 MB). Omit if using pdf_url in JSON body."),
):
    """
    Extract PDF layout and generate an editable HTML page.

    Accepts either:
    - **multipart/form-data** with `file` field (PDF upload)
    - **application/json** with `pdf_url` field (server downloads the PDF)

    JSON body example:
    ```json
    { "pdf_url": "https://example.com/document.pdf" }
    ```
    """
    if not settings.enable_public_urls or session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires ENABLE_PUBLIC_URLS=true in server configuration",
        )

    pdf_fd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf", prefix="upload_")
    os.close(pdf_fd)
    pdf_path = Path(pdf_temp_path)
    filename = "document.pdf"

    try:
        if file is not None:
            # --- Mode A: file upload ---
            filename = file.filename or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")
            with open(pdf_path, "wb") as buf:
                shutil.copyfileobj(file.file, buf)
        else:
            # --- Mode B: JSON body with pdf_url ---
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Provide a PDF file (multipart) or a JSON body with pdf_url",
                )
            pdf_url = body.get("pdf_url") or body.get("url")
            if not pdf_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JSON body must contain 'pdf_url' field",
                )
            try:
                parsed = urlparse(pdf_url)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("missing scheme or host")
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pdf_url")

            url_filename = Path(unquote(parsed.path)).name
            if url_filename:
                filename = url_filename if url_filename.lower().endswith(".pdf") else url_filename + ".pdf"

            try:
                resp = requests.get(pdf_url, stream=True, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.Timeout:
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Timeout downloading PDF")
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to download PDF: {e}")

            with open(pdf_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size}MB)",
            )

        session_id = session_manager.create_session(filename)
        session = session_manager.get_session(session_id)
        out_dir = session.output_dir

        layout = extract_layout(str(pdf_path), str(out_dir))

        base_url = get_base_url(request)
        assets: list[AssetUrl] = []
        for img_name in layout.get("image_files", []):
            img_url = f"{base_url}/api/v1/images/{session_id}/{img_name}"
            assets.append(AssetUrl(filename=img_name, url=img_url))

        assets_base_url = f"{base_url}/api/v1/images/{session_id}/"

        html = render_html(layout, assets_base_url=assets_base_url)
        html_exact = render_html_exact(layout, assets_base_url=assets_base_url)

        return HtmlExtractionResponse(
            html=html,
            html_exact=html_exact,
            layout=layout,
            assets=assets,
            session_id=session_id,
            session_expires=session.expires_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting HTML: {str(e)}",
        )
    finally:
        _cleanup_paths(pdf_path)


@router.post(
    "/extract-structured",
    response_model=dict,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format (only PDF allowed)"},
        413: {"model": ErrorResponse, "description": "File size exceeds maximum allowed limit"},
        500: {"model": ErrorResponse, "description": "Server error during extraction"},
    },
    summary="🔬 Extract structured element data from PDF (for n8n slot-based pipeline)",
    description="""
    Extracts all elements from a digital PDF as structured JSON — text, images, and shapes
    each with their bounding boxes, styles, and identifiers.

    **Designed for the n8n slot-based pipeline.** Does NOT generate HTML.

    **Returns extractor_output JSON with:**
    - `pages[].elements[]`: text (with `normalized_text` + style), image (with URL + phash + xref), rect (with colors)
    - `pages[].lines[]` / `pages[].blocks[]`: groupings for context
    - `pages[].render_png`: full-page render URL for fallback

    Accepts either:
    - **multipart/form-data** with `file` field (PDF upload)
    - **application/json** with `pdf_url` field (server downloads the PDF)
    """,
)
async def extract_structured_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None, description="PDF file (max 50 MB)"),
):
    """Extract structured element data for the n8n slot-based template pipeline."""
    if not settings.enable_public_urls or session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires ENABLE_PUBLIC_URLS=true",
        )

    pdf_fd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf", prefix="structured_")
    os.close(pdf_fd)
    pdf_path = Path(pdf_temp_path)
    filename = "document.pdf"

    try:
        if file is not None:
            filename = file.filename or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")
            with open(pdf_path, "wb") as buf:
                shutil.copyfileobj(file.file, buf)
        else:
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Provide a PDF file (multipart) or a JSON body with pdf_url",
                )
            pdf_url = body.get("pdf_url") or body.get("url")
            if not pdf_url:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON body must contain 'pdf_url'")

            from urllib.parse import urlparse, unquote as _unquote
            parsed = urlparse(pdf_url)
            url_filename = Path(_unquote(parsed.path)).name
            if url_filename:
                filename = url_filename if url_filename.lower().endswith(".pdf") else url_filename + ".pdf"

            try:
                resp = requests.get(pdf_url, stream=True, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.Timeout:
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Timeout downloading PDF")
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to download PDF: {e}")

            with open(pdf_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({settings.max_file_size}MB)",
            )

        session_id = session_manager.create_session(filename)
        session = session_manager.get_session(session_id)
        out_dir = str(session.output_dir)
        base_url = get_base_url(request)

        structured = extract_structured(
            pdf_path=str(pdf_path),
            out_dir=out_dir,
            session_id=session_id,
            base_url=base_url,
            source_filename=filename,
        )

        # Add session metadata to the response for n8n to use
        structured["session_id"] = session_id
        structured["session_expires"] = session.expires_at.isoformat()

        return structured

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting structured data: {str(e)}",
        )
    finally:
        _cleanup_paths(pdf_path)


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
