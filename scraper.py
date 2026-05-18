import os
import json
from urllib.parse import urljoin
import urllib.parse
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Load environment variables (useful for local testing)
load_dotenv()

# Configuration
PORTAL_USERNAME = os.environ.get("PORTAL_USERNAME")
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD")


JOBS_FILE = "jobs.json"

# Note: Replace these with your actual college TnP portal URLs
LOGIN_URL = "https://tp.bitmesra.co.in/login.html"
DASHBOARD_URL = "https://tp.bitmesra.co.in/"

def load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=4)

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_discord_alert(company, deadline, apply_link):
    # Discord expects a JSON payload with a "content" key
    message = {
        "content": (
            f"🚨 **New Placement Drive!**\n\n"
            f"🏢 **Company:** {company}\n"
            f"⏰ **Deadline:** {deadline}\n"
            f"🔗 **Apply Here:** {apply_link}"
        )
    }
    
    # Send a POST request to the Webhook URL
    response = requests.post(DISCORD_WEBHOOK_URL, json=message)
    
    # Discord returns a 204 status code for a successful webhook post
    if response.status_code == 204:
        print(f"Discord alert sent successfully for {company}!")
    else:
        print(f"Failed to send alert. Status code: {response.status_code}")

def main():
    # Validate environment variables
    required_vars = [
        "PORTAL_USERNAME", "PORTAL_PASSWORD", 
        "DISCORD_WEBHOOK_URL"
    ]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    jobs_data = load_jobs()
    new_jobs_found = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to login page...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            
            print("Logging in...")
            # Using the exact locators from Playwright Codegen
            page.get_by_role("textbox", name="Enter username").fill(PORTAL_USERNAME)
            page.get_by_role("textbox", name="Enter password").fill(PORTAL_PASSWORD)
            page.get_by_role("button", name="Login").click()
            
            print("Waiting for dashboard/table to load...")
            # Wait for the DataTables element specifically.
            page.wait_for_selector("table tbody tr", timeout=60000)
            
            print("Scanning recent jobs...")
            rows = page.locator("table tbody tr")
            row_count = rows.count()
            print(f"Found {row_count} rows in the table.")
            
            for i in range(row_count):
                row = rows.nth(i)
                columns = row.locator("td")
                
                # Check if the row has enough columns
                if columns.count() >= 4:
                    company = columns.nth(0).inner_text().strip()
                    deadline = columns.nth(1).inner_text().strip()
                    
                    # Extract the href from the <a> tag in Column 3 (0-indexed -> 3 is the 4th column)
                    link_element = columns.nth(3).locator("a").first
                    href = link_element.get_attribute("href")
                    
                    if href:
                        absolute_link = urljoin(page.url, href)
                        
                        # Create unique ID to prevent duplicates
                        unique_id = f"{company}_{deadline}".replace(" ", "_")
                        
                        if unique_id not in jobs_data:
                            print(f"New job detected: {company}")
                            
                            job_info = {
                                "company": company,
                                "deadline": deadline,
                                "link": absolute_link
                            }
                            
                            # For testing, only send an alert for the first job to avoid spam, but save all past jobs!
                            if not new_jobs_found:
                                send_discord_alert(company, deadline, absolute_link)
                            
                            # Update local state
                            jobs_data[unique_id] = job_info
                            new_jobs_found = True
                            
        except PlaywrightTimeoutError:
            print("Timeout Error: The page or element took too long to load.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            browser.close()

    if new_jobs_found:
        print("Saving updated jobs.json...")
        save_jobs(jobs_data)
    else:
        print("No new jobs found.")

if __name__ == "__main__":
    main()
