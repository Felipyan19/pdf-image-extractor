from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from app.config import settings
from app.api.endpoints import router


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    ## 🚀 High-performance PDF Image Extraction API

    Extract images from PDF files with **PyMuPDF** - the fastest and most reliable PDF processing library.

    ### ✨ Features
    - 📄 Extract embedded images in their original format (JPEG, PNG, etc.)
    - 🖼️ Generate high-quality page renders (200 DPI PNG)
    - 📦 Download everything in a single ZIP file
    - 🔗 Two methods: Upload file or provide URL
    - ⚡ Ultra-fast processing
    - 🧹 Zero storage - files are never stored on the server

    ### 🎯 Use Cases
    - Extract images from scanned documents
    - Process PDFs with multimedia content
    - Convert PDFs to image galleries
    - Data preparation for machine learning

    ### 📊 Performance
    Can process 1,310 pages and extract 180 images in just 1.5-2 seconds!

    ### 🔒 Privacy & Security
    - All files are processed in temporary memory
    - Automatic cleanup after response
    - No data retention
    - Configurable file size limits
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "API Support",
        "url": "https://github.com/your-repo/pdf-image-extractor",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api/v1", tags=["PDF Image Extraction"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Create necessary directories
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    print(f"✅ {settings.app_name} v{settings.app_version} started successfully!")
    print(f"📁 Upload directory: {settings.upload_dir}")
    print(f"📁 Output directory: {settings.output_dir}")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }




@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
