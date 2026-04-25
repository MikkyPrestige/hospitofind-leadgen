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
    Extract Reddit post details from an F5Bot alert email.
    Handles the exact format observed in your alerts (quoted titles, 'by author').
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

    # 1. Extract subreddit, title, author using patterns tailored to your F5Bot emails
    subreddit = "unknown"
    title = "Unknown Title"
    author = "unknown_author"

    # Patterns: first for quoted title, second for unquoted title
    patterns = [
        # Quoted title: 'Title' by author
        r"Reddit\s+(?:Comments|Posts)\s+\(/r/(?P<sub>[^)]+)\):\s*'(?P<title>[^']+)'\s+by\s+(?P<author>\S+)",
        # Unquoted title, with "by" at end
        r"Reddit\s+(?:Comments|Posts)\s+\(/r/(?P<sub>[^)]+)\):\s*(?P<title>.+?)\s+by\s+(?P<author>\S+)",
    ]

    for pat in patterns:
        match = re.search(pat, full_text)
        if match:
            subreddit = match.group("sub")
            title = match.group("title").strip()
            author = match.group("author").strip()
            break

    # 2. Fallback: any /r/ for subreddit
    if subreddit == "unknown":
        sr_match = re.search(r'/r/(\w+)', full_text)
        if sr_match:
            subreddit = sr_match.group(1)

    # 3. Fallback for author: look for "u/username" anywhere
    if author == "unknown_author":
        user_match = re.search(r'(?:^|\s)u/(\w+)', full_text)
        if user_match:
            author = user_match.group(1)

    # 4. Use email subject as title fallback
    if title == "Unknown Title" and subject.startswith("F5Bot found something:"):
        keyword_part = subject.split(":", 1)[1].strip()
        title = f"Mention: {keyword_part}"

    # 5. Extract the actual comment text (the sentence containing the keyword)
    post_body = title
    keywords_to_check = ["nearest hospital", "healthcare in", "emergency clinic",
                         "need hospital", "can't find", "hospital near me",
                         "find hospital", "need doctor", "best clinic"]
    lines = body.split('\n')
    for line in lines:
        if any(kw in line.lower() for kw in keywords_to_check):
            post_body = line.strip()
            break

    # 6. Unique ID from the email's Message-ID header
    message_id = msg.get("Message-ID", str(int(time.time())))
    post_id = f"f5bot-{message_id.strip('<>')}"

    # 7. Timestamp from the email's Date header
    date_str = msg["Date"]
    try:
        from email.utils import parsedate_to_datetime
        created_utc = parsedate_to_datetime(date_str).timestamp()
    except Exception:
        created_utc = time.time()

    # 8. Construct a fake URL for deduplication
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

            # Mark as read so it won't be processed again
            mail.store(eid, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()
    except imaplib.IMAP4.error as e:
        log.error("IMAP error: %s", e)
    except Exception as e:
        log.error("Unexpected error fetching F5Bot emails: %s", e)

    return posts