import os
import json
import re
from urllib.parse import urljoin
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Load environment variables
load_dotenv()

PORTAL_USERNAME = os.environ.get("PORTAL_USERNAME")
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

JOBS_FILE = "jobs.json"
LOGIN_URL = "https://tp.bitmesra.co.in/login.html"
NEWS_URL = "https://tp.bitmesra.co.in/newsevents"

def load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r") as f:
            try: 
                data = json.load(f)
                if "jobs" not in data:
                    return {"jobs": data, "notifications": {}}
                return data
            except json.JSONDecodeError: 
                return {"jobs": {}, "notifications": {}}
    return {"jobs": {}, "notifications": {}}

def save_jobs(jobs_data):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs_data, f, indent=4)

def send_discord_alert(content_string):
    payload = {"content": content_string}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Discord alert sent successfully!")
    else:
        print(f"Failed to send alert. Status code: {response.status_code}")

def summarize_news(text):
    """Aggressively filters text to provide a short summary."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    important_lines = []
    
    keywords = ["date", "time", "venue", "link", "eligible", "shortlist", "rescheduled", "deadline", "mandatory", "apply", "register", "inform"]
    
    for line in lines:
        if any(kw in line.lower() for kw in keywords):
            important_lines.append(f"• {line}")
            
    if not important_lines and lines:
        fallback = [line for line in lines if len(line) > 30][:4]
        important_lines = [f"• {line}" for line in fallback]
        
    summary = "\n".join(important_lines)
    
    if len(summary) > 800:
        return summary[:800] + "\n\n... [Truncated]"
        
    return summary if summary else "Please click the link above to read the full notice."

def main():
    required_vars = ["PORTAL_USERNAME", "PORTAL_PASSWORD", "DISCORD_WEBHOOK_URL"]
    if any(not os.environ.get(v) for v in required_vars):
        print("Missing required environment variables. Aborting.")
        return

    database = load_jobs()
    state_changed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # ==========================================
        # LOGIN SEQUENCE
        # ==========================================
        try:
            print("Navigating to login page...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            
            print("Logging in...")
            page.get_by_role("textbox", name="Enter username").fill(PORTAL_USERNAME)
            page.get_by_role("textbox", name="Enter password").fill(PORTAL_PASSWORD)
            page.get_by_role("button", name="Login").click()
        except Exception as e:
            print(f"❌ Failed to reach or complete login screen: {e}")
            browser.close()
            return

        # ==========================================
        # PART 1: SCAN PLACEMENT DRIVES (DASHBOARD)
        # ==========================================
        try:
            print("\n[PART 1] Waiting for jobs table...")
            page.wait_for_selector("table tbody tr", timeout=15000)
            rows = page.locator("table tbody tr")
            
            for i in range(rows.count()):
                row = rows.nth(i)
                columns = row.locator("td")
                if columns.count() >= 4:
                    company = columns.nth(0).inner_text().strip()
                    deadline = columns.nth(1).inner_text().strip()
                    link_element = columns.nth(3).locator("a").first
                    href = link_element.get_attribute("href") if link_element.count() > 0 else None
                    
                    if href:
                        absolute_link = urljoin(page.url, href)
                        unique_id = f"{company}_{deadline}".replace(" ", "_")
                        
                        if unique_id not in database["jobs"]:
                            print(f"New job detected: {company}")
                            
                            msg = f"🚨 **New Placement Drive!**\n\n🏢 **Company:** {company}\n⏰ **Deadline:** {deadline}\n🔗 **Apply Here:** {absolute_link}"
                            send_discord_alert(msg)
                            
                            database["jobs"][unique_id] = {"company": company, "deadline": deadline, "link": absolute_link}
                            state_changed = True
                            
        except PlaywrightTimeoutError:
            print("⚠️ [PART 1] No jobs found on dashboard or table timed out. Proceeding to Part 2...")
        except Exception as e:
            print(f"❌ [PART 1] An error occurred: {e}")

        # ==========================================
        # PART 2: SCAN ALL NOTIFICATIONS (DUAL PATH)
        # ==========================================
        try:
            print("\n[PART 2] Navigating to News & Events...")
            page.goto(NEWS_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("table tbody tr", timeout=15000)
            
            print("Scanning table for all updates...")
            
            table_rows = page.locator("table tbody tr")
            items_to_process = []

            # Step 1: Gather ALL rows and categorize them
            for i in range(table_rows.count()):
                row_text = table_rows.nth(i).inner_text().lower()
                link_locator = table_rows.nth(i).locator("a").first
                
                if link_locator.count() > 0:
                    title = link_locator.inner_text().strip()
                    href = link_locator.get_attribute("href")
                    direct_url = urljoin(NEWS_URL, href) if href else NEWS_URL
                    
                    if title and title not in database["notifications"]:
                        # Tag check: Does the row contain the word "news"?
                        is_news = "news" in row_text
                        items_to_process.append({
                            "title": title, 
                            "url": direct_url, 
                            "is_news": is_news
                        })

            if not items_to_process:
                print("No new notices or HR updates found.")

            # Step 2: Process items based on their category
            for item in items_to_process:
                title = item["title"]
                direct_url = item["url"]
                
                if item["is_news"]:
                    print(f"Processing New 'News' Item: {title}")
                    
                    notice_link = page.locator(f"table tbody tr td a:has-text('{title}')").first
                    if notice_link.count() > 0:
                        notice_link.click()
                        page.wait_for_timeout(2000)
                        
                        # Extract Text
                        raw_body = ""
                        paragraphs = page.locator("p")
                        if paragraphs.count() > 0:
                            raw_body = "\n".join([p.inner_text().strip() for p in paragraphs.all() if p.inner_text().strip()])
                        
                        if not raw_body:
                            panel = page.locator(".card-body, .content-wrapper, .modal-body, .main-panel, td").first
                            if panel.count() > 0:
                                raw_body = panel.inner_text().strip()
                                
                        if not raw_body:
                            raw_body = page.locator("body").inner_text().strip()
                        
                        # Summarize and Alert
                        summary = summarize_news(raw_body) if raw_body else "Please click the link above to read the full notice."
                        msg = f"📰 **New TnP News Announcement!**\n\n📌 **Title:** {title}\n🔗 **Read Full Notice:** {direct_url}\n\n📝 **Quick Summary:**\n{summary}"
                        send_discord_alert(msg)
                        
                        # Save state
                        database["notifications"][title] = {"title": title, "summary": summary}
                        state_changed = True
                        
                        # Reset view back to the list
                        page.goto(NEWS_URL, wait_until="domcontentloaded")
                        page.wait_for_selector("table tbody tr", timeout=10000)
                        
                else:
                    # It's an HR update / Final Result. Skip clicking, send a one-liner!
                    print(f"Processing HR Update: {title}")
                    
                    msg = f"🎯 **New HR / Job Update!**\n\n📌 **Title:** {title}\n🔗 **Check List Here:** {direct_url}"
                    send_discord_alert(msg)
                    
                    # Save state without a summary
                    database["notifications"][title] = {"title": title, "summary": "HR Update (No summary generated)"}
                    state_changed = True
                
        except PlaywrightTimeoutError:
            print("⚠️ [PART 2] No notifications table found or timed out.")
        except Exception as e:
            print(f"❌ [PART 2] An error occurred: {e}")
            
        finally:
            browser.close()

    if state_changed:
        print("\nSaving updates to jobs.json...")
        save_jobs(database)
    else:
        print("\nNo updates found during this cycle. System standing by.")

if __name__ == "__main__":
    main()