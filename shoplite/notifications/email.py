"""Email stub: records and logs messages instead of sending them."""

import logging

logger = logging.getLogger("shoplite.email")

# Messages "sent" since start-up; tests read this.
outbox: list[dict] = []


def send_email(to: str, subject: str, body: str) -> None:
    """Pretend to send an email."""
    outbox.append({"to": to, "subject": subject, "body": body})
    logger.info("email stubbed to=%s subject=%s", to, subject)
