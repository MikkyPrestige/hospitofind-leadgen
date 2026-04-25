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
    Extract Reddit post details from an F5Bot alert email (URL‑less format).
    Returns a dict with keys: id, title, body, author, subreddit, url, created_utc.
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

    full_text = subject + "\n" + body

    # 1. Extract subreddit, title, author
    subreddit = "unknown"
    title = "Unknown Title"
    author = "unknown_author"

    # Try pattern: "Reddit Comments (/r/...): <title> by <author>"
    match = re.search(
        r'Reddit\s+(?:Comments|Posts)\s+\(/r/([^)/]+)\):\s*(.+?)\s+by\s+(\S+)',
        full_text
    )
    if match:
        subreddit = match.group(1)
        title = match.group(2).strip().rstrip('.')
        author = match.group(3).strip()
    else:
        # Fallback 1: "Reddit Comments (/r/...): <title> ..." maybe author at end after "by"
        match2 = re.search(
            r'Reddit\s+(?:Comments|Posts)\s+\(/r/([^)/]+)\):\s*(.+)',
            full_text
        )
        if match2:
            subreddit = match2.group(1)
            rest = match2.group(2).strip()
            if " by " in rest:
                parts = rest.rsplit(" by ", 1)
                title = parts[0].strip()
                author = parts[1].strip().rstrip('.')
            else:
                title = rest
        else:
            sr_match = re.search(r'/r/(\w+)', full_text)
            if sr_match:
                subreddit = sr_match.group(1)

    # 2. If author still unknown, look for "by u/..." or just "u/..."
    if author == "unknown_author":
        user_match = re.search(r'(?:by\s+)?u/(\w+)', full_text)
        if user_match:
            author = user_match.group(1)

    # 3. Use email subject as title if better
    if subject.startswith("F5Bot found something:"):
        keyword_part = subject.split(":", 1)[1].strip()
        if title == "Unknown Title":
            title = f"Mention: {keyword_part}"

    # 4. Extract the actual comment text (sentence containing the keyword)
    post_body = title
    keywords_to_check = ["nearest hospital", "healthcare in", "emergency clinic",
                         "need hospital", "can't find", "hospital near me",
                         "find hospital", "need doctor", "best clinic"]
    lines = body.split('\n')
    for line in lines:
        if any(kw in line.lower() for kw in keywords_to_check):
            post_body = line.strip()
            break

    # 5. Generate a unique ID from the email's Message-ID (or timestamp)
    message_id = msg.get("Message-ID", str(int(time.time())))
    post_id = f"f5bot-{message_id.strip('<>')}"

    # 6. Use email date as timestamp
    date_str = msg["Date"]
    try:
        from email.utils import parsedate_to_datetime
        created_utc = parsedate_to_datetime(date_str).timestamp()
    except Exception:
        created_utc = time.time()

    # 7. Construct a fake URL for deduplication
    url = f"https://reddit.com/r/{subreddit}/comments/{post_id}"

    return {
        "id": post_id,
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

        # Search for unseen emails from the F5Bot sender
        status, messages = mail.search(None, f'(UNSEEN FROM "{F5BOT_SENDER}")')
        if status != "OK":
            log.warning("IMAP search failed: %s", status)
            mail.logout()
            return posts

        email_ids = messages[0].split()
        log.info("Found %d unread F5Bot emails", len(email_ids))

        for eid in email_ids:
            res, msg_data = mail.fetch(eid, "(RFC822)")
            if res != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            parsed = _parse_f5bot_email(msg)
            if parsed:
                posts.append(parsed)
                log.info("Parsed F5Bot alert: %s", parsed["url"])
            else:
                log.warning("Failed to parse F5Bot email. Subject: %s", _decode_email_header(msg["Subject"]))

            # Always log raw body for inspection (first 500 chars)
            raw_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            raw_body = payload.decode("utf-8", errors="replace")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    raw_body = payload.decode("utf-8", errors="replace")
            log.info("Raw email body (first 500 chars): %s", raw_body[:500])

            # Mark as read so it won't be processed again
            mail.store(eid, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()
    except imaplib.IMAP4.error as e:
        log.error("IMAP error: %s", e)
    except Exception as e:
        log.error("Unexpected error fetching F5Bot emails: %s", e)

    return posts