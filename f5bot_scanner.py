# f5bot_scanner.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Fallback scanner: reads F5Bot alert emails via IMAP and extracts Reddit post details.

import logging
import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime

from config import (
    IMAP_SERVER, IMAP_PORT,
    EMAIL_ADDRESS, EMAIL_APP_PASSWORD,
    F5BOT_SENDER
)
from utils import retry

log = logging.getLogger("HospitoFind")


def _decode_email_header(header_value):
    """Decode an email header value that may be encoded (RFC 2047)."""
    if header_value is None:
        return ""
    parts = decode_header(header_value)
    decoded = ""
    for part, encoding in parts:
        if isinstance(part, bytes):
            try:
                decoded += part.decode(encoding or "utf-8", errors="replace")
            except LookupError:
                decoded += part.decode("utf-8", errors="replace")
        else:
            decoded += part
    return decoded


def _parse_f5bot_email(msg):
    """
    Extract Reddit post information from an F5Bot alert email.
    Returns a dict like the one in MOCK_POSTS, or None if parsing fails.
    """
    subject = _decode_email_header(msg["Subject"])
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdisp:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    # Combine subject and body for parsing
    full_text = subject + "\n" + body

    # Look for a Reddit URL: https://www.reddit.com/r/subreddit/comments/.../title/
    url_match = re.search(r'(https?://(?:www\.)?reddit\.com/r/[^/\s]+/comments/[^\s]+)', full_text)
    if not url_match:
        log.debug("No Reddit URL found in F5Bot email")
        return None

    url = url_match.group(1).rstrip(")/")

    # Extract subreddit
    subreddit_match = re.search(r'/r/([^/\s]+)', url)
    subreddit = subreddit_match.group(1) if subreddit_match else "unknown"

    # Extract post ID (the part after /comments/)
    post_id_match = re.search(r'/comments/([^/\s]+)', url)
    post_id = post_id_match.group(1) if post_id_match else str(int(time.time()))

    # Try to get author from "u/username" in the email text
    author_match = re.search(r'u/(\w+)', full_text)
    author = author_match.group(1) if author_match else "unknown_author"

    # Get title: either from email subject (after removing "F5Bot Alert: ") or from URL
    title_from_subject = re.sub(r'^F5Bot\s*(Alert|Notification)?\s*:\s*', '', subject, flags=re.IGNORECASE).strip()
    if title_from_subject and len(title_from_subject) > 5:
        title = title_from_subject
    else:
        # Fallback: extract from URL (last part after /)
        parts = url.rstrip("/").split("/")
        title = parts[-1].replace("_", " ") if parts else "Unknown Title"

    # F5Bot doesn't provide the post body, so we use the title as body for keyword scoring
    post_body = title

    # Use a rough created_utc from the email's date (we don't have the exact post time)
    date_str = msg["Date"]
    try:
        # Parse email date into timestamp
        from email.utils import parsedate_to_datetime
        created_utc = parsedate_to_datetime(date_str).timestamp()
    except Exception:
        created_utc = time.time()

    return {
        "id": f"f5bot-{post_id}",
        "title": title,
        "body": post_body,
        "author": author,
        "subreddit": subreddit,
        "url": url,
        "created_utc": created_utc
    }


@retry(max_attempts=2, delay=5, exceptions=(Exception,))
def fetch_recent_posts():
    """
    Connect to IMAP, read unread F5Bot emails, parse them, mark them as read,
    and return a list of post dicts.
    """
    posts = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unseen emails from F5Bot
        status, messages = mail.search(None, f'(UNSEEN FROM "{F5BOT_SENDER}")')
        if status != "OK":
            log.warning("IMAP search failed: %s", status)
            mail.logout()
            return posts

        email_ids = messages[0].split()
        log.info("Found %d unread F5Bot emails", len(email_ids))

        for eid in email_ids:
            # Fetch the email
            res, msg_data = mail.fetch(eid, "(RFC822)")
            if res != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            parsed = _parse_f5bot_email(msg)
            if parsed:
                posts.append(parsed)
                log.info("Parsed F5Bot alert: %s", parsed["url"])

            # Mark as read
            mail.store(eid, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()
    except imaplib.IMAP4.error as e:
        log.error("IMAP error: %s", e)
    except Exception as e:
        log.error("Unexpected error fetching F5Bot emails: %s", e)

    return posts