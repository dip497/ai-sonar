"""
Memory module for storing and retrieving agent memories.
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.utils.logger import setup_logger

logger = setup_logger()

class FixMemory(BaseModel):
    """Memory of a code fix."""
    issue_key: str = Field(..., description="SonarQube issue key")
    rule: str = Field(..., description="SonarQube rule ID")
    message: str = Field(..., description="Issue message")
    file_path: str = Field(..., description="Path to the file containing the issue")
    fixed_code: str = Field(..., description="Fixed code")
    original_code: Optional[str] = Field(None, description="Original code before fix")
    explanation: str = Field(..., description="Explanation of the fix")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of the fix")
    success: bool = Field(True, description="Whether the fix was successful")
    feedback: Optional[str] = Field(None, description="Feedback on the fix")
    feedback_timestamp: Optional[float] = Field(None, description="Timestamp of the feedback")

class AgentMemory:
    """
    Memory system for agents to store and retrieve previous fixes.
    """
    
    def __init__(self, memory_file: str = "agent_memory.json"):
        """
        Initialize the agent memory.
        
        Args:
            memory_file: Path to the memory file
        """
        self.memory_file = memory_file
        self.memories: List[FixMemory] = []
        self.load_memories()
    
    def load_memories(self):
        """Load memories from the memory file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [FixMemory(**item) for item in data]
                logger.info(f"Loaded {len(self.memories)} memories from {self.memory_file}")
            except Exception as e:
                logger.error(f"Error loading memories from {self.memory_file}: {str(e)}")
                self.memories = []
    
    def save_memories(self):
        """Save memories to the memory file."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump([memory.dict() for memory in self.memories], f, indent=2)
            logger.info(f"Saved {len(self.memories)} memories to {self.memory_file}")
        except Exception as e:
            logger.error(f"Error saving memories to {self.memory_file}: {str(e)}")
    
    def add_memory(self, memory: FixMemory):
        """
        Add a memory.
        
        Args:
            memory: Memory to add
        """
        self.memories.append(memory)
        self.save_memories()
    
    def get_memories_by_rule(self, rule: str, limit: int = 5) -> List[FixMemory]:
        """
        Get memories by rule.
        
        Args:
            rule: SonarQube rule ID
            limit: Maximum number of memories to return
            
        Returns:
            List of memories
        """
        # Sort by timestamp (newest first) and filter by rule
        memories = sorted(
            [m for m in self.memories if m.rule == rule and m.success],
            key=lambda m: m.timestamp,
            reverse=True
        )
        return memories[:limit]
    
    def get_similar_fixes(self, issue_key: str, rule: str, message: str, limit: int = 3) -> List[FixMemory]:
        """
        Get similar fixes for an issue.
        
        Args:
            issue_key: SonarQube issue key
            rule: SonarQube rule ID
            message: Issue message
            limit: Maximum number of fixes to return
            
        Returns:
            List of similar fixes
        """
        # First, try to find fixes for the same rule
        rule_fixes = self.get_memories_by_rule(rule, limit=limit)
        
        # If we don't have enough fixes, try to find fixes with similar messages
        if len(rule_fixes) < limit:
            # Simple similarity: check if any words in the message match
            message_words = set(message.lower().split())
            
            # Get fixes that don't match the rule but have similar messages
            similar_fixes = []
            for memory in self.memories:
                if memory.rule != rule and memory.success:
                    memory_words = set(memory.message.lower().split())
                    # Calculate word overlap
                    overlap = len(message_words.intersection(memory_words))
                    if overlap > 0:
                        similar_fixes.append((memory, overlap))
            
            # Sort by overlap (highest first)
            similar_fixes.sort(key=lambda x: x[1], reverse=True)
            
            # Add the most similar fixes until we reach the limit
            for memory, _ in similar_fixes:
                if len(rule_fixes) >= limit:
                    break
                if memory not in rule_fixes:
                    rule_fixes.append(memory)
        
        return rule_fixes
    
    def add_feedback(self, issue_key: str, feedback: str, success: bool = True):
        """
        Add feedback to a memory.
        
        Args:
            issue_key: SonarQube issue key
            feedback: Feedback on the fix
            success: Whether the fix was successful
        """
        for memory in self.memories:
            if memory.issue_key == issue_key:
                memory.feedback = feedback
                memory.feedback_timestamp = time.time()
                memory.success = success
                self.save_memories()
                logger.info(f"Added feedback to memory for issue {issue_key}")
                return
        
        logger.warning(f"No memory found for issue {issue_key}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Dictionary of statistics
        """
        total_memories = len(self.memories)
        successful_fixes = sum(1 for m in self.memories if m.success)
        rules = {}
        
        for memory in self.memories:
            rule = memory.rule
            if rule not in rules:
                rules[rule] = {"total": 0, "successful": 0}
            
            rules[rule]["total"] += 1
            if memory.success:
                rules[rule]["successful"] += 1
        
        return {
            "total_memories": total_memories,
            "successful_fixes": successful_fixes,
            "success_rate": successful_fixes / total_memories if total_memories > 0 else 0,
            "rules": rules
        }
