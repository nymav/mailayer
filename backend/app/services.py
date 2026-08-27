import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.orm import Session
from app.models import Classification, Feedback, Message, ReviewLater, SenderPreference


def _classification_map(db: Session, ids: List[int]):
    rows = db.scalars(select(Classification).where(Classification.message_id.in_(ids))).all() if ids else []
    return {r.message_id: r for r in rows}


def serialize_message(msg: Message, cls: Optional[Classification] = None) -> Dict:
    return {
        "id": msg.id,
        "gmail_id": msg.gmail_id,
        "thread_id": msg.thread_id,
        "sender_name": msg.sender_name,
        "sender_email": msg.sender_email,
        "sender_domain": msg.sender_domain,
        "subject": msg.subject,
        "snippet": msg.snippet,
        "body_text": msg.body_text,
        "received_at": msg.received_at.isoformat(),
        "is_read": msg.is_read,
        "is_starred": msg.is_starred,
        "is_important": msg.is_important,
        "is_inbox": msg.is_inbox,
        "has_attachment": msg.has_attachment,
        "list_unsubscribe": bool(msg.list_unsubscribe),
        "category": cls.category if cls else "UNKNOWN",
        "importance": cls.importance if cls else 0.5,
        "usefulness": cls.usefulness if cls else 0.5,
        "confidence": cls.confidence if cls else 0.0,
        "action_required": cls.action_required if cls else False,
        "urgency": cls.urgency if cls else "LOW",
        "summary": cls.summary if cls else msg.snippet,
        "reason": cls.reason if cls else "",
        "classification_source": cls.source if cls else "",
    }


def dashboard(db: Session, days: int = 30) -> Dict:
    since = datetime.utcnow() - timedelta(days=days)
    msgs = db.scalars(
        select(Message).where(Message.is_sent == False, Message.received_at >= since)
    ).all()
    ids = [m.id for m in msgs]
    cls_map = _classification_map(db, ids)
    categories = Counter((cls_map[m.id].category if m.id in cls_map else "UNKNOWN") for m in msgs)
    actionable = sum(1 for m in msgs if m.id in cls_map and cls_map[m.id].action_required)
    useful = sum(1 for m in msgs if m.id in cls_map and cls_map[m.id].usefulness >= 0.65)
    low_value = sum(1 for m in msgs if m.id in cls_map and cls_map[m.id].usefulness < 0.35)
    unread = sum(1 for m in msgs if not m.is_read)
    senders = Counter(m.sender_email or "(unknown)" for m in msgs)
    domains = Counter(m.sender_domain or "(unknown)" for m in msgs)

    by_day = Counter(m.received_at.date().isoformat() for m in msgs)
    daily = []
    for i in range(days - 1, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
        daily.append({"date": d, "count": by_day.get(d, 0)})

    return {
        "days": days,
        "total": len(msgs),
        "unread": unread,
        "actionable": actionable,
        "useful": useful,
        "low_value": low_value,
        "categories": dict(categories.most_common()),
        "top_senders": [{"sender": s, "count": c} for s, c in senders.most_common(8)],
        "top_domains": [{"domain": s, "count": c} for s, c in domains.most_common(8)],
        "daily": daily,
    }


def list_messages(db: Session, days: int = 90, category: str = "", search: str = "", limit: int = 100, offset: int = 0):
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(Message).where(Message.is_sent == False, Message.received_at >= since)
    if search:
        p = f"%{search}%"
        stmt = stmt.where(or_(Message.subject.ilike(p), Message.sender_email.ilike(p), Message.body_text.ilike(p)))
    if category:
        stmt = stmt.join(Classification, Classification.message_id == Message.id).where(Classification.category == category.upper())
    rows = db.scalars(stmt.order_by(Message.received_at.desc()).offset(offset).limit(limit)).all()
    cls_map = _classification_map(db, [m.id for m in rows])
    return [serialize_message(m, cls_map.get(m.id)) for m in rows]


def sender_stats(db: Session, days: int = 90) -> List[Dict]:
    since = datetime.utcnow() - timedelta(days=days)
    msgs = db.scalars(select(Message).where(Message.is_sent == False, Message.received_at >= since)).all()
    ids = [m.id for m in msgs]
    cls_map = _classification_map(db, ids)
    grouped = defaultdict(list)
    for m in msgs:
        grouped[m.sender_email or "(unknown)"].append(m)
    out = []
    for sender, group in grouped.items():
        clss = [cls_map[m.id] for m in group if m.id in cls_map]
        useful = sum(c.usefulness for c in clss) / len(clss) if clss else 0.5
        unread = sum(1 for m in group if not m.is_read)
        promo = sum(1 for c in clss if c.category in {"PROMOTION", "NEWSLETTER", "SOCIAL", "LOW_VALUE"})
        out.append({
            "sender": sender,
            "name": next((m.sender_name for m in group if m.sender_name), ""),
            "domain": next((m.sender_domain for m in group if m.sender_domain), ""),
            "count": len(group),
            "unread": unread,
            "unread_ratio": round(unread / len(group), 3),
            "avg_usefulness": round(useful, 3),
            "noise_ratio": round(promo / max(len(clss), 1), 3),
            "last_seen": max(m.received_at for m in group).isoformat(),
        })
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def subscription_stats(db: Session, days: int = 90) -> List[Dict]:
    stats = sender_stats(db, days)
    since = datetime.utcnow() - timedelta(days=days)
    out = []
    for s in stats:
        msgs = db.scalars(
            select(Message).where(Message.is_sent == False, Message.received_at >= since, Message.sender_email == s["sender"])
        ).all()
        has_unsub = any(m.list_unsubscribe or m.list_id for m in msgs)
        if not has_unsub and s["noise_ratio"] < 0.5:
            continue
        monthly = s["count"] * (30.0 / max(days, 1))
        score = (1.0 - s["avg_usefulness"]) * 0.5 + s["unread_ratio"] * 0.25 + s["noise_ratio"] * 0.25
        if score >= 0.7:
            recommendation = "REVIEW / LIKELY NOISE"
        elif score >= 0.45:
            recommendation = "REVIEW"
        else:
            recommendation = "KEEP / USEFUL"
        out.append({**s, "estimated_monthly": round(monthly, 1), "review_score": round(score, 3), "recommendation": recommendation, "has_unsubscribe_header": has_unsub})
    out.sort(key=lambda x: (x["review_score"], x["count"]), reverse=True)
    return out
