# google_sheets.py
# HospitoFind Lead Generation System — Phase 1 Refined
# Read/write to Google Sheets using a service account (gspread).

import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SHEET_ID, SHEET_NAME_LEADS, SHEET_NAME_SENT_LOG, SHEET_NAME_BLACKLIST, CREDENTIALS_FILE
from utils import retry

log = logging.getLogger("HospitoFind")

# ---------------------------------------------------------------------------
# Authentication and sheet helpers
# ---------------------------------------------------------------------------
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

_client = None  # cached authenticated client


def _get_client():
    """Return a gspread Client, creating it once."""
    global _client
    if _client is None:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
        _client = gspread.authorize(creds)
    return _client


def _open_sheet(sheet_name):
    """Open a specific sheet tab by name."""
    gc = _get_client()
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(sheet_name)


# ---------------------------------------------------------------------------
# Lead logging
# ---------------------------------------------------------------------------
@retry(max_attempts=3, delay=2, exceptions=(Exception,))
def append_lead(timestamp, post_url, subreddit, author, name, email,
                email_confidence, outreach_channel, status, notes=""):
    """
    Append a row to the 'Leads' sheet.
    All parameters are strings; status can be 'Qualified', 'Sent', 'Failed', etc.
    """
    ws = _open_sheet(SHEET_NAME_LEADS)
    row = [timestamp, post_url, subreddit, author, name, email,
           email_confidence, outreach_channel, status, notes]
    ws.append_row(row, value_input_option="USER_ENTERED")
    log.info("Lead appended to sheet: %s (%s)", author, status)


@retry(max_attempts=3, delay=2, exceptions=(Exception,))
def append_sent_log(timestamp, post_url, subreddit, author, name, email,
                    email_confidence, outreach_channel, status, notes=""):
    """Append a row to the 'Sent_Log' sheet (same columns as Leads)."""
    ws = _open_sheet(SHEET_NAME_SENT_LOG)
    row = [timestamp, post_url, subreddit, author, name, email,
           email_confidence, outreach_channel, status, notes]
    ws.append_row(row, value_input_option="USER_ENTERED")
    log.info("Sent log appended for: %s", author)


# ---------------------------------------------------------------------------
# Blacklist operations
# ---------------------------------------------------------------------------
def get_blacklist():
    """Return a set of lowercased blacklisted usernames/emails from the sheet."""
    ws = _open_sheet(SHEET_NAME_BLACKLIST)
    records = ws.get_all_values()
    blacklist = set()
    for row in records[1:]:  # skip header
        if row and row[0].strip():
            blacklist.add(row[0].strip().lower())
    return blacklist


def add_to_blacklist_sheet(entry):
    """Append a username or email to the Blacklist sheet."""
    ws = _open_sheet(SHEET_NAME_BLACKLIST)
    ws.append_row([entry.strip().lower()], value_input_option="USER_ENTERED")
    log.info("Blacklisted: %s", entry)


# ---------------------------------------------------------------------------
# Utility: check connection
# ---------------------------------------------------------------------------
def test_connection():
    """Quick connection test: list sheet titles."""
    gc = _get_client()
    sh = gc.open_by_key(SHEET_ID)
    sheets = [ws.title for ws in sh.worksheets()]
    log.info("Successfully connected to Google Sheet. Tabs: %s", sheets)
    return sheets