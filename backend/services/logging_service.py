"""
Logging Service - Records all interactions for retraining pipeline
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class LoggingService:
    """
    Logs all prompts, SQL generations, executions, and feedback
    for future model retraining and analysis.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize logging service.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.interactions_file = os.path.join(log_dir, "interactions.jsonl")
        self.feedback_file = os.path.join(log_dir, "feedback.jsonl")
        self.errors_file = os.path.join(log_dir, "errors.jsonl")
    
    def log_interaction(
        self,
        question: str,
        prompt: str,
        retrieved_examples: List[Dict],
        refined_sql: Optional[str],
        final_sql: str,
        explanation: str,
        execution_results: Optional[List[Dict]],
        execution_time_ms: float,
        validation_passed: bool,
        error: Optional[str] = None
    ):
        """
        Log a complete interaction from question to results.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'prompt': prompt,
            'retrieved_examples': [
                {
                    'question': ex.get('question'),
                    'sql': ex.get('sql'),
                    'score': ex.get('score')
                }
                for ex in retrieved_examples
            ],
            'tinyllama_sql': None,  # Legacy field kept for backward compatibility
            'refined_sql': refined_sql,
            'final_sql': final_sql,
            'explanation': explanation,
            'execution_time_ms': execution_time_ms,
            'validation_passed': validation_passed,
            'result_count': len(execution_results) if execution_results else 0,
            'error': error,
            'model_chain': ['tinyllama']  # Legacy field kept for backward compatibility
        }
        
        self._append_to_jsonl(self.interactions_file, log_entry)
    
    def log_feedback(
        self,
        question: str,
        generated_sql: str,
        accepted: bool,
        corrected_sql: Optional[str] = None,
        user_notes: Optional[str] = None
    ):
        """
        Log user feedback for retraining pipeline.
        """
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'generated_sql': generated_sql,
            'accepted': accepted,
            'corrected_sql': corrected_sql,
            'user_notes': user_notes
        }
        
        self._append_to_jsonl(self.feedback_file, feedback_entry)
    
    def log_error(
        self,
        error_type: str,
        message: str,
        context: Dict[str, Any]
    ):
        """
        Log errors for debugging and monitoring.
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'message': message,
            'context': context
        }
        
        self._append_to_jsonl(self.errors_file, error_entry)
    
    def _append_to_jsonl(self, filepath: str, data: Dict):
        """Append a JSON line to a file."""
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  Logging error: {e}")
    
    def get_recent_interactions(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve recent interactions for analysis.
        """
        if not os.path.exists(self.interactions_file):
            return []
        
        interactions = []
        try:
            with open(self.interactions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        interactions.append(json.loads(line))
        except Exception as e:
            print(f"⚠️  Error reading interactions: {e}")
        
        return interactions[-limit:]
    
    def get_feedback_for_retraining(self) -> List[Dict]:
        """
        Get all feedback entries for retraining dataset.
        """
        if not os.path.exists(self.feedback_file):
            return []
        
        feedback = []
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        feedback.append(json.loads(line))
        except Exception as e:
            print(f"⚠️  Error reading feedback: {e}")
        
        return feedback


def create_logging_service(log_dir: str = "logs") -> LoggingService:
    """Factory function to create logging service."""
    return LoggingService(log_dir=log_dir)
