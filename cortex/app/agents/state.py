from typing import TypedDict, Annotated, List, Union, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    State for the specific agent execution.
    """
    input: str
    chat_history: List[BaseMessage]
    # intermediate_steps usually tracks list of (action, observation) tuples
    intermediate_steps: Annotated[List[tuple], operator.add]
    agent_outcome: Union[str, None]
    iteration: int
