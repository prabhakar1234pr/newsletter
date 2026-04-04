"""Firestore CRUD wrapper for the newsletter platform.

Uses google-cloud-firestore directly with Application Default Credentials.
No Firebase Admin SDK required — connects straight to the GCP Firestore instance.

Usage (standalone seed):
    uv run python tools/firestore_client.py --seed-prompt
    uv run python tools/firestore_client.py --seed-test-subscription
    uv run python tools/firestore_client.py --get-prompt
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ai-newsletter-2026")

# Pipeline starts this many minutes before the user's chosen delivery time (UTC clock).
PREPARE_LEAD_MINUTES = int(os.getenv("NEWSLETTER_PREPARE_LEAD_MINUTES", "2"))

# ---------------------------------------------------------------------------
# Client (module-level singleton)
# ---------------------------------------------------------------------------

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


# ---------------------------------------------------------------------------
# Prompt versions
# ---------------------------------------------------------------------------

INITIAL_SYSTEM_PROMPT = """You are a newsletter content editor for "AI Newsletter", a branded publication.

Your job: take raw research sources and produce a structured newsletter in JSON format.

Output ONLY valid JSON with this exact structure (no markdown fences, no explanation):
{
  "headline": "Compelling newsletter headline",
  "subtitle": "One-line subtitle that hooks the reader",
  "summary": "2-3 sentence overview of the newsletter topic",
  "sections": [
    {
      "heading": "Section title",
      "body": "2-3 paragraphs of well-written content. Use plain text, no markdown.",
      "key_stat": "A pull-quote or striking statistic from this section (or null if none)"
    }
  ],
  "chart_data": {
    "title": "Chart title",
    "type": "bar or line or pie",
    "labels": ["Label1", "Label2", "Label3"],
    "values": [10, 20, 30],
    "x_label": "X axis label",
    "y_label": "Y axis label"
  },
  "infographic_prompt": "A detailed prompt for generating a visual infographic about the topic. Describe the layout, what data/concepts to visualize, the style (modern, clean, professional), and specify colors: Primary Blue #2F94FB, Deep Blue #2367D3, Indigo #4B3FE0, Purple #8331A6 on a white background. Include text labels that should appear in the infographic.",
  "cta": {
    "text": "Call to action button text",
    "url": "https://relevant-link.com"
  },
  "sources": [
    {"title": "Source article title", "url": "https://source-url.com"}
  ]
}

Rules:
- Produce 3-4 sections with substantive, original writing that synthesizes the sources
- chart_data should contain REAL numbers from the research. If no quantitative data exists, set chart_data to null
- infographic_prompt should describe a visual that explains a key concept from the newsletter
- sources should reference the original research URLs
- cta should link to the most relevant source or a related resource
- Write for the specified tone and audience
- Do NOT use markdown formatting in body text — plain text only
- Focus on events and developments from the LAST 24 HOURS only
- Lead with the most impactful story from the research"""


def get_active_prompt() -> str:
    """Return the currently active synthesis prompt text."""
    db = _get_db()
    docs = (
        db.collection("prompt_versions")
        .where(filter=FieldFilter("active", "==", True))
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.to_dict()["prompt_text"]
    return INITIAL_SYSTEM_PROMPT  # fallback if nothing in Firestore


def seed_initial_prompt() -> str:
    """Write the initial prompt to Firestore. Skips if an active prompt already exists."""
    db = _get_db()
    existing = list(
        db.collection("prompt_versions")
        .where(filter=FieldFilter("active", "==", True))
        .limit(1)
        .stream()
    )
    if existing:
        doc_id = existing[0].id
        print(f"Active prompt already exists: {doc_id}")
        return doc_id

    _, doc_ref = db.collection("prompt_versions").add({
        "prompt_text": INITIAL_SYSTEM_PROMPT,
        "created_at": datetime.now(timezone.utc),
        "created_by": "system",
        "change_reason": "Initial prompt — baseline version",
        "active": True,
        "version": 1,
    })
    print(f"Seeded initial prompt: {doc_ref.id}")
    return doc_ref.id


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

def _local_time_to_utc_hm(local_hour: int, local_minute: int, tz_str: str) -> tuple[int, int]:
    """Convert local delivery clock time to UTC (hour, minute) for today's date.

    Handles DST via ZoneInfo. Falls back to treating local time as UTC.
    """
    utc_dt = local_delivery_to_utc_datetime(local_hour, local_minute, tz_str)
    return utc_dt.hour, utc_dt.minute


def local_delivery_to_utc_datetime(local_hour: int, local_minute: int, tz_str: str) -> datetime:
    """Today's calendar date in the subscription TZ + local delivery clock → instant in UTC."""
    now_utc = datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(tz_str)
        local_today = now_utc.astimezone(tz)
        local_dt = datetime(
            local_today.year,
            local_today.month,
            local_today.day,
            local_hour,
            local_minute,
            0,
            tzinfo=tz,
        )
        return local_dt.astimezone(timezone.utc)
    except (ZoneInfoNotFoundError, Exception):
        return datetime(
            now_utc.year, now_utc.month, now_utc.day,
            local_hour, local_minute, tzinfo=timezone.utc,
        )


def _utc_hm_minus_minutes(utc_hour_v: int, utc_minute_v: int, delta_minutes: int) -> tuple[int, int]:
    base = datetime(2000, 1, 1, utc_hour_v, utc_minute_v, 0, tzinfo=timezone.utc)
    t = base - timedelta(minutes=delta_minutes)
    return t.hour, t.minute


def get_subscriptions_due_send(utc_hour: int, utc_minute: int) -> list[dict]:
    """Subscriptions whose scheduled local delivery maps to this UTC minute (email send)."""
    db = _get_db()
    docs = (
        db.collection("subscriptions")
        .where(filter=FieldFilter("is_active", "==", True))
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        lh = int(data.get("delivery_hour", 0))
        lm = int(data.get("delivery_minute", 0))
        uh, um = _local_time_to_utc_hm(lh, lm, data.get("timezone", "UTC"))
        if uh == utc_hour and um == utc_minute:
            results.append(data)
    return results


def get_subscriptions_due_prepare(utc_hour: int, utc_minute: int) -> list[dict]:
    """Subscriptions whose pipeline should start now (send time minus PREPARE_LEAD_MINUTES)."""
    db = _get_db()
    docs = (
        db.collection("subscriptions")
        .where(filter=FieldFilter("is_active", "==", True))
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        lh = int(data.get("delivery_hour", 0))
        lm = int(data.get("delivery_minute", 0))
        send_uh, send_um = _local_time_to_utc_hm(lh, lm, data.get("timezone", "UTC"))
        prep_uh, prep_um = _utc_hm_minus_minutes(send_uh, send_um, PREPARE_LEAD_MINUTES)
        if prep_uh == utc_hour and prep_um == utc_minute:
            results.append(data)
    return results


# Backward-compatible name
def get_subscriptions_due(utc_hour: int, utc_minute: int) -> list[dict]:
    return get_subscriptions_due_send(utc_hour, utc_minute)


def get_subscription(subscription_id: str) -> dict | None:
    """Fetch a single subscription by ID."""
    db = _get_db()
    doc = db.collection("subscriptions").document(subscription_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def create_subscription(user_id: str, topic: str, sub_genre: str | None,
                        delivery_hour: int, timezone_str: str,
                        delivery_minute: int = 0,
                        frequency: str = "daily") -> str:
    """Create a new subscription. Returns the new doc ID."""
    db = _get_db()
    _, doc_ref = db.collection("subscriptions").add({
        "user_id": user_id,
        "topic": topic,
        "sub_genre": sub_genre,
        "delivery_hour": delivery_hour,
        "delivery_minute": delivery_minute,
        "timezone": timezone_str,
        "frequency": frequency,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    return doc_ref.id


def update_subscription_status(subscription_id: str, is_active: bool) -> None:
    """Pause or resume a subscription."""
    db = _get_db()
    db.collection("subscriptions").document(subscription_id).update({
        "is_active": is_active,
        "updated_at": datetime.now(timezone.utc),
    })


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def upsert_user(uid: str, email: str, name: str) -> None:
    """Create or update a user record (called after auth signup)."""
    db = _get_db()
    db.collection("users").document(uid).set({
        "email": email,
        "name": name,
        "updated_at": datetime.now(timezone.utc),
    }, merge=True)


def get_user(uid: str) -> dict | None:
    """Fetch a user by UID."""
    db = _get_db()
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------

def _edition_date_for_display(scheduled_send_utc: datetime, tz_str: str) -> str:
    try:
        return scheduled_send_utc.astimezone(ZoneInfo(tz_str)).date().isoformat()
    except (ZoneInfoNotFoundError, Exception):
        return scheduled_send_utc.strftime("%Y-%m-%d")


def same_utc_minute(a, b) -> bool:
    def to_minute_utc(x):
        if x is None:
            return None
        if hasattr(x, "replace"):
            if x.tzinfo is None:
                x = x.replace(tzinfo=timezone.utc)
            x = x.astimezone(timezone.utc)
            return (x.year, x.month, x.day, x.hour, x.minute)
        return None

    return to_minute_utc(a) == to_minute_utc(b)


def create_edition(subscription_id: str, user_id: str, subject: str,
                   html_gcs_url: str, plain_text_preview: str,
                   research_query: str) -> str:
    """Record a sent newsletter edition (immediate send path). Returns the new doc ID."""
    db = _get_db()
    now = datetime.now(timezone.utc)
    _, doc_ref = db.collection("editions").add({
        "subscription_id": subscription_id,
        "user_id": user_id,
        "date": now.strftime("%Y-%m-%d"),
        "subject": subject,
        "html_gcs_url": html_gcs_url,
        "text_gcs_url": None,
        "plain_text_preview": plain_text_preview[:500],
        "research_query": research_query,
        "sent_at": now,
        "quality_score": None,
        "agent_notes": None,
        "status": "sent",
        "scheduled_send_at": None,
    })
    return doc_ref.id


def create_edition_pending(
    subscription_id: str,
    user_id: str,
    subject: str,
    html_gcs_url: str,
    text_gcs_url: str,
    plain_text_preview: str,
    research_query: str,
    scheduled_send_utc: datetime,
    tz_str: str,
) -> str:
    """Edition ready for email at scheduled_send_utc (status pending_email)."""
    db = _get_db()
    prepared_at = datetime.now(timezone.utc)
    _, doc_ref = db.collection("editions").add({
        "subscription_id": subscription_id,
        "user_id": user_id,
        "date": _edition_date_for_display(scheduled_send_utc, tz_str),
        "subject": subject,
        "html_gcs_url": html_gcs_url,
        "text_gcs_url": text_gcs_url,
        "plain_text_preview": plain_text_preview[:500],
        "research_query": research_query,
        "prepared_at": prepared_at,
        "scheduled_send_at": scheduled_send_utc,
        "sent_at": None,
        "quality_score": None,
        "agent_notes": None,
        "status": "pending_email",
    })
    return doc_ref.id


def get_pending_edition_for_send(subscription_id: str, utc_now: datetime) -> dict | None:
    """Return a pending edition for this subscription scheduled for this UTC minute."""
    db = _get_db()
    docs = (
        db.collection("editions")
        .where(filter=FieldFilter("subscription_id", "==", subscription_id))
        .where(filter=FieldFilter("status", "==", "pending_email"))
        .stream()
    )
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        sas = data.get("scheduled_send_at")
        if sas and same_utc_minute(sas, utc_now):
            return data
    return None


def finalize_edition_sent(edition_id: str) -> None:
    db = _get_db()
    db.collection("editions").document(edition_id).update({
        "sent_at": datetime.now(timezone.utc),
        "status": "sent",
    })


def has_pending_for_scheduled_send(subscription_id: str, scheduled_send_utc: datetime) -> bool:
    """True if a pending_email edition already exists for this subscription and send minute."""
    pending = get_pending_edition_for_send(subscription_id, scheduled_send_utc)
    return pending is not None


def get_editions_for_date(date_str: str) -> list[dict]:
    """Return all editions sent on a given date (YYYY-MM-DD). Used by the agent."""
    db = _get_db()
    docs = (
        db.collection("editions")
        .where(filter=FieldFilter("date", "==", date_str))
        .where(filter=FieldFilter("status", "==", "sent"))
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def get_editions_for_subscription(subscription_id: str, limit: int = 30) -> list[dict]:
    """Return recent sent editions for a subscription (archive / history)."""
    db = _get_db()
    docs = (
        db.collection("editions")
        .where(filter=FieldFilter("subscription_id", "==", subscription_id))
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("status") != "sent":
            continue
        data["id"] = doc.id
        results.append(data)

    def _sort_key(row: dict):
        s = row.get("sent_at")
        if s is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        d = s
        if hasattr(d, "timestamp") and getattr(d, "tzinfo", None) is None:
            d = d.replace(tzinfo=timezone.utc)
        elif hasattr(d, "timestamp"):
            d = s.astimezone(timezone.utc)
        return d

    results.sort(key=_sort_key, reverse=True)
    return results[:limit]


def update_edition_quality(edition_id: str, score: int, notes: str) -> None:
    """Set quality score + notes on an edition (called by the nightly agent)."""
    db = _get_db()
    db.collection("editions").document(edition_id).update({
        "quality_score": score,
        "agent_notes": notes,
    })


def mark_edition_failed(edition_id: str, error: str) -> None:
    """Mark an edition as failed to prevent infinite retries."""
    db = _get_db()
    db.collection("editions").document(edition_id).update({
        "status": "failed",
        "error": error,
        "updated_at": datetime.now(timezone.utc),
    })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Firestore admin operations")
    parser.add_argument("--seed-prompt", action="store_true",
                        help="Write the initial synthesis prompt to Firestore")
    parser.add_argument("--get-prompt", action="store_true",
                        help="Print the active prompt")
    parser.add_argument("--seed-test-subscription", action="store_true",
                        help="Create a test subscription at the current UTC hour")
    args = parser.parse_args()

    if args.seed_prompt:
        doc_id = seed_initial_prompt()
        print(f"Prompt doc ID: {doc_id}")

    elif args.get_prompt:
        prompt = get_active_prompt()
        print(prompt[:300] + "...")

    elif args.seed_test_subscription:
        now = datetime.now(timezone.utc)
        sub_id = create_subscription(
            user_id="test_user_001",
            topic="Telugu cinema",
            sub_genre=None,
            delivery_hour=now.hour,
            timezone_str="UTC",
            delivery_minute=now.minute,
        )
        print(f"Test subscription created: {sub_id}")
        print(f"Delivery time (UTC): {now.hour}:{now.minute:02d}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
