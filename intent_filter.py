# intent_filter.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Scores a Reddit post for lead intent using keyword lists from config.py.

import logging
from config import (
    NEED_KEYWORDS, PAIN_KEYWORDS, COMPETITOR_KEYWORDS,
    TRAVEL_KEYWORDS, VALUE_KEYWORDS,
    COUNTRY_BOOSTERS, NEGATIVE_KEYWORDS,
    MIN_INTENT_SCORE
)

log = logging.getLogger("HospitoFind")


def score_post(title, body, subreddit=""):
    """
    Return an intent score for a post (0 = no intent, higher = stronger lead).

    Scoring logic:
      +1  if ANY positive keyword matches (need, pain, competitor, travel, value)
      +1  if a pain or need keyword is found (strong intent)
      +1  if a country booster is present
      -1  for EACH negative keyword found (floor 0)

    Returns:
        (score, matched_categories)
        matched_categories is a set of category labels e.g. {'need','pain','country'}
    """
    text = (title + " " + body).lower()
    score = 0
    matched = set()

    # Combine positive categories
    positive_categories = {
        "need": NEED_KEYWORDS,
        "pain": PAIN_KEYWORDS,
        "competitor": COMPETITOR_KEYWORDS,
        "travel": TRAVEL_KEYWORDS,
        "value": VALUE_KEYWORDS,
    }

    # First pass: any positive keyword
    any_positive = False
    for category, keywords in positive_categories.items():
        for kw in keywords:
            if kw.lower() in text:
                any_positive = True
                matched.add(category)
                break  # one match per category is enough

    if any_positive:
        score += 1
        log.debug("Positive keyword found, score +1")

    # Second pass: strong intent boost (need or pain)
    strong_keywords = NEED_KEYWORDS + PAIN_KEYWORDS
    for kw in strong_keywords:
        if kw.lower() in text:
            score += 1
            matched.add("strong_intent")
            log.debug("Strong intent keyword found, score +1")
            break

    # Country booster
    for country in COUNTRY_BOOSTERS:
        if country.lower() in text:
            score += 1
            matched.add("country")
            log.debug("Country booster found: %s, score +1", country)
            break

    # Negative keywords
    for nk in NEGATIVE_KEYWORDS:
        if nk.lower() in text:
            score -= 1
            matched.add("negative")
            log.debug("Negative keyword found: %s, score -1", nk)
            if score < 0:
                score = 0
            break  # only apply negative penalty once for simplicity

    return max(score, 0), matched


def is_qualified(title, body, subreddit=""):
    """Return True if the post meets the minimum intent score."""
    score, matched = score_post(title, body, subreddit)
    return score >= MIN_INTENT_SCORE


# ---------------------------------------------------------------------------
# Utility: basic filtering of already-seen posts (duplicates within a batch)
# ---------------------------------------------------------------------------
def filter_duplicates(posts, seen_ids):
    """
    Remove posts whose URL or ID is already in `seen_ids` set.
    `posts` is a list of dicts with at least a 'url' key.
    """
    unique = []
    for post in posts:
        post_id = post.get("url", "")
        if post_id not in seen_ids:
            seen_ids.add(post_id)
            unique.append(post)
    return unique