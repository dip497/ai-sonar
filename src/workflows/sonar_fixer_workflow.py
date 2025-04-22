"""
LangGraph workflow for the AI Sonar Issue Fixer.
"""
from typing import Dict, List, Any, TypedDict, Optional, Annotated, Literal, Union
import os
import time
from datetime import datetime
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from git import Repo
from src.utils.logger import setup_logger
from src.sonarqube.issue_fetcher import SonarQubeIssueFetcher
from src.git.repo_manager import GitRepoManager
from src.agents.issue_analyzer import IssueAnalyzerAgent, IssueAnalysisInput, IssueAnalysisOutput
from src.agents.code_fixer import CodeFixerAgent, CodeFixInput, CodeFixOutput
from src.agents.pr_creator import PRCreatorAgent, PRCreatorInput, PRCreatorOutput
from src.workflows.parallel_processor import ParallelProcessor
from config import MAX_ISSUES_PER_RUN, TEMP_DIR

logger = setup_logger()

# Define the state for our workflow
class WorkflowState(BaseModel):
    """State for the AI Sonar Issue Fixer workflow."""
    # Input parameters
    max_issues: int = Field(MAX_ISSUES_PER_RUN, description="Maximum number of issues to process")
    days_lookback: int = Field(1, description="Number of days to look back for issues")
    parallel_workers: int = Field(5, description="Number of parallel workers for issue processing")
    use_parallel: bool = Field(True, description="Whether to use parallel processing")

    # Workflow state
    start_time: float = Field(default_factory=time.time, description="Start time of the workflow")
    status: str = Field("initializing", description="Current status of the workflow")
    current_step: str = Field("fetch_issues", description="Current step in the workflow")
    error: Optional[str] = Field(None, description="Error message if any")

    # Repository state
    repo_path: Optional[str] = Field(None, description="Path to the cloned repository")
    branch_name: Optional[str] = Field(None, description="Name of the branch with fixes")

    # Issue state
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of issues to fix")
    current_issue_index: int = Field(0, description="Index of the current issue being processed")
    analyzed_issues: List[IssueAnalysisOutput] = Field(default_factory=list, description="List of analyzed issues")
    fixed_issues: List[CodeFixOutput] = Field(default_factory=list, description="List of fixed issues")
    skipped_issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of skipped issues")
    processing_times: Dict[str, float] = Field(default_factory=dict, description="Processing time for each issue")

    # PR state
    pr_url: Optional[str] = Field(None, description="URL of the created PR")
    pr_title: Optional[str] = Field(None, description="Title of the PR")
    pr_description: Optional[str] = Field(None, description="Description of the PR")

    # Results
    num_issues_found: int = Field(0, description="Number of issues found")
    num_issues_fixed: int = Field(0, description="Number of issues fixed")
    duration_seconds: Optional[float] = Field(None, description="Duration of the run in seconds")
    parallel_processing_time: Optional[float] = Field(None, description="Time spent in parallel processing")

# Define the agents
issue_fetcher = SonarQubeIssueFetcher()
issue_analyzer = IssueAnalyzerAgent()
code_fixer = CodeFixerAgent()
pr_creator = PRCreatorAgent()

# Define the workflow steps
def fetch_issues(state: WorkflowState) -> WorkflowState:
    """
    Fetch issues from SonarQube.

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    logger.info("Fetching issues from SonarQube...")
    state.status = "fetching_issues"

    try:
        # Fetch issues
        issues = issue_fetcher.fetch_new_issues(
            max_issues=state.max_issues,
            days=state.days_lookback
        )

        state.issues = issues
        state.num_issues_found = len(issues)

        if not issues:
            logger.info("No issues found. Workflow complete.")
            state.status = "completed"
            state.current_step = "end"
            state.duration_seconds = time.time() - state.start_time
        else:
            logger.info(f"Found {len(issues)} issues to fix")
            state.status = "issues_fetched"
            state.current_step = "setup_repository"

    except Exception as e:
        logger.error(f"Error fetching issues: {str(e)}")
        state.status = "error"
        state.error = f"Error fetching issues: {str(e)}"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time

    return state

def setup_repository(state: WorkflowState) -> WorkflowState:
    """
    Set up the Git repository.

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    logger.info("Setting up repository...")
    state.status = "setting_up_repository"

    try:
        # Generate branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/sonar-{timestamp}"
        state.branch_name = branch_name

        # Create temp directory if it doesn't exist
        os.makedirs(TEMP_DIR, exist_ok=True)

        # Clone repository and create branch
        git_manager = GitRepoManager()
        repo_path = git_manager.clone_repo()
        git_manager.create_branch(branch_name)

        state.repo_path = repo_path
        state.status = "repository_setup"
        state.current_step = "process_issue"

    except Exception as e:
        logger.error(f"Error setting up repository: {str(e)}")
        state.status = "error"
        state.error = f"Error setting up repository: {str(e)}"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time

    return state

def process_issues_parallel(state: WorkflowState) -> WorkflowState:
    """
    Process all issues in parallel.

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    logger.info(f"Processing {len(state.issues)} issues in parallel with {state.parallel_workers} workers")
    state.status = "processing_issues_parallel"

    try:
        # Initialize the parallel processor
        processor = ParallelProcessor(max_workers=state.parallel_workers)

        # Process all issues in parallel
        start_time = time.time()
        result = processor.process_issues(state.issues, state.repo_path)
        state.parallel_processing_time = time.time() - start_time

        # Update state with results
        state.fixed_issues = result.successful_fixes
        state.skipped_issues = result.failed_issues
        state.processing_times = result.processing_times

        # Apply fixes and commit changes
        git_manager = GitRepoManager()
        git_manager.repo_path = state.repo_path
        # We need to recreate the repo object from the existing path
        git_manager.repo = Repo(state.repo_path)

        for fix in state.fixed_issues:
            try:
                # Extract file path
                file_path = fix.file_path
                full_file_path = os.path.join(state.repo_path, file_path)

                # Apply the fix
                # The context might be missing in the fix object, so we need to handle that
                context = None
                if hasattr(fix, 'analysis'):
                    context = fix.analysis.context
                elif hasattr(fix, 'original_code'):
                    # Create a simple context if we have the original code
                    context = {
                        'start_line': 1,
                        'end_line': len(fix.original_code.split('\n')),
                        'context_text': fix.original_code
                    }

                if context is None:
                    logger.warning(f"Missing context for issue {fix.issue_key}. Cannot apply fix.")
                    continue

                success = code_fixer.apply_fix(
                    file_path=full_file_path,
                    context=context,
                    fixed_code=fix.fixed_code
                )

                if success:
                    # Commit the change
                    commit_message = f"Fix SonarQube issue: {fix.issue_key}"
                    git_manager.commit_changes(file_path, commit_message)
                    logger.info(f"Committed fix for issue: {fix.issue_key}")
            except Exception as e:
                logger.error(f"Error applying fix for issue {fix.issue_key}: {str(e)}")

        logger.info(f"Parallel processing completed: {len(state.fixed_issues)} issues fixed, {len(state.skipped_issues)} issues skipped")
        state.status = "issues_processed"
        state.current_step = "create_pull_request"

    except Exception as e:
        logger.error(f"Error in parallel processing: {str(e)}")
        state.status = "error"
        state.error = f"Error in parallel processing: {str(e)}"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time

    return state

def process_issue(state: WorkflowState) -> WorkflowState:
    """
    Process the current issue (sequential fallback).

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    # If parallel processing is enabled, use that instead
    if state.use_parallel:
        return process_issues_parallel(state)

    # Check if we've processed all issues
    if state.current_issue_index >= len(state.issues):
        logger.info("All issues processed")
        state.status = "issues_processed"
        state.current_step = "create_pull_request"
        return state

    # Get the current issue
    issue = state.issues[state.current_issue_index]
    issue_key = issue.get('key', 'unknown')

    logger.info(f"Processing issue {state.current_issue_index + 1}/{len(state.issues)}: {issue_key}")
    state.status = f"processing_issue_{issue_key}"

    try:
        # Extract file path
        file_path = issue['component'].split(':')[-1]
        full_file_path = os.path.join(state.repo_path, file_path)

        # Skip if file doesn't exist
        if not os.path.exists(full_file_path):
            logger.warning(f"File not found: {file_path}. Skipping issue.")
            state.skipped_issues.append(issue)
            state.current_issue_index += 1
            return state

        # Record start time
        start_time = time.time()

        # Analyze the issue
        analysis_input = IssueAnalysisInput(
            issue=issue,
            file_path=full_file_path
        )

        analysis = issue_analyzer.analyze_issue(analysis_input)
        state.analyzed_issues.append(analysis)

        # Fix the issue
        fix_input = CodeFixInput(analysis=analysis, use_memory=True)
        fix = code_fixer.fix_issue(fix_input)

        # Apply the fix
        success = code_fixer.apply_fix(
            file_path=full_file_path,
            context=analysis.context,
            fixed_code=fix.fixed_code
        )

        # Record processing time
        processing_time = time.time() - start_time
        state.processing_times[issue_key] = processing_time

        if success:
            # Commit the change
            git_manager = GitRepoManager()
            git_manager.repo_path = state.repo_path
            git_manager.repo = Repo(state.repo_path)

            commit_message = f"Fix SonarQube issue: {issue_key}\n\n{issue['message']}"
            git_manager.commit_changes(file_path, commit_message)

            state.fixed_issues.append(fix)
            logger.info(f"Successfully fixed issue: {issue_key} in {processing_time:.2f} seconds")
        else:
            logger.warning(f"Could not apply fix for issue {issue_key}. Skipping.")
            state.skipped_issues.append(issue)

    except Exception as e:
        logger.error(f"Error processing issue {issue_key}: {str(e)}")
        state.skipped_issues.append(issue)

    # Move to the next issue
    state.current_issue_index += 1

    return state

def create_pull_request(state: WorkflowState) -> WorkflowState:
    """
    Create a pull request with the fixed issues.

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    logger.info("Creating pull request...")
    state.status = "creating_pull_request"

    # Check if any issues were fixed
    if not state.fixed_issues:
        logger.info("No issues were fixed. Skipping PR creation.")
        state.status = "completed"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time
        return state

    try:
        # Push the branch
        git_manager = GitRepoManager()
        git_manager.repo_path = state.repo_path
        git_manager.repo = Repo(state.repo_path)

        logger.info(f"Pushing branch {state.branch_name} to remote")
        git_manager.push_branch(state.branch_name)

        # Create pull request
        pr_input = PRCreatorInput(
            fixed_issues=state.fixed_issues,
            branch_name=state.branch_name
        )

        pr_output = pr_creator.create_pull_request(pr_input)

        state.pr_url = pr_output.pr_url
        state.pr_title = pr_output.pr_title
        state.pr_description = pr_output.pr_description
        state.num_issues_fixed = len(state.fixed_issues)

        state.status = "completed"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time

    except Exception as e:
        logger.error(f"Error creating pull request: {str(e)}")
        state.status = "error"
        state.error = f"Error creating pull request: {str(e)}"
        state.current_step = "end"
        state.duration_seconds = time.time() - state.start_time

    return state

def cleanup(state: WorkflowState) -> WorkflowState:
    """
    Clean up resources.

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state
    """
    logger.info("Cleaning up resources...")

    try:
        # Clean up Git repository
        if state.repo_path:
            git_manager = GitRepoManager()
            git_manager.repo_path = state.repo_path
            git_manager.cleanup()

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

    return state

# Define the workflow router
def router(state: WorkflowState) -> str:
    """
    Route the workflow to the next step.

    Args:
        state: Current workflow state

    Returns:
        Next step name
    """
    if state.current_step == "end":
        return END
    return state.current_step

# Create the workflow graph
def create_workflow_graph() -> StateGraph:
    """
    Create the workflow graph.

    Returns:
        StateGraph: The workflow graph
    """
    # Create the graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("fetch_issues", fetch_issues)
    workflow.add_node("setup_repository", setup_repository)
    workflow.add_node("process_issue", process_issue)
    workflow.add_node("create_pull_request", create_pull_request)
    workflow.add_node("cleanup", cleanup)

    # Add edges
    workflow.add_edge("fetch_issues", "setup_repository")
    workflow.add_edge("setup_repository", "process_issue")
    workflow.add_edge("process_issue", "process_issue")
    workflow.add_edge("process_issue", "create_pull_request")
    workflow.add_edge("create_pull_request", "cleanup")
    workflow.add_edge("cleanup", END)

    # Set the entry point
    workflow.set_entry_point("fetch_issues")

    # Set the router
    workflow.set_conditional_edges(
        "process_issue",
        lambda state: "create_pull_request" if state.current_issue_index >= len(state.issues) else "process_issue"
    )

    return workflow

# Create a compiled version of the workflow
sonar_fixer_workflow = create_workflow_graph().compile()

# Function to run the workflow
def run_workflow(max_issues: int = MAX_ISSUES_PER_RUN, days_lookback: int = 1,
                parallel_workers: int = 5, use_parallel: bool = True) -> WorkflowState:
    """
    Run the AI Sonar Issue Fixer workflow.

    Args:
        max_issues: Maximum number of issues to process
        days_lookback: Number of days to look back for issues
        parallel_workers: Number of parallel workers for issue processing
        use_parallel: Whether to use parallel processing

    Returns:
        Final workflow state
    """
    # Create initial state
    initial_state = WorkflowState(
        max_issues=max_issues,
        days_lookback=days_lookback,
        parallel_workers=parallel_workers,
        use_parallel=use_parallel
    )

    # Run the workflow
    logger.info(f"Starting AI Sonar Issue Fixer workflow with max_issues={max_issues}, "
               f"days_lookback={days_lookback}, parallel_workers={parallel_workers}, "
               f"use_parallel={use_parallel}")
    final_state = sonar_fixer_workflow.invoke(initial_state)

    # Log results
    if final_state.status == "completed":
        logger.info(f"Workflow completed successfully in {final_state.duration_seconds:.2f} seconds")
        logger.info(f"Found {final_state.num_issues_found} issues, fixed {final_state.num_issues_fixed} issues")

        if final_state.parallel_processing_time:
            logger.info(f"Parallel processing time: {final_state.parallel_processing_time:.2f} seconds")

        if final_state.pr_url:
            logger.info(f"Created PR: {final_state.pr_url}")
    else:
        logger.error(f"Workflow failed: {final_state.error}")

    return final_state
