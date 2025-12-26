"""
State definition for the InventoryDB Agent ReAct workflow
"""

from typing import TypedDict, Sequence, Optional
from langchain_core.messages import BaseMessage
import pandas as pd


class AgentState(TypedDict):
    """
    State schema for ReAct agent workflow
    
    Fields:
    - messages: Conversation history (HumanMessage, AIMessage, ToolMessage)
    - user_input: Original user query
    - schema: Database schema (cached after first retrieval)
    - sql_query: Generated SQL query
    - query_results: Query execution results (DataFrame)
    - iteration_count: Number of agent iterations
    """
    
    # Core ReAct state
    messages: Sequence[BaseMessage]
    
    # User input
    user_input: str
    
    # Cached data (optional - populated during execution)
    schema: Optional[dict]
    
    # Tool outputs (optional - populated during execution)
    sql_query: Optional[str]
    query_results: Optional[pd.DataFrame]
    
    # Control
    iteration_count: int