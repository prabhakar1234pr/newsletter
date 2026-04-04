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
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ai-newsletter-2026")

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

def get_subscriptions_due(delivery_hour_utc: int) -> list[dict]:
    """Return all active subscriptions due at the given UTC hour."""
    db = _get_db()
    docs = (
        db.collection("subscriptions")
        .where(filter=FieldFilter("delivery_hour", "==", delivery_hour_utc))
        .where(filter=FieldFilter("is_active", "==", True))
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


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
                        frequency: str = "daily") -> str:
    """Create a new subscription. Returns the new doc ID."""
    db = _get_db()
    _, doc_ref = db.collection("subscriptions").add({
        "user_id": user_id,
        "topic": topic,
        "sub_genre": sub_genre,
        "delivery_hour": delivery_hour,
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

def create_edition(subscription_id: str, user_id: str, subject: str,
                   html_gcs_url: str, plain_text_preview: str,
                   research_query: str) -> str:
    """Record a sent newsletter edition. Returns the new doc ID."""
    db = _get_db()
    _, doc_ref = db.collection("editions").add({
        "subscription_id": subscription_id,
        "user_id": user_id,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "subject": subject,
        "html_gcs_url": html_gcs_url,
        "plain_text_preview": plain_text_preview[:500],
        "research_query": research_query,
        "sent_at": datetime.now(timezone.utc),
        "quality_score": None,
        "agent_notes": None,
        "status": "sent",
    })
    return doc_ref.id


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
    """Return recent editions for a subscription (for the archive page)."""
    db = _get_db()
    docs = (
        db.collection("editions")
        .where(filter=FieldFilter("subscription_id", "==", subscription_id))
        .order_by("sent_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


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
        current_hour = datetime.now(timezone.utc).hour
        sub_id = create_subscription(
            user_id="test_user_001",
            topic="Telugu cinema",
            sub_genre=None,
            delivery_hour=current_hour,
            timezone_str="Asia/Kolkata",
        )
        print(f"Test subscription created: {sub_id}")
        print(f"Delivery hour (UTC): {current_hour}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
