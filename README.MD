The Master Prompt
Context & Objective
Act as a senior software engineer. I need to build an automated web scraper and notification system for my college's Training & Placement (TnP) portal. The system will log into the portal, scan the "Recent Jobs" table, identify new company placement drives, and send a WhatsApp alert to my phone. It must run automatically on the cloud for free.

Tech Stack

Language: Python 3.10

Web Automation: Playwright (sync API)

Notifications: Twilio WhatsApp Sandbox API

State Management: Local jobs.json file (to prevent duplicate alerts)

Automation & Hosting: GitHub Actions (Cron jobs)

Environment Management: python-dotenv (for local testing)

Folder Structure Required

Plaintext
tnp-job-monitor/
├── .github/workflows/tnp_scraper.yml
├── scraper.py
├── requirements.txt
├── .gitignore
├── .env
└── jobs.json
System Logic & Requirements

1. scraper.py (The Core Engine)

Load environment variables (Username, Password, Twilio SID, Twilio Token).

Load jobs.json to check previously seen jobs.

Launch Playwright (Chromium, headless).

Navigate to the TnP portal login page and authenticate using the credentials.

Wait for the dashboard to load, specifically targeting the DataTables element (table tbody tr).

Loop through the table rows and extract:

Company Name (Column 0)

Deadline (Column 1)

View & Apply Link (Extract href from the <a> tag in Column 3). Ensure relative URLs are converted to absolute URLs.

Create a unique ID for each row (e.g., Company_Deadline).

If the unique ID is not in jobs.json:

Trigger the Twilio WhatsApp API to send a formatted markdown message to my verified number.

Add the new job to the dictionary.

If new jobs were found, overwrite jobs.json with the updated dictionary.

Future-proofing note: Include inline comments indicating where I can eventually add a function to click the "Apply" link and scrape the job description to filter specifically for Data Scientist and Finance roles before sending the alert.

2. GitHub Actions (.github/workflows/tnp_scraper.yml)

Trigger: Cron schedule every 3 hours, plus workflow_dispatch for manual triggers.

Environment: ubuntu-latest.

Steps:

Checkout repository.

Setup Python 3.10.

Install dependencies from requirements.txt and run playwright install chromium.

Run scraper.py while safely injecting GitHub Secrets as environment variables (PORTAL_USERNAME, PORTAL_PASSWORD, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).

Configure Git user (bot) to commit and push any changes made to jobs.json back to the main branch so the state is maintained for the next run.

3. Setup Files

requirements.txt: Must include playwright, twilio, and python-dotenv.

.gitignore: Must explicitly ignore .env, __pycache__/, and .pytest_cache/. Do NOT ignore jobs.json.

Please generate the complete, production-ready code for all of these files based on these exact specifications. Ensure the Python code includes robust error handling for network timeouts or missing DOM elements.