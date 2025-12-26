"""
ReAct Agent Graph for InventoryDB Agent
LLM decides which tools to use dynamically
"""

import json
import logging
import pandas as pd
import time
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import OPENAI_API_KEY, engine, QUERY_TIMEOUT_SECONDS
from src.state import AgentState
from src.tools import tools
from src.prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Bind tools to the LLM
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.3, api_key=OPENAI_API_KEY)
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> AgentState:
    """
    Agent reasoning node - LLM decides what to do next
    """
    messages = state["messages"]
    iteration_count = state.get("iteration_count", 0)
    
    logger.info(f"=== AGENT NODE - Iteration {iteration_count + 1} ===")
    logger.info(f"Current messages count: {len(messages)}")
    
    # Check iteration limit
    if iteration_count >= 5:
        logger.warning("Max iterations reached")
        return {
            **state,
            "messages": messages + [SystemMessage(content="Maximum iterations reached. Ending task.")]
        }
    
    # Call LLM with tools
    logger.info("Calling LLM with tools...")
    response = llm_with_tools.invoke(messages)
    
    # Increment iteration count
    new_iteration_count = iteration_count + 1
    
    tool_call_count = len(response.tool_calls) if hasattr(response, 'tool_calls') and response.tool_calls else 0
    logger.info(f"Agent iteration {new_iteration_count}: {tool_call_count} tool calls")
    
    if tool_call_count > 0:
        logger.info(f"Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    
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
    
    logger.info(f"=== CUSTOM TOOL NODE ===")
    
    tool_messages = []
    new_state_updates = {}
    
    # Ensure last message has tool_calls
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        logger.warning("custom_tool_node called but no tool_calls found")
        return state
    
    logger.info(f"Processing {len(last_message.tool_calls)} tool call(s)")
    
    # Execute each tool call
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        logger.info(f"Executing tool: {tool_name} (id={tool_id})")
        
        try:
            if tool_name == "get_database_schema":
                from src.tools import get_database_schema
                result = get_database_schema.invoke({})
                # Cache schema in state
                try:
                    new_state_updates["schema"] = json.loads(result)
                except:
                    pass
                tool_messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_id,
                    name=tool_name
                ))
            
            elif tool_name == "execute_sql_query":
                sql_query = tool_args.get("sql_query", "")
                
                if not engine:
                    result_msg = json.dumps({"error": "Database connection not available"})
                    tool_messages.append(ToolMessage(
                        content=result_msg,
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
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
                    new_state_updates["sql_query"] = sql_query
                    
                    # Return summary to LLM (not full data)
                    result_msg = f"Query executed successfully. Retrieved {total_rows} rows in {execution_time:.3f}s."
                    if total_rows > 0:
                        result_msg += f"\n\nSample data (first 5 rows):\n{query_results_df.head(5).to_string()}"
                    else:
                        result_msg += "\n\nQuery returned 0 rows (empty result set)."
                    
                    tool_messages.append(ToolMessage(
                        content=result_msg,
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
                
                except SQLAlchemyError as e:
                    error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                    if "timeout" in error_msg.lower():
                        error_msg = f"Query timeout ({QUERY_TIMEOUT_SECONDS}s)"
                    logger.error(f"Query failed: {error_msg}")
                    tool_messages.append(ToolMessage(
                        content=f"Error: {error_msg}",
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
            
            else:
                # Unknown tool
                tool_messages.append(ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_id,
                    name=tool_name
                ))
        
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}", exc_info=True)
            tool_messages.append(ToolMessage(
                content=f"Error executing {tool_name}: {str(e)}",
                tool_call_id=tool_id,
                name=tool_name
            ))
    
    logger.info(f"Created {len(tool_messages)} tool message(s)")
    
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
    workflow.add_node("tools", custom_tool_node)
    
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