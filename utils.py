# utils.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Shared helper functions: logging, blacklist, deduplication, retry.

import os
import csv
import time
import logging
from functools import wraps
from config import LOG_DIR, LOG_FILE, LOG_FORMAT, LOG_LEVEL


# ---------------------------------------------------------------------------
# 1. Logging setup (used by main.py and all modules)
# ---------------------------------------------------------------------------
def setup_logging():
    """Configure logging to both a file and the console."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("HospitoFind")


# ---------------------------------------------------------------------------
# 2. Blacklist helpers
# ---------------------------------------------------------------------------
BLACKLIST_FILE = os.path.join("data", "blacklist.txt")


def load_blacklist():
    """Return a set of blacklisted usernames and email addresses (lowercase)."""
    blacklist = set()
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                entry = line.strip().lower()
                if entry:
                    blacklist.add(entry)
    return blacklist


def add_to_blacklist(entry):
    """Add a username or email to the local blacklist file (one per line)."""
    entry = entry.strip().lower()
    if not entry:
        return
    os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def is_blacklisted(username_or_email, blacklist_set=None):
    """Check if a username or email is in the blacklist (case‑insensitive)."""
    if blacklist_set is None:
        blacklist_set = load_blacklist()
    return username_or_email.strip().lower() in blacklist_set


# ---------------------------------------------------------------------------
# 3. Deduplication (local CSV)
# ---------------------------------------------------------------------------
SENT_LEADS_CSV = os.path.join("data", "sent_leads.csv")


def load_sent_ids():
    """Return a set of post IDs/URLs that have already been actioned."""
    sent = set()
    if os.path.exists(SENT_LEADS_CSV):
        with open(SENT_LEADS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "Post_URL" in row:
                    sent.add(row["Post_URL"].strip())
    return sent


def save_sent_lead(timestamp, post_url, subreddit, author, name, email,
                   email_confidence, outreach_channel, status, notes):
    """Append a row to the local deduplication CSV."""
    file_exists = os.path.exists(SENT_LEADS_CSV)
    os.makedirs(os.path.dirname(SENT_LEADS_CSV), exist_ok=True)
    with open(SENT_LEADS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Post_URL", "Subreddit", "Author",
                             "Name", "Email", "Email_Confidence",
                             "Outreach_Channel", "Status", "Notes"])
        writer.writerow([timestamp, post_url, subreddit, author, name, email,
                         email_confidence, outreach_channel, status, notes])


# ---------------------------------------------------------------------------
# 4. Retry decorator (for network calls)
# ---------------------------------------------------------------------------
def retry(max_attempts=3, delay=2, backoff=2, exceptions=(Exception,)):
    """
    Decorator that retries a function on failure.

    :param max_attempts: total attempts (1 original + retries)
    :param delay: initial delay in seconds
    :param backoff: multiplier for delay after each attempt
    :param exceptions: tuple of exception types to catch
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    logger = logging.getLogger("HospitoFind")
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s. Retrying in %ds...",
                        attempt, max_attempts, func.__name__, e, _delay
                    )
                    time.sleep(_delay)
                    _delay *= backoff
        return wrapper
    return decorator