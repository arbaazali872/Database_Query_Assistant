"""
Configuration settings for InventoryDB Agent
Loads environment variables and initializes shared resources
"""

import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# =============================================================================
# OPENAI CLIENT
# =============================================================================

client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}")

# =============================================================================
# DATABASE ENGINE
# =============================================================================

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        print(f"Warning: Failed to initialize database engine: {e}")

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging(log_dir: str = "logs", log_file: str = "inventorydb_agent.log"):
    """
    Configure logging for the application
    
    Args:
        log_dir: Directory to store log files
        log_file: Name of the log file
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, log_file)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Log initialization status
    if client:
        logger.info("OpenAI client initialized successfully")
    else:
        logger.warning("OpenAI client not initialized - OPENAI_API_KEY missing")
    
    if engine:
        logger.info("Database engine initialized successfully")
    else:
        logger.warning("Database engine not initialized - DATABASE_URL missing")
    
    return logger

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

DEFAULT_MODEL = "gpt-4.1-nano"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_DISPLAY_CAP = 500
QUERY_TIMEOUT_SECONDS = 20