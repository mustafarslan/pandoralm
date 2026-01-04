
import re
import json
import time
from playwright.sync_api import sync_playwright

BENCHMARK_FILE = "tests/management_book_benchmarks.md"
OUTPUT_FILE = "tests/benchmark_results.json"
BASE_URL = "http://localhost:3000"

def parse_questions(file_path):
    questions = []
    current_type = None
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if "Vector RAG" in line:
                current_type = "Vector"
            elif "GraphRAG" in line:
                current_type = "Graph"
            elif re.match(r'^\d+\.', line):
                q_text = re.sub(r'^\d+\.\s*', '', line)
                if current_type:
                    questions.append({"type": current_type, "question": q_text})
    return questions

def run_tests():
    questions = parse_questions(BENCHMARK_FILE)
    if not questions:
        print("No questions found in benchmark file.")
        return

    print(f"Loaded {len(questions)} questions.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to {BASE_URL}...")
        try:
            page.goto(BASE_URL)
        except Exception as e:
            print(f"Failed to load {BASE_URL}: {e}")
            print("Make sure the server is running.")
            return

        # Check for login/onboarding
        time.sleep(2)
        if "onboarding" in page.url:
            print("System is in Onboarding mode. Please complete onboarding first.")
            return
        if "login" in page.url or "signin" in page.url:
             print("Login page detected. Attempting to bypass or warn...")
             # Here we might try default credentials if known, but for now we warn.
             print("Please disable authentication or provide credentials in script.")
             # For testing purposes, we assume we might be able to proceed or fail.
        
        # Select workspace if needed (basic heuristic: click first available workspace or just chat)
        # Wait for chat input
        try:
            page.wait_for_selector("textarea#primary-prompt-input", timeout=3000)
            print("Chat input found. Ready to test.")
        except:
             print("Chat input not found on home page. Attempting to navigate to workspace...")
             try:
                 # Try clicking "Send Chat"
                 if page.get_by_text("Send Chat").is_visible():
                     print("Clicking 'Send Chat'...")
                     page.get_by_text("Send Chat").click()
                 # Or try clicking first workspace in sidebar
                 elif page.locator("a[href^='/workspace/']").first.is_visible():
                     print("Clicking first workspace...")
                     page.locator("a[href^='/workspace/']").first.click()
                 
                 page.wait_for_selector("textarea#primary-prompt-input", timeout=10000)
                 print("Chat input found after navigation.")
             except Exception as e:
                 print(f"Chat input not found. URL: {page.url}")
                 page.screenshot(path="tests/debug_failure.png")
                 print("Screenshot saved to tests/debug_failure.png")
                 print(f"Navigation failed: {e}")
                 return

        results = []
        for i, item in enumerate(questions):
            q = item['question']
            q_type = item['type']
            print(f"[{i+1}/{len(questions)}] ({q_type}) Asking: {q}")
            
            try:
                # Type and send
                page.fill("textarea#primary-prompt-input", q)
                # Ensure the send button is clickable
                page.click("button[type='submit']")
                
                # Wait for response completion
                # We wait for the 'Stop Generation' button to APPEAR then DISAPPEAR
                # Or we wait for the Send button to be disabled then enabled.
                
                # Wait for processing to start (Stop button appears)
                # It might appear very quickly or take a moment.
                try:
                     # Stop button usually has an aria-label or specific class.
                     # Based on code: <StopGenerationButton />
                     # If not found, maybe it was too fast?
                     # We'll wait for the send button to become enabled again.
                     # The send button has disabled={isDisabled}
                     
                     # Better: Wait for the chat history len to increase.
                     # But we don't know the previous len easily without tracking.
                     # Let's wait for 'StopGenerationButton' selector if possible, or just a fixed delay + polling for 'Send' button availability.
                     
                     # Wait for answer to start streaming (GraphRAG might take time to switch modes)
                     print("Waiting for generation to start...")
                     page.wait_for_selector("button[aria-label='Stop generating']", timeout=60000)
                     print("Generation started (Stop button appeared).")
                     
                     # Wait for answer to finish (Stop button disappears)
                     print("Waiting for generation to finish...")
                     page.wait_for_selector("button[aria-label='Stop generating']", state="detached", timeout=600000)
                     print("Generation finished.")
                except Exception as e:
                    # Fallback: maybe response was instant or selector failed.
                    print(f"Warning: Stream detection timed out or failed: {e}")
                    print("Waiting 10s extra before capturing text...")
                    time.sleep(10)

                # Capture last message
                # The chat history container is #chat-history
                # Messages are in .bg-theme-bg-chat. Last child might be a scroll button.
                # We want the last message container's text.
                
                last_msg_container = page.locator(".bg-theme-bg-chat").last
                # The text is usually in a .break-words div
                response_text_el = last_msg_container.locator(".break-words").first
                
                if response_text_el.count() > 0:
                     response_text = response_text_el.inner_text()
                else:
                     # Fallback if structure changes
                     response_text = last_msg_container.inner_text()
                
                print(f"Captured response length: {len(response_text)}")
                
                # Check for "Reasoning" or "Graph" UI indicators
                # This is heuristic based on the user's request "Intermediate Reasoning Steps"
                ui_flags = []
                if "Reasoning" in response_text: # Very naive check
                    ui_flags.append("Reasoning_Keyword")
                
                # If there's an internal collapsible element, we might detect it by class
                # But we don't have the class name yet.
                
                results.append({
                    "id": i+1,
                    "type": q_type,
                    "question": q,
                    "response_length": len(response_text),
                    "response_snippet": response_text[:100],
                    "ui_flags": ui_flags
                })
                
            except Exception as e:
                print(f"Error processing question {i+1}: {e}")
                results.append({
                    "id": i+1,
                    "type": q_type,
                    "question": q,
                    "error": str(e)
                })

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Done. Results saved to {OUTPUT_FILE}")
        browser.close()

if __name__ == "__main__":
    run_tests()
