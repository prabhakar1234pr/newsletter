"""Step 3a: Visual infographic generation via Nano Banana Pro.

Uses Gemini 3 Pro Image (Nano Banana Pro) to generate a styled infographic
from a text prompt produced by the synthesis step.

Usage:
    uv run python tools/generate_infographic.py --input .tmp/newsletter_content.json
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / ".tmp" / "newsletter_content.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp"


def generate_infographic(prompt: str, output_path: Path):
    """Generate an infographic using Nano Banana Pro.

    Args:
        prompt: Detailed description of the infographic to generate.
        output_path: Where to save the PNG.
    """
    client = genai.Client()

    # Wrap the prompt with brand style instructions
    full_prompt = (
        f"Create a professional infographic for a newsletter. "
        f"Style: modern, clean, minimal. White background. "
        f"Use these brand colors: Primary Blue #2F94FB, Deep Blue #2367D3, "
        f"Indigo #4B3FE0, Purple #8331A6. "
        f"Use clean sans-serif typography. "
        f"The infographic should be vertical, suitable for embedding in an email.\n\n"
        f"{prompt}"
    )

    print("Generating infographic via Nano Banana Pro...", file=sys.stderr)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Extract the generated image from response parts
    saved = False
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_data = part.inline_data.data
                output_path.write_bytes(image_data)
                saved = True
                break

    if not saved:
        print("ERROR: No image was generated in the response", file=sys.stderr)
        if hasattr(response, "text") and response.text:
            print(f"Model response text: {response.text[:200]}", file=sys.stderr)
        sys.exit(1)

    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"Infographic saved to {output_path} ({output_path.stat().st_size} bytes)",
              file=sys.stderr)
    else:
        print("ERROR: Output file is empty", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate infographic via Nano Banana Pro")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Content JSON path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    content = json.loads(args.input.read_text(encoding="utf-8"))
    infographic_prompt = content.get("infographic_prompt")

    if not infographic_prompt:
        print("No infographic_prompt in content, skipping.", file=sys.stderr)
        sys.exit(0)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "infographic_001.png"

    generate_infographic(infographic_prompt, output_path)
    print(str(output_path))


if __name__ == "__main__":
    main()
