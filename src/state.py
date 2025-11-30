"""
State definition for the InventoryDB Agent LangGraph workflow
Defines the structure of data passed between nodes
"""

from typing import TypedDict, Optional, Any, Dict
import pandas as pd


class AgentState(TypedDict, total=False):
    """
    State schema for the InventoryDB Agent workflow
    
    Fields are added progressively as the graph executes:
    - user_input: Original natural language query from user
    - show_sql: Boolean flag to display SQL in UI
    - display_cap: Maximum rows to display (default: 500)
    - schema: Database schema retrieved from PostgreSQL
    - improved_prompt: Clarified natural language prompt
    - user_confirmed: Whether user confirmed the improved prompt (for future use)
    - sql_query: Generated SQL SELECT statement
    - sql_valid: Boolean indicating if SQL generation was successful
    - query_results: Pandas DataFrame with query results
    - total_rows: Total number of rows returned
    - execution_time: Query execution time in seconds
    - error: Error message if any step fails
    - metadata: Additional metadata for display
    - insights: AI-generated insights about the results
    """
    
    # Input fields
    user_input: str
    show_sql: bool
    display_cap: int
    
    # Schema retrieval
    schema: Dict[str, Any]
    
    # Prompt improvement
    improved_prompt: str
    user_confirmed: Optional[bool]
    
    # Query generation
    sql_query: str
    sql_valid: bool
    
    # Query execution
    query_results: Optional[pd.DataFrame]
    total_rows: int
    execution_time: float
    
    # Error handling
    error: Optional[str]
    
    # Output
    metadata: Dict[str, Any]
    insights: Optional[str]