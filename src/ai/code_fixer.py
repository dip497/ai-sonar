"""
AI-powered code fixer using Gemini 2.0 via LangChain.
"""
import os
from langchain.llms import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from config import GEMINI_API_KEY, CONTEXT_LINES_BEFORE, CONTEXT_LINES_AFTER
from src.utils.context_extractor import extract_code_context
from src.utils.logger import setup_logger

logger = setup_logger()

class CodeFixer:
    """
    AI-powered code fixer using Gemini 2.0.
    """
    
    def __init__(self):
        """Initialize the code fixer."""
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
You are an AI assistant designed to help improve code by fixing issues identified by SonarQube. The following is the context and task you need to handle:

1. **Issue Information**: 
   - SonarQube Rule: {rule} (the rule ID that was violated)
   - Message: {message} (a description of what was wrong)
   - Affected File: {file}
   - Affected Line: {line}

2. **Code Context**:
{code_context}

3. **Task**:
   - Understand the problem described in the SonarQube issue.
   - Use best practices to fix the code while maintaining readability and efficiency.
   - Return ONLY the fixed code snippet that resolves the issue.
   - Do not include any explanations or comments outside the code.
   - Preserve the indentation and formatting of the original code.
   - Make minimal changes necessary to fix the issue.

4. **Return Format**:
Return ONLY the fixed code snippet, nothing else. The fixed code should be a direct replacement for the provided code context.
"""
        )
    
    def extract_context(self, file_path, issue):
        """
        Extract code context from a file for a specific issue.
        
        Args:
            file_path (str): Path to the file
            issue (dict): SonarQube issue
            
        Returns:
            dict: Extracted context
        """
        # Get the line number from the issue
        line_number = issue.get('line', 1)
        
        # Extract context
        context = extract_code_context(
            file_path,
            line_number,
            context_before=CONTEXT_LINES_BEFORE,
            context_after=CONTEXT_LINES_AFTER
        )
        
        return context
    
    def fix_issue(self, issue, context):
        """
        Fix a SonarQube issue using AI.
        
        Args:
            issue (dict): SonarQube issue
            context (dict): Code context
            
        Returns:
            str: Fixed code
        """
        if not context:
            logger.error("No context provided for issue")
            return None
        
        try:
            # Extract issue information
            rule = issue.get('rule', '')
            message = issue.get('message', '')
            file = issue.get('component', '').split(':')[-1]
            line = issue.get('line', 1)
            
            # Format the prompt
            prompt = self.prompt_template.format(
                rule=rule,
                message=message,
                file=file,
                line=line,
                code_context=context['context_text']
            )
            
            # Generate the fixed code
            logger.info(f"Generating fix for issue {issue.get('key')} using Gemini")
            fixed_code = self.llm.invoke(prompt)
            
            # Clean up the response
            fixed_code = fixed_code.strip()
            
            # Log success
            logger.info(f"Successfully generated fix for issue {issue.get('key')}")
            return fixed_code
        
        except Exception as e:
            logger.error(f"Error fixing issue: {str(e)}")
            return None
    
    def apply_fix(self, file_path, context, fixed_code):
        """
        Apply the fixed code to the file.
        
        Args:
            file_path (str): Path to the file
            context (dict): Code context
            fixed_code (str): Fixed code
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Replace the context lines with the fixed code
            start_line = context['start_line'] - 1  # Convert to 0-based indexing
            end_line = context['end_line'] - 1      # Convert to 0-based indexing
            
            # Split the fixed code into lines
            fixed_lines = fixed_code.split('\n')
            
            # Add newline character to each line except the last one
            fixed_lines = [line + '\n' for line in fixed_lines[:-1]] + [fixed_lines[-1]]
            
            # Replace the lines
            new_lines = lines[:start_line] + fixed_lines + lines[end_line + 1:]
            
            # Write the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
            
            logger.info(f"Successfully applied fix to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error applying fix to {file_path}: {str(e)}")
            return False
