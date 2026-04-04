"""Step 6: Send newsletter email via Resend API.

Replaces the Gmail OAuth approach with a simple API key call.
Reads RESEND_API_KEY from .env.

Usage:
    uv run python tools/send_email_resend.py \
        --html .tmp/newsletter.html \
        --text .tmp/newsletter.txt \
        --to recipient@example.com \
        --subject "Your AI Newsletter — April 2, 2026"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_FROM = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")


def send_email(
    html_path: Path,
    text_path: Path,
    recipients: list[str],
    subject: str,
) -> str:
    """Send a newsletter email via Resend.

    Args:
        html_path: Path to rendered HTML file.
        text_path: Path to plain-text fallback file.
        recipients: List of recipient email addresses.
        subject: Email subject line.

    Returns:
        Resend message ID on success.

    Raises:
        SystemExit on failure.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("ERROR: RESEND_API_KEY not set in environment", file=sys.stderr)
        sys.exit(1)

    html_content = html_path.read_text(encoding="utf-8")
    text_content = text_path.read_text(encoding="utf-8")

    payload = {
        "from": RESEND_FROM,
        "to": recipients,
        "subject": subject,
        "html": html_content,
        "text": text_content,
        "headers": {
            # CAN-SPAM / GDPR compliance headers
            "List-Unsubscribe": f"<mailto:unsubscribe@resend.dev?subject=unsubscribe>",
            "X-Entity-Ref-ID": subject,
        },
    }

    print(f"Sending to {recipients} via Resend...", file=sys.stderr)

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"ERROR: Resend API returned {e.response.status_code}: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Email send failed: {e}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    message_id = data.get("id", "unknown")
    print(f"Email sent successfully. Message ID: {message_id}", file=sys.stderr)
    return message_id


def main():
    parser = argparse.ArgumentParser(description="Send newsletter via Resend")
    parser.add_argument("--html", type=Path, required=True, help="Path to HTML file")
    parser.add_argument("--text", type=Path, required=True, help="Path to plain-text file")
    parser.add_argument("--to", required=True, help="Recipient email (comma-separated for multiple)")
    parser.add_argument("--subject", required=True, help="Email subject line")
    args = parser.parse_args()

    recipients = [r.strip() for r in args.to.split(",") if r.strip()]

    if not args.html.exists():
        print(f"ERROR: HTML file not found: {args.html}", file=sys.stderr)
        sys.exit(1)
    if not args.text.exists():
        print(f"ERROR: Text file not found: {args.text}", file=sys.stderr)
        sys.exit(1)

    message_id = send_email(args.html, args.text, recipients, args.subject)
    print(message_id)


if __name__ == "__main__":
    main()
