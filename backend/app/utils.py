import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr, getaddresses
from typing import Any, Dict, Iterable, List, Tuple


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str, default):
    try:
        return json.loads(value or "")
    except Exception:
        return default


def parse_from(value: str) -> Tuple[str, str]:
    name, addr = parseaddr(value or "")
    return name.strip(), addr.strip().lower()


def parse_addresses(value: str) -> List[str]:
    return [addr.strip().lower() for _, addr in getaddresses([value or ""]) if addr]


def domain_of(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower() if "@" in email else ""


def parse_email_date(header_value: str, internal_ms: int) -> datetime:
    if header_value:
        try:
            dt = parsedate_to_datetime(header_value)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            pass
    return datetime.utcfromtimestamp((internal_ms or 0) / 1000.0)


def compact_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", (text or "")).strip()


def trim_quoted_reply(text: str) -> str:
    if not text:
        return ""
    markers = [
        r"\nOn .{0,200} wrote:\s*\n",
        r"\n-{2,}Original Message-{2,}\n",
        r"\nFrom:\s+.{1,200}\nSent:\s+",
    ]
    cut = len(text)
    for pat in markers:
        m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            cut = min(cut, m.start())
    return text[:cut].strip()


def header_map(headers: Iterable[Dict[str, str]]) -> Dict[str, str]:
    return {str(h.get("name", "")).lower(): str(h.get("value", "")) for h in headers or []}
