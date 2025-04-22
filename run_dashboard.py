#!/usr/bin/env python3
"""
Script to run the AI Sonar Issue Fixer dashboard.
"""
import os
import sys
from src.dashboard.app import run_dashboard
from src.utils.logger import setup_logger

logger = setup_logger()

if __name__ == "__main__":
    try:
        logger.info("Starting AI Sonar Issue Fixer dashboard")
        run_dashboard()
    except Exception as e:
        logger.error(f"Error running dashboard: {str(e)}")
        sys.exit(1)
