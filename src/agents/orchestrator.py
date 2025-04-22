"""
Orchestrator Agent for coordinating the AI Sonar Issue Fixer workflow.
"""
from typing import Dict, List, Any, TypedDict, Optional
from datetime import datetime
import os
from pydantic import BaseModel, Field
from config import MAX_ISSUES_PER_RUN, TEMP_DIR
from src.utils.logger import setup_logger
from src.sonarqube.issue_fetcher import SonarQubeIssueFetcher
from src.git.repo_manager import GitRepoManager
from src.agents.issue_analyzer import IssueAnalyzerAgent, IssueAnalysisInput
from src.agents.code_fixer import CodeFixerAgent, CodeFixInput
from src.agents.pr_creator import PRCreatorAgent, PRCreatorInput

logger = setup_logger()

class OrchestratorInput(BaseModel):
    """Input for the orchestrator agent."""
    max_issues: int = Field(MAX_ISSUES_PER_RUN, description="Maximum number of issues to process")
    days_lookback: int = Field(1, description="Number of days to look back for issues")

class OrchestratorOutput(BaseModel):
    """Output from the orchestrator agent."""
    num_issues_found: int = Field(..., description="Number of issues found")
    num_issues_fixed: int = Field(..., description="Number of issues fixed")
    pr_url: Optional[str] = Field(None, description="URL of the created PR")
    branch_name: Optional[str] = Field(None, description="Name of the branch with fixes")
    duration_seconds: float = Field(..., description="Duration of the run in seconds")

class OrchestratorAgent:
    """
    Agent for orchestrating the AI Sonar Issue Fixer workflow.
    """
    
    def __init__(self):
        """Initialize the orchestrator agent."""
        self.issue_fetcher = SonarQubeIssueFetcher()
        self.git_manager = None
        self.issue_analyzer = IssueAnalyzerAgent()
        self.code_fixer = CodeFixerAgent()
        self.pr_creator = PRCreatorAgent()
    
    def run(self, input_data: OrchestratorInput) -> OrchestratorOutput:
        """
        Run the AI Sonar Issue Fixer workflow.
        
        Args:
            input_data: Input data for the workflow
            
        Returns:
            Workflow output
        """
        import time
        start_time = time.time()
        
        # Generate timestamp and branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/sonar-{timestamp}"
        
        logger.info(f"Starting AI Sonar Issue Fixer run at {timestamp}")
        
        try:
            # Create temp directory if it doesn't exist
            os.makedirs(TEMP_DIR, exist_ok=True)
            
            # Fetch new issues from SonarQube
            logger.info("Fetching new issues from SonarQube...")
            issues = self.issue_fetcher.fetch_new_issues(
                max_issues=input_data.max_issues,
                days=input_data.days_lookback
            )
            
            if not issues:
                logger.info("No new issues found. Exiting.")
                return OrchestratorOutput(
                    num_issues_found=0,
                    num_issues_fixed=0,
                    duration_seconds=time.time() - start_time
                )
            
            logger.info(f"Found {len(issues)} new issues to fix")
            
            # Clone repository and create a new branch
            logger.info(f"Cloning repository and creating branch: {branch_name}")
            self.git_manager = GitRepoManager()
            repo_path = self.git_manager.clone_repo()
            self.git_manager.create_branch(branch_name)
            
            # Process each issue
            fixed_issues = []
            
            for i, issue in enumerate(issues):
                logger.info(f"Processing issue {i+1}/{len(issues)}: {issue['key']}")
                
                try:
                    # Extract file path
                    file_path = issue['component'].split(':')[-1]
                    full_file_path = os.path.join(repo_path, file_path)
                    
                    # Skip if file doesn't exist
                    if not os.path.exists(full_file_path):
                        logger.warning(f"File not found: {file_path}. Skipping issue.")
                        continue
                    
                    # Step 1: Analyze the issue
                    analysis_input = IssueAnalysisInput(
                        issue=issue,
                        file_path=full_file_path
                    )
                    
                    analysis = self.issue_analyzer.analyze_issue(analysis_input)
                    
                    # Step 2: Fix the issue
                    fix_input = CodeFixInput(analysis=analysis)
                    fix = self.code_fixer.fix_issue(fix_input)
                    
                    # Step 3: Apply the fix
                    success = self.code_fixer.apply_fix(
                        file_path=full_file_path,
                        context=analysis.context,
                        fixed_code=fix.fixed_code
                    )
                    
                    if not success:
                        logger.warning(f"Could not apply fix for issue {issue['key']}. Skipping.")
                        continue
                    
                    # Step 4: Commit the change
                    commit_message = f"Fix SonarQube issue: {issue['key']}\n\n{issue['message']}"
                    self.git_manager.commit_changes(file_path, commit_message)
                    
                    fixed_issues.append(fix)
                    logger.info(f"Successfully fixed issue: {issue['key']}")
                    
                except Exception as e:
                    logger.error(f"Error processing issue {issue['key']}: {str(e)}")
            
            # If no issues were fixed, exit
            if not fixed_issues:
                logger.info("No issues were fixed. Exiting without creating PR.")
                return OrchestratorOutput(
                    num_issues_found=len(issues),
                    num_issues_fixed=0,
                    duration_seconds=time.time() - start_time
                )
            
            # Push the branch
            logger.info(f"Pushing branch {branch_name} to remote")
            self.git_manager.push_branch(branch_name)
            
            # Create pull request
            logger.info("Creating pull request")
            pr_input = PRCreatorInput(
                fixed_issues=fixed_issues,
                branch_name=branch_name
            )
            
            pr_output = self.pr_creator.create_pull_request(pr_input)
            
            # Create the output
            output = OrchestratorOutput(
                num_issues_found=len(issues),
                num_issues_fixed=len(fixed_issues),
                pr_url=pr_output.pr_url,
                branch_name=branch_name,
                duration_seconds=time.time() - start_time
            )
            
            logger.info(f"AI Sonar Issue Fixer run completed in {output.duration_seconds:.2f} seconds")
            return output
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}")
            return OrchestratorOutput(
                num_issues_found=len(issues) if 'issues' in locals() else 0,
                num_issues_fixed=len(fixed_issues) if 'fixed_issues' in locals() else 0,
                duration_seconds=time.time() - start_time
            )
        
        finally:
            # Clean up
            if self.git_manager:
                self.git_manager.cleanup()
