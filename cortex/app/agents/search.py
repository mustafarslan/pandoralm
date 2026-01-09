import logging
import operator
from typing import Annotated, List, Union, Dict, Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

class GoogleSearchAgent:
    """
    Autonomous agent for conducting web research using Google/Tavily Search.
    Uses LangGraph for state management and iterative refinement.
    """

    def __init__(self):
        # Initialize LLM
        self.llm = self._get_llm()

        # Initialize Tools
        self.search_tool = self._get_search_tool()

        # Build Graph
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _get_llm(self):
        """Get the LLM based on configuration."""
        if settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                api_key=settings.OPENAI_API_KEY
            )
        else:
            # Fallback to Ollama or limited functionality
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(model=settings.LLM_ROUTER_MODEL, base_url=settings.LLM_ROUTER_API_BASE)
            except Exception:
                logger.warning("No LLM provider configured correctly for Agent.")
                return None

    def _get_search_tool(self):
        """Get the search tool (Tavily or Mock)."""
        import os
        tavily_key = os.getenv("TAVILY_API_KEY")

        if tavily_key:
            try:
                from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
                from langchain_community.tools.tavily_search import TavilySearchResults
                wrapper = TavilySearchAPIWrapper(tavily_api_key=tavily_key)
                return TavilySearchResults(api_wrapper=wrapper, max_results=5)
            except ImportError:
                logger.warning("langchain-community not installed or Tavily missing.")
                pass

        # Mock Tool
        def mock_search(query: str):
            return f"[MOCK RESULTS] for '{query}'.\n1. Result A: Relevent info about {query}.\n2. Result B: More details."

        return Tool(
            name="google_search",
            func=mock_search,
            description="Searches Google for the given query."
        )

    # --- Nodes ---

    def search_node(self, state: AgentState):
        """Execute search."""
        query = state["input"]
        iteration = state.get("iteration", 0)

        # If refining, use the last generated query or similar logic (simplified here)
        logger.info(f"Agent executing search for: {query} (Iteration {iteration})")

        try:
            results = self.search_tool.invoke(query)
        except Exception as e:
            results = f"Search failed: {e}"

        # Update input? No, typically we keep input as original query,
        # but specialized agents might refine it.
        # We append directly to intermediate_steps

        return {
            "intermediate_steps": [("search", results)],
            "iteration": iteration + 1
        }

    def analyze_node(self, state: AgentState):
        """Analyze search results."""
        input_query = state["input"]
        steps = state["intermediate_steps"]
        last_result = steps[-1][1] if steps else ""

        prompt = f"""
        User Query: {input_query}
        Search Results: {last_result}

        Does this information answer the query?
        If yes, provide the FINAL ANSWER.
        If no, reply with "RETRY".
        """

        if self.llm:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
        else:
            content = "FINAL ANSWER: Mock answer (LLM missing)"

        if "RETRY" in content and not "FINAL ANSWER" in content:
             return {"agent_outcome": None} # Loop back handles this logic via edges
        else:
             return {"agent_outcome": content}

    # --- Edges ---

    def should_continue(self, state: AgentState):
        """Condition to determine next step."""
        iteration = state.get("iteration", 0)
        outcome = state.get("agent_outcome")

        if outcome:
            return "end"

        if iteration >= 3:
            return "end" # Force end to avoid infinite loop

        return "search" # Retry (simplification: in real agent, 'refine' node would generate new query)

    def _build_graph(self):
        """Define the StateGraph."""
        workflow = StateGraph(AgentState)

        workflow.add_node("search", self.search_node)
        workflow.add_node("analyze", self.analyze_node)

        workflow.set_entry_point("search")

        workflow.add_edge("search", "analyze")

        workflow.add_conditional_edges(
            "analyze",
            self.should_continue,
            {
                "search": "search",
                "end": END
            }
        )

        return workflow

    async def run(self, query: str):
        """Entry point to run the agent."""
        initial_state = {
            "input": query,
            "chat_history": [],
            "intermediate_steps": [],
            "agent_outcome": None,
            "iteration": 0
        }

        result = await self.app.ainvoke(initial_state)

        # If finished with no outcome (max iterations), synthesize what we have
        final = result.get("agent_outcome")
        if not final:
            final = f"Searched {result.get('iteration')} times but could not find a complete answer. Last results: {result.get('intermediate_steps')[-1][1] if result.get('intermediate_steps') else 'None'}"

        return final
