import os
import json
import time
from typing import Dict, Any
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =============================================================================
# PROMPT TEMPLATES (from the plan)
# =============================================================================

PROMPT_IMPROVER_SYSTEM = """You are a prompt improvement assistant for SQL generation. Input: the user's raw natural-language request and the database schema (tables and columns). Output: a single, clearer, more explicit instruction that a SQL generator can use to produce a safe, read-only SELECT query. The improved prompt must:
- Clarify date ranges, filters, required columns (if inferable).  
- Suggest sensible defaults if user omitted key info (e.g., default date range: none; default row cap: 500 display).  
- Preserve user intent and avoid changing the question's meaning.  
- If the original request is ambiguous in a way you cannot resolve, add a short explicit note like: "[NOTE: ambiguous: user didn't specify X — defaulting to Y]".

Return only the improved prompt text (no explanation). Keep it concise (1–3 sentences)."""

QUERY_GENERATOR_SYSTEM = """You are an assistant that converts a confirmed natural-language request into one correct, read-only SQL SELECT statement. Use only the provided schema. Rules:
1. Produce a single SELECT statement (no DML/DDL/multiple statements).  
2. Validate all tables/columns — if any referenced item doesn't exist, output a short error naming it and stop.  
3. Do not invent joins or columns not present in the schema.  
4. If the user specified columns, include exactly those columns. If not, SELECT * is allowed.  
5. Do not add LIMIT to the executed query unless the DB cannot handle large results; instead enforce a UI display cap.  

Output: only the final SQL in a single code block."""

INSIGHTS_GENERATOR_SYSTEM = """You are a concise data analyst. Input: (a) original user request; (b) the query result sample or full table (structured rows + column names). Decide silently whether the user likely wants insights. If yes, output up to 3 concise insights (each 1–3 short sentences). Each insight should be factual, include simple numeric facts where possible (counts, percent change, top-K), and avoid speculative language. If no insights are needed, output nothing. Do not ask follow-up questions, and do not suggest charts."""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def call_llm(system_prompt: str, user_message: str, model: str = "gpt-4.1-nano") -> str:
    """Helper function to call OpenAI API"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def extract_sql_from_response(response: str) -> str:
    """Extract SQL from code block if present"""
    if "```sql" in response:
        sql = response.split("```sql")[1].split("```")[0].strip()
        return sql
    elif "```" in response:
        sql = response.split("```")[1].split("```")[0].strip()
        return sql
    return response.strip()

# =============================================================================
# NODE FUNCTIONS
# =============================================================================

def user_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point - initializes the state with user input
    In Streamlit, this will be called after user submits the form
    """
    # Just pass through - actual input comes from Streamlit
    return {
        "edit_count": state.get("edit_count", 0),
        "metadata": state.get("metadata", {})
    }

def sql_schema_retriever(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool to retrieve database schema
    For now, returns a placeholder - you'll provide the real schema later
    """
    # Placeholder schema - you'll replace this with your actual schema
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
    
    return {"schema": placeholder_schema}

def prompt_improver_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Improves the user's raw prompt using LLM
    Returns improved prompt for user confirmation
    """
    print(f"state in prompt_improver_node: {state}")
    user_input = state["user_input"]
    schema = state.get("schema", {})
    
    # Format schema for the prompt
    schema_text = json.dumps(schema, indent=2)
    
    user_message = f"""User's request: {user_input}

Database schema:
{schema_text}

Improve this prompt for SQL generation."""
    
    improved_prompt = call_llm(PROMPT_IMPROVER_SYSTEM, user_message)
    
    return {
        "improved_prompt": improved_prompt,
        "user_confirmed": None  # Will be set by UI
    }

def query_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates SQL query from the confirmed improved prompt
    Validates against schema
    """
    confirmed_prompt = state.get("improved_prompt")  # After user confirms
    schema = state.get("schema", {})
    
    schema_text = json.dumps(schema, indent=2)
    
    user_message = f"""Generate SQL for this request: {confirmed_prompt}

Database schema:
{schema_text}

Remember: produce only a single SELECT statement. Validate all tables and columns."""
    
    sql_response = call_llm(QUERY_GENERATOR_SYSTEM, user_message)
    
    # Check if response contains an error
    if "error" in sql_response.lower() and "ERROR:" in sql_response:
        return {
            "error": sql_response,
            "sql_valid": False
        }
    
    # Extract SQL from code block
    sql_query = extract_sql_from_response(sql_response)
    
    # Basic validation - check if it's a SELECT statement
    if not sql_query.upper().strip().startswith("SELECT"):
        return {
            "error": "Generated query is not a SELECT statement",
            "sql_valid": False
        }
    
    return {
        "sql_query": sql_query,
        "sql_valid": True,
        "error": None
    }

def query_runner_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the SQL query (read-only with timeout)
    For now, returns mock data - you'll connect to real DB later
    """
    sql_query = state["sql_query"]
    
    # TODO: Replace with actual DB execution
    # For now, return mock success
    import pandas as pd
    
    # Mock result
    mock_data = {
        "project_id": [1, 2, 3],
        "project_name": ["Project A", "Project B", "Project C"],
        "status": ["Active", "Completed", "Active"]
    }
    
    start_time = time.time()
    
    # Simulate query execution
    query_results = pd.DataFrame(mock_data)
    
    execution_time = time.time() - start_time
    
    return {
        "query_results": query_results,
        "total_rows": len(query_results),
        "execution_time": execution_time,
        "error": None
    }

def user_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares output for display (handles display cap)
    This node just prepares metadata - actual rendering happens in Streamlit
    """
    query_results = state.get("query_results")
    total_rows = state.get("total_rows", 0)
    display_cap = state.get("display_cap", 500)
    
    # Apply display cap
    display_results = query_results
    if total_rows > display_cap:
        display_results = query_results.head(display_cap)
    
    metadata = {
        "total_rows": total_rows,
        "displayed_rows": len(display_results),
        "execution_time": state.get("execution_time", 0),
        "capped": total_rows > display_cap
    }
    
    return {
        "query_results": display_results,
        "metadata": metadata
    }

def insights_generator_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates insights based on query results (optional, silent decision)
    """
    user_input = state["user_input"]
    query_results = state.get("query_results")
    
    if query_results is None or len(query_results) == 0:
        return {"insights": None}
    
    # Check heuristics for generating insights
    insight_keywords = ["trend", "compare", "analysis", "insight", "summary", 
                       "top", "breakdown", "average", "mean", "median", "percent"]
    
    should_generate = any(kw in user_input.lower() for kw in insight_keywords)
    
    # Also generate if we have numeric columns and enough rows
    numeric_cols = query_results.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0 and len(query_results) >= 20:
        should_generate = True
    
    if not should_generate:
        return {"insights": None}
    
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
    
    # If LLM returns something meaningful, include it
    if insights and len(insights) > 10 and "no insight" not in insights.lower():
        return {"insights": insights}
    
    return {"insights": None}

# =============================================================================
# CONDITIONAL EDGES
# =============================================================================

def should_continue_after_prompt_improvement(state: Dict[str, Any]) -> str:
    """Decide whether to proceed to query generation or wait for user confirmation"""
    # In practice, this will be controlled by Streamlit UI
    # For testing, we'll assume confirmation
    if state.get("user_confirmed") is True:
        return "generate_query"
    elif state.get("user_confirmed") is False:
        # User wants to edit - go back to improver
        return "improve_again"
    else:
        # Waiting for user input
        return "wait_for_confirmation"

def should_proceed_after_query_generation(state: Dict[str, Any]) -> str:
    """Check if SQL generation was successful"""
    if state.get("sql_valid") is True:
        return "run_query"
    else:
        return "error"