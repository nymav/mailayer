import json
import re
from typing import Dict, Optional
from sqlalchemy import select
from app.models import Classification, Feedback, Message, SenderPreference

CATEGORIES = {
    "CRITICAL", "ACTION_REQUIRED", "PERSONAL", "WORK", "JOB_RECRUITMENT", "ACADEMIC",
    "FINANCE", "SECURITY", "TRAVEL", "TRANSACTION", "RECEIPT", "ORDER", "NEWSLETTER",
    "PROMOTION", "SOCIAL", "AUTOMATED_NOTIFICATION", "LOW_VALUE", "SPAM_SUSPICIOUS", "UNKNOWN",
}


def _contains(text: str, words) -> bool:
    low = text.lower()
    return any(w in low for w in words)


def heuristic_classification(msg: Message) -> Dict:
    text = f"{msg.subject}\n{msg.snippet}\n{msg.body_text[:5000]}".lower()
    labels = set(json.loads(msg.labels_json or "[]"))
    category = "UNKNOWN"
    importance = 0.45
    usefulness = 0.5
    confidence = 0.55
    action_required = False
    urgency = "LOW"
    reason = []

    if _contains(text, ["security alert", "verification code", "one-time password", "otp", "new sign-in", "password reset", "suspicious activity"]):
        category, importance, usefulness, confidence, urgency = "SECURITY", 0.95, 0.95, 0.9, "HIGH"
        reason.append("Security/account language detected")
    elif _contains(text, ["interview", "application", "recruiter", "hiring", "job opportunity", "position", "candidate", "phd", "doctoral"]):
        category, importance, usefulness, confidence = "JOB_RECRUITMENT", 0.82, 0.9, 0.78
        reason.append("Job/recruitment/application language detected")
    elif _contains(text, ["university", "professor", "conference", "manuscript", "paper", "research", "seminar", "thesis"]):
        category, importance, usefulness, confidence = "ACADEMIC", 0.72, 0.82, 0.7
        reason.append("Academic/research language detected")
    elif _contains(text, ["payment due", "invoice", "bank", "statement", "refund", "credit card", "debit card", "transaction"]):
        category, importance, usefulness, confidence = "FINANCE", 0.8, 0.88, 0.75
        reason.append("Financial language detected")
    elif _contains(text, ["order confirmed", "order shipped", "delivery", "tracking number", "out for delivery"]):
        category, importance, usefulness, confidence = "ORDER", 0.6, 0.76, 0.76
        reason.append("Order/shipping language detected")
    elif _contains(text, ["receipt", "thanks for your purchase", "purchase confirmation"]):
        category, importance, usefulness, confidence = "RECEIPT", 0.52, 0.7, 0.74
        reason.append("Receipt/purchase language detected")
    elif "CATEGORY_PROMOTIONS" in labels or msg.list_unsubscribe:
        if msg.list_id or _contains(text, ["newsletter", "digest", "weekly update", "daily update"]):
            category, importance, usefulness, confidence = "NEWSLETTER", 0.28, 0.38, 0.78
            reason.append("Mailing-list/newsletter signals detected")
        else:
            category, importance, usefulness, confidence = "PROMOTION", 0.2, 0.25, 0.82
            reason.append("Gmail promotion or unsubscribe signal detected")
    elif "CATEGORY_SOCIAL" in labels:
        category, importance, usefulness, confidence = "SOCIAL", 0.28, 0.35, 0.8
        reason.append("Gmail social category detected")
    elif "CATEGORY_UPDATES" in labels:
        category, importance, usefulness, confidence = "AUTOMATED_NOTIFICATION", 0.4, 0.48, 0.68
        reason.append("Gmail updates category detected")

    if _contains(text, ["please reply", "please respond", "action required", "confirm your", "let me know", "your response", "deadline", "due by", "required by"]):
        action_required = True
        importance = max(importance, 0.8)
        usefulness = max(usefulness, 0.82)
        urgency = "HIGH" if _contains(text, ["urgent", "today", "tomorrow", "deadline", "due by"]) else "MEDIUM"
        reason.append("Likely action/request language detected")

    if msg.is_important:
        importance = min(1.0, importance + 0.08)
        usefulness = min(1.0, usefulness + 0.05)
        reason.append("Gmail IMPORTANT label present")
    if msg.is_starred:
        importance = min(1.0, importance + 0.1)
        usefulness = min(1.0, usefulness + 0.12)
        reason.append("Message is starred")
    if not msg.is_read and category in {"PROMOTION", "NEWSLETTER", "SOCIAL"}:
        usefulness = max(0.0, usefulness - 0.05)

    summary = (msg.snippet or msg.subject or "")[:500]
    return {
        "category": category,
        "importance": round(importance, 3),
        "usefulness": round(usefulness, 3),
        "confidence": round(confidence, 3),
        "action_required": action_required,
        "urgency": urgency,
        "summary": summary,
        "reason": "; ".join(reason) or "No strong heuristic signal; AI enrichment recommended",
    }


def personalized_adjustment(db, msg: Message, usefulness: float) -> float:
    pref = db.scalar(select(SenderPreference).where(SenderPreference.sender_email == msg.sender_email))
    if pref:
        usefulness += pref.preference * 0.2
    recent_feedback = db.scalars(
        select(Feedback).where(Feedback.message_id == msg.id).order_by(Feedback.created_at.desc())
    ).first()
    if recent_feedback and recent_feedback.useful is not None:
        usefulness += 0.25 if recent_feedback.useful else -0.25
    return min(1.0, max(0.0, usefulness))


def upsert_classification(db, msg: Message, result: Dict, source: str, model_used: str = "", overwrite_llm: bool = True) -> Classification:
    row = db.scalar(select(Classification).where(Classification.message_id == msg.id))
    if row and row.source == "llm" and not overwrite_llm:
        return row
    if row is None:
        row = Classification(message_id=msg.id)
        db.add(row)
    category = str(result.get("category", "UNKNOWN")).upper()
    if category not in CATEGORIES:
        category = "UNKNOWN"
    row.category = category
    row.importance = min(1.0, max(0.0, float(result.get("importance", 0.5))))
    row.usefulness = personalized_adjustment(db, msg, min(1.0, max(0.0, float(result.get("usefulness", 0.5)))))
    row.confidence = min(1.0, max(0.0, float(result.get("confidence", 0.5))))
    row.action_required = bool(result.get("action_required", False))
    row.urgency = str(result.get("urgency", "LOW")).upper()[:32]
    row.summary = str(result.get("summary", ""))[:2000]
    row.reason = str(result.get("reason", ""))[:3000]
    row.source = source
    row.model_used = model_used
    db.flush()
    return row
