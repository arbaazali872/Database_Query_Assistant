"""
ReAct Agent Graph for InventoryDB Agent
LLM decides which tools to use dynamically
"""

import json
import logging
import pandas as pd
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END

from config import client
from src.state import AgentState
from src.tools import tools, get_database_schema, generate_sql_query, execute_sql_query, generate_insights_from_data
from src.prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Bind tools to the LLM
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> AgentState:
    """
    Agent reasoning node - LLM decides what to do next
    """
    messages = state["messages"]
    iteration_count = state.get("iteration_count", 0)
    
    # Check iteration limit
    if iteration_count >= 5:
        logger.warning("Max iterations reached")
        return {
            **state,
            "messages": messages + [SystemMessage(content="Maximum iterations reached. Ending task.")]
        }
    
    # Call LLM with tools
    response = llm_with_tools.invoke(messages)
    
    # Increment iteration count
    new_iteration_count = iteration_count + 1
    
    logger.info(f"Agent iteration {new_iteration_count}: {len(response.tool_calls)} tool calls")
    
    return {
        **state,
        "messages": messages + [response],
        "iteration_count": new_iteration_count
    }


def custom_tool_node(state: AgentState) -> AgentState:
    """
    Custom tool execution node that captures DataFrames and updates state
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    new_state_updates = {}
    
    # Execute each tool call
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            # Execute the appropriate tool
            if tool_name == "get_database_schema":
                result = get_database_schema.invoke({})
                # Cache schema in state
                try:
                    new_state_updates["schema"] = json.loads(result)
                except:
                    pass
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_id))
            
            elif tool_name == "generate_sql_query":
                result = generate_sql_query.invoke(tool_args)
                # Store SQL in state
                if not result.startswith("ERROR"):
                    new_state_updates["sql_query"] = result
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_id))
            
            elif tool_name == "execute_sql_query":
                sql_query = tool_args.get("sql_query", "")
                
                # Execute query and capture DataFrame
                from src.tools import engine, QUERY_TIMEOUT_SECONDS
                from sqlalchemy import text
                from sqlalchemy.exc import SQLAlchemyError
                import time
                
                if not engine:
                    result_msg = json.dumps({"error": "Database connection not available"})
                    tool_messages.append(ToolMessage(content=result_msg, tool_call_id=tool_id))
                    continue
                
                try:
                    start_time = time.time()
                    
                    with engine.connect() as connection:
                        connection.execute(text(f"SET statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
                        result = connection.execute(text(sql_query))
                        query_results_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    
                    execution_time = time.time() - start_time
                    total_rows = len(query_results_df)
                    
                    logger.info(f"Query executed: {total_rows} rows in {execution_time:.3f}s")
                    
                    # Store DataFrame in state (for Streamlit)
                    new_state_updates["query_results"] = query_results_df
                    
                    # Return summary to LLM (not full data)
                    result_msg = f"Query executed successfully. Retrieved {total_rows} rows in {execution_time:.3f}s."
                    if total_rows > 0:
                        result_msg += f"\n\nSample data (first 3 rows):\n{query_results_df.head(3).to_string()}"
                    
                    tool_messages.append(ToolMessage(content=result_msg, tool_call_id=tool_id))
                
                except SQLAlchemyError as e:
                    error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                    if "timeout" in error_msg.lower():
                        error_msg = f"Query timeout ({QUERY_TIMEOUT_SECONDS}s)"
                    logger.error(f"Query failed: {error_msg}")
                    tool_messages.append(ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_id))
            
            elif tool_name == "generate_insights_from_data":
                # Get DataFrame from state
                df = state.get("query_results")
                user_question = state.get("user_input", "")
                
                if df is None or len(df) == 0:
                    result = "No data available to generate insights."
                else:
                    # Prepare data summary for insights
                    from src.prompts import INSIGHTS_GENERATOR_SYSTEM
                    from src.utils import call_llm
                    
                    rows = len(df)
                    data_summary = f"""
Results: {rows} rows

Sample data (first 10 rows):
{df.head(10).to_string()}
"""
                    
                    user_message = f"""Original question: {user_question}

Query results:
{data_summary}

Generate 2-3 concise insights."""
                    
                    result = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
                    
                    if result:
                        new_state_updates["insights"] = result
                
                tool_messages.append(ToolMessage(content=result or "Insights generated.", tool_call_id=tool_id))
        
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            tool_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_id))
    
    # Return updated state
    return {
        **state,
        **new_state_updates,
        "messages": messages + tool_messages
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Determine if agent should continue or end
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check iteration limit
    if state.get("iteration_count", 0) >= 5:
        return "end"
    
    # If LLM makes tool calls, continue to tools node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end
    return "end"


def create_react_graph():
    """
    Create the ReAct agent graph
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", custom_tool_node)  # Use custom tool node
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # After tools, always go back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile
    app = workflow.compile()
    
    logger.info("ReAct graph compiled successfully")
    
    return app


def run_agent(user_query: str) -> dict:
    """
    Execute the ReAct agent
    
    Args:
        user_query: Natural language question from user
    
    Returns:
        Final state with results
    """
    app = create_react_graph()
    
    # Initialize state
    initial_state = {
        "messages": [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            HumanMessage(content=user_query)
        ],
        "user_input": user_query,
        "iteration_count": 0
    }
    
    logger.info(f"Starting ReAct agent for query: {user_query[:100]}...")
    
    # Run the graph
    result = app.invoke(initial_state)
    
    logger.info("ReAct agent completed")
    
    return result