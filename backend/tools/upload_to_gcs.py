"""Step 4: Upload images to Google Cloud Storage.

Uploads PNG files from .tmp/ to the newsletter GCS bucket and returns public URLs.

Usage:
    uv run python tools/upload_to_gcs.py --files .tmp/chart_001.png,.tmp/infographic_001.png
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / ".tmp" / "image_urls.json"


def upload_files(file_paths: list[str], bucket_name: str,
                 user_id: str = "shared") -> list[dict]:
    """Upload files to GCS and return public URLs.

    Args:
        file_paths: List of local file paths to upload.
        bucket_name: GCS bucket name.
        user_id: User ID — used to namespace GCS paths per subscriber.

    Returns:
        List of dicts with local_path, gcs_url, and blob_name.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    date_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uploads = []

    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            print(f"WARNING: File not found, skipping: {path}", file=sys.stderr)
            continue

        # Per-user, date-stamped path to avoid collisions across editions
        blob_name = f"editions/{user_id}/{date_stamp}/{path.name}"
        blob = bucket.blob(blob_name)

        content_type = (
            "image/png" if path.suffix == ".png"
            else "text/html; charset=utf-8" if path.suffix == ".html"
            else "text/plain; charset=utf-8" if path.suffix == ".txt"
            else "application/octet-stream"
        )

        print(f"Uploading {path.name} → gs://{bucket_name}/{blob_name}", file=sys.stderr)
        blob.upload_from_filename(str(path), content_type=content_type)
        blob.cache_control = "public, max-age=86400"
        blob.patch()

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

        uploads.append({
            "local_path": str(path),
            "blob_name": blob_name,
            "gcs_url": public_url,
        })

        print(f"  → {public_url}", file=sys.stderr)

    return uploads


def download_public_gcs_url(gcs_url: str, dest: Path) -> None:
    """Download a publicly readable object URL to a local path."""
    prefix = "https://storage.googleapis.com/"
    if not gcs_url.startswith(prefix):
        raise ValueError(f"Unexpected GCS URL (expected {prefix}...): {gcs_url[:60]}...")
    rest = gcs_url[len(prefix) :]
    bucket_name, _, blob_path = rest.partition("/")
    if not bucket_name or not blob_path:
        raise ValueError(f"Could not parse bucket/path from URL: {gcs_url[:80]}...")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(dest))
    print(f"Downloaded gs://{bucket_name}/{blob_path} → {dest}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Upload images to GCS")
    parser.add_argument("--files", required=True, help="Comma-separated file paths to upload")
    parser.add_argument("--bucket", default=None, help="GCS bucket name (defaults to GCS_BUCKET_NAME env)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    bucket_name = args.bucket or os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        print("ERROR: No bucket name. Set --bucket or GCS_BUCKET_NAME in .env", file=sys.stderr)
        sys.exit(1)

    file_paths = [f.strip() for f in args.files.split(",") if f.strip()]
    if not file_paths:
        print("No files to upload.", file=sys.stderr)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"uploads": []}, indent=2))
        print(str(args.output))
        sys.exit(0)

    uploads = upload_files(file_paths, bucket_name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"uploads": uploads}, indent=2, ensure_ascii=False),
                           encoding="utf-8")

    print(f"\nOutput written to {args.output}", file=sys.stderr)
    print(str(args.output))


if __name__ == "__main__":
    main()
