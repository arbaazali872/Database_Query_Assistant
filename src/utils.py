"""
Utility functions for InventoryDB Agent
Includes LLM calls, validation, and helper functions
"""

import logging
from typing import Optional
from config import client, DEFAULT_MODEL, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)


def call_llm(
    system_prompt: str, 
    user_message: str, 
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE
) -> str:
    """
    Call OpenAI API with system and user messages
    
    Args:
        system_prompt: System instructions for the model
        user_message: User's message/query
        model: OpenAI model to use (default: gpt-4o-mini)
        temperature: Sampling temperature (default: 0.3)
    
    Returns:
        Model's response as a string, or error message if call fails
    """
    if not client:
        logger.error("OpenAI client not initialized")
        return "ERROR: OpenAI client not configured. Check OPENAI_API_KEY."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {str(e)}", exc_info=True)
        return f"ERROR: {str(e)}"


def extract_sql_from_response(response: str) -> str:
    """
    Extract SQL from code block if present in LLM response
    
    Args:
        response: Raw LLM response that may contain SQL in markdown code blocks
    
    Returns:
        Extracted SQL query string
    """
    if "```sql" in response:
        sql = response.split("```sql")[1].split("```")[0].strip()
        return sql
    elif "```" in response:
        sql = response.split("```")[1].split("```")[0].strip()
        return sql
    return response.strip()


def validate_select_query(sql_query: str) -> tuple[bool, Optional[str]]:
    """
    Validate that SQL query is a safe SELECT statement
    
    Args:
        sql_query: SQL query string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if query is safe, False otherwise
        - error_message: None if valid, error description if invalid
    """
    sql_upper = sql_query.upper().strip()
    
    # Check if it starts with SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Generated query is not a SELECT statement. This system only supports read-only queries."
    
    # Check for dangerous keywords
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
        "TRUNCATE", "GRANT", "REVOKE", "EXECUTE", "EXEC"
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False, f"Query contains forbidden keyword '{keyword}'. Only SELECT queries are allowed."
    
    return True, None


def validate_openai_connection() -> tuple[bool, str]:
    """
    Check if OpenAI API key exists and client is initialized
    
    Returns:
        Tuple of (is_valid, status_message)
    """
    if not client:
        return False, "OPENAI_API_KEY not found in environment variables"
    
    try:
        # Client is already initialized, so just return success
        return True, "OpenAI API key configured"
    except Exception as e:
        return False, f"OpenAI API key invalid: {str(e)}"


def validate_database_connection() -> tuple[bool, str]:
    """
    Check if database connection is available and working
    
    Returns:
        Tuple of (is_valid, status_message)
    """
    from config import engine
    from sqlalchemy import text
    
    if not engine:
        return False, "DATABASE_URL not found in environment variables"
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"