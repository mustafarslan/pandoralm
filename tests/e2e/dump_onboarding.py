
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:3001/")
        
        # Login if needed
        if "keycloak" in page.url:
            page.fill("#username", "admin")
            page.fill("#password", "admin")
            page.click("#kc-login")
            page.wait_for_url("http://localhost:3001/", timeout=15000)
            
        page.wait_for_timeout(3000)
        print(f"Final URL: {page.url}")
        print("--- HTML START ---")
        print(page.content())
        print("--- HTML END ---")
        browser.close()

if __name__ == "__main__":
    run()
