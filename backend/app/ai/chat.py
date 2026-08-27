from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ai.lm_studio import answer_with_evidence
from app.models import Classification, Message
from app.search import hybrid_search
from app.services import sender_stats, subscription_stats


def _source(msg: Message) -> Dict:
    return {
        "message_id": msg.id,
        "gmail_id": msg.gmail_id,
        "subject": msg.subject,
        "sender_email": msg.sender_email,
        "received_at": msg.received_at.isoformat(),
    }


def _message_evidence(db: Session, msgs: List[Message]) -> str:
    ids = [m.id for m in msgs]
    cls_rows = db.scalars(select(Classification).where(Classification.message_id.in_(ids))).all() if ids else []
    cmap = {c.message_id: c for c in cls_rows}
    chunks = []
    for m in msgs:
        c = cmap.get(m.id)
        chunks.append(
            f"MESSAGE_ID: {m.id}\nDATE: {m.received_at.isoformat()}\nFROM: {m.sender_email}\nSUBJECT: {m.subject}\n"
            f"CATEGORY: {c.category if c else 'UNKNOWN'}\nUSEFULNESS: {c.usefulness if c else 0.5}\n"
            f"ACTION_REQUIRED: {c.action_required if c else False}\nSUMMARY: {(c.summary if c else m.snippet)[:600]}\n"
            f"BODY_EXCERPT: {(m.body_text or m.snippet)[:1800]}"
        )
    return "\n\n---\n\n".join(chunks)


def chat(db: Session, query: str, days: int = 90) -> Dict:
    q = query.lower()
    if any(x in q for x in ["who sent", "most emails", "top sender", "top senders"]):
        rows = sender_stats(db, days)[:20]
        evidence = "SENDER STATISTICS\n" + "\n".join(
            f"{r['sender']}: {r['count']} emails, unread_ratio={r['unread_ratio']}, avg_usefulness={r['avg_usefulness']}" for r in rows
        )
        return {"answer": answer_with_evidence(query, evidence), "sources": [], "tool": "sender_stats"}

    if any(x in q for x in ["subscription", "unsubscribe", "newsletter", "inbox noise"]):
        rows = subscription_stats(db, days)[:20]
        evidence = "SUBSCRIPTION STATISTICS\n" + "\n".join(
            f"{r['sender']}: {r['count']} emails, estimated_monthly={r['estimated_monthly']}, avg_usefulness={r['avg_usefulness']}, review_score={r['review_score']}, recommendation={r['recommendation']}" for r in rows
        )
        return {"answer": answer_with_evidence(query, evidence), "sources": [], "tool": "subscription_stats"}

    since = datetime.utcnow() - timedelta(days=days)
    if any(x in q for x in ["action required", "need reply", "need to reply", "important emails", "needs attention"]):
        msgs = db.scalars(
            select(Message)
            .join(Classification, Classification.message_id == Message.id)
            .where(Message.is_sent == False, Message.received_at >= since)
            .where((Classification.action_required == True) | (Classification.importance >= 0.75))
            .order_by(Classification.importance.desc(), Message.received_at.desc())
            .limit(15)
        ).all()
        evidence = _message_evidence(db, msgs)
        return {"answer": answer_with_evidence(query, evidence), "sources": [_source(m) for m in msgs], "tool": "attention_search"}

    msgs = hybrid_search(db, query, days=days, limit=12)
    evidence = _message_evidence(db, msgs)
    return {"answer": answer_with_evidence(query, evidence), "sources": [_source(m) for m in msgs], "tool": "hybrid_search"}
