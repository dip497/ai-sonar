"""
PR Creator Agent for creating pull requests with fixed code.
"""
from typing import Dict, List, Any, TypedDict, Optional
from langchain.prompts import PromptTemplate
from langchain.llms import GoogleGenerativeAI
from pydantic import BaseModel, Field
from config import GEMINI_API_KEY, GIT_MASTER_BRANCH
from src.utils.logger import setup_logger
from src.azure.devops_client import AzureDevOpsClient
from src.agents.code_fixer import CodeFixOutput

logger = setup_logger()

class PRCreatorInput(BaseModel):
    """Input for the PR creator agent."""
    fixed_issues: List[CodeFixOutput] = Field(..., description="List of fixed issues")
    branch_name: str = Field(..., description="Name of the branch with fixes")
    target_branch: str = Field(GIT_MASTER_BRANCH, description="Target branch for the PR")

class PRCreatorOutput(BaseModel):
    """Output from the PR creator agent."""
    pr_url: str = Field(..., description="URL of the created PR")
    pr_title: str = Field(..., description="Title of the PR")
    pr_description: str = Field(..., description="Description of the PR")
    num_issues_fixed: int = Field(..., description="Number of issues fixed")

class PRCreatorAgent:
    """
    Agent for creating pull requests with fixed code.
    """
    
    def __init__(self):
        """Initialize the PR creator agent."""
        self.api_key = GEMINI_API_KEY
        self.azure_client = AzureDevOpsClient()
        
        # Validate configuration
        if not self.api_key:
            logger.error("Gemini API key not configured")
            raise ValueError("Gemini API key not configured")
        
        # Initialize the LLM
        self.llm = GoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=self.api_key,
            temperature=0.2,
            top_p=0.95,
            max_output_tokens=2048
        )
        
        # Create the prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["fixed_issues_json"],
            template="""
You are an expert at creating clear and informative pull request descriptions. Your task is to create a PR description for the following fixed SonarQube issues:

1. **Fixed Issues**:
{fixed_issues_json}

2. **PR Description Task**:
   - Create a clear and concise PR title
   - Create a detailed PR description that explains the fixes
   - Group similar issues together
   - Highlight any important changes

3. **Return Format**:
Return your PR description in the following JSON format:
```json
{{
  "pr_title": "Fix SonarQube issues: [brief summary]",
  "pr_description": "# Fixed SonarQube Issues\\n\\n[detailed description with markdown formatting]"
}}
```
"""
        )
    
    def create_pull_request(self, input_data: PRCreatorInput) -> PRCreatorOutput:
        """
        Create a pull request with fixed code.
        
        Args:
            input_data: Input data containing the fixed issues and branch information
            
        Returns:
            PR creation output
        """
        fixed_issues = input_data.fixed_issues
        branch_name = input_data.branch_name
        target_branch = input_data.target_branch
        
        # Convert fixed issues to JSON for the prompt
        import json
        fixed_issues_json = json.dumps([{
            "issue_key": issue.issue_key,
            "file_path": issue.file_path,
            "explanation": issue.explanation,
            "confidence": issue.confidence
        } for issue in fixed_issues], indent=2)
        
        # Format the prompt
        prompt = self.prompt_template.format(
            fixed_issues_json=fixed_issues_json
        )
        
        # Generate the PR description
        logger.info(f"Generating PR description for {len(fixed_issues)} fixed issues")
        pr_text = self.llm.invoke(prompt)
        
        # Parse the PR description
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Find JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', pr_text, re.DOTALL)
            if json_match:
                pr_json = json.loads(json_match.group(1))
            else:
                # Try to find JSON without the markdown code block
                json_match = re.search(r'({.*})', pr_text, re.DOTALL)
                if json_match:
                    pr_json = json.loads(json_match.group(1))
                else:
                    logger.warning("Could not parse JSON from PR description")
                    pr_json = {
                        "pr_title": f"Fix {len(fixed_issues)} SonarQube issues",
                        "pr_description": self._generate_fallback_description(fixed_issues)
                    }
        except Exception as e:
            logger.error(f"Error parsing PR description: {str(e)}")
            pr_json = {
                "pr_title": f"Fix {len(fixed_issues)} SonarQube issues",
                "pr_description": self._generate_fallback_description(fixed_issues)
            }
        
        # Create the PR
        pr_title = pr_json.get("pr_title", f"Fix {len(fixed_issues)} SonarQube issues")
        pr_description = pr_json.get("pr_description", self._generate_fallback_description(fixed_issues))
        
        logger.info(f"Creating PR from {branch_name} to {target_branch}")
        pr_url = self.azure_client.create_pull_request(
            source_branch=branch_name,
            target_branch=target_branch,
            title=pr_title,
            description=pr_description
        )
        
        # Create the output
        output = PRCreatorOutput(
            pr_url=pr_url,
            pr_title=pr_title,
            pr_description=pr_description,
            num_issues_fixed=len(fixed_issues)
        )
        
        logger.info(f"Successfully created PR: {pr_url}")
        return output
    
    def _generate_fallback_description(self, fixed_issues: List[CodeFixOutput]) -> str:
        """
        Generate a fallback PR description if the LLM fails.
        
        Args:
            fixed_issues: List of fixed issues
            
        Returns:
            Fallback PR description
        """
        description = "# AI Sonar Issue Fixer\n\n"
        description += f"This PR fixes {len(fixed_issues)} SonarQube issues.\n\n"
        description += "## Fixed Issues\n\n"
        
        for issue in fixed_issues:
            description += f"- **{issue.issue_key}**\n"
            description += f"  - File: `{issue.file_path}`\n"
            description += f"  - Explanation: {issue.explanation}\n\n"
        
        description += "\n\n---\n"
        description += "This PR was automatically generated by the AI Sonar Issue Fixer."
        
        return description
