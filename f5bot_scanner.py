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
    posts = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Fetch ALL unread emails (ignore sender for now)
        status, messages = mail.search(None, 'UNSEEN')
        if status == "OK":
            email_ids = messages[0].split()
            log.info("Found %d total unread emails", len(email_ids))
            for eid in email_ids[:20]:   # limit for safety
                res, msg_data = mail.fetch(eid, "(RFC822)")
                if res != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode_email_header(msg["Subject"])
                from_addr = msg["From"]
                log.info("Unseen – From: %s | Subject: %s", from_addr, subject)

                # If we find any email containing "f5bot" in the sender, parse it
                if "f5bot" in from_addr.lower():
                    parsed = _parse_f5bot_email(msg)
                    if parsed:
                        posts.append(parsed)
                        log.info("Successfully parsed F5Bot alert")
                    else:
                        log.warning("Failed to parse F5Bot email")
                # Do NOT mark as read so we can reuse for testing
        mail.close()
        mail.logout()
    except Exception as e:
        log.error("Error: %s", e)
    return posts