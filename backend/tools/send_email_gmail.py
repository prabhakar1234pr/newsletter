"""Step 6: Send newsletter email via Gmail SMTP + App Password.

No OAuth, no domain needed. Works for any recipient.

Required env vars:
    GMAIL_USER          your Gmail address (e.g. you@gmail.com)
    GMAIL_APP_PASSWORD  16-char app password from myaccount.google.com/apppasswords

Usage:
    uv run python tools/send_email_gmail.py \
        --html .tmp/newsletter.html \
        --text .tmp/newsletter.txt \
        --to recipient@example.com \
        --subject "Your AI Newsletter"
"""

import argparse
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(
    html_path: Path,
    text_path: Path,
    recipients: list[str],
    subject: str,
) -> str:
    """Send newsletter via Gmail SMTP.

    Returns:
        Comma-separated recipient list on success.

    Raises:
        SystemExit on failure.
    """
    gmail_user = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not app_password:
        print("ERROR: GMAIL_USER and GMAIL_APP_PASSWORD must be set in .env", file=sys.stderr)
        sys.exit(1)

    html_content = html_path.read_text(encoding="utf-8")
    text_content = text_path.read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AI Newsletter <{gmail_user}>"
    msg["To"]      = ", ".join(recipients)
    msg["List-Unsubscribe"] = f"<mailto:{gmail_user}?subject=unsubscribe>"

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html",  "utf-8"))

    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...", file=sys.stderr)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_user, app_password)
            server.sendmail(gmail_user, recipients, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: SMTP send failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Email sent to {recipients}", file=sys.stderr)
    return ",".join(recipients)


def main():
    parser = argparse.ArgumentParser(description="Send newsletter via Gmail SMTP")
    parser.add_argument("--html",    type=Path, required=True)
    parser.add_argument("--text",    type=Path, required=True)
    parser.add_argument("--to",      required=True, help="Recipient(s), comma-separated")
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()

    recipients = [r.strip() for r in args.to.split(",") if r.strip()]

    for p in [args.html, args.text]:
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    result = send_email(args.html, args.text, recipients, args.subject)
    print(result)


if __name__ == "__main__":
    main()
