"""
Central logging configuration for the project using loguru.
"""
from loguru import logger
import sys
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logger
logger.remove()  # Remove default handler

# Add console handler with beautiful format
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    backtrace=True,
    diagnose=True,
    level="INFO"
)

# Add file logging with rotation
logger.add(
    "logs/islob_bot.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    backtrace=True,
    diagnose=True,
    enqueue=True  # Thread-safe logging
)

# Add error file for critical errors only
logger.add(
    "logs/errors.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    backtrace=True,
    diagnose=True,
    enqueue=True
)

# Function to get a contextualized logger
def get_logger(name):
    """
    Returns a logger with the specified name.
    
    Args:
        name: The name of the logger (typically __name__)
        
    Returns:
        A loguru logger instance with context
    """
    return logger.bind(name=name)
