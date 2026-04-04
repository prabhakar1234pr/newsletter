"""FastAPI backend for the AI Newsletter platform.

Endpoints:
    GET  /health                      — liveness check
    GET  /subscriptions               — list user's subscriptions
    POST /subscriptions               — create subscription
    PATCH /subscriptions/{id}         — pause / resume / update
    DELETE /subscriptions/{id}        — delete subscription
    GET  /editions?subscription_id=   — archive for one subscription
    POST /internal/run-due            — Cloud Scheduler trigger (hourly)

Auth:
    All /subscriptions and /editions routes require a valid Firebase ID token
    in the Authorization: Bearer <token> header.

    /internal/run-due is protected by the X-Internal-Secret header.
"""

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import firebase_admin
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth as firebase_auth, credentials
from pydantic import BaseModel

# Add backend/ to path so tools/ imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.firestore_client import (
    create_subscription,
    get_subscription,
    get_subscriptions_due,
    update_subscription_status,
    get_user,
    upsert_user,
    get_editions_for_subscription,
)
from tools import firestore_client as _fc
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Firebase Admin SDK init (uses Application Default Credentials on Cloud Run,
# or GOOGLE_APPLICATION_CREDENTIALS locally)
# ---------------------------------------------------------------------------

if not firebase_admin._apps:
    firebase_admin.initialize_app()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Newsletter API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "dev-secret-change-in-prod")

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def get_current_user(authorization: str = Header(default=None)) -> dict:
    """Verify Firebase ID token and return decoded claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except firebase_admin.exceptions.FirebaseError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


def verify_internal(x_internal_secret: str = Header(default=None)):
    """Verify Cloud Scheduler / internal requests."""
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SubscriptionCreate(BaseModel):
    topic: str
    sub_genre: str | None = None
    delivery_hour: int          # 0–23 UTC
    timezone: str               # e.g. "Asia/Kolkata"
    frequency: str = "daily"


class SubscriptionUpdate(BaseModel):
    is_active: bool | None = None
    delivery_hour: int | None = None
    timezone: str | None = None
    sub_genre: str | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@app.get("/subscriptions")
def list_subscriptions(user: dict = Depends(get_current_user)):
    """Return all subscriptions for the authenticated user."""
    db = _fc._get_db()
    from google.cloud.firestore_v1.base_query import FieldFilter
    docs = (
        db.collection("subscriptions")
        .where(filter=FieldFilter("user_id", "==", user["uid"]))
        .stream()
    )
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        # Convert Firestore timestamps to ISO strings for JSON serialisation
        for k, v in data.items():
            if hasattr(v, "isoformat"):
                data[k] = v.isoformat()
        result.append(data)
    return result


@app.post("/subscriptions", status_code=status.HTTP_201_CREATED)
def create_sub(body: SubscriptionCreate, user: dict = Depends(get_current_user)):
    """Create a new subscription for the authenticated user."""
    # Ensure user doc exists in Firestore
    upsert_user(
        uid=user["uid"],
        email=user.get("email", ""),
        name=user.get("name", user.get("email", "")),
    )

    sub_id = create_subscription(
        user_id=user["uid"],
        topic=body.topic,
        sub_genre=body.sub_genre,
        delivery_hour=body.delivery_hour,
        timezone_str=body.timezone,
        frequency=body.frequency,
    )
    return {"id": sub_id, "message": "Subscription created"}


@app.patch("/subscriptions/{sub_id}")
def update_sub(
    sub_id: str,
    body: SubscriptionUpdate,
    user: dict = Depends(get_current_user),
):
    """Update pause/resume status or delivery settings."""
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub["user_id"] != user["uid"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    db = _fc._get_db()
    updates = {}
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.delivery_hour is not None:
        updates["delivery_hour"] = body.delivery_hour
    if body.timezone is not None:
        updates["timezone"] = body.timezone
    if body.sub_genre is not None:
        updates["sub_genre"] = body.sub_genre
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        db.collection("subscriptions").document(sub_id).update(updates)

    return {"id": sub_id, "updated": list(updates.keys())}


@app.delete("/subscriptions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub(sub_id: str, user: dict = Depends(get_current_user)):
    """Permanently delete a subscription."""
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub["user_id"] != user["uid"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    _fc._get_db().collection("subscriptions").document(sub_id).delete()


# ---------------------------------------------------------------------------
# Editions (archive)
# ---------------------------------------------------------------------------

@app.get("/editions")
def list_editions(subscription_id: str, user: dict = Depends(get_current_user)):
    """Return past editions for a subscription (archive page)."""
    sub = get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub["user_id"] != user["uid"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    editions = get_editions_for_subscription(subscription_id, limit=50)
    # Serialise Firestore timestamps
    for ed in editions:
        for k, v in ed.items():
            if hasattr(v, "isoformat"):
                ed[k] = v.isoformat()
            elif hasattr(v, "_seconds"):
                # Firestore DatetimeWithNanoseconds
                ed[k] = {"_seconds": v._seconds, "_nanoseconds": getattr(v, "_nanoseconds", 0)}
    return editions


# ---------------------------------------------------------------------------
# Internal: Cloud Scheduler trigger
# ---------------------------------------------------------------------------

@app.post("/internal/run-due")
def run_due(
    _: None = Depends(verify_internal),
    dry_run: bool = False,
):
    """Find all subscriptions due at the current UTC hour and run their pipelines.

    Called by Cloud Scheduler every hour.
    Each pipeline runs in its own background thread so this endpoint returns
    immediately without waiting for pipeline completion.
    """
    current_hour = datetime.now(timezone.utc).hour
    due = get_subscriptions_due(current_hour)

    if not due:
        return {"triggered": 0, "hour": current_hour, "message": "No subscriptions due"}

    if dry_run:
        return {
            "triggered": 0,
            "dry_run": True,
            "hour": current_hour,
            "would_run": [s["id"] for s in due],
        }

    triggered = []
    for sub in due:
        sub_id = sub["id"]
        t = threading.Thread(
            target=_run_pipeline_safe,
            args=(sub_id,),
            daemon=True,
            name=f"pipeline-{sub_id[:8]}",
        )
        t.start()
        triggered.append(sub_id)

    return {
        "triggered": len(triggered),
        "hour": current_hour,
        "subscription_ids": triggered,
    }


def _run_pipeline_safe(subscription_id: str):
    """Run the pipeline for a subscription, catching all exceptions."""
    try:
        from main import run_pipeline
        from tools.firestore_client import get_subscription, get_user

        sub = get_subscription(subscription_id)
        if not sub or not sub.get("is_active"):
            return

        user = get_user(sub["user_id"])
        if not user:
            print(f"[scheduler] No user found for subscription {subscription_id}", flush=True)
            return

        run_pipeline(
            topic=sub["topic"],
            sub_genre=sub.get("sub_genre"),
            recipient_email=user["email"],
            user_id=sub["user_id"],
            subscription_id=subscription_id,
        )
    except Exception as e:
        print(f"[scheduler] Pipeline failed for {subscription_id}: {e}", flush=True)


# ---------------------------------------------------------------------------
# Unsubscribe link (one-click from email)
# ---------------------------------------------------------------------------

@app.get("/unsubscribe/{sub_id}")
def unsubscribe(sub_id: str, token: str = ""):
    """One-click unsubscribe from email footer.

    The token is the subscription_id itself (simple — improve with HMAC for prod).
    """
    sub = get_subscription(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    update_subscription_status(sub_id, is_active=False)
    return {"message": "You have been unsubscribed. You can re-enable this in your dashboard."}
