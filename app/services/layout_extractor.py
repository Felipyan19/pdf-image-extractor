import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List


def _hex_color(c: int) -> str:
    """Convert PyMuPDF color integer to hex string."""
    try:
        return f"#{int(c):06x}"
    except (TypeError, ValueError):
        return "#000000"


def _merge_spans_to_blocks(raw_blocks: list) -> list:
    """
    Merge raw PyMuPDF text spans into logical text blocks (lines then paragraphs).
    Each line merges all spans with similar y-coordinate.
    Adjacent lines with same font/size and small vertical gap merge into paragraphs.
    """
    # Step 1: Merge spans on the same line
    lines = []
    for b in raw_blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            line_spans = []
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                line_spans.append({
                    "text": text,
                    "bbox": list(span["bbox"]),
                    "font": span.get("font", ""),
                    "size": span.get("size", 12),
                    "color": _hex_color(span.get("color", 0)),
                    "flags": span.get("flags", 0),
                })
            if not line_spans:
                continue
            merged_text = " ".join(s["text"] for s in line_spans)
            x0 = min(s["bbox"][0] for s in line_spans)
            y0 = min(s["bbox"][1] for s in line_spans)
            x1 = max(s["bbox"][2] for s in line_spans)
            y1 = max(s["bbox"][3] for s in line_spans)
            dominant = max(line_spans, key=lambda s: s["size"])
            lines.append({
                "type": "text",
                "bbox": [x0, y0, x1, y1],
                "text": merged_text,
                "font": dominant["font"],
                "size": dominant["size"],
                "color": dominant["color"],
                "flags": dominant["flags"],
            })

    if not lines:
        return []

    # Step 2: Merge adjacent lines into paragraphs.
    # Gap threshold is relative to font size so small legal text (8pt) and
    # body text (12pt) both merge correctly without merging across sections.
    paragraphs = []
    current = dict(lines[0])

    for line in lines[1:]:
        prev_bottom = current["bbox"][3]
        curr_top = line["bbox"][1]
        gap = curr_top - prev_bottom
        avg_size = (current["size"] + line["size"]) / 2
        # Allow up to 60% of font size as inter-line gap (covers normal 1.2–1.5 leading)
        merge_gap = avg_size * 0.6
        same_size = abs(line["size"] - current["size"]) < 3
        # Allow x0 drift up to 40% of page-level indentation (handles justified text)
        similar_x = abs(line["bbox"][0] - current["bbox"][0]) < 50

        if gap <= merge_gap and same_size and similar_x:
            current["text"] = current["text"] + " " + line["text"]
            current["bbox"][2] = max(current["bbox"][2], line["bbox"][2])
            current["bbox"][3] = line["bbox"][3]
        else:
            paragraphs.append(current)
            current = dict(line)

    paragraphs.append(current)
    return paragraphs


def extract_layout(pdf_path: str, out_dir: str) -> Dict:
    """
    Extract full layout from a digital PDF (text-selectable).
    Extracts: text blocks (with font/size/color), embedded images, hyperlinks.
    Images are saved as PNG files directly in out_dir.

    Args:
        pdf_path: Path to the PDF file
        out_dir: Directory where image files will be saved

    Returns:
        Layout dict:
        {
            "pages": [
                {
                    "page": int,
                    "width": float,
                    "height": float,
                    "blocks": [
                        {"type":"text", "bbox":[x0,y0,x1,y1], "text":"...", "font":"...", "size":12, "color":"#000000", "flags":0},
                        {"type":"image", "bbox":[...], "src":"page001_img12.png"},
                        {"type":"link", "bbox":[...], "url":"https://..."}
                    ]
                }
            ],
            "image_files": ["page001_img12.png", ...]
        }
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    result: Dict = {"pages": [], "image_files": []}

    try:
        for pno in range(doc.page_count):
            page = doc.load_page(pno)
            w, h = page.rect.width, page.rect.height
            page_dict = page.get_text("dict")

            blocks_out: List[dict] = []

            # Text: merge spans → lines → paragraphs
            text_blocks = _merge_spans_to_blocks(page_dict.get("blocks", []))
            blocks_out.extend(text_blocks)

            # Images: use get_images(full=True) — more reliable than type-1 dict blocks
            # (many PDFs have type-1 blocks with xref=None which can't be extracted)
            seen_xrefs: set = set()
            for img in page.get_images(full=True):
                xref = img[0]
                if not xref or xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    bbox = page.get_image_bbox(img)
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK → RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_name = f"page{pno + 1:03d}_img{xref}.png"
                    pix.save(str(out_dir / img_name))
                    result["image_files"].append(img_name)
                    blocks_out.append({
                        "type": "image",
                        "bbox": [bbox.x0, bbox.y0, bbox.x1, bbox.y1] if bbox else [0.0, 0.0, w, h],
                        "src": img_name,
                    })
                except Exception:
                    pass

            # Links
            for link in page.get_links():
                uri = link.get("uri")
                rect = link.get("from")
                if uri and rect:
                    blocks_out.append({
                        "type": "link",
                        "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                        "url": uri,
                    })

            # Sort by reading order (top → bottom)
            blocks_out.sort(key=lambda b: b["bbox"][1])

            result["pages"].append({
                "page": pno + 1,
                "width": w,
                "height": h,
                "blocks": blocks_out,
            })
    finally:
        doc.close()

    return result
