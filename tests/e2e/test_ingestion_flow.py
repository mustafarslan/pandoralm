
import pytest
import time
from playwright.sync_api import Page, expect

def test_ingestion_flow(authenticated_page: Page):
    """
    Verifies that a file uploaded via the Chat UI appears in the Vector Inspector.
    """
    page = authenticated_page
    
    # 1. Navigate to Home
    page.goto("http://localhost:3001/")

    # 1.5 Select a Workspace if not selected
    if page.url == "http://localhost:3001/":
        print("On Home dashboard. Navigating to first workspace...")
        try:
            # Click first workspace link in sidebar
            page.locator('a[href^="/workspace/"]').first.click()
            page.wait_for_url("**/workspace/**")
        except Exception as e:
            print(f"Could not select workspace: {e}")
            # Try creating one? No, assume exists.
    
    # Handle Onboarding if present (Skip)
    # TODO: Add logic if needed. Assuming user is logged in and has workspace.
    
    # 2. Upload File
    # Ensure the file uploader is present
    try:
        page.wait_for_selector("input[type='file']", state="attached", timeout=5000)
        page.set_input_files("input[type='file']", "tests/fixtures/upload_test.txt")
        print("File set to input.")
    except Exception as e:
        # Fallback: Maybe we are on onboarding?
        print(f"Upload input not found: {e}")
        # print page content for debug
        print(page.content())
        pytest.fail("Could not find file uploader input")

    # 3. Wait for Upload Completion toast/indicator
    # Look for "uploaded and embedded" or similar text
    # Or just wait a few seconds since we don't have exact selector for success toast
    time.sleep(10) 
    
    # 4. Navigate to Admin Console
    print("Navigating to Admin Console: /settings/admin-console/vectors")
    page.goto("http://localhost:3001/settings/admin-console/vectors")
    
    # 5. Verify Vector Inspector
    # Wait for table to load
    try:
        page.wait_for_selector("table", timeout=10000)
    except:
        print("Table not found in Vector Ops")
        print(page.content())
        pytest.fail("Table not found")
    
    # Check if our file content is there
    # The file content is "This is an E2E test document..."
    # We look for a cell containing "E2E test document"
    try:
        expect(page.get_by_text("E2E test document")).to_be_visible(timeout=10000)
        print("Found uploaded chunk in Inspector!")
    except:
        # Maybe we need to select the workspace?
        # The dropdown defaults to "default" or first one.
        # If we uploaded to "default" (default workspace), it should be there.
        # Try finding the dropdown and validating it has chunks.
        options = page.locator("select option").all_inner_texts()
        print(f"Available Workspaces: {options}")
        pytest.fail("Chunk text not found in table")
        
    # Success
