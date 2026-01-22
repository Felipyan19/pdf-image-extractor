from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from app.config import settings
from app.api.endpoints import router


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A high-performance API for extracting images from PDF files using PyMuPDF",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
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
