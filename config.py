# config.py
# HospitoFind Intent-Based Lead Generation System — Phase 1 Refined
# This file contains all settings, keywords, subreddits, and message templates.
# NEVER hardcode secrets here; load them from environment variables.

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 1. Reddit API credentials
# =============================================================================
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")  # e.g., "HospitoFindLeadGen (by u/yourusername)"

# =============================================================================
# 2. Gmail credentials (for secondary outreach)
# =============================================================================
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

# =============================================================================
# 3. Google Sheets
# =============================================================================
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME_LEADS = "Leads"
SHEET_NAME_SENT_LOG = "Sent_Log"
SHEET_NAME_BLACKLIST = "Blacklist"

# Path to the service account JSON key file (should NOT be committed)
CREDENTIALS_FILE = "credentials.json"

# =============================================================================
# 4. HospitoFind details (for CAN-SPAM compliance and personalisation)
# =============================================================================
YOUR_NAME = "HospitoFind"
YOUR_WEBSITE = "https://hospitofind.online/"
YOUR_PHYSICAL_ADDRESS = "Your Company Address, Lagos, Nigeria"
UNSUBSCRIBE_LINK = "https://forms.gle/your-unsubscribe-form"   # Replace with actual unsubscribe URL

# =============================================================================
# 5. Keywords (from the approved Refined Keyword List)
# =============================================================================
NEED_KEYWORDS = [
    "need hospital in", "find hospital in", "looking for hospital",
    "need doctor in", "find doctor in", "nearest hospital",
    "good hospital in", "best clinic in", "emergency clinic in",
    "medical care in", "healthcare in", "doctor near me abroad",
    "find clinic in", "emergency room in", "hospital near me",
    "need medical help in"
]

PAIN_KEYWORDS = [
    "can't find hospital", "can't find doctor", "hard to find medical",
    "no good hospitals", "struggling to find care", "difficult to find doctor",
    "where to find hospital", "lost looking for clinic",
    "reliable hospital abroad", "trusted doctor in",
    "bad hospital experience", "medical help abroad"
]

COMPETITOR_KEYWORDS = [
    "Bookimed", "PlacidWay", "MedicalTourism.com", "Qunomedical",
    "WhatClinic", "Health-Tourism.com", "Treatment Abroad",
    "UniClinics", "Medical Departures",
    "Bookimed alternative", "PlacidWay alternative",
    "better than Bookimed", "Bookimed sucks", "PlacidWay bad",
    "frustrated with Bookimed", "instead of PlacidWay"
]

TRAVEL_KEYWORDS = [
    "medical tourism", "medical travel", "health tourism",
    "finding care abroad", "hospital for medical tourist",
    "doctor while traveling", "expats hospital", "digital nomad doctor",
    "sick in", "injured abroad", "international patient",
    "foreign hospital", "hospital anywhere", "find care anywhere",
    "global hospital search"
]

VALUE_KEYWORDS = [
    "verified hospital", "real-time hospital", "hospital availability",
    "clinic finder", "hospital directory", "emergency centers",
    "trusted hospitals worldwide"
]

# Country / city boosters (increase intent score when matched alongside a positive keyword)
COUNTRY_BOOSTERS = [
    # Africa
    "Nigeria", "Kenya", "Ghana", "South Africa", "Egypt",
    "Ethiopia", "Tanzania", "Uganda", "Rwanda", "Morocco",
    "Senegal", "Ivory Coast",
    # Europe
    "UK", "Germany", "France", "Spain", "Italy",
    "Netherlands", "Portugal", "Greece", "Poland", "Romania",
    "Hungary", "Switzerland",
    # North America
    "USA", "Canada", "Mexico", "United States",
    "New York", "Los Angeles", "Toronto", "Vancouver"
]

NEGATIVE_KEYWORDS = [
    "review", "reviews", "promo", "promotion", "advertisement",
    "sponsored", "affiliate", "best hospitals list", "top 10 hospitals",
    "ranking", "study", "survey", "news", "blog", "podcast"
]

# =============================================================================
# 6. Subreddits to scan
# =============================================================================
# Combined list of all subreddits (global + regional)
SUBREDDITS = [
    # Global
    "travel", "digitalnomad", "expat", "solotravel",
    "medical", "health", "askdocs", "travelhacks",
    # Africa
    "Nigeria", "Kenya", "southafrica", "ghana", "Ethiopia",
    "morocco", "africa",
    # Europe
    "europe", "uk", "germany", "france", "spain", "italy",
    "netherlands", "portugal",
    # North America
    "USA", "canada", "mexico", "AskAnAmerican", "AskEurope", "IWantOut"
]

# =============================================================================
# 7. Scanning settings
# =============================================================================
SCAN_INTERVAL_MINUTES = 90          # Look back this many minutes for new posts
POSTS_PER_SUBREDDIT = 100           # Fetch top 100 'new' posts per subreddit

# =============================================================================
# 8. Intent filtering thresholds
# =============================================================================
MIN_INTENT_SCORE = 2                # Posts must reach this score to be considered a lead
                                     #  1 point for any positive keyword match
                                     #  +1 if a pain/need/competitor keyword
                                     #  +1 if a country booster is present
                                     #  -1 for each negative keyword (floor 0)

# =============================================================================
# 9. Lead enrichment
# =============================================================================
EMAIL_PATTERNS = [                  # Common email patterns to guess from username
    "{username}@gmail.com",
    "{username}@yahoo.com",
    "{username}@hotmail.com",
    "{username}@outlook.com"
]
# Enricher will also check Reddit profile for public email

# =============================================================================
# 10. Message templates
# =============================================================================
# For Reddit PM (primary outreach)
PM_SUBJECT_TEMPLATE = "Re: your post in r/{subreddit}"
PM_BODY_TEMPLATE = (
    "Hey {name_or_friend},\n\n"
    "I saw your post about {quote} and I genuinely wanted to help.\n"
    "I'm building HospitoFind (https://hospitofind.online/) to make it easy to find "
    "verified hospitals, clinics, and emergency centers anywhere in the world — "
    "with real-time availability and direct booking.\n\n"
    "If you're still looking, I'd love to help you find the right care. "
    "Just reply here or visit the site.\n\n"
    "Best,\n"
    "Mikky — HospitoFind\n\n"
    "P.S. If you'd rather not be contacted again, simply reply with 'opt-out' and I'll never message you again."
)

# For email (secondary outreach, only when email validated and spam-safe)
EMAIL_SUBJECT_TEMPLATE = "Saw your post about needing a hospital in {location_or_subreddit}"
EMAIL_BODY_TEMPLATE = (
    "Hi {name_or_there},\n\n"
    "I noticed your post in r/{subreddit} about needing medical care. "
    "You said: \"{quote}\"\n\n"
    "I'm Mikky, founder of HospitoFind. We help people discover verified hospitals, clinics, "
    "and emergency centers — with real-time availability and directions.\n\n"
    "If you're still looking, I'd be happy to point you to a trusted provider. "
    "Just reply to this email or visit {site}.\n\n"
    "Warmly,\n"
    "Mikky\n"
    "{site}\n\n"
    "{address}\n\n"
    "Unsubscribe: {unsubscribe_link}"
)

# =============================================================================
# 11. Operational limits & dry-run mode
# =============================================================================
DRY_RUN = True                      # If True, scan and log but DON'T send real messages
MAX_PMS_PER_RUN = 5                 # Limit number of PMs sent per run (safety)
MAX_EMAILS_PER_RUN = 2              # Limit number of emails sent per run (Gmail daily limit is 500)

# =============================================================================
# 12. Logging
# =============================================================================
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "hospitofind.log")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "INFO"                  # Can be DEBUG for more verbose output

# =============================================================================
# 13. Reddit mock mode (to be removed when Reddit API access is granted)
# =============================================================================
REDDIT_MOCK_ENABLED = True         # Set to False when real Reddit credentials work
MOCK_PROFILES = {
    # username: { "public_email": ..., "display_name": ... }
    "john_doe": {
        "public_email": None,
        "display_name": "John Doe"
    },
    "alice_smith": {
        "public_email": "alice.smith@example.com",
        "display_name": "Alice Smith"
    },
    "test_bot_user": {
        "public_email": None,
        "display_name": "Test Bot"
    }
}