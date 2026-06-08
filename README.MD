# TnP Portal Job Monitor

An automated web scraper and notification system for a college Training & Placement (TnP) portal. The system logs into the portal, scans the "Recent Jobs" table, identifies new company placement drives, and sends a real-time alert via Discord.

## Features

- **Automated Scraping:** Uses Playwright to navigate the TnP portal and extract job listings.
- **Discord Integration:** Sends formatted Discord webhook alerts for newly posted placement drives.
- **Duplicate Prevention:** Maintains state using a `jobs.json` file to ensure you only get notified for new postings.
- **Cloud Automation:** Runs automatically on a schedule using GitHub Actions.

## Tech Stack

- **Language:** Python 3.10
- **Web Automation:** Playwright (sync API)
- **Notifications:** Discord Webhooks
- **State Management:** Local JSON storage (`jobs.json`)
- **Automation & Hosting:** GitHub Actions

## Prerequisites

- Python 3.10+
- A Discord Webhook URL for the channel where you want to receive alerts.
- Your TnP portal credentials.

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Viraj-brn/TnP-Alerts.git
   cd TnP-Alerts
   ```

2. **Create a virtual environment (Optional but recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add your credentials:
   ```env
   PORTAL_USERNAME=your_username
   PORTAL_PASSWORD=your_password
   DISCORD_WEBHOOK_URL=your_discord_webhook_url
   ```

## Usage

To run the scraper manually on your local machine:
```bash
python scraper.py
```

## Cloud Automation

This project is configured to run automatically using GitHub Actions.

To enable this on your own fork/repository:
1. Go to your repository **Settings** > **Secrets and variables** > **Actions**.
2. Add the following Repository Secrets:
   - `PORTAL_USERNAME`
   - `PORTAL_PASSWORD`
   - `DISCORD_WEBHOOK_URL`
3. Enable GitHub Actions in your repository.
4. Ensure your repository has read/write permissions for workflows to commit changes (so it can update `jobs.json`). This can be found under **Settings** > **Actions** > **General** > **Workflow permissions**.

The action will run automatically based on the cron schedule, and update `jobs.json` in the repository to maintain state between runs.