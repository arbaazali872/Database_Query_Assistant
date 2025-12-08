"""
Tools for the ReAct agent
Each tool performs a specific action the agent can choose
"""

import json
import time
import logging
import pandas as pd
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from config import engine, QUERY_TIMEOUT_SECONDS
from src.utils import call_llm, extract_sql_from_response, validate_select_query

logger = logging.getLogger(__name__)


@tool
def get_database_schema() -> str:
    """
    Retrieve the database schema including tables, columns, data types, and relationships.
    Use this when you need to understand what data is available before generating SQL.
    
    Returns:
        JSON string with schema information
    """
    if not engine:
        logger.warning("No database connection available")
        return json.dumps({"error": "Database connection not available"})
    
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
        
        logger.info(f"Retrieved schema for {len(table_names)} tables")
        return json.dumps(schema, indent=2)
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {str(e)}")
        return json.dumps({"error": f"Failed to retrieve schema: {str(e)}"})


@tool
def generate_sql_query(natural_language_request: str, database_schema: str) -> str:
    """
    Convert a natural language request into a PostgreSQL SELECT query.
    
    Args:
        natural_language_request: What the user wants to query in plain English
        database_schema: The database schema (from get_database_schema tool)
    
    Returns:
        Valid PostgreSQL SELECT statement or error message
    """
    from src.prompts import QUERY_GENERATOR_SYSTEM
    
    user_message = f"""Generate SQL for this request: {natural_language_request}

Database schema:
{database_schema}

Remember: produce only a single SELECT statement. Validate all tables and columns against the schema above."""
    
    sql_response = call_llm(QUERY_GENERATOR_SYSTEM, user_message)
    
    # Check if LLM returned an error
    if sql_response.strip().startswith("ERROR:"):
        logger.warning(f"SQL generation failed: {sql_response}")
        return sql_response
    
    # Extract SQL from code block
    sql_query = extract_sql_from_response(sql_response)
    
    # Validate the query
    is_valid, error_msg = validate_select_query(sql_query)
    
    if not is_valid:
        logger.warning(f"SQL validation failed: {error_msg}")
        return f"ERROR: {error_msg}"
    
    logger.info(f"Generated SQL: {sql_query[:100]}...")
    return sql_query


@tool
def execute_sql_query(sql_query: str) -> str:
    """
    Execute a SQL query against the database and return results.
    Only SELECT queries are allowed (read-only, 20 second timeout).
    
    Args:
        sql_query: Valid PostgreSQL SELECT statement
    
    Returns:
        JSON string with query results or error message
    """
    if not engine:
        logger.error("Database engine not available")
        return json.dumps({"error": "Database connection not available"})
    
    try:
        start_time = time.time()
        
        with engine.connect() as connection:
            connection.execute(text(f"SET statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"))
            result = connection.execute(text(sql_query))
            query_results = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        execution_time = time.time() - start_time
        total_rows = len(query_results)
        
        logger.info(f"Query executed: {total_rows} rows in {execution_time:.3f}s")
        
        # Return results as JSON
        result_dict = {
            "success": True,
            "rows": total_rows,
            "execution_time": execution_time,
            "data": query_results.to_dict(orient="records")[:500]  # Cap at 500 rows
        }
        
        return json.dumps(result_dict)
        
    except SQLAlchemyError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "timeout" in error_msg.lower():
            error_msg = f"Query timeout ({QUERY_TIMEOUT_SECONDS}s). Please add filters."
        elif "permission denied" in error_msg.lower():
            error_msg = "Permission denied for this table."
        
        logger.error(f"Query execution failed: {error_msg}")
        return json.dumps({"error": error_msg})
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return json.dumps({"error": str(e)})


@tool
def generate_insights_from_data(query_results: str, user_question: str) -> str:
    """
    Analyze query results and generate meaningful insights.
    
    Args:
        query_results: JSON string with query results from execute_sql_query
        user_question: Original user question for context
    
    Returns:
        Insights text (2-3 concise observations)
    """
    from src.prompts import INSIGHTS_GENERATOR_SYSTEM
    
    # Parse results
    try:
        results_dict = json.loads(query_results)
        
        if "error" in results_dict:
            return "Cannot generate insights due to query error."
        
        rows = results_dict.get("rows", 0)
        data = results_dict.get("data", [])
        
        if rows == 0:
            user_message = f"""Original question: {user_question}

Query returned 0 rows (empty result).

Explain what this means in the context of the user's question."""
            
            insights = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
            return insights if insights else "No data matched the query criteria."
        
        # Generate insights for non-empty results
        data_summary = f"""
Results: {rows} rows

Sample data (first 10 rows):
{json.dumps(data[:10], indent=2)}
"""
        
        user_message = f"""Original question: {user_question}

Query results:
{data_summary}

Generate 2-3 concise insights."""
        
        insights = call_llm(INSIGHTS_GENERATOR_SYSTEM, user_message)
        
        return insights if insights else "Data retrieved successfully."
        
    except Exception as e:
        logger.error(f"Insights generation failed: {str(e)}")
        return "Unable to generate insights."


# Export all tools as a list
tools = [
    get_database_schema,
    generate_sql_query,
    execute_sql_query,
    generate_insights_from_data
]