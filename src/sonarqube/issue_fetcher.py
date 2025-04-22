"""
Module for fetching and filtering SonarQube issues.
"""
import time
from datetime import datetime, timedelta
import requests
from config import SONARQUBE_PROJECT_KEY
from src.sonarqube.client import SonarQubeClient
from src.utils.logger import setup_logger

logger = setup_logger()

class SonarQubeIssueFetcher:
    """
    Class for fetching and filtering SonarQube issues.
    """
    
    def __init__(self):
        """Initialize the SonarQube issue fetcher."""
        self.client = SonarQubeClient()
    
    def fetch_new_issues(self, max_issues=50, days=1):
        """
        Fetch new issues from SonarQube.
        
        Args:
            max_issues (int, optional): Maximum number of issues to fetch
            days (int, optional): Number of days to look back for new issues
            
        Returns:
            list: List of new issues
        """
        # Calculate the date from which to fetch issues
        created_after = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Fetch issues from SonarQube
        issues = self._fetch_issues(
            project_key=SONARQUBE_PROJECT_KEY,
            statuses="OPEN",
            created_after=created_after,
            max_issues=max_issues
        )
        
        logger.info(f"Fetched {len(issues)} new issues from SonarQube")
        return issues
    
    def fetch_issues_since_last_build(self, jenkins_client, max_issues=50):
        """
        Fetch issues created since the last successful Jenkins build.
        
        Args:
            jenkins_client: Jenkins client instance
            max_issues (int, optional): Maximum number of issues to fetch
            
        Returns:
            list: List of new issues
        """
        # Get the timestamp of the last successful build
        last_build_timestamp = jenkins_client.get_last_successful_build_timestamp()
        
        if not last_build_timestamp:
            logger.warning("Could not determine last successful build timestamp. Using 1 day ago.")
            return self.fetch_new_issues(max_issues=max_issues)
        
        # Convert timestamp to ISO format
        created_after = datetime.fromtimestamp(last_build_timestamp / 1000).strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Fetch issues from SonarQube
        issues = self._fetch_issues(
            project_key=SONARQUBE_PROJECT_KEY,
            statuses="OPEN",
            created_after=created_after,
            max_issues=max_issues
        )
        
        logger.info(f"Fetched {len(issues)} issues created since last successful build")
        return issues
    
    def _fetch_issues(self, project_key, statuses="OPEN", created_after=None, max_issues=50):
        """
        Fetch issues from SonarQube with pagination.
        
        Args:
            project_key (str): SonarQube project key
            statuses (str, optional): Issue statuses to filter by
            created_after (str, optional): ISO date to filter issues created after
            max_issues (int, optional): Maximum number of issues to fetch
            
        Returns:
            list: List of issues
        """
        all_issues = []
        page = 1
        page_size = 100  # Maximum allowed by SonarQube API
        
        while len(all_issues) < max_issues:
            params = {
                'componentKeys': project_key,
                'statuses': statuses,
                'p': page,
                'ps': page_size,
                's': 'CREATION_DATE',
                'asc': 'false'  # Get newest issues first
            }
            
            if created_after:
                params['createdAfter'] = created_after
            
            try:
                response = self.client.get('issues/search', params=params)
                issues = response.get('issues', [])
                
                if not issues:
                    break
                
                all_issues.extend(issues)
                
                # Check if we've reached the last page
                if len(issues) < page_size:
                    break
                
                page += 1
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching issues: {str(e)}")
                break
        
        # Limit to max_issues
        return all_issues[:max_issues]
