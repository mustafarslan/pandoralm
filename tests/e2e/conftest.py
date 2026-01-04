
import pytest
import re
from playwright.sync_api import Playwright, APIRequestContext, expect

@pytest.fixture(scope="session")
def api_request_context(playwright: Playwright) -> APIRequestContext:
    request_context = playwright.request.new_context(
        base_url="http://localhost:3001"
    )
    yield request_context
    request_context.dispose()

@pytest.fixture(scope="session")
def admin_session(browser):
    """
    Logs in once as admin and saves storage state.
    """
    context = browser.new_context(record_video_dir="tests/e2e/videos")
    page = context.new_page()
    
    try:
        # 1. Navigate to home (redirects to Keycloak)
        page.goto("http://localhost:3001")
        
        # 2. Keycloak Login (if redirected)
        if "keycloak" in page.url or "auth" in page.url:
            page.fill("#username", "admin")
            page.fill("#password", "admin")  # Default docker-compose creds
            page.click("#kc-login")
            page.wait_for_url("http://localhost:3001/", timeout=15000)
            
        # Wait for either home or onboarding
        try:
            page.wait_for_url(re.compile(r".*/onboarding.*|.*/$"), timeout=15000)
        except:
            print(f"Login failed: Timeout 15000ms exceeded.")
            # If it times out here, it means we didn't land on home or onboarding.
            # This is likely a failure, but we'll let subsequent checks handle it.
            pass
            
        # 3. Wait for app to be ready and stabilize
        try:
            expect(page).to_have_title(re.compile(r".+"))
            page.wait_for_timeout(2000) # Give React Router time to redirect
        except:
            pass
            
        # 3.5 Handle Onboarding (if redirected)
        # Check iteratively if we landed on onboarding
        for _ in range(5):
            if "onboarding" in page.url:
                break
            page.wait_for_timeout(500)

        if "onboarding" in page.url:
            print("Onboarding detected. Completing...")
            # Click buttons until we reach home
            # Loop max 10 times to avoid infinite
            for _ in range(50):
                print(f"Onboarding Step URL: {page.url}")
                if "onboarding" not in page.url:
                    break
                # Handle specific steps based on URL or Content
                if "llm-preference" in page.url:
                    print("Selecting Ollama...")
                    try:
                        # Select the specific container (last matches the innermost div)
                        page.locator("div").filter(has=page.locator("input[value='ollama']")).last.click(timeout=2000)
                    except Exception as e: 
                        print(f"Ollama click failed: {e}")
                
                if "vector-database" in page.url:
                    print("Selecting LanceDB...")
                    try:
                        page.locator("div").filter(has=page.locator("input[value='lancedb']")).last.click(timeout=2000)
                    except Exception as e:
                        print(f"LanceDB click failed: {e}")
                    
                if "user-setup" in page.url:
                    print("Selecting 'Just me'...")
                    page.get_by_text("Just me").click()

                # Try to click common "Next" or "Continue" buttons
                # We use a broad strategy because button text varies
                try:
                    # Primary buttons usually have these labels or classes
                    next_btns = [
                        "button[type='submit']",
                        "button:has-text('Next')", 
                        "button:has-text('Continue')",
                        "button:has-text('Get Started')",
                        "button:has-text('Skip')",
                        "button:has-text('No')",
                        "button[aria-label='Continue']",
                        "button[aria-label='Next']"
                    ]
                    
                    clicked = False
                    for selector in next_btns:
                        print(f"Checking for {selector}...")
                        try:
                            # Use wait_for_selector to give it a chance to appear
                            if page.wait_for_selector(selector, state="visible", timeout=1000):
                                print(f"Clicking onboarding button: {selector}")
                                page.click(selector)
                                page.wait_for_timeout(2000) # Wait for transition
                                clicked = True
                                break
                        except:
                            continue
                            
                    if not clicked:
                        print("Stuck in onboarding, no known button found.")
                        print(page.content()) # DUMP HTML
                        break
                except Exception as e:
                    print(f"Onboarding step error: {e}")
                    
        # 4. Save state
        page.wait_for_url("http://localhost:3001/", timeout=5000)
        storage_path = "tests/e2e/state.json"
        context.storage_state(path=storage_path)
        yield storage_path
        
    except Exception as e:
        print(f"Login failed: {e}")
        # Yield empty if fail, test will fail later
        yield None
    finally:
        context.close()

@pytest.fixture(scope="function")
def authenticated_page(browser, admin_session):
    """
    Returns a page with admin session loaded.
    """
    if not admin_session:
        pytest.fail("Admin session failed to initialize")
        
    context = browser.new_context(
        storage_state=admin_session,
        record_video_dir="tests/e2e/videos"
    )
    page = context.new_page()
    yield page
    context.close()
