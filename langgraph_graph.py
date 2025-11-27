from langgraph.graph import StateGraph, END
from typing import Dict, Any

# Import nodes from the nodes file
from langgraph_nodes import *

def create_inventory_graph():
    """
    Constructs the LangGraph workflow for InventoryDB Agent
    
    Flow:
    User Input → Schema Retrieval → Prompt Improver → [User Confirms] →
    Query Generator → Query Runner → User Output → Insights Generator → END
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
    
    # Add edges (linear flow with some conditionals)
    workflow.add_edge("user_input", "schema_retrieval")
    workflow.add_edge("schema_retrieval", "prompt_improver")
    
    # After prompt improvement, wait for user confirmation
    # In Streamlit, this will be handled by the UI
    # For now, we'll make it conditional
    workflow.add_conditional_edges(
        "prompt_improver",
        should_continue_after_prompt_improvement,
        {
            "generate_query": "query_generator",
            "improve_again": "prompt_improver",
            "wait_for_confirmation": END  # Pause for user input in UI
        }
    )
    
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
# GRAPH EXECUTION HELPERS
# =============================================================================

def run_graph_until_confirmation(app, initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the graph until it needs user confirmation for improved prompt
    Returns the state at the confirmation point
    """
    # Set user_confirmed to None to trigger wait state
    initial_state["user_confirmed"] = None
    
    result = app.invoke(initial_state)
    return result

def continue_graph_after_confirmation(app, state: Dict[str, Any], confirmed: bool) -> Dict[str, Any]:
    """
    Continue graph execution after user confirms/edits the improved prompt
    """
    state["user_confirmed"] = confirmed
    
    if confirmed:
        # User confirmed - proceed with query generation
        result = app.invoke(state)
        return result
    else:
        # User wants to edit - increment edit count
        state["edit_count"] = state.get("edit_count", 0) + 1
        
        # Check if we've hit max edits (prevent infinite loop)
        if state["edit_count"] >= 10:
            state["error"] = "Maximum edit attempts reached. Please submit a new query."
            return state
        
        # Re-run prompt improver with edited input
        result = app.invoke(state)
        return result

# =============================================================================
# CONVENIENCE FUNCTION FOR FULL EXECUTION (for testing)
# =============================================================================

def run_full_graph(user_query: str, show_sql: bool = False, display_cap: int = 500) -> Dict[str, Any]:
    """
    Run the entire graph with auto-confirmation (for testing purposes)
    In production, this will be split into stages with UI interaction
    """
    app = create_inventory_graph()
    
    initial_state = {
        "user_input": user_query,
        "show_sql": show_sql,
        "display_cap": display_cap,
        "edit_count": 0,
        "metadata": {},
        "user_confirmed": True,  # Auto-confirm for testing
    }
    print(f"initial_state: {initial_state}")
    
    result = app.invoke(initial_state)
    return result