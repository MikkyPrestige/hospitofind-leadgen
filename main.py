# main.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Orchestrates scanning, filtering, enrichment, message generation, and outreach.

import logging
import time
from datetime import datetime

from config import DRY_RUN, MIN_INTENT_SCORE
from utils import setup_logging, load_sent_ids, save_sent_lead, load_blacklist, is_blacklisted
from intent_filter import score_post, is_qualified
from lead_enricher import enrich_lead
from message_generator import create_messages
from reddit_pm import send_pm, reset_pm_counter
from email_sender import send_email, reset_email_counter
from google_sheets import append_lead
from config import F5BOT_ENABLED

if F5BOT_ENABLED:
    from f5bot_scanner import fetch_recent_posts
else:
    from reddit_scanner import fetch_recent_posts

log = setup_logging()


def process_lead(post, sent_ids, blacklist):
    """
    Run the full pipeline for a single post.
    Returns True if a message was actually sent (or would have been in mock mode).
    """
    post_url = post.get("url", "")
    author = post.get("author", "")
    subreddit = post.get("subreddit", "")

    # 1. Deduplication
    if post_url in sent_ids:
        log.debug("Already processed: %s", post_url)
        return False

    # 2. Blacklist check
    if is_blacklisted(author, blacklist):
        log.info("Author blacklisted: u/%s", author)
        return False

    # 3. Intent scoring
    score, categories = score_post(post.get("title", ""), post.get("body", ""), subreddit)
    log.info("Post by u/%s scored %d, categories: %s", author, score, categories)
    if score < MIN_INTENT_SCORE:
        log.info("Post score %d below threshold %d — skipping", score, MIN_INTENT_SCORE)
        append_lead(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            post_url=post_url,
            subreddit=subreddit,
            author=author,
            name="",
            email="",
            email_confidence="",
            outreach_channel="",
            status="Low Score",
            notes=f"Score: {score}, Categories: {categories}"
        )
        return False

    # 4. Enrich lead
    enriched = enrich_lead(author, post.get("body", ""))
    # Attach the original post text so the message generator can quote it
    enriched["post_text"] = post.get("body", "")

    # 5. Log qualified lead to Leads sheet
    append_lead(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        post_url=post_url,
        subreddit=subreddit,
        author=author,
        name=enriched.get("name", ""),
        email=enriched.get("best_email", ""),
        email_confidence=enriched.get("email_confidence", ""),
        outreach_channel="pm",  # primary channel
        status="Qualified",
        notes=f"Score: {score}, Categories: {categories}"
    )

    # 6. Generate messages
    messages = create_messages(enriched, subreddit)

    # 7. Send PM (primary channel)
    pm_result = send_pm(post, enriched, messages, subreddit)
    log.info("PM result for u/%s: %s", author, pm_result.get("status"))

    # 8. Send email (secondary channel, if available)
    email_result = send_email(post, enriched, messages, subreddit)
    log.info("Email result for u/%s: %s", author, email_result.get("status"))

    # 9. Mark as processed
    sent_ids.add(post_url)
    save_sent_lead(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        post_url=post_url,
        subreddit=subreddit,
        author=author,
        name=enriched.get("name", ""),
        email=enriched.get("best_email", ""),
        email_confidence=enriched.get("email_confidence", ""),
        outreach_channel="pm",
        status=pm_result.get("status", "unknown"),
        notes=f"Categories: {categories}"
    )

    return True


def main():
    log.info("=" * 60)
    log.info("HospitoFind Lead Generation Run — %s", datetime.now().isoformat())
    log.info("DRY_RUN: %s", DRY_RUN)

    # Reset per‑run counters
    reset_pm_counter()
    reset_email_counter()

    # Load state
    sent_ids = load_sent_ids()
    blacklist = load_blacklist()

    # Fetch posts
    posts = fetch_recent_posts()
    log.info("Fetched %d posts to evaluate", len(posts))

    # Process each post
    processed = 0
    for post in posts:
        try:
            if process_lead(post, sent_ids, blacklist):
                processed += 1
        except Exception as e:
            log.exception("Error processing post %s: %s", post.get("url", ""), e)

    log.info("Run complete. Processed %d new leads.", processed)
    log.info("=" * 60)


if __name__ == "__main__":
    main()