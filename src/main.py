#!/usr/bin/env python3
"""
AI Sonar Issue Fixer - Main Entry Point

This script orchestrates the process of:
1. Fetching new SonarQube issues
2. Fixing them using AI
3. Creating pull requests with the fixes

This version uses LangGraph for a multi-agent architecture.
"""
import os
import sys
import argparse

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MAX_ISSUES_PER_RUN
from src.utils.logger import setup_logger
from src.workflows.sonar_fixer_workflow import run_workflow

# Set up logger
logger = setup_logger()

def main():
    """Main function to run the AI Sonar Issue Fixer workflow."""
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
    args = parser.parse_args()

    use_parallel = not args.no_parallel

    logger.info(f"Starting AI Sonar Issue Fixer with max_issues={args.max_issues}, "
               f"days_lookback={args.days_lookback}, parallel_workers={args.parallel_workers}, "
               f"use_parallel={use_parallel}")

    try:
        # Run the workflow
        final_state = run_workflow(
            max_issues=args.max_issues,
            days_lookback=args.days_lookback,
            parallel_workers=args.parallel_workers,
            use_parallel=use_parallel
        )

        # Print summary
        print("\n" + "=" * 50)
        print("AI Sonar Issue Fixer Summary")
        print("=" * 50)
        print(f"Status: {final_state.status}")
        print(f"Issues found: {final_state.num_issues_found}")
        print(f"Issues fixed: {final_state.num_issues_fixed}")

        if final_state.pr_url:
            print(f"\nPull Request: {final_state.pr_url}")

        if final_state.error:
            print(f"\nError: {final_state.error}")

        if final_state.parallel_processing_time:
            print(f"\nParallel processing time: {final_state.parallel_processing_time:.2f} seconds")

        print(f"\nTotal duration: {final_state.duration_seconds:.2f} seconds")
        print("=" * 50)

        # Exit with appropriate code
        if final_state.status == "error":
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
