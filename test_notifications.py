import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

PORTAL_USERNAME = os.environ.get("PORTAL_USERNAME")
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD")
LOGIN_URL = "https://tp.bitmesra.co.in/login.html"

def low_cpu_summarize(text):
    """Filters out fluff instantly by keeping lines with operational keywords."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    important_lines = []
    
    keywords = [
        "date", "time", "venue", "link", "eligible", "shortlist", 
        "rescheduled", "deadline", "mandatory", "test", "interview", "slot"
    ]
    
    for line in lines:
        if any(kw in line.lower() for kw in keywords):
            important_lines.append(f"• {line}")
            
    if not important_lines and lines:
        important_lines = lines[:3] 
        
    return "\n".join(important_lines)

def test_tray():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to login page...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            
            print("Logging in...")
            page.get_by_role("textbox", name="Enter username").fill(PORTAL_USERNAME)
            page.get_by_role("textbox", name="Enter password").fill(PORTAL_PASSWORD)
            page.get_by_role("button", name="Login").click()
            
            print("Opening the notification tray page...")
            # Click View All on the dashboard to reach the News & Events table
            page.get_by_role("link", name="View All").click()
            
            # Wait for the specific DataTables element to load
            page.wait_for_selector("table tbody tr", timeout=15000)
            
            # Anchor the URL so we can reliably return to this exact view later
            news_events_url = page.url
            print(f"Anchored News & Events URL: {news_events_url}")
            
            print("Scanning notice entries to collect titles...")
            # CRITICAL FIX: Only grab links inside the table body!
            links = page.locator("table tbody tr td a")
            count = links.count()
            
            notice_titles = []

            for i in range(count):
                text = links.nth(i).inner_text().strip()
                # If there's text, add it to our processing list (ignoring duplicates)
                if text and text not in notice_titles:
                    notice_titles.append(text)

            print(f"\nFound {len(notice_titles)} genuine notice targets in the table.")
            print(f"Collected notice titles: {notice_titles[:3]} ...")

            # Process the first 2 notice titles sequentially
            # Process the first 2 notice titles sequentially
            for idx, title in enumerate(notice_titles[:10]):
                print(f"\n🚀 --- [Notice #{idx + 1}] Processing: {title} ---")
                
                notice_link = page.locator(f"table tbody tr td a:has-text('{title}')").first
                
                if notice_link.count() == 0:
                    print(f"⚠️ Could not locate link element for '{title}'. Skipping.")
                    continue
                    
                notice_link.click()
                page.wait_for_timeout(2000)
                
                # --- NEW TEXT EXTRACTION NET ---
                raw_body = ""
                
                # Attempt 1: Look for paragraph tags (Standard format)
                paragraphs = page.locator("p")
                if paragraphs.count() > 0:
                    raw_body = "\n".join([p.inner_text().strip() for p in paragraphs.all() if p.inner_text().strip()])
                
                # Attempt 2: If paragraphs are empty, grab the Bootstrap card/panel container
                if not raw_body:
                    panel = page.locator(".card-body, .content-wrapper, .modal-body, .main-panel").first
                    if panel.count() > 0:
                        raw_body = panel.inner_text().strip()
                        
                # Attempt 3: Ultimate fallback - grab all text and let the summarizer filter it
                if not raw_body:
                    raw_body = page.locator("body").inner_text().strip()
                # ---------------------------------
                
                if raw_body:
                    print("\n[Raw Extraction Success]:")
                    # Print a preview so it doesn't flood your terminal if it grabs the whole page
                    print(raw_body[:400] + "..." if len(raw_body) > 400 else raw_body)
                    
                    print("\n[Lightweight Summary Output]:")
                    print(low_cpu_summarize(raw_body))
                else:
                    print("\n⚠️ Clicked successfully, but absolutely no text was found. (It might be an image-only notice).")
                
                print("-" * 50)
                
                print("Returning to notification list...")
                page.goto(news_events_url, wait_until="domcontentloaded")
                page.wait_for_selector("table tbody tr", timeout=10000)
                
        except PlaywrightTimeoutError:
            print("\n❌ Timeout Error: Element interaction timed out.")
        except Exception as e:
            print(f"\n❌ Error encountered: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_tray()