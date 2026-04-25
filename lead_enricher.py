# lead_enricher.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Extracts name and email from a Reddit username and post content.
# For now, the profile lookup is a placeholder that returns None.
# Email validation uses syntax + MX checking.

import logging
import re
from email_validator import validate_email, EmailNotValidError
from dns import resolver

from config import (
    EMAIL_PATTERNS, REDDIT_MOCK_ENABLED, MOCK_PROFILES
)

log = logging.getLogger("HospitoFind")


# ---------------------------------------------------------------------------
# Placeholder: Reddit profile lookup (to be implemented after Reddit API grant)
# ---------------------------------------------------------------------------
def _fetch_reddit_profile(username):
    """
    Fetch Reddit profile data.
    If REDDIT_MOCK_ENABLED, uses dummy MOCK_PROFILES from config.
    Otherwise, uses PRAW (to be implemented when Reddit API is available).
    """
    if REDDIT_MOCK_ENABLED:
        # Mock mode: return dummy profile if username exists in MOCK_PROFILES
        mock_data = MOCK_PROFILES.get(username.lower(), {})
        log.debug("Mock profile for %s: %s", username, mock_data)
        return {
            "public_email": mock_data.get("public_email"),
            "display_name": mock_data.get("display_name")
        }
    else:
        # TODO: Real PRAW implementation
        # import praw
        # reddit = praw.Reddit(...)
        # user = reddit.redditor(username)
        # ... get public info ...
        return {}


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------
def extract_name(username, post_text=""):
    """
    Try to find a real name. Looks in:
        - Reddit profile (placeholder)
        - Post text (crude heuristic: capitalized words not in a blacklist)
    If the result looks generic or is "Keyword", fall back to the Reddit username.
    """
    profile = _fetch_reddit_profile(username)
    display_name = profile.get("display_name")
    if display_name and len(display_name) > 1:
        return display_name

    # Very simple heuristic: find the first word that starts with a capital
    # and is not a common stopword, the username, or a known junk word
    stopwords = {"I", "I'm", "I'll", "I've", "Hey", "Hi", "Hello",
                 "Thanks", "Please", "My", "Where", "What", "When",
                 "Why", "How", "Can", "Do", "Does", "Is", "Are",
                 "Keyword", "Reddit", "F5Bot", "Alert", "Unknown"}
    words = post_text.split()
    for word in words:
        clean = word.strip(",.?!;:'\"")
        if clean and clean[0].isupper() and clean not in stopwords and clean != username:
            if not re.search(r'[0-9]', clean):
                return clean
    # Fall back to username
    return username


# ---------------------------------------------------------------------------
# Email generation & validation
# ---------------------------------------------------------------------------
def check_mx_record(domain):
    """Return True if the domain has MX records."""
    try:
        answers = resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except Exception:
        return False


def validate_email_syntax(email):
    """Return True if email has valid syntax (RFC compliant)."""
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def generate_email_guesses(username):
    """Generate email addresses from common patterns using the username."""
    guesses = []
    for pattern in EMAIL_PATTERNS:
        guesses.append(pattern.format(username=username))
    return guesses


def validate_and_rank_emails(emails):
    """
    Validate a list of emails. Returns list of dicts:
    [{"email": ..., "confidence": "high"|"medium"|"low"}, ...]
    Confidence: high = syntax + MX both ok, medium = syntax only, low = invalid.
    """
    results = []
    for email in emails:
        try:
            valid_syntax = validate_email_syntax(email)
            if not valid_syntax:
                results.append({"email": email, "confidence": "low"})
                continue
            # Extract domain for MX check
            domain = email.split("@")[1]
            mx_ok = check_mx_record(domain)
            if mx_ok:
                results.append({"email": email, "confidence": "high"})
            else:
                results.append({"email": email, "confidence": "medium"})
        except Exception:
            results.append({"email": email, "confidence": "low"})
    return results


def enrich_lead(username, post_text=""):
    """
    Main entry point: enrich a Reddit lead with name and possible email addresses.
    Returns dict:
        {
            "username": str,
            "name": str or None,
            "public_email": str or None,
            "guessed_emails": list of {"email": str, "confidence": str},
            "best_email": str or None,
            "email_confidence": str or None
        }
    """
    profile = _fetch_reddit_profile(username)
    public_email = profile.get("public_email")
    name = extract_name(username, post_text)

    # ------------------------------------------------------------
    # Safety: if the username is a placeholder, skip email guessing
    # ------------------------------------------------------------
    if username.lower() in ("unknown_author", "deleted", "removed", "keyword"):
        return {
            "username": username,
            "name": name,
            "public_email": None,
            "guessed_emails": [],
            "best_email": None,
            "email_confidence": None
        }

    # If profile has a public email, validate it
    if public_email:
        validated = validate_and_rank_emails([public_email])
        best = validated[0] if validated else None
        return {
            "username": username,
            "name": name,
            "public_email": best["email"] if best and best["confidence"] != "low" else None,
            "guessed_emails": validated,
            "best_email": best["email"] if best and best["confidence"] != "low" else None,
            "email_confidence": best["confidence"] if best else None
        }

    # Otherwise generate guesses from patterns
    guessed_raw = generate_email_guesses(username)
    validated = validate_and_rank_emails(guessed_raw)

    best = None
    best_email = None
    best_confidence = None
    for entry in validated:
        if entry["confidence"] == "high" and best is None:
            best = entry
            best_email = entry["email"]
            best_confidence = "high"
        elif entry["confidence"] == "medium" and best is None:
            best = entry
            best_email = entry["email"]
            best_confidence = "medium"

    # Fallback to first low confidence if none above
    if best is None and validated:
        best = validated[0]
        best_email = best["email"]
        best_confidence = "low"

    return {
        "username": username,
        "name": name,
        "public_email": None,
        "guessed_emails": validated,
        "best_email": best_email,
        "email_confidence": best_confidence
    }