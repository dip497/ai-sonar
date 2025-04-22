"""
Issue Analyzer Agent for analyzing SonarQube issues.
"""
from typing import Dict, List, Any, TypedDict, Optional
from langchain.prompts import PromptTemplate
from langchain.llms import GoogleGenerativeAI
from pydantic import BaseModel, Field
from config import GEMINI_API_KEY
from src.utils.logger import setup_logger
from src.sonarqube.issue_fetcher import SonarQubeIssueFetcher
from src.utils.context_extractor import extract_code_context

logger = setup_logger()

class IssueAnalysisInput(BaseModel):
    """Input for the issue analyzer agent."""
    issue: Dict[str, Any] = Field(..., description="SonarQube issue to analyze")
    file_path: Optional[str] = Field(None, description="Path to the file containing the issue")
    context: Optional[Dict[str, Any]] = Field(None, description="Code context if already extracted")

class IssueAnalysisOutput(BaseModel):
    """Output from the issue analyzer agent."""
    issue_key: str = Field(..., description="SonarQube issue key")
    rule: str = Field(..., description="SonarQube rule ID")
    message: str = Field(..., description="Issue message")
    file_path: str = Field(..., description="Path to the file containing the issue")
    line_number: int = Field(..., description="Line number of the issue")
    context: Dict[str, Any] = Field(..., description="Extracted code context")
    analysis: str = Field(..., description="Analysis of the issue")
    fix_strategy: str = Field(..., description="Recommended strategy to fix the issue")
    complexity: str = Field(..., description="Estimated complexity of the fix (low, medium, high)")

class IssueAnalyzerAgent:
    """
    Agent for analyzing SonarQube issues and extracting relevant information.
    """
    
    def __init__(self):
        """Initialize the issue analyzer agent."""
        self.api_key = GEMINI_API_KEY
        
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
            input_variables=["rule", "message", "file", "line", "code_context"],
            template="""
You are an expert code analyzer specializing in understanding SonarQube issues. Your task is to analyze the following issue and provide insights:

1. **Issue Information**: 
   - SonarQube Rule: {rule} (the rule ID that was violated)
   - Message: {message} (a description of what was wrong)
   - Affected File: {file}
   - Affected Line: {line}

2. **Code Context**:
{code_context}

3. **Analysis Task**:
   - Analyze the issue in detail
   - Explain what's wrong with the code
   - Suggest a strategy to fix the issue
   - Estimate the complexity of the fix (low, medium, high)

4. **Return Format**:
Return your analysis in the following JSON format:
```json
{{
  "analysis": "Detailed analysis of the issue",
  "fix_strategy": "Recommended approach to fix the issue",
  "complexity": "low|medium|high"
}}
```
"""
        )
    
    def analyze_issue(self, input_data: IssueAnalysisInput) -> IssueAnalysisOutput:
        """
        Analyze a SonarQube issue.
        
        Args:
            input_data: Input data containing the issue and context
            
        Returns:
            Analysis output
        """
        issue = input_data.issue
        file_path = input_data.file_path
        context = input_data.context
        
        # Extract issue information
        issue_key = issue.get('key', '')
        rule = issue.get('rule', '')
        message = issue.get('message', '')
        component = issue.get('component', '')
        line_number = issue.get('line', 1)
        
        # Extract file path from component
        if not file_path:
            file_path = component.split(':')[-1]
        
        # Extract context if not provided
        if not context:
            context = extract_code_context(file_path, line_number)
            
            if not context:
                logger.error(f"Could not extract context for issue {issue_key}")
                raise ValueError(f"Could not extract context for issue {issue_key}")
        
        # Format the prompt
        prompt = self.prompt_template.format(
            rule=rule,
            message=message,
            file=file_path,
            line=line_number,
            code_context=context['context_text']
        )
        
        # Generate the analysis
        logger.info(f"Analyzing issue {issue_key} using Gemini")
        analysis_text = self.llm.invoke(prompt)
        
        # Parse the analysis
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Find JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', analysis_text, re.DOTALL)
            if json_match:
                analysis_json = json.loads(json_match.group(1))
            else:
                # Try to find JSON without the markdown code block
                json_match = re.search(r'({.*})', analysis_text, re.DOTALL)
                if json_match:
                    analysis_json = json.loads(json_match.group(1))
                else:
                    logger.warning(f"Could not parse JSON from analysis for issue {issue_key}")
                    analysis_json = {
                        "analysis": "Analysis parsing failed",
                        "fix_strategy": "Manual review required",
                        "complexity": "high"
                    }
        except Exception as e:
            logger.error(f"Error parsing analysis for issue {issue_key}: {str(e)}")
            analysis_json = {
                "analysis": "Analysis parsing failed",
                "fix_strategy": "Manual review required",
                "complexity": "high"
            }
        
        # Create the output
        output = IssueAnalysisOutput(
            issue_key=issue_key,
            rule=rule,
            message=message,
            file_path=file_path,
            line_number=line_number,
            context=context,
            analysis=analysis_json.get("analysis", "Analysis not available"),
            fix_strategy=analysis_json.get("fix_strategy", "Fix strategy not available"),
            complexity=analysis_json.get("complexity", "high")
        )
        
        logger.info(f"Successfully analyzed issue {issue_key}")
        return output
