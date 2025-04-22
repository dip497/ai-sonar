"""
Parallel processing module for handling multiple issues simultaneously.
"""
import concurrent.futures
from typing import List, Dict, Any, Optional
import os
import time
from pydantic import BaseModel, Field
from src.utils.logger import setup_logger
from src.agents.issue_analyzer import IssueAnalyzerAgent, IssueAnalysisInput, IssueAnalysisOutput
from src.agents.code_fixer import CodeFixerAgent, CodeFixInput, CodeFixOutput

logger = setup_logger()

class ParallelProcessingResult(BaseModel):
    """Result of parallel processing."""
    successful_fixes: List[CodeFixOutput] = Field(default_factory=list, description="Successfully fixed issues")
    failed_issues: List[Dict[str, Any]] = Field(default_factory=list, description="Issues that failed to be fixed")
    processing_times: Dict[str, float] = Field(default_factory=dict, description="Processing time for each issue")
    total_time: float = Field(..., description="Total processing time")

class ParallelProcessor:
    """
    Processor for handling multiple issues in parallel.
    """

    def __init__(self, max_workers: int = 5):
        """
        Initialize the parallel processor.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.issue_analyzer = IssueAnalyzerAgent()
        self.code_fixer = CodeFixerAgent()

    def process_issues(self, issues: List[Dict[str, Any]], repo_path: str) -> ParallelProcessingResult:
        """
        Process multiple issues in parallel.

        Args:
            issues: List of SonarQube issues to process
            repo_path: Path to the repository

        Returns:
            Result of parallel processing
        """
        start_time = time.time()
        successful_fixes = []
        failed_issues = []
        processing_times = {}

        logger.info(f"Processing {len(issues)} issues in parallel with {self.max_workers} workers")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all issues for processing
            future_to_issue = {
                executor.submit(self._process_single_issue, issue, repo_path): issue
                for issue in issues
            }

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_issue):
                issue = future_to_issue[future]
                issue_key = issue.get('key', 'unknown')

                try:
                    result = future.result()
                    if result:
                        successful_fixes.append(result)
                        logger.info(f"Successfully fixed issue {issue_key}")
                    else:
                        failed_issues.append(issue)
                        logger.warning(f"Failed to fix issue {issue_key}")

                    # Record processing time
                    processing_times[issue_key] = result.processing_time if result else 0

                except Exception as e:
                    logger.error(f"Error processing issue {issue_key}: {str(e)}")
                    failed_issues.append(issue)

        total_time = time.time() - start_time
        logger.info(f"Parallel processing completed in {total_time:.2f} seconds")
        logger.info(f"Successfully fixed {len(successful_fixes)} issues, failed to fix {len(failed_issues)} issues")

        return ParallelProcessingResult(
            successful_fixes=successful_fixes,
            failed_issues=failed_issues,
            processing_times=processing_times,
            total_time=total_time
        )

    def _process_single_issue(self, issue: Dict[str, Any], repo_path: str) -> Optional[CodeFixOutput]:
        """
        Process a single issue.

        Args:
            issue: SonarQube issue to process
            repo_path: Path to the repository

        Returns:
            Fixed issue output if successful, None otherwise
        """
        issue_key = issue.get('key', 'unknown')
        start_time = time.time()

        try:
            # Extract file path
            file_path = issue['component'].split(':')[-1]
            full_file_path = os.path.join(repo_path, file_path)

            # Skip if file doesn't exist
            if not os.path.exists(full_file_path):
                logger.warning(f"File not found: {file_path}. Skipping issue {issue_key}.")
                return None

            # Step 1: Analyze the issue
            analysis_input = IssueAnalysisInput(
                issue=issue,
                file_path=full_file_path
            )

            analysis = self.issue_analyzer.analyze_issue(analysis_input)

            # Step 2: Fix the issue
            fix_input = CodeFixInput(analysis=analysis, use_memory=True)
            fix = self.code_fixer.fix_issue(fix_input)

            # Add processing time to the output
            processing_time = time.time() - start_time
            setattr(fix, 'processing_time', processing_time)

            return fix

        except Exception as e:
            logger.error(f"Error processing issue {issue_key}: {str(e)}")
            return None
