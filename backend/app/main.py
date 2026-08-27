from datetime import datetime
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ai.chat import chat as chat_service
from app.ai.jobs import jobs
from app.ai.lm_studio import health as lm_health
from app.ai.workflows import classify_pending, index_pending_embeddings
from app.config import settings
from app.database import SessionLocal, init_db, session_scope
from app.gmail.auth import connect_interactive, credentials_exist, disconnect, token_exists
from app.gmail.client import get_gmail_service, get_profile
from app.gmail.sync import full_sync, incremental_sync
from app.models import Feedback, Message, ReviewLater, SenderPreference, SyncState
from app.schemas import ChatRequest, FeedbackRequest, FullSyncRequest, ReviewRequest
from app.services import dashboard, list_messages, sender_stats, serialize_message, subscription_stats

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "name": settings.app_name}


@app.get("/api/status")
def status(db: Session = Depends(get_db)):
    account = db.scalar(select(SyncState).order_by(SyncState.id.desc()))
    return {
        "credentials_file": credentials_exist(),
        "gmail_connected": token_exists(),
        "account": account.account_email if account else "",
        "last_full_sync": account.last_full_sync.isoformat() if account and account.last_full_sync else None,
        "last_incremental_sync": account.last_incremental_sync.isoformat() if account and account.last_incremental_sync else None,
        "lm_studio": lm_health(),
        "recent_jobs": jobs.recent(),
    }


@app.post("/api/auth/connect")
def connect_gmail():
    try:
        connect_interactive()
        service = get_gmail_service()
        return {"ok": True, "profile": get_profile(service)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/auth/disconnect")
def disconnect_gmail():
    disconnect()
    return {"ok": True}


@app.post("/api/sync/full")
def start_full_sync(req: FullSyncRequest):
    return jobs.submit("Full Gmail sync", lambda progress: full_sync(req.days, req.include_sent, progress))


@app.post("/api/sync/incremental")
def start_incremental_sync():
    return jobs.submit("Incremental Gmail sync", lambda progress: incremental_sync(progress))


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/dashboard")
def get_dashboard(days: int = Query(30, ge=1, le=3650), db: Session = Depends(get_db)):
    return dashboard(db, days)


@app.get("/api/messages")
def get_messages(
    days: int = Query(90, ge=1, le=3650),
    category: str = "",
    search: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return list_messages(db, days, category, search, limit, offset)


@app.get("/api/messages/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    from app.models import Classification
    cls = db.scalar(select(Classification).where(Classification.message_id == msg.id))
    return serialize_message(msg, cls)


@app.get("/api/senders")
def get_senders(days: int = Query(90, ge=1, le=3650), db: Session = Depends(get_db)):
    return sender_stats(db, days)


@app.get("/api/subscriptions")
def get_subscriptions(days: int = Query(90, ge=1, le=3650), db: Session = Depends(get_db)):
    return subscription_stats(db, days)


@app.post("/api/messages/{message_id}/review-later")
def add_review_later(message_id: int, req: ReviewRequest, db: Session = Depends(get_db)):
    if not db.get(Message, message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    row = db.scalar(select(ReviewLater).where(ReviewLater.message_id == message_id))
    if row is None:
        row = ReviewLater(message_id=message_id)
        db.add(row)
    row.priority = req.priority.upper()[:32]
    row.reason = req.reason
    row.completed_at = None
    db.commit()
    return {"ok": True}


@app.delete("/api/messages/{message_id}/review-later")
def remove_review_later(message_id: int, db: Session = Depends(get_db)):
    row = db.scalar(select(ReviewLater).where(ReviewLater.message_id == message_id))
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@app.get("/api/review-later")
def get_review_later(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ReviewLater, Message).join(Message, Message.id == ReviewLater.message_id).where(ReviewLater.completed_at.is_(None)).order_by(ReviewLater.added_at.desc())
    ).all()
    return [
        {
            "review_id": review.id,
            "priority": review.priority,
            "reason": review.reason,
            "added_at": review.added_at.isoformat(),
            "message": serialize_message(msg),
        }
        for review, msg in rows
    ]


@app.post("/api/messages/{message_id}/feedback")
def add_feedback(message_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.add(Feedback(message_id=message_id, useful=req.useful, category_override=req.category_override.upper(), note=req.note))
    if req.useful is not None and msg.sender_email:
        pref = db.scalar(select(SenderPreference).where(SenderPreference.sender_email == msg.sender_email))
        if pref is None:
            pref = SenderPreference(sender_email=msg.sender_email, preference=0.0)
            db.add(pref)
        pref.preference = max(-1.0, min(1.0, pref.preference + (0.15 if req.useful else -0.15)))
    db.commit()
    return {"ok": True}


@app.post("/api/ai/classify-pending")
def start_ai_classification(limit: int = Query(100, ge=1, le=1000)):
    return jobs.submit("AI classify pending", lambda progress: classify_pending(limit, progress))


@app.post("/api/embeddings/index-pending")
def start_embedding_index(limit: int = Query(200, ge=1, le=2000)):
    return jobs.submit("Index embeddings", lambda progress: index_pending_embeddings(limit, progress))


@app.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        return chat_service(db, req.query, req.days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
