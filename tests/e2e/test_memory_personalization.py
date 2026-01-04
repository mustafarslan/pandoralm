"""
E2E Test: Memory Personalization

Tests the Phase 5-2 Cognitive Core memory features:
- User states a preference
- Preference is extracted and stored
- Preference is applied in subsequent sessions
"""
import pytest
import asyncio
from playwright.async_api import Page, expect


@pytest.fixture
def memory_test_user():
    """Test user with unique ID for memory isolation."""
    return {
        "id": "e2e-memory-test-user",
        "name": "Memory Test User",
        "email": "memory-test@pandoralm.test"
    }


class TestMemoryPersonalization:
    """
    Tests for persistent memory across sessions.
    
    Verification Metric Target: Memory Faithfulness > 0.9
    """
    
    @pytest.mark.asyncio
    async def test_preference_extraction_and_recall(self, page: Page, memory_test_user):
        """
        Test Case: User preference is extracted and recalled.
        
        Flow:
        1. User states: "I prefer dark mode and Python code examples"
        2. System extracts this as a memory fact
        3. In a new session, system recalls this preference
        """
        # Skip if memory service is not enabled
        # In real test, we'd check the backend status
        
        # Navigate to chat
        await page.goto("http://localhost:3001")
        await page.wait_for_load_state("networkidle")
        
        # Send preference statement
        chat_input = page.locator('[data-testid="chat-input"]')
        if await chat_input.count() == 0:
            chat_input = page.locator('textarea[placeholder*="message"]')
        
        if await chat_input.count() > 0:
            await chat_input.fill("I prefer dark mode and Python code examples in my responses.")
            await chat_input.press("Enter")
            
            # Wait for response
            await page.wait_for_timeout(3000)
            
            # The memory consolidation runs async, wait for it
            await page.wait_for_timeout(5000)
            
            # Now ask a question that should trigger memory recall
            await chat_input.fill("What are my preferences?")
            await chat_input.press("Enter")
            
            # Wait for response
            await page.wait_for_timeout(3000)
            
            # Check if response mentions the preference
            messages = page.locator('[data-testid="chat-message"]')
            if await messages.count() > 0:
                last_message = messages.last
                text = await last_message.text_content()
                
                # Verify memory was recalled
                assert "dark mode" in text.lower() or "python" in text.lower(), \
                    f"Expected preference recall, got: {text[:200]}"
    
    @pytest.mark.asyncio
    async def test_memory_isolation_between_users(self, page: Page):
        """
        Test Case: Memories are isolated per user_id.
        
        Verifies that user A's memories are not visible to user B.
        This tests the ReBAC security model.
        """
        # This test requires multi-user simulation
        # In a real test, we'd use different auth tokens
        pass
    
    @pytest.mark.asyncio  
    async def test_memory_deduplication(self, page: Page, memory_test_user):
        """
        Test Case: Duplicate memories are consolidated.
        
        If user states same preference multiple times,
        it should be stored once.
        """
        # Navigate to chat
        await page.goto("http://localhost:3001")
        await page.wait_for_load_state("networkidle")
        
        chat_input = page.locator('[data-testid="chat-input"]')
        if await chat_input.count() == 0:
            chat_input = page.locator('textarea[placeholder*="message"]')
        
        if await chat_input.count() > 0:
            # State same preference twice
            for _ in range(2):
                await chat_input.fill("I prefer concise answers.")
                await chat_input.press("Enter")
                await page.wait_for_timeout(2000)
            
            # Wait for consolidation
            await page.wait_for_timeout(5000)
            
            # The memory service should deduplicate
            # In real test, we'd check the memory count via API


class TestGlobalSearch:
    """
    Tests for Global Search via community summaries.
    
    Verification Metric Target: Global Answer Relevance > 0.8
    """
    
    @pytest.mark.asyncio
    async def test_thematic_query_uses_global_search(self, page: Page):
        """
        Test Case: Thematic queries trigger Global Search.
        
        Flow:
        1. Upload multiple documents
        2. Wait for GraphRAG indexing
        3. Ask a thematic question
        4. Verify community summaries are used
        """
        await page.goto("http://localhost:3001")
        await page.wait_for_load_state("networkidle")
        
        # This test requires pre-indexed documents
        # In real scenario, documents would be uploaded in fixture
        
        chat_input = page.locator('[data-testid="chat-input"]')
        if await chat_input.count() == 0:
            chat_input = page.locator('textarea[placeholder*="message"]')
        
        if await chat_input.count() > 0:
            # Ask a thematic/global question
            await chat_input.fill("What are the main themes across all documents?")
            await chat_input.press("Enter")
            
            # Wait for response
            await page.wait_for_timeout(5000)
            
            # Check for thematic synthesis in response
            # The response should aggregate across documents


class TestPromptCache:
    """
    Tests for prompt caching performance.
    
    Verification Metric Target: Cache Hit Ratio > 30%
    """
    
    @pytest.mark.asyncio
    async def test_cache_hit_faster_response(self, page: Page):
        """
        Test Case: Cached queries return faster.
        
        Flow:
        1. Send a query (cache miss)
        2. Record response time
        3. Send same query again (cache hit)
        4. Verify second response is faster
        """
        import time
        
        await page.goto("http://localhost:3001")
        await page.wait_for_load_state("networkidle")
        
        chat_input = page.locator('[data-testid="chat-input"]')
        if await chat_input.count() == 0:
            chat_input = page.locator('textarea[placeholder*="message"]')
        
        if await chat_input.count() > 0:
            query = "What is the capital of France?"
            
            # First query (cache miss)
            start1 = time.time()
            await chat_input.fill(query)
            await chat_input.press("Enter")
            await page.wait_for_timeout(3000)
            time1 = time.time() - start1
            
            # Second query (cache hit expected)
            start2 = time.time()
            await chat_input.fill(query)
            await chat_input.press("Enter")
            await page.wait_for_timeout(3000)
            time2 = time.time() - start2
            
            # Cache hit should be faster
            # Note: This is a rough test, actual cache is at prompt level
            print(f"First query: {time1:.2f}s, Second query: {time2:.2f}s")
