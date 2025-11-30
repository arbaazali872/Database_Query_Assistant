"""
LangGraph nodes for InventoryDB Agent
Each node represents a step in the NL-to-SQL workflow
"""

import json
import time
import logging
from typing import Dict, Any
import pandas as pd
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from config import engine, QUERY_TIMEOUT_SECONDS
from src.utils import call_llm, extract_sql_from_response, validate_select_query
from src.prompts import (
    PROMPT_IMPROVER_SYSTEM,
    QUERY_GENERATOR_SYSTEM,
    INSIGHTS_GENERATOR_SYSTEM
)

logger = logging.getLogger(__name__)

# =============================================================================
# NODE FUNCTIONS
# =============================================================================

def user_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point - initializes the state with user input
    In Streamlit, this will be called after user submits the form
    """
    logger.info(f"Starting workflow with query: {state.get('user_input', '')[:100]}...")
    return state


def sql_schema_retriever(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve database schema from PostgreSQL
    Fetches tables, columns, data types, primary keys, and foreign keys
    """
    if not engine:
        logger.warning("No database connection - using placeholder schema")
        placeholder_schema = {
            "tables": {
                "projects": {
                    "columns": {
                        "project_id": "INTEGER",
                        "project_name": "TEXT",
                        "start_date": "DATE",
                        "end_date": "DATE",
                        "client_id": "INTEGER",
                        "status": "TEXT",
                        "budget": "NUMERIC"
                    },
                    "primary_key": "project_id",
                    "foreign_keys": {"client_id": "clients.client_id"}
                },
                "clients": {
                    "columns": {
                        "client_id": "INTEGER",
                        "client_name": "TEXT",
                        "industry": "TEXT",
                        "contact_email": "TEXT"
                    },
                    "primary_key": "client_id",
                    "foreign_keys": {}
                },
                "orders": {
                    "columns": {
                        "order_id": "INTEGER",
                        "project_id": "INTEGER",
                        "order_date": "DATE",
                        "amount": "NUMERIC",
                        "status": "TEXT"
                    },
                    "primary_key": "order_id",
                    "foreign_keys": {"project_id": "projects.project_id"}
                }
            }
        }
        return {**state, "schema": placeholder_schema}
    
    try:
        inspector = inspect(engine)
        schema = {"tables": {}}
        
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            columns = {}
            for column in inspector.get_columns(table_name):
                columns[column['name']] = str(column['type'])
            
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_key = pk_constraint['constrained_columns'][0] if pk_constraint['constrained_columns'] else None
            
            foreign_keys = {}
            for fk in inspector.get_foreign_keys(table_name):
                for local_col, remote_col in zip(fk['constrained_columns'], fk['referred_columns']):
                    foreign_keys[local_col] = f"{fk['referred_table']}.{remote_col}"
            
            schema["tables"][table_name] = {
                "columns": columns,
                "primary_key": primary_key,
                "foreign_keys": foreign_keys
            }
        
        logger.info(f"Retrieved schema for {len(table_names)} tables: {', '.join(table_names)}")
        return {**state, "schema": schema}
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {str(e)}", exc_info=True)
        return {**state, "error": f"Schema retrieval failed: {str(e)}"}


def prompt_improver_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Improve user's raw prompt using LLM
    Converts vague requests into clear natural language descriptions
    """
    user_input = state["user_input"]
    schema = state.get("schema", {})
    
    schema_text = json.dumps(schema, indent=2)
    
    user_message = f"""User's request: {user_input}

Database schema:
{schema_text}

Improve this prompt for SQL generation."""
    
    improved_prompt = call_llm(PROMPT_IMPROVER_SYSTEM, user_message)
    
    logger.info(f"Improved prompt: {improved_prompt[:100]}...")
    
    return {
        **state,
        "improved_prompt": improved_prompt
    }


def query_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate SQL query from the improved prompt
    Validates against schema and ensures PostgreSQL compatibility
    """
    confirmed_prompt = state.get("improved_prompt")
    schema = state.get("schema", {})
    
    schema_text = json.dumps(schema, indent=2)
    
    user_message = f"""Generate SQL for this request: {confirmed_prompt}

Database schema:
{schema_text}

Remember: produce only a single SELECT statement. Validate all tables and columns against the schema above."""
    
    sql_response = call_llm(QUERY_GENERATOR_SYSTEM, user_message)
    
    # Check if response is an error from the LLM
    if sql_response.strip().startswith("ERROR:"):
        logger.warning(f"SQL generation failed: {sql_response}")
        return {
            **state,
            "error": sql_response.strip(),
            "sql_valid": False
        }
    
    # Extract SQL from code block
    sql_query = extract_sql_from_response(sql_response)
    
    # Validate the query
    is_valid, error_msg = validate_select_query(sql_query)
    
    if not is_valid:
        logger.warning(f"SQL validation failed: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "sql_valid": False
        }
    
    logger.info(f"Generated SQL: {sql_query[:100]}...")
    
    return {
        **state,
        "sql_query": sql_query,
        "sql_valid": True,
        "error": None
    }


def query_runner_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute SQL query against PostgreSQL database
    Enforces read-only access with timeout protection
    """
    sql_query = state["sql_query"]
    
    if not engine:
        logger.error("Query execution attempted without database connection")
        return {
            **state,
            "error": "Database connection not available. Please check DATABASE_URL in .env file",
            "query_results": None
        }
    
    try:
        start_time = time.time()
        
        with engine.connect() as connection:
            # Set statement timeout to prevent long-running queries
            connection.execute(text(f"SET statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
            
            result = connection.execute(text(sql_query))
            query_results = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        execution_time = time.time() - start_time
        total_rows = len(query_results)
        
        logger.info(f"Query executed successfully: {total_rows} rows in {execution_time:.3f}s")
        
        return {
            **state,
            "query_results": query_results,
            "total_rows": total_rows,
            "execution_time": execution_time,
            "error": None
        }
        
    except SQLAlchemyError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "timeout" in error_msg.lower():
            error_msg = f"Query exceeded time limit ({QUERY_TIMEOUT_SECONDS}s). Please add filters or narrow your query."
            logger.warning(f"Query timeout: {sql_query[:100]}...")
        elif "permission denied" in error_msg.lower():
            error_msg = "Permission denied. You don't have access to read from this table."
            logger.error(f"Permission denied: {sql_query[:100]}...")
        else:
            logger.error(f"Query execution failed: {error_msg}", exc_info=True)
        
        return {
            **state,
            "error": f"Query execution failed: {error_msg}",
            "query_results": None,
            "total_rows": 0,
            "execution_time": 0
        }
    
    except Exception as e:
        logger.error(f"Unexpected error during query execution: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {str(e)}",
            "query_results": None,
            "total_rows": 0,
            "execution_time": 0
        }


def user_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare output for display
    Applies display cap and creates metadata
    """
    query_results = state.get("query_results")
    total_rows = state.get("total_rows", 0)
    display_cap = state.get("display_cap", 500)
    
    display_results = query_results
    if total_rows > display_cap:
        display_results = query_results.head(display_cap)
    
    result_message = None
    if total_rows == 0:
        result_message = "✅ Query executed successfully, but returned 0 rows. This means no data matched your criteria."
    elif total_rows > display_cap:
        result_message = f"⚠️ Showing {display_cap} of {total_rows} rows. Query returned more data than can be displayed."
    
    metadata = {
        "total_rows": total_rows,
        "displayed_rows": len(display_results) if display_results is not None else 0,
        "execution_time": state.get("execution_time", 0),
        "capped": total_rows > display_cap,
        "result_message": result_message
    }
    
    logger.info(f"Prepared output: {metadata['displayed_rows']} rows for display")
    
    return {
        **state,
        "query_results": display_results,
        "metadata": metadata
    }


def insights_generator_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI insights from query results
    Special handling for empty results
    """
    user_input = state["user_input"]
    query_results = state.get("query_results")
    total_rows = state.get("total_rows", 0)
    
    # Special case: Empty results (0 rows)
    if total_rows == 0:
        user_message = f"""Original request: {user_input}

Query returned 0 rows (empty result set).
Columns that would have been returned: {', '.join(query_results.columns.tolist()) if query_results is not None else 'N/A'}

Explain what this empty result means in the context of the user's question."""
        
        insights = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
        
        if insights and len(insights) > 10:
            logger.info("Generated insights for empty result")
            return {**state, "insights": insights}
        else:
            return {**state, "insights": "No data matched your query criteria. This could mean the conditions specified don't apply to any records in the database."}
    
    # Regular case: Results with data
    if query_results is None or len(query_results) == 0:
        return {**state, "insights": None}
    
    # Check heuristics for generating insights
    insight_keywords = ["trend", "compare", "analysis", "insight", "summary", 
                       "top", "breakdown", "average", "mean", "median", "percent",
                       "total", "count", "over", "under", "exceed", "below"]
    
    should_generate = any(kw in user_input.lower() for kw in insight_keywords)
    
    # Also generate if we have numeric columns and enough rows
    numeric_cols = query_results.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0 and len(query_results) >= 3:
        should_generate = True
    
    if not should_generate:
        return {**state, "insights": None}
    
    # Prepare data summary for LLM
    data_summary = f"""
Result has {len(query_results)} rows and columns: {', '.join(query_results.columns.tolist())}

First 10 rows:
{query_results.head(10).to_string()}

Basic stats for numeric columns:
{query_results.describe().to_string() if len(numeric_cols) > 0 else 'No numeric columns'}
"""
    
    user_message = f"""Original request: {user_input}

Query results summary:
{data_summary}

Generate 0-3 concise insights if appropriate."""
    
    insights = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
    
    if insights and len(insights) > 10 and "no insight" not in insights.lower():
        logger.info("Generated insights for query results")
        return {**state, "insights": insights}
    
    return {**state, "insights": None}