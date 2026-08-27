import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.ai.lm_studio import configured_embeddings, embed_texts
from app.models import Classification, EmailEmbedding, Message


def keyword_search(db: Session, query: str, days: int = 90, limit: int = 20) -> List[Message]:
    since = datetime.utcnow() - timedelta(days=days)
    try:
        rows = db.execute(
            text(
                """
                SELECT m.id
                FROM messages_fts f
                JOIN messages m ON CAST(f.message_id AS INTEGER) = m.id
                WHERE messages_fts MATCH :q AND m.received_at >= :since AND m.is_sent = 0
                ORDER BY bm25(messages_fts)
                LIMIT :limit
                """
            ),
            {"q": query, "since": since, "limit": limit},
        ).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return []
        found = db.scalars(select(Message).where(Message.id.in_(ids))).all()
        by_id = {m.id: m for m in found}
        return [by_id[i] for i in ids if i in by_id]
    except Exception:
        pattern = f"%{query}%"
        return db.scalars(
            select(Message)
            .where(Message.is_sent == False, Message.received_at >= since)
            .where((Message.subject.ilike(pattern)) | (Message.body_text.ilike(pattern)) | (Message.sender_email.ilike(pattern)))
            .order_by(Message.received_at.desc())
            .limit(limit)
        ).all()


def semantic_search(db: Session, query: str, days: int = 90, limit: int = 20) -> List[Tuple[Message, float]]:
    if not configured_embeddings():
        return []
    qvec = np.asarray(embed_texts([query])[0], dtype=np.float32)
    qnorm = np.linalg.norm(qvec) or 1.0
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(EmailEmbedding, Message)
        .join(Message, Message.id == EmailEmbedding.message_id)
        .where(Message.received_at >= since, Message.is_sent == False)
    ).all()
    scored = []
    for emb, msg in rows:
        vec = np.asarray(json.loads(emb.vector_json), dtype=np.float32)
        denom = (np.linalg.norm(vec) or 1.0) * qnorm
        score = float(np.dot(vec, qvec) / denom)
        scored.append((msg, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def hybrid_search(db: Session, query: str, days: int = 90, limit: int = 12) -> List[Message]:
    kw = keyword_search(db, query, days, limit=limit * 2)
    sem = semantic_search(db, query, days, limit=limit * 2) if configured_embeddings() else []
    scores: Dict[int, float] = {}
    msgs: Dict[int, Message] = {}
    for rank, msg in enumerate(kw):
        msgs[msg.id] = msg
        scores[msg.id] = scores.get(msg.id, 0.0) + 1.0 / (rank + 1)
    for rank, (msg, sim) in enumerate(sem):
        msgs[msg.id] = msg
        scores[msg.id] = scores.get(msg.id, 0.0) + max(0.0, sim) + 0.5 / (rank + 1)
    ids = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [msgs[i] for i in ids]
