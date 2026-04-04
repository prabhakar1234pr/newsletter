"""Newsletter pipeline orchestrator.

Runs the full 6-step pipeline for a given subscription, loading all parameters
from Firestore. Called by the Cloud Run Job scheduler, or directly for testing.

Usage (by subscription ID from Firestore):
    uv run python backend/main.py --subscription-id <id>

Usage (direct CLI for local testing, bypasses Firestore):
    uv run python backend/main.py \
        --topic "Telugu cinema" \
        --to your@email.com \
        --user-id test_user_001
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Add backend/ to path so tools/ imports work regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv()

from tools import (
    generate_chart,
    generate_infographic,
    render_html,
    research_topic,
    send_email_gmail,
    synthesize_content,
    upload_to_gcs,
)
from tools.upload_to_gcs import download_public_gcs_url
from tools.firestore_client import (
    create_edition,
    create_edition_pending,
    finalize_edition_sent,
    get_active_prompt,
    get_pending_edition_for_send,
    get_subscription,
    get_user,
    has_pending_for_scheduled_send,
    local_delivery_to_utc_datetime,
    mark_edition_failed,
)

GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "ai-newsletter-images-2026")


def build_research_query(topic: str, sub_genre: str | None) -> str:
    """Construct the Firecrawl-replacement query string."""
    if sub_genre:
        return f"{topic} {sub_genre} news last 24 hours"
    return f"{topic} news last 24 hours"


def run_pipeline(
    topic: str,
    sub_genre: str | None,
    recipient_email: str,
    user_id: str,
    subscription_id: str,
    tone: str = "professional but approachable",
    audience: str = "general professionals",
    *,
    defer_email: bool = False,
    delivery_timezone: str | None = None,
    delivery_hour: int | None = None,
    delivery_minute: int | None = None,
) -> str | None:
    """Execute the newsletter pipeline (steps 1–6, or 1–5 + pending edition if defer_email).

    When defer_email is True, HTML/text are uploaded to GCS and a pending edition is
    created; Gmail is sent later at the scheduled minute by send_scheduled_edition.

    Returns:
        The Firestore edition doc ID on success, or None if prepare was skipped (duplicate).

    Raises:
        SystemExit on unrecoverable failure.
    """
    research_query = build_research_query(topic, sub_genre)
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Pipeline starting", file=sys.stderr)
    print(f"  Subscription: {subscription_id}", file=sys.stderr)
    print(f"  User: {user_id}", file=sys.stderr)
    print(f"  Query: {research_query}", file=sys.stderr)
    print(f"  Recipient: {recipient_email}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Use a per-subscription temp directory to avoid file collisions
    # when multiple pipelines run in parallel
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"newsletter_{subscription_id[:8]}_"))

    research_output = tmp_dir / "research_raw.json"
    content_output = tmp_dir / "newsletter_content.json"
    infographic_output = tmp_dir / "infographic_001.png"
    chart_output = tmp_dir / "chart_001.png"
    image_urls_output = tmp_dir / "image_urls.json"
    html_output = tmp_dir / "newsletter.html"
    text_output = tmp_dir / "newsletter.txt"

    edition_id = None

    if defer_email:
        if not delivery_timezone or delivery_hour is None or delivery_minute is None:
            raise ValueError("defer_email requires delivery_timezone, delivery_hour, delivery_minute")
        scheduled_send_utc = local_delivery_to_utc_datetime(
            delivery_hour, delivery_minute, delivery_timezone
        )
        if has_pending_for_scheduled_send(subscription_id, scheduled_send_utc):
            print(
                "Prepare skipped: pending edition already exists for this send slot",
                file=sys.stderr,
            )
            return None

    try:
        # ── Step 1: Research ──────────────────────────────────────────
        print("Step 1/6: Researching...", file=sys.stderr)
        research_data = research_topic.research(topic, num_results=5, sub_genre=sub_genre)
        research_output.write_text(
            json.dumps(research_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  ✓ {len(research_data['sources'])} sources collected", file=sys.stderr)

        # ── Step 2: Synthesize ────────────────────────────────────────
        print("Step 2/6: Synthesizing content...", file=sys.stderr)
        active_prompt = get_active_prompt()
        content = synthesize_content.synthesize(
            research_data, tone, audience, system_prompt=active_prompt
        )
        content_output.write_text(
            json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  ✓ Headline: {content.get('headline', '')[:60]}", file=sys.stderr)

        # ── Step 3a: Generate infographic ─────────────────────────────
        print("Step 3a/6: Generating infographic...", file=sys.stderr)
        infographic_prompt = content.get("infographic_prompt")
        if infographic_prompt:
            generate_infographic.generate_infographic(
                prompt=infographic_prompt,
                output_path=infographic_output,
            )
            print("  ✓ Infographic generated", file=sys.stderr)
        else:
            print("  SKIP: No infographic prompt in content", file=sys.stderr)

        # ── Step 3b: Generate chart ───────────────────────────────────
        print("Step 3b/6: Generating chart...", file=sys.stderr)
        chart_data = content.get("chart_data")
        if chart_data:
            generate_chart.apply_brand_style()
            chart_type = chart_data.get("type", "bar").lower()
            generator_fn = generate_chart.CHART_GENERATORS.get(chart_type,
                                                                 generate_chart.CHART_GENERATORS["bar"])
            generator_fn(chart_data, chart_output)
            print("  ✓ Chart generated", file=sys.stderr)
        else:
            print("  SKIP: No chart data in content", file=sys.stderr)

        # ── Step 4: Upload images ─────────────────────────────────────
        print("Step 4/6: Uploading images to GCS...", file=sys.stderr)
        image_files = [
            str(p) for p in [infographic_output, chart_output] if p.exists()
        ]
        if image_files:
            uploads = upload_to_gcs.upload_files(image_files, GCS_BUCKET, user_id=user_id)
            image_urls_output.write_text(
                json.dumps({"uploads": uploads}, indent=2), encoding="utf-8"
            )
            print(f"  ✓ {len(uploads)} images uploaded", file=sys.stderr)
        else:
            image_urls_output.write_text(json.dumps({"uploads": []}), encoding="utf-8")
            print("  SKIP: No images to upload", file=sys.stderr)

        image_urls_data = json.loads(image_urls_output.read_text(encoding="utf-8"))
        html_gcs_url = ""  # filled after HTML render + upload below

        # ── Step 5: Render HTML ───────────────────────────────────────
        print("Step 5/6: Rendering HTML...", file=sys.stderr)
        images_data = json.loads(image_urls_output.read_text(encoding="utf-8"))
        context = render_html.build_template_context(content, images_data)
        from jinja2 import Environment, FileSystemLoader
        templates_dir = Path(__file__).resolve().parent / "tools" / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
        template = env.get_template("newsletter.html.j2")
        html = template.render(**context)
        html_output.write_text(html, encoding="utf-8")
        plain_text = render_html.html_to_plain_text(html)
        text_output.write_text(plain_text, encoding="utf-8")
        print("  ✓ HTML rendered", file=sys.stderr)

        # Upload HTML (and plain text if deferring send) to GCS
        upload_paths = [str(html_output), str(text_output)] if defer_email else [str(html_output)]
        uploads = upload_to_gcs.upload_files(upload_paths, GCS_BUCKET, user_id=user_id)
        html_gcs_url = ""
        text_gcs_url = ""
        for u in uploads:
            lp = u.get("local_path", "")
            if lp.endswith(".html"):
                html_gcs_url = u["gcs_url"]
            elif lp.endswith(".txt"):
                text_gcs_url = u["gcs_url"]
        if html_gcs_url:
            print(f"  ✓ HTML uploaded: {html_gcs_url}", file=sys.stderr)
        if defer_email and text_gcs_url:
            print(f"  ✓ Plain text uploaded: {text_gcs_url}", file=sys.stderr)

        subject = f"AI Newsletter — {content.get('headline', topic)} [{datetime.now().strftime('%b %d')}]"

        if defer_email:
            print("Step 6/6: Deferred — edition saved for scheduled send", file=sys.stderr)
            edition_id = create_edition_pending(
                subscription_id=subscription_id,
                user_id=user_id,
                subject=subject,
                html_gcs_url=html_gcs_url,
                text_gcs_url=text_gcs_url,
                plain_text_preview=plain_text[:500],
                research_query=research_query,
                scheduled_send_utc=scheduled_send_utc,
                tz_str=delivery_timezone,
            )
            print(f"\n✓ Prepare complete. Pending edition: {edition_id}", file=sys.stderr)
            return edition_id

        # ── Step 6: Send email ────────────────────────────────────────
        print("Step 6/6: Sending email...", file=sys.stderr)
        message_id = send_email_gmail.send_email(
            html_path=html_output,
            text_path=text_output,
            recipients=[recipient_email],
            subject=subject,
        )
        print(f"  ✓ Email sent: {message_id}", file=sys.stderr)

        edition_id = create_edition(
            subscription_id=subscription_id,
            user_id=user_id,
            subject=subject,
            html_gcs_url=html_gcs_url,
            plain_text_preview=plain_text[:500],
            research_query=research_query,
        )
        print(f"\n✓ Pipeline complete. Edition: {edition_id}", file=sys.stderr)
        return edition_id

    except Exception as e:
        err_msg = str(e)
        print(f"\nERROR in pipeline: {err_msg}", file=sys.stderr)
        if edition_id:
            mark_edition_failed(edition_id, err_msg)
        raise


def send_scheduled_edition(subscription_id: str) -> bool:
    """If a pending edition is due this UTC minute, download assets from GCS, send email, finalize.

    Returns:
        True if an email was sent, False if nothing was pending for this minute.
    """
    now = datetime.now(timezone.utc)
    pending = get_pending_edition_for_send(subscription_id, now)
    if not pending:
        return False

    user = get_user(pending["user_id"])
    if not user:
        print(f"[send_scheduled] No user for edition {pending['id']}", file=sys.stderr)
        return False

    text_url = pending.get("text_gcs_url") or ""
    if not pending.get("html_gcs_url") or not text_url:
        print(f"[send_scheduled] Missing GCS URLs on edition {pending['id']}", file=sys.stderr)
        mark_edition_failed(pending["id"], "Missing html_gcs_url or text_gcs_url")
        return False

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"newsletter_send_{subscription_id[:8]}_"))
    html_path = tmp_dir / "newsletter.html"
    text_path = tmp_dir / "newsletter.txt"
    try:
        download_public_gcs_url(pending["html_gcs_url"], html_path)
        download_public_gcs_url(text_url, text_path)
        send_email_gmail.send_email(
            html_path=html_path,
            text_path=text_path,
            recipients=[user["email"]],
            subject=pending["subject"],
        )
        finalize_edition_sent(pending["id"])
        print(f"[send_scheduled] Sent edition {pending['id']} to {user['email']}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[send_scheduled] Failed edition {pending['id']}: {e}", file=sys.stderr)
        mark_edition_failed(pending["id"], str(e))
        raise


def main():
    parser = argparse.ArgumentParser(description="Run the newsletter pipeline")

    # Firestore-driven mode (production)
    parser.add_argument("--subscription-id", help="Firestore subscription doc ID")

    # Direct CLI mode (testing)
    parser.add_argument("--topic", help="Topic (direct mode)")
    parser.add_argument("--sub-genre", help="Sub-genre (direct mode, optional)")
    parser.add_argument("--to", help="Recipient email (direct mode)")
    parser.add_argument("--user-id", default="test_user_001", help="User ID (direct mode)")
    parser.add_argument("--tone", default="professional but approachable")
    parser.add_argument("--audience", default="general professionals")

    args = parser.parse_args()

    if args.subscription_id:
        # ── Production mode: load params from Firestore ──────────────
        print(f"Loading subscription {args.subscription_id} from Firestore...", file=sys.stderr)
        sub = get_subscription(args.subscription_id)
        if not sub:
            print(f"ERROR: Subscription not found: {args.subscription_id}", file=sys.stderr)
            sys.exit(1)
        if not sub.get("is_active"):
            print("Subscription is paused, skipping.", file=sys.stderr)
            sys.exit(0)

        user = get_user(sub["user_id"])
        if not user:
            print(f"ERROR: User not found for subscription: {sub['user_id']}", file=sys.stderr)
            sys.exit(1)

        edition_id = run_pipeline(
            topic=sub["topic"],
            sub_genre=sub.get("sub_genre"),
            recipient_email=user["email"],
            user_id=sub["user_id"],
            subscription_id=args.subscription_id,
            tone=args.tone,
            audience=args.audience,
        )

    elif args.topic and args.to:
        # ── Direct test mode ─────────────────────────────────────────
        print("Running in direct test mode (Firestore not used for params)...", file=sys.stderr)
        edition_id = run_pipeline(
            topic=args.topic,
            sub_genre=args.sub_genre,
            recipient_email=args.to,
            user_id=args.user_id,
            subscription_id=f"test_{args.user_id}",
            tone=args.tone,
            audience=args.audience,
        )

    else:
        parser.print_help()
        sys.exit(1)

    print(edition_id)


if __name__ == "__main__":
    main()
