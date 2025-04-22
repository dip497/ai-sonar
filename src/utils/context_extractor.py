"""
Utility for extracting code context from files.
"""
import os
from config import CONTEXT_LINES_BEFORE, CONTEXT_LINES_AFTER
from src.utils.logger import setup_logger

logger = setup_logger()

def extract_code_context(file_path, line_number, context_before=None, context_after=None):
    """
    Extract code context from a file around a specific line number.
    
    Args:
        file_path (str): Path to the file
        line_number (int): Line number to extract context around
        context_before (int, optional): Number of lines to include before the target line
        context_after (int, optional): Number of lines to include after the target line
        
    Returns:
        dict: Dictionary containing the extracted context
    """
    if context_before is None:
        context_before = CONTEXT_LINES_BEFORE
    
    if context_after is None:
        context_after = CONTEXT_LINES_AFTER
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Convert to 0-based indexing
        line_index = line_number - 1
        
        # Calculate start and end indices
        start_index = max(0, line_index - context_before)
        end_index = min(len(lines) - 1, line_index + context_after)
        
        # Extract the context lines
        context_lines = lines[start_index:end_index + 1]
        
        # Create a context object
        context = {
            'file_path': file_path,
            'target_line': line_number,
            'start_line': start_index + 1,  # Convert back to 1-based indexing
            'end_line': end_index + 1,      # Convert back to 1-based indexing
            'context_text': ''.join(context_lines),
            'all_lines': lines,
            'context_lines': context_lines,
        }
        
        return context
    
    except Exception as e:
        logger.error(f"Error extracting context from {file_path}: {str(e)}")
        return None
