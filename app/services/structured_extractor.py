"""
Structured extractor for the slot-based n8n pipeline.

Returns per-element data (text + bbox + style, images + bbox + phash, shapes)
suitable for deterministic slot matching in n8n. Does NOT generate HTML.
"""

import io
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

try:
    from PIL import Image
    import imagehash
    _PHASH_AVAILABLE = True
except ImportError:
    _PHASH_AVAILABLE = False


# ── Color helpers ──────────────────────────────────────────────────────────────

def _color_to_hex(color: Any) -> Optional[str]:
    """Convert a PyMuPDF color value to #rrggbb hex string."""
    if color is None:
        return None

    if isinstance(color, (list, tuple)) and len(color) >= 3:
        try:
            r, g, b = int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        except (TypeError, ValueError):
            return None

    if isinstance(color, int):
        return f"#{color & 0xFFFFFF:06x}"

    if isinstance(color, float):
        # Grayscale 0..1
        v = int(color * 255)
        return f"#{v:02x}{v:02x}{v:02x}"

    return None


def _infer_font_weight(font_name: str, flags: int) -> str:
    """Infer font weight from font name string and PyMuPDF flags."""
    name_lower = font_name.lower()
    if "bold" in name_lower or "heavy" in name_lower or "black" in name_lower:
        return "bold"
    # PyMuPDF flag bit 4 (0b10000 = 16) indicates bold
    if flags & 16:
        return "bold"
    return "normal"


def _infer_font_style(font_name: str, flags: int) -> str:
    name_lower = font_name.lower()
    if "italic" in name_lower or "oblique" in name_lower:
        return "italic"
    # PyMuPDF flag bit 1 (0b10 = 2) indicates italic
    if flags & 2:
        return "italic"
    return "normal"


# ── Text elements ──────────────────────────────────────────────────────────────

def _extract_text_elements(page: "fitz.Page", page_idx: int) -> List[Dict]:
    """Extract text elements at the line level with full style information."""
    elements = []
    order_counter = 100  # text elements start at 100 (shapes are 0-99)

    raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            # Merge span texts
            line_text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if not line_text:
                continue

            # Use dominant span (largest font size) for style
            dominant = max(spans, key=lambda s: s.get("size", 0))
            font_name = dominant.get("font", "")
            font_size = round(dominant.get("size", 12.0), 1)
            flags = dominant.get("flags", 0)
            color_int = dominant.get("color", 0)

            color_hex = _color_to_hex(color_int) or "#000000"

            # Line bbox from PyMuPDF line dict
            lb = line["bbox"]
            bbox = {"x0": round(lb[0], 2), "y0": round(lb[1], 2),
                    "x1": round(lb[2], 2), "y1": round(lb[3], 2)}

            elements.append({
                "id": f"t_{page_idx}_{order_counter:04d}",
                "type": "text",
                "text": line_text,
                "raw_text": line_text,
                "bbox": bbox,
                "style": {
                    "font_family": font_name,
                    "font_size": font_size,
                    "font_weight": _infer_font_weight(font_name, flags),
                    "font_style": _infer_font_style(font_name, flags),
                    "color": color_hex,
                },
                "order": order_counter,
            })
            order_counter += 1

    return elements


# ── Image elements ─────────────────────────────────────────────────────────────

def _extract_image_elements(
    page: "fitz.Page",
    doc: "fitz.Document",
    page_idx: int,
    out_dir: Path,
    session_id: str,
    base_url: str,
) -> List[Dict]:
    """Extract embedded images, save to disk, compute phash, return element list."""
    elements = []

    for img_idx, img_info in enumerate(page.get_images(full=True)):
        xref = img_info[0]

        # Get all rects for this image on the page
        rects = page.get_image_rects(xref)
        if not rects:
            continue
        rect = rects[0]

        try:
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img_ext = base_image.get("ext", "png").lower()
            if img_ext == "jpeg":
                img_ext = "jpg"

            # Generate a stable filename
            img_filename = f"page{page_idx + 1:03d}_img{img_idx + 1:02d}_xref{xref}.{img_ext}"
            img_path = out_dir / img_filename

            with open(img_path, "wb") as f:
                f.write(img_bytes)

            # Dimensions and phash
            width_px = height_px = 0
            phash = None
            if _PHASH_AVAILABLE:
                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    width_px, height_px = pil_img.size
                    phash = str(imagehash.phash(pil_img))
                except Exception:
                    pass
            if not width_px:
                width_px = int(rect.width)
                height_px = int(rect.height)

            src_url = f"{base_url}/api/v1/images/{session_id}/{img_filename}"

            bbox = {
                "x0": round(rect.x0, 2), "y0": round(rect.y0, 2),
                "x1": round(rect.x1, 2), "y1": round(rect.y1, 2),
            }

            elements.append({
                "id": f"i_{page_idx}_{img_idx:04d}",
                "type": "image",
                "src": src_url,
                "bbox": bbox,
                "width_px": width_px,
                "height_px": height_px,
                "phash": phash,
                "order": img_idx,  # images are low order (painted first as backgrounds)
            })

        except Exception:
            continue

    return elements


# ── Shape / Rect elements ──────────────────────────────────────────────────────

def _extract_shape_elements(page: "fitz.Page", page_idx: int) -> List[Dict]:
    """Extract rectangle/shape drawing elements (backgrounds, separators, borders)."""
    elements = []

    for draw_idx, drawing in enumerate(page.get_drawings()):
        rect = drawing.get("rect")
        if not rect:
            continue

        r = fitz.Rect(rect)
        if r.width < 2 or r.height < 2:
            continue

        fill_color   = _color_to_hex(drawing.get("fill"))
        stroke_color = _color_to_hex(drawing.get("color"))

        # Skip shapes with no visible fill or stroke
        if not fill_color and not stroke_color:
            continue

        bbox = {
            "x0": round(r.x0, 2), "y0": round(r.y0, 2),
            "x1": round(r.x1, 2), "y1": round(r.y1, 2),
        }

        elements.append({
            "id": f"r_{page_idx}_{draw_idx:04d}",
            "type": "rect",
            "bbox": bbox,
            "fill_color": fill_color,
            "stroke_color": stroke_color,
            "stroke_width": round(drawing.get("width", 0) or 0, 1),
            "order": draw_idx,  # shapes are ordered by paint order (very low)
        })

    return elements


# ── Lines / Blocks groupings ───────────────────────────────────────────────────

def _extract_lines_and_blocks(page: "fitz.Page") -> Tuple[List, List]:
    """Return line-level and block-level groupings from the page."""
    raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    lines_out = []
    blocks_out = []

    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue

        block_lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if not line_text:
                continue
            lb = line["bbox"]
            entry = {
                "text": line_text,
                "bbox": {
                    "x0": round(lb[0], 2), "y0": round(lb[1], 2),
                    "x1": round(lb[2], 2), "y1": round(lb[3], 2),
                },
            }
            lines_out.append(entry)
            block_lines.append(entry)

        if block_lines:
            bb = block["bbox"]
            blocks_out.append({
                "text": " ".join(l["text"] for l in block_lines),
                "bbox": {
                    "x0": round(bb[0], 2), "y0": round(bb[1], 2),
                    "x1": round(bb[2], 2), "y1": round(bb[3], 2),
                },
                "lines": block_lines,
            })

    return lines_out, blocks_out


# ── Page render PNG ────────────────────────────────────────────────────────────

def _render_page_png(
    page: "fitz.Page",
    page_idx: int,
    out_dir: Path,
    session_id: str,
    base_url: str,
    dpi: int = 150,
) -> str:
    """Render the page to a PNG file and return its public URL."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    filename = f"page{page_idx + 1:03d}_render.png"
    path = out_dir / filename
    pix.save(str(path))
    return f"{base_url}/api/v1/images/{session_id}/{filename}"


# ── Main function ──────────────────────────────────────────────────────────────

def extract_structured(
    pdf_path: str,
    out_dir: str,
    session_id: str,
    base_url: str,
    render_dpi: int = 150,
    source_filename: Optional[str] = None,
) -> Dict:
    """
    Extract structured element data from a digital PDF.

    Returns a dict matching the extractor_output schema expected by n8n.
    Does NOT generate HTML — all orchestration happens in n8n.

    Args:
        pdf_path:   Path to the PDF file on disk.
        out_dir:    Directory where image files and render PNGs will be saved.
        session_id: Session ID for constructing public URLs.
        base_url:   Base URL of the extractor service (e.g. https://host.com).
        render_dpi: DPI for page render PNGs (default 150).

    Returns:
        extractor_output dict (see schemas/extractor_output.example.json).
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    doc_id = session_id[:8]

    result: Dict = {
        "doc_id": doc_id,
        "source_filename": source_filename or Path(pdf_path).name,
        "extracted_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "pages": [],
    }

    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Extract each element type
        shape_elements = _extract_shape_elements(page, page_idx)
        image_elements = _extract_image_elements(page, doc, page_idx, out_path, session_id, base_url)
        text_elements  = _extract_text_elements(page, page_idx)

        # Merge and sort: shapes first (background), then images, then text (foreground)
        all_elements = shape_elements + image_elements + text_elements
        all_elements.sort(key=lambda e: e["order"])

        # Groupings
        lines, blocks = _extract_lines_and_blocks(page)

        # Page render
        render_png_url = _render_page_png(page, page_idx, out_path, session_id, base_url, render_dpi)

        result["pages"].append({
            "page_index": page_idx,
            "width_pt": round(page.rect.width, 2),
            "height_pt": round(page.rect.height, 2),
            "rotation": page.rotation,
            "elements": all_elements,
            "lines": lines,
            "blocks": blocks,
            "render_png": render_png_url,
        })

    doc.close()
    return result
