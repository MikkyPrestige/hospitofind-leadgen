# reddit_pm.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Sends personalised Reddit Private Messages (PMs).
# Supports mock mode while Reddit API access is unavailable.

import logging
import time
from config import (
    REDDIT_MOCK_ENABLED,
    DRY_RUN, MAX_PMS_PER_RUN
)
from utils import retry, load_blacklist, is_blacklisted, add_to_blacklist
from google_sheets import append_sent_log

log = logging.getLogger("HospitoFind")

_pms_sent_this_run = 0


# ---------------------------------------------------------------------------
# Mock PM sender (logs to console)
# ---------------------------------------------------------------------------
def _send_pm_mock(username, subject, body):
    """Simulate sending a PM by printing it to the log."""
    log.info("MOCK PM to u/%s", username)
    log.info("  Subject: %s", subject)
    log.info("  Body: %s", body.replace("\n", "\\n"))
    return True


# ---------------------------------------------------------------------------
# Real PM sender (to be implemented with PRAW)
# ---------------------------------------------------------------------------
def _send_pm_real(username, subject, body):
    """
    Placeholder: Uses PRAW to send a PM.
    Will be implemented when Reddit API credentials are approved.
    """
    # TODO: import praw
    # reddit = praw.Reddit(...)
    # reddit.redditor(username).message(subject, body)
    raise NotImplementedError("Real Reddit PM sender not yet available. Use mock mode.")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def send_pm(lead, enriched_lead, messages, subreddit="") -> dict:
    """
    Send a Reddit Private Message to a qualified lead.
    Returns a status dict with the outcome.
    """
    global _pms_sent_this_run

    result = {
        "status": "skipped",
        "reason": "",
        "channel": "pm",
        "username": lead.get("author")
    }

    username = lead.get("author")
    if not username:
        result["reason"] = "no username"
        return result

    # Check blacklist
    bl = load_blacklist()
    if is_blacklisted(username, bl):
        result["reason"] = "blacklisted"
        return result

    # Rate limit
    if _pms_sent_this_run >= MAX_PMS_PER_RUN:
        result["reason"] = "run limit reached"
        return result

    # Dry‑run?
    if DRY_RUN:
        log.info("DRY_RUN: would have PMed u/%s", username)
        result["status"] = "dry_run_skipped"
        result["reason"] = "DRY_RUN enabled"

        # Always log to Sent_Log
        append_sent_log(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            post_url=lead.get("url", ""),
            subreddit=subreddit,
            author=username,
            name=enriched_lead.get("name", ""),
            email=enriched_lead.get("best_email", ""),
            email_confidence=enriched_lead.get("email_confidence", ""),
            outreach_channel="pm",
            status=result["status"],
            notes=result["reason"]
        )
        return result

    # Send (real or mock)
    try:
        if REDDIT_MOCK_ENABLED:
            success = _send_pm_mock(username, messages["pm_subject"], messages["pm_body"])
        else:
            success = _send_pm_real(username, messages["pm_subject"], messages["pm_body"])

        if success:
            _pms_sent_this_run += 1
            result["status"] = "sent"
            result["reason"] = ""
        else:
            result["status"] = "failed"
            result["reason"] = "unknown failure"
    except Exception as e:
        log.error("Failed to PM u/%s: %s", username, e)
        result["status"] = "failed"
        result["reason"] = str(e)

    # Always log to Sent_Log
    append_sent_log(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        post_url=lead.get("url", ""),
        subreddit=subreddit,
        author=username,
        name=enriched_lead.get("name", ""),
        email=enriched_lead.get("best_email", ""),
        email_confidence=enriched_lead.get("email_confidence", ""),
        outreach_channel="pm",
        status=result["status"],
        notes=result.get("reason", "")
    )

    return result


def reset_pm_counter():
    global _pms_sent_this_run
    _pms_sent_this_run = 0