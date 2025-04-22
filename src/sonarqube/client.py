"""
SonarQube API client for interacting with SonarQube.
"""
import requests
from retry import retry
from config import SONARQUBE_URL, SONARQUBE_TOKEN
from src.utils.logger import setup_logger

logger = setup_logger()

class SonarQubeClient:
    """
    Client for interacting with the SonarQube API.
    """
    
    def __init__(self, base_url=None, token=None):
        """
        Initialize the SonarQube client.
        
        Args:
            base_url (str, optional): SonarQube base URL
            token (str, optional): SonarQube API token
        """
        self.base_url = base_url or SONARQUBE_URL
        self.token = token or SONARQUBE_TOKEN
        self.auth = (self.token, '')  # SonarQube uses token as username and empty password
        
        # Validate configuration
        if not self.base_url or not self.token:
            logger.error("SonarQube URL or token not configured")
            raise ValueError("SonarQube URL or token not configured")
    
    @retry(tries=3, delay=2, backoff=2, logger=logger)
    def get(self, endpoint, params=None):
        """
        Make a GET request to the SonarQube API.
        
        Args:
            endpoint (str): API endpoint
            params (dict, optional): Query parameters
            
        Returns:
            dict: Response JSON
        """
        url = f"{self.base_url}/api/{endpoint}"
        logger.debug(f"Making GET request to {url}")
        
        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to SonarQube API: {str(e)}")
            raise
    
    @retry(tries=3, delay=2, backoff=2, logger=logger)
    def post(self, endpoint, data=None, params=None):
        """
        Make a POST request to the SonarQube API.
        
        Args:
            endpoint (str): API endpoint
            data (dict, optional): Request body
            params (dict, optional): Query parameters
            
        Returns:
            dict: Response JSON
        """
        url = f"{self.base_url}/api/{endpoint}"
        logger.debug(f"Making POST request to {url}")
        
        try:
            response = requests.post(url, json=data, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            
            # Some SonarQube endpoints return empty responses
            if response.text:
                return response.json()
            return {}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to SonarQube API: {str(e)}")
            raise
