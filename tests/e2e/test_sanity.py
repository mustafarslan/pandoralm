
import pytest
import re
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page):
    try:
        page.goto("http://localhost:3001")
        # Check title is not empty
        expect(page).to_have_title(re.compile(r".+"))
        print(f"Page Title: {page.title()}")
    except Exception as e:
        pytest.fail(f"Failed to load homepage: {e}")
