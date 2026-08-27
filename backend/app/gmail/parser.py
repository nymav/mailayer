import base64
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from app.config import settings
from app.utils import compact_ws, domain_of, header_map, parse_addresses, parse_email_date, parse_from, trim_quoted_reply


def _decode(data: str) -> str:
    if not data:
        return ""
    try:
        padded = data + "=" * (-len(data) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _walk_parts(part: Dict, plain: List[str], html: List[str]) -> bool:
    has_attachment = False
    mime = (part.get("mimeType") or "").lower()
    filename = part.get("filename") or ""
    body = part.get("body") or {}
    if filename or body.get("attachmentId"):
        has_attachment = True

    data = body.get("data")
    if data:
        decoded = _decode(data)
        if mime == "text/plain":
            plain.append(decoded)
        elif mime == "text/html":
            html.append(decoded)

    for child in part.get("parts") or []:
        has_attachment = _walk_parts(child, plain, html) or has_attachment
    return has_attachment


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    return soup.get_text("\n")


def parse_gmail_message(raw: Dict) -> Dict:
    payload = raw.get("payload") or {}
    headers = header_map(payload.get("headers") or [])
    sender_name, sender_email = parse_from(headers.get("from", ""))
    to_emails = parse_addresses(headers.get("to", ""))
    labels = raw.get("labelIds") or []
    internal_ms = int(raw.get("internalDate") or 0)

    plain, html = [], []
    has_attachment = _walk_parts(payload, plain, html)
    body = "\n".join(plain).strip()
    if not body and html:
        body = _html_to_text("\n".join(html))
    body = trim_quoted_reply(body)
    body = body[: settings.max_email_body_chars]

    return {
        "gmail_id": raw["id"],
        "thread_id": raw.get("threadId") or "",
        "history_id": str(raw.get("historyId") or ""),
        "sender_name": sender_name,
        "sender_email": sender_email,
        "sender_domain": domain_of(sender_email),
        "to_emails": ",".join(to_emails),
        "subject": headers.get("subject", "").strip(),
        "snippet": compact_ws(raw.get("snippet", "")),
        "body_text": body,
        "received_at": parse_email_date(headers.get("date", ""), internal_ms),
        "internal_date_ms": internal_ms,
        "labels": labels,
        "list_unsubscribe": headers.get("list-unsubscribe", ""),
        "list_id": headers.get("list-id", ""),
        "is_read": "UNREAD" not in labels,
        "is_starred": "STARRED" in labels,
        "is_important": "IMPORTANT" in labels,
        "is_sent": "SENT" in labels,
        "is_inbox": "INBOX" in labels,
        "has_attachment": has_attachment,
    }
