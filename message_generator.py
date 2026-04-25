# message_generator.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Creates personalised Reddit PM and email messages from templates.

import logging
from config import (
    PM_SUBJECT_TEMPLATE, PM_BODY_TEMPLATE,
    EMAIL_SUBJECT_TEMPLATE, EMAIL_BODY_TEMPLATE,
    YOUR_WEBSITE, YOUR_PHYSICAL_ADDRESS, UNSUBSCRIBE_LINK
)

log = logging.getLogger("HospitoFind")


def _extract_quote(post_text, max_length=120):
    """
    Return a cleaned, shortened snippet from the post text.
    Used to show the user we actually read their post.
    """
    if not post_text:
        return "your post"
    # Remove extra whitespace and newlines
    clean = " ".join(post_text.split())
    if len(clean) <= max_length:
        return clean
    # Truncate without cutting words
    truncated = clean[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."


def _get_location_or_subreddit(enriched_lead, subreddit=""):
    """
    Try to extract a location string for the email subject.
    Falls back to subreddit name.
    """
    # This is a simple approach; later we can use the country boosters logic.
    # For now, if the post body contains a known country, we could extract it,
    # but to keep it simple: return the subreddit as the location.
    return subreddit if subreddit else "your area"


def _format_name_or_fallback(name):
    """Return the name, or a friendly placeholder."""
    if name and len(name.strip()) > 1:
        return name.strip()
    return "friend"


def generate_pm_content(enriched_lead, subreddit=""):
    """
    Build subject and body for a Reddit Private Message.

    :param enriched_lead: dict from lead_enricher.enrich_lead()
    :param subreddit: the subreddit where the post was found
    :return: (subject, body) strings
    """
    username = enriched_lead.get("username", "there")
    name = _format_name_or_fallback(enriched_lead.get("name"))
    post_text = enriched_lead.get("post_text", "")  # we'll attach this in main.py later
    quote = _extract_quote(post_text)

    subject = PM_SUBJECT_TEMPLATE.format(subreddit=subreddit)
    body = PM_BODY_TEMPLATE.format(
        name_or_friend=name,
        quote=quote
    ).strip()

    log.debug("Generated PM for %s", username)
    return subject, body


def generate_email_content(enriched_lead, subreddit=""):
    """
    Build subject and body for an email outreach.

    :param enriched_lead: dict from lead_enricher.enrich_lead()
    :param subreddit: the subreddit where the post was found
    :return: (subject, body) strings
    """
    username = enriched_lead.get("username", "there")
    name = _format_name_or_fallback(enriched_lead.get("name"))
    post_text = enriched_lead.get("post_text", "")
    quote = _extract_quote(post_text)
    location = _get_location_or_subreddit(enriched_lead, subreddit)

    subject = EMAIL_SUBJECT_TEMPLATE.format(location_or_subreddit=location)
    body = EMAIL_BODY_TEMPLATE.format(
        name_or_there=name,
        subreddit=subreddit,
        quote=quote,
        site=YOUR_WEBSITE,
        address=YOUR_PHYSICAL_ADDRESS,
        unsubscribe_link=UNSUBSCRIBE_LINK
    ).strip()

    log.debug("Generated email for %s", username)
    return subject, body


# ---------------------------------------------------------------------------
# Convenience: create both messages for a lead
# ---------------------------------------------------------------------------
def create_messages(enriched_lead, subreddit=""):
    """
    Return a dict with pm_subject, pm_body, email_subject, email_body,
    ready for the sender modules.
    """
    pm_subject, pm_body = generate_pm_content(enriched_lead, subreddit)
    email_subject, email_body = generate_email_content(enriched_lead, subreddit)

    return {
        "pm_subject": pm_subject,
        "pm_body": pm_body,
        "email_subject": email_subject,
        "email_body": email_body
    }