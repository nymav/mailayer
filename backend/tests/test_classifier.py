from datetime import datetime
from app.intelligence.classifier import heuristic_classification
from app.models import Message


def msg(subject, body="", labels="[]", unsub=""):
    return Message(
        gmail_id="x", thread_id="t", received_at=datetime.utcnow(), sender_email="a@example.com",
        sender_domain="example.com", subject=subject, body_text=body, snippet=body[:100],
        labels_json=labels, list_unsubscribe=unsub, is_read=False, is_starred=False, is_important=False,
        is_sent=False, is_inbox=True, has_attachment=False, to_emails=""
    )


def test_security_email():
    r = heuristic_classification(msg("Security alert", "New sign-in detected"))
    assert r["category"] == "SECURITY"
    assert r["importance"] >= 0.9


def test_promotion_email():
    r = heuristic_classification(msg("Big sale", "Shop now", labels='["CATEGORY_PROMOTIONS"]', unsub="<https://x>"))
    assert r["category"] in {"PROMOTION", "NEWSLETTER"}
