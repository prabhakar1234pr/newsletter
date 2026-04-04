"""Step 5: Render newsletter HTML from content + image URLs via Jinja2.

Produces email-safe HTML and a plain text fallback.

Usage:
    uv run python tools/render_html.py --content .tmp/newsletter_content.json --images .tmp/image_urls.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_CONTENT = PROJECT_ROOT / ".tmp" / "newsletter_content.json"
DEFAULT_IMAGES = PROJECT_ROOT / ".tmp" / "image_urls.json"
DEFAULT_HTML_OUTPUT = PROJECT_ROOT / ".tmp" / "newsletter.html"
DEFAULT_TEXT_OUTPUT = PROJECT_ROOT / ".tmp" / "newsletter.txt"


def build_template_context(content: dict, images: dict) -> dict:
    """Build the Jinja2 template context from content and image URLs."""
    # Map image URLs by filename pattern
    image_map = {}
    for upload in images.get("uploads", []):
        local = upload.get("local_path", "")
        url = upload.get("gcs_url", "")
        if "infographic" in local:
            image_map["infographic"] = url
        elif "chart" in local:
            image_map["chart"] = url

    # Get logo URL from GCS
    bucket_name = os.getenv("GCS_BUCKET_NAME", "newsletter-images")
    logo_url = f"https://storage.googleapis.com/{bucket_name}/brand/logo.png"

    return {
        "headline": content.get("headline", "Newsletter"),
        "subtitle": content.get("subtitle", ""),
        "summary": content.get("summary", ""),
        "sections": content.get("sections", []),
        "chart_url": image_map.get("chart"),
        "chart_title": content.get("chart_data", {}).get("title", "Chart") if content.get("chart_data") else "",
        "infographic_url": image_map.get("infographic"),
        "cta": content.get("cta"),
        "sources": content.get("sources", []),
        "logo_url": logo_url,
        "date": datetime.now().strftime("%B %d, %Y"),
    }


def html_to_plain_text(html: str) -> str:
    """Strip HTML tags to produce a plain text version."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</h[1-6]>", "\n\n", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&bull;", "•", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Render newsletter HTML via Jinja2")
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT, help="Content JSON path")
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES, help="Image URLs JSON path")
    parser.add_argument("--template", default="newsletter.html.j2", help="Template filename")
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML_OUTPUT, help="HTML output path")
    parser.add_argument("--text-output", type=Path, default=DEFAULT_TEXT_OUTPUT, help="Plain text output path")
    args = parser.parse_args()

    if not args.content.exists():
        print(f"ERROR: Content file not found: {args.content}", file=sys.stderr)
        sys.exit(1)

    content = json.loads(args.content.read_text(encoding="utf-8"))

    # Images file is optional — newsletter works without images
    images = {}
    if args.images.exists():
        images = json.loads(args.images.read_text(encoding="utf-8"))

    # Render template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template(args.template)

    context = build_template_context(content, images)
    html = template.render(**context)

    # Write HTML
    args.html_output.parent.mkdir(parents=True, exist_ok=True)
    args.html_output.write_text(html, encoding="utf-8")
    print(f"HTML written to {args.html_output}", file=sys.stderr)

    # Write plain text fallback
    plain_text = html_to_plain_text(html)
    args.text_output.write_text(plain_text, encoding="utf-8")
    print(f"Plain text written to {args.text_output}", file=sys.stderr)

    print(str(args.html_output))


if __name__ == "__main__":
    main()
