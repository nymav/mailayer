import json
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import select
from app.ai.lm_studio import classify_email, configured_embeddings, embed_texts
from app.config import settings
from app.database import session_scope
from app.intelligence.classifier import upsert_classification
from app.models import Classification, EmailEmbedding, Message


def classify_pending(limit: int = 100, progress=None) -> Dict:
    with session_scope() as db:
        rows = db.execute(
            select(Message, Classification)
            .join(Classification, Classification.message_id == Message.id)
            .where(Message.is_sent == False)
            .where((Classification.source != "llm") | (Classification.confidence < 0.7))
            .order_by(Message.received_at.desc())
            .limit(limit)
        ).all()
        items = [(m.id, m.sender_email, m.subject, m.body_text or m.snippet) for m, _ in rows]

    done = 0
    errors = 0
    for idx, (mid, sender, subject, body) in enumerate(items, 1):
        try:
            result = classify_email(subject, sender, body)
            with session_scope() as db:
                msg = db.get(Message, mid)
                upsert_classification(db, msg, result, source="llm", model_used=settings.lmstudio_chat_model, overwrite_llm=True)
            done += 1
        except Exception:
            errors += 1
        if progress:
            progress(idx / max(len(items), 1), f"AI classified {idx}/{len(items)}")
    return {"classified": done, "errors": errors, "requested": len(items)}


def index_pending_embeddings(limit: int = 200, progress=None) -> Dict:
    if not configured_embeddings():
        raise RuntimeError("LMSTUDIO_EMBEDDING_MODEL is blank; configure an embedding model first.")
    with session_scope() as db:
        existing_subq = select(EmailEmbedding.message_id)
        msgs = db.scalars(
            select(Message)
            .where(Message.is_sent == False, ~Message.id.in_(existing_subq))
            .order_by(Message.received_at.desc())
            .limit(limit)
        ).all()
        payloads = [(m.id, f"From: {m.sender_email}\nSubject: {m.subject}\n{(m.body_text or m.snippet)[:8000]}") for m in msgs]

    batch_size = 16
    done = 0
    for start in range(0, len(payloads), batch_size):
        batch = payloads[start:start + batch_size]
        vectors = embed_texts([text for _, text in batch])
        with session_scope() as db:
            for (mid, _), vector in zip(batch, vectors):
                row = db.scalar(select(EmailEmbedding).where(EmailEmbedding.message_id == mid))
                if row is None:
                    row = EmailEmbedding(message_id=mid, model=settings.lmstudio_embedding_model, vector_json=json.dumps(vector))
                    db.add(row)
                else:
                    row.model = settings.lmstudio_embedding_model
                    row.vector_json = json.dumps(vector)
                done += 1
        if progress:
            progress(done / max(len(payloads), 1), f"Embedded {done}/{len(payloads)}")
    return {"embedded": done, "requested": len(payloads), "model": settings.lmstudio_embedding_model}
