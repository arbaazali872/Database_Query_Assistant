"""
LangGraph workflow definition for InventoryDB Agent
Defines the graph structure and execution flow
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from src.nodes import (
    user_input_node,
    sql_schema_retriever,
    prompt_improver_node,
    query_generator_node,
    query_runner_tool_node,
    user_output_node,
    insights_generator_tool_node
)

logger = logging.getLogger(__name__)


def create_inventory_graph():
    """
    Constructs the LangGraph workflow for InventoryDB Agent
    
    Flow:
    User Input → Schema Retrieval → Prompt Improver → Query Generator → 
    Query Runner → User Output → Insights Generator → END
    
    Simple linear flow with no confirmation loops
    """
    
    workflow = StateGraph(dict)
    
    # Add all nodes
    workflow.add_node("user_input", user_input_node)
    workflow.add_node("schema_retrieval", sql_schema_retriever)
    workflow.add_node("prompt_improver", prompt_improver_node)
    workflow.add_node("query_generator", query_generator_node)
    workflow.add_node("query_runner", query_runner_tool_node)
    workflow.add_node("user_output", user_output_node)
    workflow.add_node("insights_generator", insights_generator_tool_node)
    
    # Set entry point
    workflow.set_entry_point("user_input")
    
    # Add edges (fully linear flow)
    workflow.add_edge("user_input", "schema_retrieval")
    workflow.add_edge("schema_retrieval", "prompt_improver")
    workflow.add_edge("prompt_improver", "query_generator")
    
    # After query generation, check if valid
    workflow.add_conditional_edges(
        "query_generator",
        should_proceed_after_query_generation,
        {
            "run_query": "query_runner",
            "error": END
        }
    )
    
    # Linear flow after successful query execution
    workflow.add_edge("query_runner", "user_output")
    workflow.add_edge("user_output", "insights_generator")
    workflow.add_edge("insights_generator", END)
    
    # Compile the graph
    app = workflow.compile()
    
    logger.info("LangGraph workflow compiled successfully")
    
    return app


def should_proceed_after_query_generation(state: Dict[str, Any]) -> str:
    """
    Conditional edge: Check if SQL generation was successful
    
    Returns:
        "run_query" if SQL is valid, "error" otherwise
    """
    if state.get("sql_valid") is True:
        return "run_query"
    else:
        return "error"


def run_graph(user_query: str, show_sql: bool = False, display_cap: int = 500) -> Dict[str, Any]:
    """
    Execute the entire graph from start to finish
    
    Args:
        user_query: Natural language query from user
        show_sql: Whether to display generated SQL in UI
        display_cap: Maximum rows to display (default: 500)
    
    Returns:
        Final state dictionary with results
    """
    app = create_inventory_graph()
    
    initial_state = {
        "user_input": user_query,
        "show_sql": show_sql,
        "display_cap": display_cap,
        "metadata": {},
    }
    
    logger.info(f"Executing graph for query: {user_query[:100]}...")
    
    result = app.invoke(initial_state)
    
    logger.info("Graph execution completed")
    
    return result