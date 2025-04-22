"""
Git repository manager for cloning, branching, committing, and pushing changes.
"""
import os
import shutil
import tempfile
from git import Repo, GitCommandError
from retry import retry
from config import (
    GIT_REPO_URL,
    GIT_USERNAME,
    GIT_PASSWORD,
    GIT_EMAIL,
    GIT_NAME,
    GIT_MASTER_BRANCH,
    TEMP_DIR
)
from src.utils.logger import setup_logger

logger = setup_logger()

class GitRepoManager:
    """
    Manager for Git repository operations.
    """
    
    def __init__(self):
        """Initialize the Git repository manager."""
        self.repo_url = GIT_REPO_URL
        self.username = GIT_USERNAME
        self.password = GIT_PASSWORD
        self.email = GIT_EMAIL
        self.name = GIT_NAME
        self.master_branch = GIT_MASTER_BRANCH
        self.repo_path = None
        self.repo = None
        
        # Validate configuration
        if not self.repo_url:
            logger.error("Git repository URL not configured")
            raise ValueError("Git repository URL not configured")
    
    def clone_repo(self):
        """
        Clone the Git repository.
        
        Returns:
            str: Path to the cloned repository
        """
        # Create a unique directory for this run
        self.repo_path = tempfile.mkdtemp(dir=TEMP_DIR)
        logger.info(f"Cloning repository to {self.repo_path}")
        
        try:
            # Construct the URL with credentials if provided
            clone_url = self.repo_url
            if self.username and self.password:
                # Extract protocol and rest of the URL
                protocol, rest = self.repo_url.split('://', 1)
                clone_url = f"{protocol}://{self.username}:{self.password}@{rest}"
            
            # Clone the repository
            self.repo = Repo.clone_from(clone_url, self.repo_path)
            
            # Configure Git user
            with self.repo.config_writer() as git_config:
                git_config.set_value('user', 'email', self.email)
                git_config.set_value('user', 'name', self.name)
            
            logger.info(f"Repository cloned successfully to {self.repo_path}")
            return self.repo_path
        
        except GitCommandError as e:
            logger.error(f"Error cloning repository: {str(e)}")
            self.cleanup()
            raise
    
    def create_branch(self, branch_name):
        """
        Create a new branch.
        
        Args:
            branch_name (str): Name of the branch to create
        """
        if not self.repo:
            logger.error("Repository not cloned yet")
            raise ValueError("Repository not cloned yet")
        
        try:
            # Checkout master branch first
            self.repo.git.checkout(self.master_branch)
            
            # Create and checkout new branch
            self.repo.git.checkout('-b', branch_name)
            logger.info(f"Created and checked out branch: {branch_name}")
        
        except GitCommandError as e:
            logger.error(f"Error creating branch {branch_name}: {str(e)}")
            raise
    
    def commit_changes(self, file_path, commit_message):
        """
        Commit changes to a file.
        
        Args:
            file_path (str): Path to the file to commit
            commit_message (str): Commit message
        """
        if not self.repo:
            logger.error("Repository not cloned yet")
            raise ValueError("Repository not cloned yet")
        
        try:
            # Add the file
            self.repo.git.add(file_path)
            
            # Commit the changes
            self.repo.git.commit('-m', commit_message)
            logger.info(f"Committed changes to {file_path}")
        
        except GitCommandError as e:
            logger.error(f"Error committing changes: {str(e)}")
            raise
    
    @retry(tries=3, delay=2, backoff=2, logger=logger)
    def push_branch(self, branch_name):
        """
        Push a branch to the remote repository.
        
        Args:
            branch_name (str): Name of the branch to push
        """
        if not self.repo:
            logger.error("Repository not cloned yet")
            raise ValueError("Repository not cloned yet")
        
        try:
            # Push the branch
            self.repo.git.push('--set-upstream', 'origin', branch_name)
            logger.info(f"Pushed branch {branch_name} to remote")
        
        except GitCommandError as e:
            logger.error(f"Error pushing branch {branch_name}: {str(e)}")
            raise
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.repo_path and os.path.exists(self.repo_path):
            logger.info(f"Cleaning up repository at {self.repo_path}")
            shutil.rmtree(self.repo_path, ignore_errors=True)
