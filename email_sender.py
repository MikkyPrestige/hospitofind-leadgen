# email_sender.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Sends emails via Microsoft Graph API using OAuth2 refresh token.

import logging
import time
import json
import urllib.request
import urllib.parse
import urllib.error

from config import (
    EMAIL_ADDRESS, CLIENT_ID, REFRESH_TOKEN,
    DRY_RUN, MAX_EMAILS_PER_RUN,
    YOUR_PHYSICAL_ADDRESS, UNSUBSCRIBE_LINK
)
from utils import retry, load_blacklist, is_blacklisted
from google_sheets import append_sent_log

log = logging.getLogger("HospitoFind")

_emails_sent_this_run = 0


# ---------------------------------------------------------------------------
# Spam trigger words (same as before)
# ---------------------------------------------------------------------------
SPAM_TRIGGER_WORDS = [
    "free", "act now", "limited time", "click here", "click below",
    "order now", "buy now", "call now", "100% free", "money back",
    "guaranteed", "winner", "earn money", "make money", "cash bonus",
    "congratulations", "you have been selected", "urgent", "exclusive deal"
]


def spam_score(text):
    text_lower = text.lower()
    score = 0
    for word in SPAM_TRIGGER_WORDS:
        if word in text_lower:
            score += 1
    return score


# ---------------------------------------------------------------------------
# OAuth2 token management
# ---------------------------------------------------------------------------
@retry(max_attempts=3, delay=3, backoff=2, exceptions=(Exception,))
def _get_access_token():
    """
    Uses the REFRESH_TOKEN to obtain a new access token silently.
    This is the only OAuth2 call needed after initial setup.
    """
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "scope": "https://graph.microsoft.com/mail.send offline_access"
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"No access_token in response: {token_data}")
        new_refresh = token_data.get("refresh_token")
        if new_refresh:
            log.info("New refresh token received; update your .env if rotation is desired.")
        return access_token


# ---------------------------------------------------------------------------
# Core send via Graph API
# ---------------------------------------------------------------------------
@retry(max_attempts=3, delay=3, backoff=2, exceptions=(Exception,))
def _send_email_via_graph_api(to_address, subject, body):
    """Sends email using Microsoft Graph API with access token."""
    token = _get_access_token()
    endpoint = f"https://graph.microsoft.com/v1.0/users/{EMAIL_ADDRESS}/sendMail"

    email_msg = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": to_address}}
            ]
        },
        "saveToSentItems": "true"
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(email_msg).encode("utf-8")
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req) as resp:
        if resp.status == 202:
            log.info("Email sent successfully to %s", to_address)
            return True
        else:
            log.error("Unexpected response status: %d", resp.status)
            return False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def send_email(lead, enriched_lead, messages, subreddit="") -> dict:
    global _emails_sent_this_run

    result = {
        "status": "skipped",
        "reason": "",
        "channel": "email",
        "to_address": None
    }

    email_address = enriched_lead.get("best_email")
    if not email_address:
        result["reason"] = "no email available"
        return result

    confidence = enriched_lead.get("email_confidence", "low")
    if confidence == "low":
        result["reason"] = "email confidence too low"
        return result

    bl = load_blacklist()
    if is_blacklisted(email_address, bl) or is_blacklisted(lead.get("author", ""), bl):
        result["reason"] = "blacklisted"
        return result

    if _emails_sent_this_run >= MAX_EMAILS_PER_RUN:
        result["reason"] = "run limit reached"
        return result

    full_text = messages["email_subject"] + " " + messages["email_body"]
    score = spam_score(full_text)
    if score > 1:
        log.warning("Email to %s held: spam score %d", email_address, score)
        result["reason"] = f"spam score {score} too high"
        return result

    if DRY_RUN:
        log.info("DRY_RUN: would have emailed %s", email_address)
        result["status"] = "dry_run_skipped"
        result["reason"] = "DRY_RUN enabled"

        # Always log to Sent_Log
        append_sent_log(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            post_url=lead.get("url", ""),
            subreddit=subreddit,
            author=lead.get("author", ""),
            name=enriched_lead.get("name", ""),
            email=email_address,
            email_confidence=confidence,
            outreach_channel="email",
            status=result["status"],
            notes=result["reason"]
        )
        return result

    # Send real email
    try:
        success = _send_email_via_graph_api(
            to_address=email_address,
            subject=messages["email_subject"],
            body=messages["email_body"]
        )
        if success:
            _emails_sent_this_run += 1
            result["status"] = "sent"
            result["to_address"] = email_address
        else:
            result["status"] = "failed"
            result["reason"] = "unknown API failure"
    except Exception as e:
        log.error("Failed to email %s: %s", email_address, e)
        result["status"] = "failed"
        result["reason"] = str(e)

    # Always log to Sent_Log
    append_sent_log(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        post_url=lead.get("url", ""),
        subreddit=subreddit,
        author=lead.get("author", ""),
        name=enriched_lead.get("name", ""),
        email=email_address,
        email_confidence=confidence,
        outreach_channel="email",
        status=result["status"],
        notes=result.get("reason", "")
    )

    return result


def reset_email_counter():
    global _emails_sent_this_run
    _emails_sent_this_run = 0