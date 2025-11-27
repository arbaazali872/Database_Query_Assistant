import os
import json
import time
from typing import Dict, Any
from openai import OpenAI
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = None
    print("⚠️ WARNING: DATABASE_URL not found in environment variables")

# =============================================================================
# PROMPT TEMPLATES (from the plan)
# =============================================================================

PROMPT_IMPROVER_SYSTEM = """You are a prompt improvement assistant for SQL generation. Input: the user's raw natural-language request and the database schema (tables and columns). Output: a single, clearer, more explicit instruction that a SQL generator can use to produce a safe, read-only SELECT query.

CRITICAL RULES:
1. Write in IMPERATIVE/INSTRUCTIONAL tone (third-person instruction to SQL generator), NOT conversational tone
2. PRESERVE the user's original intent - even if tables/columns don't exist in schema, keep them in the improved prompt
3. DO NOT change, correct, or substitute table/column names - validation happens later
4. Add clarifications for: date ranges, filters, specific columns, sorting, grouping
5. Suggest sensible defaults ONLY for: row limits (default 500), date ranges (if unspecified), column selection (if vague)
6. If user's request references non-existent tables/columns, preserve them AS-IS and add: "[NOTE: table/column 'X' not found in schema - will be validated in next step]"
7. If ambiguous in other ways, add: "[NOTE: ambiguous - assuming X]"

CORRECT FORMAT (imperative):
"Select project_id, project_name, start_date from projects where start_date between '2021-01-01' and '2024-12-31', order by start_date ascending."

INCORRECT FORMAT (conversational):
"Please show me the projects, specifying which columns you want..."

Return only the improved prompt text (no preamble, no explanation). Keep it concise (1-3 sentences)."""

QUERY_GENERATOR_SYSTEM = """You are an assistant that converts a confirmed natural-language request into one correct, read-only SQL SELECT statement for PostgreSQL. Use only the provided schema. Rules:
1. Produce a single SELECT statement (no DML/DDL/multiple statements).  
2. VALIDATE all tables/columns against the schema - if ANY referenced table or column doesn't exist, respond ONLY with: "ERROR: Table 'X' does not exist in schema. Available tables: [list]" or "ERROR: Column 'Y' does not exist in table 'X'. Available columns: [list]"
3. Do not attempt to correct, guess, or substitute non-existent tables/columns - return an error immediately
4. Do not invent joins or columns not present in the schema.  
5. If the user specified columns, include exactly those columns. If not, SELECT * is allowed.  
6. Do not add LIMIT to the executed query unless the DB cannot handle large results; instead enforce a UI display cap.  
7. For date filters, use proper SQL date format: 'YYYY-MM-DD'
8. Ensure proper JOIN syntax if multiple tables are referenced

POSTGRESQL-SPECIFIC RULES (CRITICAL):
9. NEVER use column aliases in WHERE, HAVING, or GROUP BY clauses - PostgreSQL doesn't allow this
10. In HAVING clauses, always use the full aggregate expression (e.g., "HAVING SUM(amount) > 1000" NOT "HAVING total_amount > 1000")
11. In GROUP BY, list actual column names, never aliases
12. Column aliases (AS) should only be used in the SELECT clause for display purposes

CORRECT PostgreSQL Example:
SELECT p.project_id, SUM(o.amount) AS total_amount
FROM projects p JOIN orders o ON p.project_id = o.project_id
GROUP BY p.project_id
HAVING SUM(o.amount) > p.budget;

INCORRECT (will fail in PostgreSQL):
SELECT p.project_id, SUM(o.amount) AS total_amount
FROM projects p JOIN orders o ON p.project_id = o.project_id
GROUP BY p.project_id
HAVING total_amount > p.budget;  -- ❌ Can't use alias in HAVING

Output: only the final SQL in a single code block, OR an error message starting with "ERROR:"."""

INSIGHTS_GENERATOR_SYSTEM = """You are a concise data analyst. Input: (a) original user request; (b) the query result sample or full table (structured rows + column names); (c) whether the result is empty (0 rows).

RULES:
1. If result has 0 rows: Generate 1-2 insights explaining what this means in the context of the user's question. Focus on what the empty result tells us about the data. Example: "No projects exceeded their budget, indicating effective budget management across all projects."
2. If result has data: Decide silently whether insights would add value. If yes, output up to 3 concise insights (each 1-3 short sentences).
3. Each insight should be factual, include simple numeric facts where possible (counts, percent change, top-K), and avoid speculative language.
4. Do not ask follow-up questions, and do not suggest charts.
5. If insights wouldn't add value to a simple data lookup, output nothing.

Output: The insights text only (no preamble like "Here are the insights:")."""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def call_llm(system_prompt: str, user_message: str, model: str = "gpt-4o-mini") -> str:
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
    # Ensure we preserve all state
    return state

def sql_schema_retriever(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool to retrieve database schema from the connected PostgreSQL database
    Fetches tables, columns, data types, primary keys, and foreign keys
    """
    if not engine:
        # Fallback to placeholder if no database connection
        print("⚠️ No database connection - using placeholder schema")
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
        # Use SQLAlchemy inspector to get schema information
        inspector = inspect(engine)
        schema = {"tables": {}}
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            # Get columns with their types
            columns = {}
            for column in inspector.get_columns(table_name):
                columns[column['name']] = str(column['type'])
            
            # Get primary key
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_key = pk_constraint['constrained_columns'][0] if pk_constraint['constrained_columns'] else None
            
            # Get foreign keys
            foreign_keys = {}
            for fk in inspector.get_foreign_keys(table_name):
                for local_col, remote_col in zip(fk['constrained_columns'], fk['referred_columns']):
                    foreign_keys[local_col] = f"{fk['referred_table']}.{remote_col}"
            
            schema["tables"][table_name] = {
                "columns": columns,
                "primary_key": primary_key,
                "foreign_keys": foreign_keys
            }
        
        print(f"✅ Successfully retrieved schema for {len(table_names)} tables: {', '.join(table_names)}")
        return {**state, "schema": schema}
        
    except Exception as e:
        print(f"❌ Error retrieving schema: {str(e)}")
        return {**state, "error": f"Schema retrieval failed: {str(e)}"}

def prompt_improver_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Improves the user's raw prompt using LLM
    Returns improved prompt for user confirmation
    """
    user_input = state["user_input"]
    schema = state.get("schema", {})
    
    # Format schema for the prompt
    schema_text = json.dumps(schema, indent=2)
    
    user_message = f"""User's request: {user_input}

Database schema:
{schema_text}

Improve this prompt for SQL generation."""
    
    improved_prompt = call_llm(PROMPT_IMPROVER_SYSTEM, user_message)
    
    # Return full state with updates
    return {
        **state,
        "improved_prompt": improved_prompt,
        "user_confirmed": state.get("user_confirmed")  # Preserve confirmation status
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

Remember: produce only a single SELECT statement. Validate all tables and columns against the schema above."""
    
    sql_response = call_llm(QUERY_GENERATOR_SYSTEM, user_message)
    
    # Check if response is an error
    if sql_response.strip().startswith("ERROR:"):
        return {
            **state,
            "error": sql_response.strip(),
            "sql_valid": False
        }
    
    # Extract SQL from code block
    sql_query = extract_sql_from_response(sql_response)
    
    # Basic validation - check if it's a SELECT statement
    sql_upper = sql_query.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return {
            **state,
            "error": "Generated query is not a SELECT statement. This system only supports read-only queries.",
            "sql_valid": False
        }
    
    # Additional safety check - reject if contains DML/DDL keywords
    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return {
                **state,
                "error": f"Query contains forbidden keyword '{keyword}'. Only SELECT queries are allowed.",
                "sql_valid": False
            }
    
    return {
        **state,
        "sql_query": sql_query,
        "sql_valid": True,
        "error": None
    }

def query_runner_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the SQL query against the PostgreSQL database (with timeout)
    Enforces read-only by wrapping query in a transaction that rolls back
    """
    sql_query = state["sql_query"]
    
    if not engine:
        return {
            **state,
            "error": "Database connection not available. Please check DATABASE_URL in .env file",
            "query_results": None
        }
    
    try:
        start_time = time.time()
        
        # Execute query with timeout (20 seconds default)
        with engine.connect() as connection:
            # Set statement timeout to prevent long-running queries
            connection.execute(text("SET statement_timeout = '20s'"))
            
            # Execute the user's query
            result = connection.execute(text(sql_query))
            
            # Fetch results into pandas DataFrame
            query_results = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Note: We're not committing anything, so even if someone tries DML,
            # it won't persist (but ideally use a read-only user in production)
        
        execution_time = time.time() - start_time
        total_rows = len(query_results)
        
        print(f"✅ Query executed successfully: {total_rows} rows in {execution_time:.3f}s")
        
        return {
            **state,
            "query_results": query_results,
            "total_rows": total_rows,
            "execution_time": execution_time,
            "error": None
        }
        
    except SQLAlchemyError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Check for common errors
        if "timeout" in error_msg.lower():
            error_msg = "Query exceeded time limit (20s). Please add filters or narrow your query."
        elif "permission denied" in error_msg.lower():
            error_msg = "Permission denied. You don't have access to read from this table."
        
        print(f"❌ Query execution failed: {error_msg}")
        
        return {
            **state,
            "error": f"Query execution failed: {error_msg}",
            "query_results": None,
            "total_rows": 0,
            "execution_time": 0
        }
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return {
            **state,
            "error": f"Unexpected error: {str(e)}",
            "query_results": None,
            "total_rows": 0,
            "execution_time": 0
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
    
    # Create user-friendly message for empty results
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
    
    return {
        **state,
        "query_results": display_results,
        "metadata": metadata
    }

def insights_generator_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates insights based on query results (optional, silent decision)
    Special handling for empty results (0 rows)
    """
    user_input = state["user_input"]
    query_results = state.get("query_results")
    total_rows = state.get("total_rows", 0)
    
    # Special case: Empty results (0 rows)
    if total_rows == 0:
        # ALWAYS generate insights for empty results to explain what it means
        user_message = f"""Original request: {user_input}

Query returned 0 rows (empty result set).
Columns that would have been returned: {', '.join(query_results.columns.tolist()) if query_results is not None else 'N/A'}

Explain what this empty result means in the context of the user's question."""
        
        insights = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
        
        if insights and len(insights) > 10:
            return {**state, "insights": insights}
        else:
            # Fallback if LLM doesn't provide good insights
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
    if len(numeric_cols) > 0 and len(query_results) >= 3:  # Lowered threshold from 20 to 3
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
    
    # If LLM returns something meaningful, include it
    if insights and len(insights) > 10 and "no insight" not in insights.lower():
        return {**state, "insights": insights}
    
    return {**state, "insights": None}

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