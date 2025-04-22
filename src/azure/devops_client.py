"""
Azure DevOps client for creating and managing pull requests.
"""
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from retry import retry
from config import (
    AZURE_DEVOPS_ORG,
    AZURE_DEVOPS_PROJECT,
    AZURE_DEVOPS_TOKEN,
    AZURE_DEVOPS_REPO_ID
)
from src.utils.logger import setup_logger

logger = setup_logger()

class AzureDevOpsClient:
    """
    Client for interacting with Azure DevOps API.
    """
    
    def __init__(self):
        """Initialize the Azure DevOps client."""
        self.organization = AZURE_DEVOPS_ORG
        self.project = AZURE_DEVOPS_PROJECT
        self.token = AZURE_DEVOPS_TOKEN
        self.repo_id = AZURE_DEVOPS_REPO_ID
        
        # Validate configuration
        if not all([self.organization, self.project, self.token, self.repo_id]):
            logger.error("Azure DevOps configuration incomplete")
            raise ValueError("Azure DevOps configuration incomplete")
        
        # Create a connection to Azure DevOps
        credentials = BasicAuthentication('', self.token)
        self.connection = Connection(base_url=f"https://dev.azure.com/{self.organization}", creds=credentials)
        
        # Get clients
        self.git_client = self.connection.clients.get_git_client()
    
    @retry(tries=3, delay=2, backoff=2, logger=logger)
    def create_pull_request(self, source_branch, target_branch, title, description):
        """
        Create a pull request in Azure DevOps.
        
        Args:
            source_branch (str): Source branch name
            target_branch (str): Target branch name
            title (str): Pull request title
            description (str): Pull request description
            
        Returns:
            str: URL of the created pull request
        """
        from azure.devops.v6_0.git.models import GitPullRequest
        
        logger.info(f"Creating pull request from {source_branch} to {target_branch}")
        
        try:
            # Create pull request
            pr = GitPullRequest(
                source_ref_name=f"refs/heads/{source_branch}",
                target_ref_name=f"refs/heads/{target_branch}",
                title=title,
                description=description
            )
            
            created_pr = self.git_client.create_pull_request(pr, self.repo_id, self.project)
            
            # Get the PR URL
            pr_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{self.repo_id}/pullrequest/{created_pr.pull_request_id}"
            
            logger.info(f"Pull request created successfully: {pr_url}")
            return pr_url
        
        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}")
            raise
    
    @retry(tries=3, delay=2, backoff=2, logger=logger)
    def add_reviewers_to_pr(self, pull_request_id, reviewer_ids):
        """
        Add reviewers to a pull request.
        
        Args:
            pull_request_id (int): Pull request ID
            reviewer_ids (list): List of reviewer IDs
        """
        from azure.devops.v6_0.git.models import IdentityRefWithVote
        
        logger.info(f"Adding reviewers to pull request {pull_request_id}")
        
        try:
            reviewers = [IdentityRefWithVote(id=reviewer_id) for reviewer_id in reviewer_ids]
            
            for reviewer in reviewers:
                self.git_client.create_pull_request_reviewer(
                    reviewer,
                    self.repo_id,
                    pull_request_id,
                    reviewer.id,
                    self.project
                )
            
            logger.info(f"Added {len(reviewers)} reviewers to pull request {pull_request_id}")
        
        except Exception as e:
            logger.error(f"Error adding reviewers to pull request: {str(e)}")
            raise
