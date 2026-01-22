"""
Example client script to test the PDF Image Extractor API
"""
import requests
import json
from pathlib import Path


# API Configuration
API_URL = "http://localhost:5050/api/v1"


def extract_images_from_pdf(pdf_path: str, output_format: str = "png"):
    """
    Extract images from a PDF file using the API

    Args:
        pdf_path: Path to the PDF file
        output_format: Desired output format (png, jpg, jpeg)
    """
    # Check if file exists
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ Error: File not found: {pdf_path}")
        return

    print(f"📄 Processing: {pdf_file.name}")
    print(f"📊 File size: {pdf_file.stat().st_size / 1024:.2f} KB")

    # Prepare the request
    url = f"{API_URL}/extract"
    files = {"file": (pdf_file.name, open(pdf_file, "rb"), "application/pdf")}
    params = {"output_format": output_format} if output_format else {}

    try:
        # Send request
        print(f"\n🚀 Sending request to {url}...")
        response = requests.post(url, files=files, params=params)

        # Close file
        files["file"][1].close()

        # Check response
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS!")
            print(f"📊 Total pages: {data['total_pages']}")
            print(f"🖼️  Total images extracted: {data['total_images']}")
            print(f"⏱️  Extraction time: {data['extraction_time']:.2f} seconds")

            if data['images']:
                print("\n📋 Extracted images:")
                for img in data['images']:
                    print(f"  - {img['filename']}")
                    print(f"    Page: {img['page_number']}, Size: {img['width']}x{img['height']}, Format: {img['format']}")
                    print(f"    File size: {img['size_bytes'] / 1024:.2f} KB")
        else:
            print(f"\n❌ Error {response.status_code}:")
            print(json.dumps(response.json(), indent=2))

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API.")
        print("Make sure the server is running on http://localhost:5050")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def check_health():
    """Check if the API is running"""
    url = f"{API_URL}/health"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy!")
            print(f"   App: {data['app_name']}")
            print(f"   Version: {data['version']}")
            print(f"   Status: {data['status']}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API")
        print("Make sure the server is running on http://localhost:5050")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Image Extractor - Example Client")
    print("=" * 60)

    # Check API health
    print("\n1️⃣  Checking API health...")
    if not check_health():
        exit(1)

    # Example: Extract images from a PDF
    print("\n2️⃣  Extracting images from PDF...")
    print("-" * 60)

    # Replace with your PDF file path
    pdf_path = "sample.pdf"

    # You can also specify the output format
    extract_images_from_pdf(pdf_path, output_format="png")

    print("\n" + "=" * 60)
    print("✅ Done! Check the 'outputs' directory for extracted images.")
    print("=" * 60)
