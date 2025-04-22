"""
Feedback module for collecting and processing feedback on fixes.
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.utils.logger import setup_logger
from src.utils.memory import AgentMemory, FixMemory

logger = setup_logger()

class FeedbackItem(BaseModel):
    """Feedback on a code fix."""
    issue_key: str = Field(..., description="SonarQube issue key")
    feedback_text: str = Field(..., description="Feedback text")
    success: bool = Field(True, description="Whether the fix was successful")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of the feedback")
    source: str = Field("user", description="Source of the feedback (user, automated, etc.)")

class FeedbackManager:
    """
    Manager for collecting and processing feedback on fixes.
    """
    
    def __init__(self, feedback_file: str = "feedback.json", memory: Optional[AgentMemory] = None):
        """
        Initialize the feedback manager.
        
        Args:
            feedback_file: Path to the feedback file
            memory: Agent memory instance
        """
        self.feedback_file = feedback_file
        self.feedback_items: List[FeedbackItem] = []
        self.memory = memory or AgentMemory()
        self.load_feedback()
    
    def load_feedback(self):
        """Load feedback from the feedback file."""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.feedback_items = [FeedbackItem(**item) for item in data]
                logger.info(f"Loaded {len(self.feedback_items)} feedback items from {self.feedback_file}")
            except Exception as e:
                logger.error(f"Error loading feedback from {self.feedback_file}: {str(e)}")
                self.feedback_items = []
    
    def save_feedback(self):
        """Save feedback to the feedback file."""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump([item.dict() for item in self.feedback_items], f, indent=2)
            logger.info(f"Saved {len(self.feedback_items)} feedback items to {self.feedback_file}")
        except Exception as e:
            logger.error(f"Error saving feedback to {self.feedback_file}: {str(e)}")
    
    def add_feedback(self, feedback: FeedbackItem):
        """
        Add feedback.
        
        Args:
            feedback: Feedback to add
        """
        self.feedback_items.append(feedback)
        self.save_feedback()
        
        # Update memory with feedback
        if self.memory:
            self.memory.add_feedback(
                issue_key=feedback.issue_key,
                feedback=feedback.feedback_text,
                success=feedback.success
            )
    
    def get_feedback_for_issue(self, issue_key: str) -> List[FeedbackItem]:
        """
        Get feedback for an issue.
        
        Args:
            issue_key: SonarQube issue key
            
        Returns:
            List of feedback items
        """
        return [item for item in self.feedback_items if item.issue_key == issue_key]
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics.
        
        Returns:
            Dictionary of statistics
        """
        total_feedback = len(self.feedback_items)
        positive_feedback = sum(1 for item in self.feedback_items if item.success)
        
        sources = {}
        for item in self.feedback_items:
            source = item.source
            if source not in sources:
                sources[source] = {"total": 0, "positive": 0}
            
            sources[source]["total"] += 1
            if item.success:
                sources[source]["positive"] += 1
        
        return {
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "positive_rate": positive_feedback / total_feedback if total_feedback > 0 else 0,
            "sources": sources
        }
    
    def process_automated_feedback(self, issue_key: str, fixed_code: str, original_code: str) -> FeedbackItem:
        """
        Process automated feedback on a fix.
        
        Args:
            issue_key: SonarQube issue key
            fixed_code: Fixed code
            original_code: Original code
            
        Returns:
            Feedback item
        """
        # Simple automated feedback: check if the code has changed
        if fixed_code == original_code:
            feedback_text = "The code was not changed."
            success = False
        else:
            # Check if the fix is minimal (less than 20% change)
            original_lines = original_code.strip().split('\n')
            fixed_lines = fixed_code.strip().split('\n')
            
            # Calculate the difference in line count
            line_diff = abs(len(fixed_lines) - len(original_lines))
            line_diff_percent = line_diff / len(original_lines) if original_lines else 0
            
            if line_diff_percent > 0.2:
                feedback_text = f"The fix changed {line_diff_percent:.0%} of the code, which is more than expected."
                success = True  # Still consider it a success, but with a warning
            else:
                feedback_text = "The fix made minimal changes to the code."
                success = True
        
        # Create feedback item
        feedback = FeedbackItem(
            issue_key=issue_key,
            feedback_text=feedback_text,
            success=success,
            source="automated"
        )
        
        # Add feedback
        self.add_feedback(feedback)
        
        return feedback
