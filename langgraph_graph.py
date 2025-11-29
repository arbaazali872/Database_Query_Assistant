from langgraph.graph import StateGraph, END
from typing import Dict, Any

# Import nodes from the nodes file
from langgraph_nodes import *

def create_inventory_graph():
    """
    Constructs the LangGraph workflow for InventoryDB Agent
    
    Flow:
    User Input → Schema Retrieval → Prompt Improver → Query Generator → 
    Query Runner → User Output → Insights Generator → END
    
    Simple linear flow with no confirmation loops
    """
    
    # Initialize the graph with our state schema
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
            "error": END  # Stop if error
        }
    )
    
    # Linear flow after successful query execution
    workflow.add_edge("query_runner", "user_output")
    workflow.add_edge("user_output", "insights_generator")
    workflow.add_edge("insights_generator", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app

# =============================================================================
# CONDITIONAL EDGES
# =============================================================================

def should_proceed_after_query_generation(state: Dict[str, Any]) -> str:
    """Check if SQL generation was successful"""
    if state.get("sql_valid") is True:
        return "run_query"
    else:
        return "error"

# =============================================================================
# GRAPH EXECUTION HELPER
# =============================================================================

def run_graph(user_query: str, show_sql: bool = False, display_cap: int = 500) -> Dict[str, Any]:
    """
    Run the entire graph from start to finish
    Simple execution with no pauses or confirmations
    """
    app = create_inventory_graph()
    
    initial_state = {
        "user_input": user_query,
        "show_sql": show_sql,
        "display_cap": display_cap,
        "metadata": {},
    }
    
    result = app.invoke(initial_state)
    return result