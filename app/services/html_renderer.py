from typing import List, Optional


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _escape(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;"))


def _area(bbox: list) -> float:
    return max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))


def _overlaps(a: list, b: list, expand: float = 4.0) -> bool:
    """Check if two bboxes overlap, with optional expansion of b."""
    return not (
        a[2] <= b[0] - expand
        or b[2] + expand <= a[0]
        or a[3] <= b[1] - expand
        or b[3] + expand <= a[1]
    )


def _find_link(bbox: list, links: list) -> Optional[str]:
    """Return the URL of the first link whose bbox overlaps this block."""
    for lnk in links:
        if _overlaps(bbox, lnk["bbox"]):
            return lnk.get("url")
    return None


# ---------------------------------------------------------------------------
# Editable renderer (Modo B: semantic blocks)
# ---------------------------------------------------------------------------

def _split_sections(blocks: list, gap: float = 25.0) -> List[list]:
    """Split sorted blocks into sections separated by vertical gaps."""
    if not blocks:
        return []
    sorted_b = sorted(blocks, key=lambda b: b["bbox"][1])
    sections, current = [], [sorted_b[0]]
    last_bottom = sorted_b[0]["bbox"][3]
    for b in sorted_b[1:]:
        if b["bbox"][1] - last_bottom > gap and current:
            sections.append(current)
            current = []
        current.append(b)
        last_bottom = max(last_bottom, b["bbox"][3])
    if current:
        sections.append(current)
    return sections


def _tag(b: dict) -> str:
    size = b.get("size", 12)
    flags = b.get("flags", 0)
    bold = bool(flags & 0b10000)
    if size >= 22:
        return "h1"
    if size >= 17 or (size >= 14 and bold):
        return "h2"
    if size >= 13:
        return "h3"
    if size <= 9:
        return "legal"
    return "p"


def _detect_column_split(text_blocks: list, page_width: float) -> Optional[float]:
    """
    Detect a single vertical split point for a 2-column layout.
    Uses x0 gap analysis: finds the largest gap between consecutive x0 values
    that falls in the middle 40–75% of the page width.
    Both resulting columns must contain at least 2 blocks.
    Returns the split x coordinate, or None if no valid split found.
    """
    if len(text_blocks) < 4:
        return None

    x0_vals = sorted(b["bbox"][0] for b in text_blocks)

    best_gap = 0.0
    best_split: Optional[float] = None
    for i in range(1, len(x0_vals)):
        gap = x0_vals[i] - x0_vals[i - 1]
        split = (x0_vals[i] + x0_vals[i - 1]) / 2.0
        # Split must be in the middle zone (not near edges)
        if gap > best_gap and page_width * 0.25 < split < page_width * 0.80:
            # Both sides must have at least 2 blocks
            left = sum(1 for b in text_blocks if b["bbox"][0] < split)
            right = sum(1 for b in text_blocks if b["bbox"][0] >= split)
            if left >= 2 and right >= 2:
                best_gap = gap
                best_split = split

    # Only use the split if the gap is meaningful (>10% of page width)
    if best_gap > page_width * 0.10:
        return best_split
    return None


def _text_html(b: dict, links: list) -> str:
    kind = _tag(b)
    text = _escape(b.get("text", ""))
    color = b.get("color", "#000000")
    style = f' style="color:{color}"' if color and color not in ("#000000", "#000") else ""

    href = _find_link(b["bbox"], links)
    inner = f'<a href="{_escape(href)}" target="_blank">{text}</a>' if href else text

    if kind == "h1":
        return f'<h1 contenteditable="true"{style}>{inner}</h1>\n'
    if kind == "h2":
        return f'<h2 contenteditable="true"{style}>{inner}</h2>\n'
    if kind == "h3":
        return f'<h3 contenteditable="true"{style}>{inner}</h3>\n'
    if kind == "legal":
        return f'<p class="legal" contenteditable="true"{style}>{inner}</p>\n'
    return f'<p contenteditable="true"{style}>{inner}</p>\n'


def _section_html(blocks: list, page_width: float, assets_base_url: str) -> str:
    images = [b for b in blocks if b["type"] == "image"]
    texts = sorted([b for b in blocks if b["type"] == "text"], key=lambda b: b["bbox"][1])
    links = [b for b in blocks if b["type"] == "link"]

    html = '<section class="sec">\n'

    # Hero image: largest image (only if big enough)
    hero = None
    if images:
        biggest = max(images, key=lambda b: _area(b["bbox"]))
        if _area(biggest["bbox"]) > 8000:
            hero = biggest
            src = assets_base_url + biggest["src"]
            html += f'<div class="hero"><img src="{_escape(src)}" alt="" /></div>\n'

    # Column detection using x0 clustering
    split_x = _detect_column_split(texts, page_width) if texts else None

    if split_x is not None:
        left_col = sorted([b for b in texts if b["bbox"][0] < split_x], key=lambda b: b["bbox"][1])
        right_col = sorted([b for b in texts if b["bbox"][0] >= split_x], key=lambda b: b["bbox"][1])
        html += '<div class="cols">\n<div class="col">\n'
        for t in left_col:
            html += _text_html(t, links)
        html += '</div>\n<div class="col">\n'
        for t in right_col:
            html += _text_html(t, links)
        html += '</div>\n</div>\n'
    else:
        for t in texts:
            html += _text_html(t, links)

    # Non-hero images inline
    for img in images:
        if img is hero:
            continue
        src = assets_base_url + img["src"]
        html += f'<div class="img-block"><img src="{_escape(src)}" alt="" /></div>\n'

    html += '</section>\n'
    return html


_EDITABLE_CSS = """
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; background: #e5e7eb; font-family: system-ui, Segoe UI, Roboto, Arial, sans-serif; }
  .wrap { max-width: 940px; margin: 0 auto; padding: 20px; }
  .page { background: #fff; padding: 28px 36px; margin-bottom: 24px; box-shadow: 0 2px 24px rgba(0,0,0,.10); border-radius: 4px; }
  .sec { padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
  .sec:last-child { border-bottom: none; }
  .hero img { width: 100%; height: auto; display: block; border-radius: 6px; margin-bottom: 14px; }
  .img-block img { max-width: 100%; height: auto; display: block; margin: 8px 0; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  h1 { font-size: 28px; line-height: 1.15; margin: 12px 0 8px; }
  h2 { font-size: 20px; line-height: 1.25; margin: 10px 0 6px; }
  h3 { font-size: 16px; line-height: 1.3; margin: 8px 0 4px; font-weight: 600; }
  p { font-size: 14px; line-height: 1.65; margin: 5px 0; }
  .legal { font-size: 10px; opacity: .72; line-height: 1.4; }
  a { color: inherit; text-decoration: underline; }
  [contenteditable="true"] { outline: none; border-radius: 3px; padding: 1px 2px; }
  [contenteditable="true"]:focus { box-shadow: 0 0 0 2px rgba(59,130,246,.45); background: rgba(59,130,246,.04); }
"""


def render_html(layout: dict, assets_base_url: str = "") -> str:
    """
    Generate a semantic, editable HTML page (Modo B).
    Uses section/heading/paragraph blocks — easier to edit, not pixel-perfect.
    """
    body = ""
    for page in layout.get("pages", []):
        page_width = page.get("width", 595.0)
        sections = _split_sections(page.get("blocks", []))
        body += f'<div class="page" data-page="{page["page"]}">\n'
        for sec in sections:
            body += _section_html(sec, page_width, assets_base_url)
        body += '</div>\n'

    return (
        '<!doctype html>\n<html lang="es">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '<title>PDF \u2192 HTML (editable)</title>\n'
        f'<style>\n{_EDITABLE_CSS}</style>\n'
        '</head>\n<body>\n  <div class="wrap">\n'
        f'{body}'
        '  </div>\n</body>\n</html>\n'
    )


# ---------------------------------------------------------------------------
# Pixel-perfect renderer (Modo A: absolute positioning)
# ---------------------------------------------------------------------------

_EXACT_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #e5e7eb; }
  .wrap { display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 20px; }
  .page { position: relative; background: #fff; box-shadow: 0 2px 24px rgba(0,0,0,.10); overflow: hidden; }
  .t { position: absolute; white-space: pre-wrap; word-break: break-word; line-height: 1.2; outline: none; cursor: text; }
  .t:focus { box-shadow: 0 0 0 2px rgba(59,130,246,.5); background: rgba(59,130,246,.04); border-radius: 2px; }
  .i { position: absolute; object-fit: contain; }
  .hot { position: absolute; display: block; }
"""


def render_html_exact(layout: dict, assets_base_url: str = "") -> str:
    """
    Generate a pixel-perfect HTML page (Modo A).
    Every element is absolutely positioned using its bbox from the PDF.
    Images use public URLs. Text blocks are contenteditable.
    Links are transparent overlays (<a> tags) placed over their bbox.
    """
    pages_html = ""

    for page in layout.get("pages", []):
        w = page.get("width", 595.0)
        h = page.get("height", 842.0)
        blocks = page.get("blocks", [])

        page_html = (
            f'<div class="page" data-page="{page["page"]}" '
            f'style="width:{w:.1f}px;height:{h:.1f}px;">\n'
        )

        # Render images first (background layer), then text, then link overlays
        for layer in ("image", "text", "link"):
            for b in blocks:
                if b["type"] != layer:
                    continue
                x0, y0, x1, y1 = b["bbox"]
                bw = max(1.0, x1 - x0)
                bh = max(1.0, y1 - y0)
                pos = f"left:{x0:.1f}px;top:{y0:.1f}px;width:{bw:.1f}px;"

                if layer == "text":
                    size = b.get("size", 12.0)
                    color = b.get("color", "#000000")
                    flags = b.get("flags", 0)
                    bold = "bold" if (flags & 0b10000) else "normal"
                    italic = "italic" if (flags & 0b1) else "normal"
                    style = (
                        f"{pos}min-height:{bh:.1f}px;"
                        f"font-size:{size:.1f}px;color:{color};"
                        f"font-weight:{bold};font-style:{italic};"
                    )
                    text = _escape(b.get("text", ""))
                    # Wrap in <a> if a link overlaps this text block
                    href = _find_link(b["bbox"], [x for x in blocks if x["type"] == "link"])
                    if href:
                        inner = f'<a href="{_escape(href)}" target="_blank">{text}</a>'
                    else:
                        inner = text
                    page_html += f'<div class="t" contenteditable="true" style="{style}">{inner}</div>\n'

                elif layer == "image":
                    src = assets_base_url + b["src"]
                    style = f"{pos}height:{bh:.1f}px;"
                    page_html += f'<img class="i" src="{_escape(src)}" style="{style}" alt="" />\n'

                elif layer == "link":
                    style = f"{pos}height:{bh:.1f}px;z-index:10;"
                    page_html += (
                        f'<a class="hot" href="{_escape(b["url"])}" '
                        f'target="_blank" style="{style}" '
                        f'title="{_escape(b["url"])}"></a>\n'
                    )

        page_html += '</div>\n'
        pages_html += page_html

    return (
        '<!doctype html>\n<html lang="es">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '<title>PDF \u2192 HTML (pixel-perfect)</title>\n'
        f'<style>\n{_EXACT_CSS}</style>\n'
        '</head>\n<body>\n  <div class="wrap">\n'
        f'{pages_html}'
        '  </div>\n</body>\n</html>\n'
    )
