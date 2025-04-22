#!/usr/bin/env python3
"""
Script to run the AI Sonar Issue Fixer dashboard.
"""
import os
import sys
from src.dashboard.app import run_dashboard
from src.utils.logger import setup_logger

logger = setup_logger()

def check_streamlit_installed():
    """Check if Streamlit is installed."""
    try:
        import streamlit
        return True
    except ImportError:
        return False

if __name__ == "__main__":
    try:
        # Check if Streamlit is installed
        if not check_streamlit_installed():
            logger.error("Streamlit is not installed. Please install it with 'pip install streamlit'.")
            print("\nError: Streamlit is not installed. Please install it with 'pip install streamlit'.")
            sys.exit(1)

        logger.info("Starting AI Sonar Issue Fixer dashboard")
        run_dashboard()
    except Exception as e:
        logger.error(f"Error running dashboard: {str(e)}")
        sys.exit(1)
