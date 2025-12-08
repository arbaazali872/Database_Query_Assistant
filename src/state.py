"""
State definition for the InventoryDB Agent ReAct workflow
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from operator import add
import pandas as pd


class AgentState(TypedDict):
    """
    State schema for ReAct agent workflow
    
    Fields:
    - messages: Conversation history (HumanMessage, AIMessage, ToolMessage)
    - user_input: Original user query
    - schema: Database schema (cached)
    - sql_query: Generated SQL query
    - query_results: Query execution results (DataFrame)
    - insights: Generated insights
    - iteration_count: Number of agent iterations
    """
    
    # Core ReAct state
    messages: Annotated[Sequence[BaseMessage], add]
    
    # User input
    user_input: str
    
    # Cached data
    schema: dict
    
    # Tool outputs
    sql_query: str
    query_results: pd.DataFrame
    insights: str
    
    # Control
    iteration_count: int