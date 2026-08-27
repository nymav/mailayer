from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set
from googleapiclient.errors import HttpError
from sqlalchemy import select, text
from app.database import session_scope
from app.gmail.client import get_gmail_service, get_profile
from app.gmail.parser import parse_gmail_message
from app.intelligence.classifier import heuristic_classification, upsert_classification
from app.models import Classification, EmailEmbedding, Feedback, Message, MessageEvent, ReviewLater, SyncState
from app.utils import dumps, loads


def _gmail_query(days: int, include_sent: bool) -> str:
    parts = ["-in:spam", "-in:trash"]
    if days > 0:
        parts.append(f"newer_than:{days}d")
    if not include_sent:
        parts.append("-in:sent")
    return " ".join(parts)


def _list_message_ids(service, query: str) -> List[str]:
    ids: List[str] = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me",
            q=query or None,
            maxResults=500,
            pageToken=page_token,
        ).execute()
        ids.extend([m["id"] for m in resp.get("messages", [])])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def _fetch_message(service, gmail_id: str) -> Dict:
    return service.users().messages().get(userId="me", id=gmail_id, format="full").execute()


def _record_state_events(db, existing: Optional[Message], parsed: Dict) -> None:
    if existing is None:
        db.add(MessageEvent(gmail_id=parsed["gmail_id"], event_type="sent" if parsed["is_sent"] else "received"))
        return
    if existing.is_read != parsed["is_read"]:
        db.add(MessageEvent(gmail_id=parsed["gmail_id"], event_type="became_read" if parsed["is_read"] else "became_unread"))
    if existing.is_starred != parsed["is_starred"]:
        db.add(MessageEvent(gmail_id=parsed["gmail_id"], event_type="starred" if parsed["is_starred"] else "unstarred"))
    if existing.is_inbox and not parsed["is_inbox"]:
        db.add(MessageEvent(gmail_id=parsed["gmail_id"], event_type="left_inbox"))
    elif not existing.is_inbox and parsed["is_inbox"]:
        db.add(MessageEvent(gmail_id=parsed["gmail_id"], event_type="entered_inbox"))


def _upsert_message(db, parsed: Dict) -> Message:
    existing = db.scalar(select(Message).where(Message.gmail_id == parsed["gmail_id"]))
    _record_state_events(db, existing, parsed)
    if existing is None:
        existing = Message(gmail_id=parsed["gmail_id"], thread_id=parsed["thread_id"], received_at=parsed["received_at"])
        db.add(existing)
        db.flush()

    for key in [
        "thread_id", "history_id", "sender_name", "sender_email", "sender_domain", "to_emails",
        "subject", "snippet", "body_text", "received_at", "internal_date_ms", "list_unsubscribe",
        "list_id", "is_read", "is_starred", "is_important", "is_sent", "is_inbox", "has_attachment",
    ]:
        setattr(existing, key, parsed[key])
    existing.labels_json = dumps(parsed["labels"])
    db.flush()

    db.execute(text("DELETE FROM messages_fts WHERE message_id = :mid"), {"mid": str(existing.id)})
    db.execute(
        text("INSERT INTO messages_fts(message_id, subject, sender_email, body_text) VALUES(:mid,:sub,:sender,:body)"),
        {"mid": str(existing.id), "sub": existing.subject or "", "sender": existing.sender_email or "", "body": existing.body_text or ""},
    )

    result = heuristic_classification(existing)
    upsert_classification(db, existing, result, source="heuristic", overwrite_llm=False)
    return existing


def full_sync(days: int = 90, include_sent: bool = True, progress=None) -> Dict:
    service = get_gmail_service()
    profile = get_profile(service)
    account = profile.get("emailAddress", "")
    query = _gmail_query(days, include_sent)
    ids = _list_message_ids(service, query)

    count = 0
    for idx, gmail_id in enumerate(ids, 1):
        raw = _fetch_message(service, gmail_id)
        parsed = parse_gmail_message(raw)
        with session_scope() as db:
            _upsert_message(db, parsed)
        count += 1
        if progress:
            progress(idx / max(len(ids), 1), f"Synced {idx}/{len(ids)} messages")

    # Store the history ID captured before the full listing began. Any mailbox
    # changes during the long sync will be picked up by the next incremental
    # History API sync instead of being skipped.
    base_history_id = str(profile.get("historyId") or "")
    with session_scope() as db:
        state = db.scalar(select(SyncState).where(SyncState.account_email == account))
        if state is None:
            state = SyncState(account_email=account)
            db.add(state)
        state.history_id = base_history_id
        state.sync_days = days
        state.include_sent = include_sent
        state.last_full_sync = datetime.utcnow()

    return {"account": account, "messages_synced": count, "history_id": base_history_id}


def _get_sync_state(account: str):
    with session_scope() as db:
        state = db.scalar(select(SyncState).where(SyncState.account_email == account))
        if not state:
            return None
        return {
            "history_id": state.history_id,
            "sync_days": state.sync_days,
            "include_sent": state.include_sent,
        }


def incremental_sync(progress=None) -> Dict:
    service = get_gmail_service()
    profile = get_profile(service)
    account = profile.get("emailAddress", "")
    state = _get_sync_state(account)
    if not state or not state["history_id"]:
        raise RuntimeError("No sync history found. Run Full Sync first.")

    affected: Set[str] = set()
    deleted: Set[str] = set()
    page_token = None
    last_history_id = state["history_id"]

    try:
        while True:
            resp = service.users().history().list(
                userId="me",
                startHistoryId=state["history_id"],
                pageToken=page_token,
                maxResults=500,
            ).execute()
            for h in resp.get("history", []):
                for item in h.get("messagesAdded", []):
                    if item.get("message", {}).get("id"):
                        affected.add(item["message"]["id"])
                for item in h.get("labelsAdded", []):
                    if item.get("message", {}).get("id"):
                        affected.add(item["message"]["id"])
                for item in h.get("labelsRemoved", []):
                    if item.get("message", {}).get("id"):
                        affected.add(item["message"]["id"])
                for item in h.get("messagesDeleted", []):
                    if item.get("message", {}).get("id"):
                        deleted.add(item["message"]["id"])
            last_history_id = str(resp.get("historyId") or last_history_id)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    except HttpError as exc:
        if getattr(exc, "resp", None) is not None and exc.resp.status == 404:
            raise RuntimeError("Gmail history ID is expired/invalid. Run Full Sync again.") from exc
        raise

    affected -= deleted
    changed = list(affected)
    for idx, gmail_id in enumerate(changed, 1):
        try:
            raw = _fetch_message(service, gmail_id)
        except HttpError as exc:
            if getattr(exc, "resp", None) is not None and exc.resp.status == 404:
                deleted.add(gmail_id)
                continue
            raise
        parsed = parse_gmail_message(raw)
        with session_scope() as db:
            _upsert_message(db, parsed)
        if progress:
            progress(idx / max(len(changed), 1), f"Updated {idx}/{len(changed)} changed messages")

    with session_scope() as db:
        for gmail_id in deleted:
            msg = db.scalar(select(Message).where(Message.gmail_id == gmail_id))
            if msg:
                db.execute(text("DELETE FROM messages_fts WHERE message_id = :mid"), {"mid": str(msg.id)})
                for model in (Classification, EmailEmbedding, Feedback, ReviewLater):
                    for row in db.scalars(select(model).where(model.message_id == msg.id)).all():
                        db.delete(row)
                db.delete(msg)
                db.add(MessageEvent(gmail_id=gmail_id, event_type="deleted"))
        db_state = db.scalar(select(SyncState).where(SyncState.account_email == account))
        db_state.history_id = str(get_profile(service).get("historyId") or last_history_id)
        db_state.last_incremental_sync = datetime.utcnow()

    return {"account": account, "updated": len(changed), "deleted": len(deleted), "history_id": last_history_id}
