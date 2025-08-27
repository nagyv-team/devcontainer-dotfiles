#!/usr/bin/env python3
"""
Claude Code Hook: Stop
Saves LLM output to PostgreSQL database when Claude Code session ends.
Extracts the last assistant message from transcript files and persists it 
with metadata for analysis and monitoring purposes.
"""
import os
import sys
import json
import logging
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

logger = logging.getLogger(__name__)


def parse_hook_input() -> Dict[str, Any]:
    """
    Read and validate hook input from stdin.
    
    Expected stdin input schema:
    {
        "session_id": "abc123",
        "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
        "hook_event_name": "Stop",
        "stop_hook_active": true,
        "cwd": "/workspaces/project-dir"
    }
    
    Returns:
        Parsed hook data dictionary
        
    Raises:
        json.JSONDecodeError: If stdin contains invalid JSON
        ValueError: If required fields are missing
    
    TODO for task 1: Implement JSON parsing and validation logic
    """
    pass  # TODO for task 1: Read JSON from stdin, validate required fields, return parsed data


def read_transcript_file(transcript_path: str) -> Optional[Dict[str, Any]]:
    """
    Read transcript JSONL file and extract the last assistant message.
    
    Args:
        transcript_path: Path to the transcript JSONL file
        
    Returns:
        The last assistant message dict or None if not found
    
    TODO for task 1: Implement file reading and parsing logic
    - Handle file not found
    - Parse JSONL line by line
    - Handle malformed JSON gracefully (skip bad lines)
    - Return last assistant message
    """
    pass  # TODO for task 1: Read JSONL file, find last assistant message


def extract_llm_metadata(assistant_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract LLM output and metadata from assistant message.
    
    Expected message structure:
    {
        "message": {
            "content": [{"type": "text", "text": "output text"}],
            "model": "claude-opus-4-1-20250805",
            "usage": {
                "input_tokens": 6,
                "output_tokens": 567,
                "service_tier": "standard"
            }
        }
    }
    
    Args:
        assistant_message: The assistant message dict from transcript
        
    Returns:
        Dictionary with extracted metadata:
        - output: The text content
        - model: Model name (nullable)
        - input_tokens: Input token count (nullable)
        - output_tokens: Output token count (nullable)
        - service_tier: Service tier (nullable)
    
    TODO for task 1: Implement metadata extraction logic
    """
    pass  # TODO for task 1: Extract text content and usage statistics from message


def get_postgres_connection():
    """
    Establish PostgreSQL connection using environment variables.
    
    Similar to save_user_prompt.py implementation:
    - Check for CLAUDE_POSTGRES_SERVER_DSN first
    - Fall back to individual env vars (HOST_PORT, USER, PASS, DB_NAME)
    - Enable SSL/TLS
    - Return connection object or None on failure
    
    TODO for task 2: Implement PostgreSQL connection logic
    """
    pass  # TODO for task 2: Establish database connection


def extract_repository_from_git(cwd: Optional[str] = None) -> Optional[str]:
    """
    Extract repository info from git context.
    
    Args:
        cwd: Working directory path, defaults to current directory
        
    Returns:
        Normalized repository format (e.g., github.com/user/repo) or None
    
    TODO for task 2: Implement git repository extraction (reuse from save_user_prompt.py)
    """
    pass  # TODO for task 2: Extract and normalize repository from git remote


def save_llm_output_to_postgres(connection, llm_data: Dict[str, Any]) -> bool:
    """
    Save LLM output data to the llm_outputs table.
    
    Database schema:
    - id: SERIAL PRIMARY KEY
    - created_at: TIMESTAMP NOT NULL, indexed
    - output: TEXT NOT NULL
    - session_id: VARCHAR(255), indexed
    - repository: VARCHAR(500), indexed
    - input_tokens: int
    - output_tokens: int
    - model: VARCHAR(100)
    - service_tier: VARCHAR(100)
    
    Args:
        connection: PostgreSQL connection object
        llm_data: Dictionary with all fields to save
        
    Returns:
        True on success, False on failure
    
    TODO for task 2: Implement database insert logic
    """
    pass  # TODO for task 2: Insert data into llm_outputs table


def main():
    """
    Main entry point for the Stop hook script.
    
    Orchestrates the flow:
    1. Parse hook input from stdin
    2. Read transcript file
    3. Extract LLM output and metadata
    4. Establish database connection
    5. Save to PostgreSQL
    6. Handle errors appropriately (no fallback)
    
    TODO for task 3: Wire together all components
    """
    # TODO for task 3: Implement main flow
    # - Parse hook input
    # - Extract transcript path and session_id
    # - Read transcript file
    # - Extract LLM metadata
    # - Get repository info
    # - Connect to database
    # - Save to PostgreSQL
    # - Handle all error cases
    pass


if __name__ == "__main__":
    main()