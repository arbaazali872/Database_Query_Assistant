"""
Tools for the ReAct agent
Each tool performs a specific action the agent can choose
"""

import json
import logging
import pandas as pd
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from config import engine

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
def execute_sql_query(sql_query: str) -> str:
    """
    Execute a SQL query against the database and return results summary.
    Only SELECT queries are allowed (read-only, 20 second timeout).
    
    Args:
        sql_query: Valid PostgreSQL SELECT statement
    
    Returns:
        Summary of query execution (row count, sample data)
    """
    # This tool is intentionally minimal
    # The actual execution and DataFrame storage happens in custom_tool_node
    # This just defines the interface for the agent
    return "Tool execution handled by custom_tool_node"


# Export all tools as a list
tools = [
    get_database_schema,
    execute_sql_query
]