# reddit_scanner.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Fetches recent Reddit posts from target subreddits.
# Supports a mock mode (using dummy data) while Reddit API access is unavailable.

import logging
from datetime import datetime, timedelta, timezone
from config import (
    SUBREDDITS, POSTS_PER_SUBREDDIT, SCAN_INTERVAL_MINUTES,
    REDDIT_MOCK_ENABLED, MOCK_PROFILES
)
from utils import retry

log = logging.getLogger("HospitoFind")

# ---------------------------------------------------------------------------
# Mock data (extended from config MOCK_PROFILES for full post simulation)
# ---------------------------------------------------------------------------
MOCK_POSTS = [
    {
        "id": "mock001",
        "title": "Need hospital in Nairobi urgently",
        "body": "I sprained my ankle and can't find a good clinic. Bookimed let me down.",
        "author": "john_doe",
        "subreddit": "digitalnomad",
        "url": "https://reddit.com/r/digitalnomad/comments/mock001",
        "created_utc": (datetime.now(timezone.utc) - timedelta(minutes=30)).timestamp()
    },
    {
        "id": "mock002",
        "title": "Best hospitals list for medical tourism in Thailand",
        "body": "Here is a review of the top 10 hospitals ranking in Bangkok. podcast episode included.",
        "author": "alice_smith",
        "subreddit": "travel",
        "url": "https://reddit.com/r/travel/comments/mock002",
        "created_utc": (datetime.now(timezone.utc) - timedelta(minutes=45)).timestamp()
    },
    {
        "id": "mock003",
        "title": "Sick in Mexico, need doctor near me abroad",
        "body": "I'm a digital nomad and I've been feeling terrible. Where can I find a reliable hospital?",
        "author": "tom_jones",
        "subreddit": "solotravel",
        "url": "https://reddit.com/r/solotravel/comments/mock003",
        "created_utc": (datetime.now(timezone.utc) - timedelta(minutes=60)).timestamp()
    }
]


# ---------------------------------------------------------------------------
# Real Reddit scanner (to be implemented when PRAW is available)
# ---------------------------------------------------------------------------
def _fetch_posts_real():
    """
    Placeholder: Uses PRAW to fetch posts from all subreddits.
    Will be implemented when Reddit API credentials are approved.
    """
    # TODO: import praw
    # reddit = praw.Reddit(
    #     client_id=...,
    #     client_secret=...,
    #     user_agent=...
    # )
    # posts = []
    # for sub in SUBREDDITS:
    #     for submission in reddit.subreddit(sub).new(limit=POSTS_PER_SUBREDDIT):
    #         ...
    # return posts
    raise NotImplementedError("Real Reddit scanner not yet implemented. Use mock mode.")


# ---------------------------------------------------------------------------
# Public function (dispatches to real or mock)
# ---------------------------------------------------------------------------
@retry(max_attempts=2, delay=2, exceptions=(Exception,))
def fetch_recent_posts():
    """
    Return a list of recent posts from all target subreddits.
    Each post is a dict with keys: id, title, body, author, subreddit, url, created_utc.
    """
    if REDDIT_MOCK_ENABLED:
        log.info("Reddit mock mode active — using dummy posts.")
        return MOCK_POSTS
    else:
        return _fetch_posts_real()