# HospitoFind Lead Generation System

A zero‑cost, fully automated pipeline that finds people on Reddit who are actively searching for hospitals, clinics, or doctors abroad – and logs them as warm leads, ready for helpful outreach.

The system listens for distress keywords like “can’t find a hospital in…”, extracts real Reddit usernames, filters out bots, and stores qualified leads in Google Sheets. When Reddit API access is granted, it will send one personalised, opt‑out‑able private message to each person, pointing them to **[HospitoFind](https://www.hospitofind.online/)** – a free, verified hospital directory.

> 💡 **Live right now**: The pipeline is running every hour on GitHub Actions using F5Bot alerts (no Reddit API needed). It already collects real, actionable leads.

---

## Features

- 🔎 **Real‑time monitoring** – Detects high‑intent Reddit posts via F5Bot keyword alerts.
- 🧠 **Intent scoring** – Scores each post based on need, pain, competitor frustration, and location.
- 👤 **Real username extraction** – Gets the author’s Reddit username from alert emails.
- 🛡️ **Bot filtering** – Skips AutoModerator, deleted accounts, and other non‑personal users.
- 📧 **Email enrichment** – Attempts to guess and validate an email (when available), with MX record checks.
- ✉️ **Outreach ready** – Generates personalised PM and email templates (dry‑run mode until Reddit API access).
- 📊 **Google Sheets logging** – Full audit trail: Leads, Sent_Log, and Blacklist tabs.
- 🕒 **Hourly automation** – GitHub Actions cron job runs every hour, completely free.
- 🔒 **Compliant** – CAN‑SPAM compliant emails, instant opt‑out, no data stored beyond public post info.

---

## How it works

1. **F5Bot** monitors Reddit for keywords like “need hospital in”, “can’t find doctor”, “Bookimed sucks”, etc. and sends email alerts.
2. Alerts are forwarded to a Gmail inbox (IMAP enabled).
3. Every hour, a Python script fetches unread F5Bot emails, parses the post details, and extracts:
   - Subreddit
   - Post title / body snippet
   - Reddit username (e.g., `u/nattcatttt`)
4. Posts are scored with an intent filter. Low‑score posts (reviews, ads) are ignored.
5. Qualified leads are enriched (name guess, basic email attempt) and logged to Google Sheets.
6. When Reddit API access is granted, the system will automatically send one helpful PM per lead, with an instant opt‑out mechanism.
7. Email outreach is already functional (Outlook via Microsoft Graph OAuth2) but only used when a validated email is available.

---

## Tech Stack

- **Python 3.11+**
- **F5Bot** (free Reddit keyword monitoring)
- **GitHub Actions** (free cron scheduler)
- **Google Sheets API** (free CRM / logging)
- **Microsoft Graph API** (email sending via OAuth2)
- **IMAP** (reading F5Bot emails)

---

## Getting Started

### Prerequisites

- Python 3.10–3.12
- A GitHub account
- A Google account (for Sheets and a Gmail inbox)
- An Outlook account (for sending emails)
- A free [F5Bot](https://f5bot.com) account

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/MikkyPrestige/hospitofind-leadgen.git
   cd hospitofind-leadgen
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # On Windows Git Bash
   pip install -r requirements.txt
   ```

3. **Set up Google Sheets**
   - Create a Google Sheet named `HospitoFind Leads`.
   - Add three tabs: `Leads`, `Sent_Log`, `Blacklist`.
   - Create a Google Cloud service account, download the JSON key, and rename it to `credentials.json`.
   - Share the sheet with the service account email (Editor rights).
   - Copy the Sheet ID from the URL.

4. **Set up Outlook (Microsoft Graph)**
   - Register an app in the Azure Portal with `Mail.Send` permission and “personal Microsoft accounts” support.
   - Enable public client flows.
   - Use the device code flow to get a refresh token (run the provided helper script).

5. **Configure F5Bot**
   - Create alerts for keywords like `"need hospital in"`, `"can't find doctor"`, `"Bookimed sucks"`.
   - Set your notification email to a Gmail address (IMAP enabled).
   - Generate a Gmail app password for IMAP access.

6. **Create a `.env` file**
   ```
   REDDIT_CLIENT_ID=dummy
   REDDIT_CLIENT_SECRET=dummy
   REDDIT_USER_AGENT=HospitoFindLeadGen (by u/yourbot)
   EMAIL_ADDRESS=hospitoFind@outlook.com
   EMAIL_APP_PASSWORD=your_gmail_app_password_for_imap
   SHEET_ID=your_google_sheet_id
   CLIENT_ID=your_azure_client_id
   TENANT_ID=your_azure_tenant_id
   REFRESH_TOKEN=your_refresh_token
   F5BOT_ENABLED=True
   ```

7. **Run the pipeline locally**
   ```bash
   python main.py
   ```

8. **Deploy on GitHub Actions**
   - Add all `.env` values as repository secrets.
   - Add `GOOGLE_CREDENTIALS_JSON` secret with the full content of `credentials.json`.
   - The workflow (`.github/workflows/main.yml`) will run every hour automatically.

---

## Configuration

All keywords, subreddits, scoring thresholds, and message templates are in `config.py`. You can adjust:

- `NEED_KEYWORDS`, `PAIN_KEYWORDS`, `COMPETITOR_KEYWORDS`, etc.
- `SUBREDDITS` (the full list of target subreddits)
- `MIN_INTENT_SCORE` (default 2)
- `DRY_RUN` (set to `False` only when Reddit API access is live)
- `F5BOT_ENABLED` (toggle between F5Bot and direct Reddit scanner)
- `MAX_PMS_PER_RUN`, `MAX_EMAILS_PER_RUN`

---

## Compliance & Ethics

- This bot only responds to **public, unsolicited requests for help**. It never spams.
- Every message includes a clear **opt‑out** instruction. Opt‑outs are permanently blacklisted.
- We do **not** store any non‑public Reddit data. Only the post URL and username are kept for deduplication.
- Email outreach complies with **CAN‑SPAM** regulations (physical address and unsubscribe link included).
- The project is fully transparent and open‑source to demonstrate responsible building.

---

## Roadmap

- [x] F5Bot fallback scanner (Reddit API‑free)
- [x] Intent scoring and bot filtering
- [x] Outlook email sending via OAuth2
- [x] Google Sheets logging
- [ ] Reddit PM sending (pending API approval)
- [ ] Twitter/X monitoring (Phase 2)
- [ ] LLM‑based scoring and reply drafting

---

## About HospitoFind

**[HospitoFind](https://www.hospitofind.online/)** is a free, verified hospital and clinic directory that helps anyone, anywhere find reliable medical care. This lead‑generation system is an automated way to reach people who are already asking for the exact kind of help HospitoFind provides.

---
