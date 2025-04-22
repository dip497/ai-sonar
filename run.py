#!/usr/bin/env python3
"""
Runner script for the AI Sonar Issue Fixer.

This script uses a multi-agent architecture with LangGraph to fix SonarQube issues.
"""
import os
import sys
import argparse
from src.main import main
from src.utils.logger import setup_logger
from config import MAX_ISSUES_PER_RUN

logger = setup_logger()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AI Sonar Issue Fixer')
    parser.add_argument('--max-issues', type=int, default=MAX_ISSUES_PER_RUN,
                      help=f'Maximum number of issues to process (default: {MAX_ISSUES_PER_RUN})')
    parser.add_argument('--days-lookback', type=int, default=1,
                      help='Number of days to look back for issues (default: 1)')
    parser.add_argument('--parallel-workers', type=int, default=5,
                      help='Number of parallel workers for issue processing (default: 5)')
    parser.add_argument('--no-parallel', action='store_true',
                      help='Disable parallel processing')

    # Pass the arguments to sys.argv
    args, unknown = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + [
        f'--max-issues={args.max_issues}',
        f'--days-lookback={args.days_lookback}',
        f'--parallel-workers={args.parallel_workers}'
    ]

    # Add --no-parallel flag if specified
    if args.no_parallel:
        sys.argv.append('--no-parallel')

    # Add any unknown arguments
    sys.argv.extend(unknown)

    try:
        logger.info("Starting AI Sonar Issue Fixer with LangGraph multi-agent architecture")
        main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running AI Sonar Issue Fixer: {str(e)}")
        sys.exit(1)
