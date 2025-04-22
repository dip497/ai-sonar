"""
Configuration settings for the AI Sonar Issue Fixer.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SonarQube Configuration
SONARQUBE_URL = os.getenv("SONARQUBE_URL", "https://sonarqube.example.com")
SONARQUBE_TOKEN = os.getenv("SONARQUBE_TOKEN", "")
SONARQUBE_PROJECT_KEY = os.getenv("SONARQUBE_PROJECT_KEY", "")

# Git Configuration
GIT_REPO_URL = os.getenv("GIT_REPO_URL", "")
GIT_USERNAME = os.getenv("GIT_USERNAME", "")
GIT_PASSWORD = os.getenv("GIT_PASSWORD", "")
GIT_EMAIL = os.getenv("GIT_EMAIL", "ai-sonar-fixer@example.com")
GIT_NAME = os.getenv("GIT_NAME", "AI Sonar Fixer")
GIT_MASTER_BRANCH = os.getenv("GIT_MASTER_BRANCH", "master")

# Azure DevOps Configuration
AZURE_DEVOPS_ORG = os.getenv("AZURE_DEVOPS_ORG", "")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT", "")
AZURE_DEVOPS_TOKEN = os.getenv("AZURE_DEVOPS_TOKEN", "")
AZURE_DEVOPS_REPO_ID = os.getenv("AZURE_DEVOPS_REPO_ID", "")

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Jenkins Configuration
JENKINS_URL = os.getenv("JENKINS_URL", "")
JENKINS_JOB_NAME = os.getenv("JENKINS_JOB_NAME", "")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME", "")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN", "")

# Application Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/ai-sonar-fixer")
MAX_ISSUES_PER_RUN = int(os.getenv("MAX_ISSUES_PER_RUN", "50"))
CONTEXT_LINES_BEFORE = int(os.getenv("CONTEXT_LINES_BEFORE", "10"))
CONTEXT_LINES_AFTER = int(os.getenv("CONTEXT_LINES_AFTER", "10"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds
