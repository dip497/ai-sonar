"""
Code Fixer Agent for fixing code issues identified by SonarQube.
"""
from typing import Dict, List, Any, TypedDict, Optional
from langchain.prompts import PromptTemplate
from langchain.llms import GoogleGenerativeAI
from pydantic import BaseModel, Field
from config import GEMINI_API_KEY
from src.utils.logger import setup_logger
from src.utils.memory import AgentMemory, FixMemory
from src.utils.feedback import FeedbackManager, FeedbackItem
from src.agents.issue_analyzer import IssueAnalysisOutput

logger = setup_logger()

class CodeFixInput(BaseModel):
    """Input for the code fixer agent."""
    analysis: IssueAnalysisOutput = Field(..., description="Analysis of the issue")
    use_memory: bool = Field(True, description="Whether to use memory for fixing")

class CodeFixOutput(BaseModel):
    """Output from the code fixer agent."""
    issue_key: str = Field(..., description="SonarQube issue key")
    rule: str = Field(..., description="SonarQube rule ID")
    message: str = Field(..., description="Issue message")
    file_path: str = Field(..., description="Path to the file containing the issue")
    fixed_code: str = Field(..., description="Fixed code")
    original_code: Optional[str] = Field(None, description="Original code before fix")
    explanation: str = Field(..., description="Explanation of the fix")
    confidence: float = Field(..., description="Confidence in the fix (0-1)")
    used_memory: bool = Field(False, description="Whether memory was used for the fix")
    similar_fixes: List[Dict[str, Any]] = Field(default_factory=list, description="Similar fixes from memory")
    feedback: Optional[FeedbackItem] = Field(None, description="Automated feedback on the fix")

class CodeFixerAgent:
    """
    Agent for fixing code issues identified by SonarQube.
    """

    def __init__(self, memory_file: str = "agent_memory.json", feedback_file: str = "feedback.json"):
        """Initialize the code fixer agent."""
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

        # Initialize memory
        self.memory = AgentMemory(memory_file=memory_file)

        # Initialize feedback manager
        self.feedback_manager = FeedbackManager(feedback_file=feedback_file, memory=self.memory)

        # Create the memory-enhanced prompt template
        self.memory_prompt_template = PromptTemplate(
            input_variables=["rule", "message", "file", "line", "code_context", "analysis", "fix_strategy", "similar_fixes"],
            template="""
You are an expert code fixer specializing in fixing SonarQube issues. Your task is to fix the following issue:

1. **Issue Information**:
   - SonarQube Rule: {rule} (the rule ID that was violated)
   - Message: {message} (a description of what was wrong)
   - Affected File: {file}
   - Affected Line: {line}

2. **Code Context**:
{code_context}

3. **Issue Analysis**:
{analysis}

4. **Fix Strategy**:
{fix_strategy}

5. **Similar Fixes From Memory**:
{similar_fixes}

6. **Fix Task**:
   - Fix the code to resolve the SonarQube issue
   - Make minimal changes to the code
   - Ensure the fix follows best practices
   - Preserve the original code style and formatting
   - Learn from the similar fixes provided

7. **Return Format**:
Return your fix in the following JSON format:
```json
{{
  "fixed_code": "The complete fixed code that should replace the provided context",
  "explanation": "Explanation of the changes made",
  "confidence": 0.95,
  "memory_usage": "Explanation of how the similar fixes influenced your solution"
}}
```

The confidence should be a number between 0 and 1 indicating how confident you are in the fix.
"""
        )

        # Create the standard prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["rule", "message", "file", "line", "code_context", "analysis", "fix_strategy"],
            template="""
You are an expert code fixer specializing in fixing SonarQube issues. Your task is to fix the following issue:

1. **Issue Information**:
   - SonarQube Rule: {rule} (the rule ID that was violated)
   - Message: {message} (a description of what was wrong)
   - Affected File: {file}
   - Affected Line: {line}

2. **Code Context**:
{code_context}

3. **Issue Analysis**:
{analysis}

4. **Fix Strategy**:
{fix_strategy}

5. **Fix Task**:
   - Fix the code to resolve the SonarQube issue
   - Make minimal changes to the code
   - Ensure the fix follows best practices
   - Preserve the original code style and formatting

6. **Return Format**:
Return your fix in the following JSON format:
```json
{{
  "fixed_code": "The complete fixed code that should replace the provided context",
  "explanation": "Explanation of the changes made",
  "confidence": 0.95
}}
```

The confidence should be a number between 0 and 1 indicating how confident you are in the fix.
"""
        )

    def fix_issue(self, input_data: CodeFixInput) -> CodeFixOutput:
        """
        Fix a SonarQube issue.

        Args:
            input_data: Input data containing the issue analysis

        Returns:
            Fix output
        """
        analysis = input_data.analysis
        use_memory = input_data.use_memory
        similar_fixes = []
        used_memory = False
        memory_usage = ""

        # Get original code
        original_code = analysis.context['context_text']

        # Check if we should use memory
        if use_memory:
            # Get similar fixes from memory
            memory_fixes = self.memory.get_similar_fixes(
                issue_key=analysis.issue_key,
                rule=analysis.rule,
                message=analysis.message
            )

            if memory_fixes:
                used_memory = True
                logger.info(f"Found {len(memory_fixes)} similar fixes in memory for issue {analysis.issue_key}")

                # Format similar fixes for the prompt
                similar_fixes_text = ""
                for i, fix in enumerate(memory_fixes):
                    similar_fixes_text += f"Similar Fix #{i+1}:\n"
                    similar_fixes_text += f"Rule: {fix.rule}\n"
                    similar_fixes_text += f"Message: {fix.message}\n"
                    similar_fixes_text += f"Original Code:\n```\n{fix.original_code}\n```\n"
                    similar_fixes_text += f"Fixed Code:\n```\n{fix.fixed_code}\n```\n"
                    similar_fixes_text += f"Explanation: {fix.explanation}\n\n"

                # Convert to dict for output
                similar_fixes = [
                    {
                        "rule": fix.rule,
                        "message": fix.message,
                        "original_code": fix.original_code,
                        "fixed_code": fix.fixed_code,
                        "explanation": fix.explanation
                    }
                    for fix in memory_fixes
                ]

                # Use memory-enhanced prompt
                prompt = self.memory_prompt_template.format(
                    rule=analysis.rule,
                    message=analysis.message,
                    file=analysis.file_path,
                    line=analysis.line_number,
                    code_context=original_code,
                    analysis=analysis.analysis,
                    fix_strategy=analysis.fix_strategy,
                    similar_fixes=similar_fixes_text
                )
            else:
                # No similar fixes found, use standard prompt
                logger.info(f"No similar fixes found in memory for issue {analysis.issue_key}")
                prompt = self.prompt_template.format(
                    rule=analysis.rule,
                    message=analysis.message,
                    file=analysis.file_path,
                    line=analysis.line_number,
                    code_context=original_code,
                    analysis=analysis.analysis,
                    fix_strategy=analysis.fix_strategy
                )
        else:
            # Use standard prompt without memory
            prompt = self.prompt_template.format(
                rule=analysis.rule,
                message=analysis.message,
                file=analysis.file_path,
                line=analysis.line_number,
                code_context=original_code,
                analysis=analysis.analysis,
                fix_strategy=analysis.fix_strategy
            )

        # Generate the fix
        logger.info(f"Fixing issue {analysis.issue_key} using Gemini" + (" with memory" if used_memory else ""))
        fix_text = self.llm.invoke(prompt)

        # Parse the fix
        try:
            # Extract JSON from the response
            import json
            import re

            # Find JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', fix_text, re.DOTALL)
            if json_match:
                fix_json = json.loads(json_match.group(1))
            else:
                # Try to find JSON without the markdown code block
                json_match = re.search(r'({.*})', fix_text, re.DOTALL)
                if json_match:
                    fix_json = json.loads(json_match.group(1))
                else:
                    logger.warning(f"Could not parse JSON from fix for issue {analysis.issue_key}")
                    # If we can't parse JSON, assume the entire response is the fixed code
                    fix_json = {
                        "fixed_code": fix_text.strip(),
                        "explanation": "Fix parsing failed, using raw response",
                        "confidence": 0.5
                    }

            # Extract memory usage if available
            if "memory_usage" in fix_json and used_memory:
                memory_usage = fix_json["memory_usage"]

        except Exception as e:
            logger.error(f"Error parsing fix for issue {analysis.issue_key}: {str(e)}")
            # If we can't parse JSON, assume the entire response is the fixed code
            fix_json = {
                "fixed_code": fix_text.strip(),
                "explanation": f"Fix parsing failed: {str(e)}",
                "confidence": 0.5
            }

        # Generate automated feedback
        feedback = self.feedback_manager.process_automated_feedback(
            issue_key=analysis.issue_key,
            fixed_code=fix_json.get("fixed_code", ""),
            original_code=original_code
        )

        # Create the output
        output = CodeFixOutput(
            issue_key=analysis.issue_key,
            rule=analysis.rule,
            message=analysis.message,
            file_path=analysis.file_path,
            fixed_code=fix_json.get("fixed_code", ""),
            original_code=original_code,
            explanation=fix_json.get("explanation", "Explanation not available"),
            confidence=fix_json.get("confidence", 0.5),
            used_memory=used_memory,
            similar_fixes=similar_fixes,
            feedback=feedback
        )

        # Save to memory
        memory_item = FixMemory(
            issue_key=analysis.issue_key,
            rule=analysis.rule,
            message=analysis.message,
            file_path=analysis.file_path,
            fixed_code=fix_json.get("fixed_code", ""),
            original_code=original_code,
            explanation=fix_json.get("explanation", "Explanation not available"),
            success=feedback.success
        )
        self.memory.add_memory(memory_item)

        if used_memory:
            logger.info(f"Successfully fixed issue {analysis.issue_key} using memory")
            if memory_usage:
                logger.info(f"Memory usage: {memory_usage}")
        else:
            logger.info(f"Successfully fixed issue {analysis.issue_key}")

        logger.info(f"Automated feedback: {feedback.feedback_text} (Success: {feedback.success})")

        return output

    def apply_fix(self, file_path: str, context: Dict[str, Any], fixed_code: str) -> bool:
        """
        Apply the fixed code to the file.

        Args:
            file_path: Path to the file
            context: Code context
            fixed_code: Fixed code

        Returns:
            True if successful, False otherwise
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
