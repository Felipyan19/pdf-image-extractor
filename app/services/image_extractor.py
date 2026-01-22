import fitz  # PyMuPDF
import os
import time
import zipfile
from pathlib import Path
from typing import List, Dict, Tuple
from PIL import Image
import io

from app.config import settings
from app.models.schemas import ImageInfo


class PDFImageExtractor:
    """
    Service class for extracting images from PDF files using PyMuPDF.
    PyMuPDF is the fastest and most reliable library for PDF image extraction.
    """

    def __init__(self):
        self.output_dir = Path(settings.output_dir)
        self.output_format = settings.output_format.lower()
        self.image_quality = settings.image_quality

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_images(self, pdf_path: str, output_subdir: str = None) -> Tuple[List[ImageInfo], float]:
        """
        Extract all images from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            output_subdir: Optional subdirectory name for outputs

        Returns:
            Tuple of (list of ImageInfo objects, extraction time in seconds)
        """
        start_time = time.time()
        images_info = []

        # Create output subdirectory if specified
        if output_subdir:
            output_path = self.output_dir / output_subdir
        else:
            output_path = self.output_dir / Path(pdf_path).stem

        output_path.mkdir(parents=True, exist_ok=True)

        # Open PDF document
        pdf_document = fitz.open(pdf_path)

        try:
            image_counter = 1

            # Iterate through each page
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]

                # Get list of images on the page
                image_list = page.get_images(full=True)

                # Extract each image
                for img_index, img in enumerate(image_list):
                    xref = img[0]  # Get the XREF of the image

                    # Extract image data
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Get image metadata
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    colorspace = base_image.get("colorspace", "unknown")

                    # Convert colorspace to string if it's an integer
                    if isinstance(colorspace, int):
                        # Map common PyMuPDF colorspace integers to names
                        colorspace_map = {
                            1: "DeviceGray",
                            3: "DeviceRGB",
                            4: "DeviceCMYK"
                        }
                        colorspace = colorspace_map.get(colorspace, f"Colorspace-{colorspace}")
                    elif not isinstance(colorspace, str):
                        colorspace = str(colorspace)

                    # Generate output filename
                    output_filename = f"page_{page_num + 1}_img_{image_counter}.{self.output_format}"
                    output_filepath = output_path / output_filename

                    # Convert and save image if needed
                    if image_ext != self.output_format:
                        self._convert_and_save_image(
                            image_bytes,
                            output_filepath,
                            self.output_format
                        )
                    else:
                        # Save directly
                        with open(output_filepath, "wb") as img_file:
                            img_file.write(image_bytes)

                    # Get file size
                    file_size = output_filepath.stat().st_size

                    # Create image info
                    img_info = ImageInfo(
                        filename=output_filename,
                        page_number=page_num + 1,
                        width=width,
                        height=height,
                        format=self.output_format,
                        size_bytes=file_size,
                        color_space=colorspace
                    )

                    images_info.append(img_info)
                    image_counter += 1

        finally:
            pdf_document.close()

        extraction_time = time.time() - start_time
        return images_info, extraction_time

    def extract_images_and_renders(
        self,
        pdf_path: str,
        output_subdir: str = None,
        render_dpi: int = 200
    ) -> Tuple[Path, Path, int, int, float]:
        """
        Extract embedded images and render each page to PNG, then package everything into a ZIP.

        Args:
            pdf_path: Path to the PDF file
            output_subdir: Optional subdirectory name for outputs
            render_dpi: DPI for rendered page images

        Returns:
            Tuple of (output directory, zip path, render count, total files, extraction time)
        """
        start_time = time.time()

        if output_subdir:
            output_path = self.output_dir / output_subdir
        else:
            output_path = self.output_dir / Path(pdf_path).stem

        output_path.mkdir(parents=True, exist_ok=True)

        pdf_document = fitz.open(pdf_path)

        extracted_files = []
        render_count = 0

        try:
            for page_index in range(len(pdf_document)):
                page = pdf_document[page_index]
                page_no = page_index + 1

                # Render full page
                pix = page.get_pixmap(dpi=render_dpi)
                render_name = output_path / f"page{page_no:03d}_render.png"
                pix.save(str(render_name))
                extracted_files.append(render_name)
                render_count += 1

                # Extract embedded images
                image_list = page.get_images(full=True)
                for img_i, img in enumerate(image_list, start=1):
                    xref = img[0]
                    base = pdf_document.extract_image(xref)
                    img_bytes = base["image"]
                    ext = base.get("ext", "bin")

                    img_name = output_path / f"page{page_no:03d}_img{img_i:02d}_xref{xref}.{ext}"
                    with open(img_name, "wb") as f:
                        f.write(img_bytes)

                    extracted_files.append(img_name)

        finally:
            pdf_document.close()

        # Create ZIP with all generated files
        zip_path = self.output_dir / f"{output_path.name}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in extracted_files:
                zf.write(file_path, arcname=file_path.relative_to(output_path.parent))

        extraction_time = time.time() - start_time
        return output_path, zip_path, render_count, len(extracted_files), extraction_time

    def _convert_and_save_image(self, image_bytes: bytes, output_path: Path, target_format: str):
        """
        Convert image bytes to target format and save.

        Args:
            image_bytes: Raw image bytes
            output_path: Output file path
            target_format: Target image format (png, jpg, etc.)
        """
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))

            # Convert RGBA to RGB if saving as JPEG
            if target_format.lower() in ['jpg', 'jpeg'] and image.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
                image = background

            # Save with quality settings
            save_kwargs = {}
            if target_format.lower() in ['jpg', 'jpeg']:
                save_kwargs['quality'] = self.image_quality
                save_kwargs['optimize'] = True
            elif target_format.lower() == 'png':
                save_kwargs['optimize'] = True

            image.save(output_path, format=target_format.upper(), **save_kwargs)

        except Exception as e:
            # If conversion fails, save original bytes
            with open(output_path, "wb") as img_file:
                img_file.write(image_bytes)

    def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get basic information about a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with PDF information
        """
        pdf_document = fitz.open(pdf_path)

        try:
            info = {
                "page_count": len(pdf_document),
                "metadata": pdf_document.metadata,
                "is_encrypted": pdf_document.is_encrypted,
            }
            return info
        finally:
            pdf_document.close()
