
from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:3001/")
        
        # Login
        if "keycloak" in page.url:
            page.fill("#username", "admin")
            page.fill("#password", "admin")
            page.click("#kc-login")
            page.wait_for_url("http://localhost:3001/", timeout=15000)
            
        page.wait_for_timeout(3000)
        
        # Click Get Started
        if page.is_visible("button:has-text('Get Started')"):
            print("Clicking Get Started")
            page.click("button:has-text('Get Started')")
            time.sleep(3)
        
        print(f"URL: {page.url}")
        print("--- HTML START ---")
        print(page.content())
        print("--- HTML END ---")
        browser.close()

if __name__ == "__main__":
    run()
