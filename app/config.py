from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings and configuration"""

    # App Info
    app_name: str = "PDF Image Extractor"
    app_version: str = "1.0.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 5050

    # Upload Settings
    max_file_size: int = 50  # MB
    allowed_extensions: str = "pdf"

    # Output Settings
    output_format: str = "png"
    image_quality: int = 95

    # Directories
    upload_dir: str = "uploads"
    output_dir: str = "outputs"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
