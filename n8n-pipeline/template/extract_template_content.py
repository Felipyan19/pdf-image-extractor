#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def is_likely_image_url(value: str) -> bool:
    if not value:
        return False
    url = value.strip()
    if not url:
        return False
    if re.match(r"^data:image/", url, re.IGNORECASE):
        return True
    return bool(
        re.search(r"\.(png|jpe?g|gif|webp|svg|bmp|avif)([?#].*)?$", url, re.IGNORECASE)
    )


def replace_image_urls(html: str, data: dict, images: dict) -> str:
    image_map = {}
    image_idx = 1

    def get_or_create_key(value: str) -> str:
        nonlocal image_idx
        if value in image_map:
            return image_map[value]
        key = f"image_{image_idx:04d}"
        image_idx += 1
        image_map[value] = key
        images[key] = value
        data[key] = value
        return key

    def repl_attr(match: re.Match) -> str:
        attr = match.group(1)
        quoted = match.group(2)
        value = match.group(3) if match.group(3) is not None else match.group(4)
        if not is_likely_image_url(value):
            return match.group(0)
        key = get_or_create_key(value)
        quote = quoted[0]
        return f"{attr}={quote}{{{{{key}}}}}{quote}"

    out = re.sub(
        r"\b(src|background)\s*=\s*(\"([^\"]*)\"|'([^']*)')",
        repl_attr,
        html,
        flags=re.IGNORECASE,
    )

    def repl_url(match: re.Match) -> str:
        quote = match.group(1)
        value = match.group(2)
        if not is_likely_image_url(value):
            return match.group(0)
        key = get_or_create_key(value)
        token = f"{{{{{key}}}}}"
        if quote:
            return f"url({quote}{token}{quote})"
        return f"url({token})"

    out = re.sub(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", repl_url, out, flags=re.IGNORECASE)
    return out


def tokenize_text_nodes(html: str, data: dict, texts: dict) -> str:
    out = []
    i = 0
    in_style = False
    in_script = False
    text_idx = 1

    while i < len(html):
        ch = html[i]

        if ch == "<":
            if html.startswith("<!--", i):
                end_comment = html.find("-->", i + 4)
                if end_comment == -1:
                    out.append(html[i:])
                    break
                out.append(html[i : end_comment + 3])
                i = end_comment + 3
                continue

            end_tag = html.find(">", i + 1)
            if end_tag == -1:
                out.append(html[i:])
                break

            tag_chunk = html[i : end_tag + 1]
            out.append(tag_chunk)

            tag_match = re.match(r"<\s*(/?)\s*([a-zA-Z0-9:-]+)", tag_chunk)
            if tag_match:
                is_closing = tag_match.group(1) == "/"
                tag_name = tag_match.group(2).lower()
                if tag_name == "style":
                    in_style = not is_closing
                if tag_name == "script":
                    in_script = not is_closing

            i = end_tag + 1
            continue

        next_tag = html.find("<", i)
        end = len(html) if next_tag == -1 else next_tag
        text_chunk = html[i:end]

        should_tokenize = (
            not in_style
            and not in_script
            and text_chunk.strip() != ""
            and "{{" not in text_chunk
            and "}}" not in text_chunk
        )

        if should_tokenize:
            key = f"text_{text_idx:04d}"
            text_idx += 1
            texts[key] = text_chunk
            data[key] = text_chunk
            out.append(f"{{{{{key}}}}}")
        else:
            out.append(text_chunk)

        i = end

    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract texts + images from HTML into external JSON and generate placeholder template."
    )
    parser.add_argument("--input", required=True, help="Input HTML template path")
    parser.add_argument("--output-template", required=True, help="Output template with placeholders")
    parser.add_argument("--output-json", required=True, help="Output JSON with extracted values")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    out_template_path = Path(args.output_template).resolve()
    out_json_path = Path(args.output_json).resolve()

    raw_html = input_path.read_text(encoding="utf-8")

    data = {}
    texts = {}
    images = {}

    image_tokenized = replace_image_urls(raw_html, data, images)
    tokenized_template = tokenize_text_nodes(image_tokenized, data, texts)

    payload = {
        "meta": {
            "source_template": input_path.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "texts": len(texts),
                "images": len(images),
                "total_slots": len(data),
            },
        },
        "data": data,
        "texts": texts,
        "images": images,
    }

    out_template_path.write_text(tokenized_template, encoding="utf-8")
    out_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Generated template: {out_template_path}")
    print(f"Generated JSON: {out_json_path}")
    print(
        f"Slots: {payload['meta']['counts']['total_slots']} "
        f"(texts={payload['meta']['counts']['texts']}, images={payload['meta']['counts']['images']})"
    )


if __name__ == "__main__":
    main()
