"""
Logging utility for the AI Sonar Issue Fixer.
"""
import os
import sys
from loguru import logger
from config import LOG_LEVEL

def setup_logger():
    """
    Configure and return a logger instance.
    
    Returns:
        loguru.logger: Configured logger instance
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True
    )
    
    # Add file logger
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "ai_sonar_fixer_{time:YYYY-MM-DD}.log")
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="00:00",  # New file at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip"  # Compress rotated logs
    )
    
    return logger
