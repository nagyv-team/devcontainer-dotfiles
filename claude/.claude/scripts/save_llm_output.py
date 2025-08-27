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
    """
    try:
        # Read JSON from stdin
        hook_data = json.load(sys.stdin)
        logger.debug(f"Received hook data: {hook_data}")
        
        # Validate required fields
        required_fields = ['transcript_path', 'hook_event_name']
        missing_fields = [field for field in required_fields if field not in hook_data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate hook event name
        if hook_data['hook_event_name'] != 'Stop':
            raise ValueError(f"Expected Stop hook, got {hook_data['hook_event_name']}")
        
        # Expand transcript path if it contains ~
        if 'transcript_path' in hook_data:
            hook_data['transcript_path'] = os.path.expanduser(hook_data['transcript_path'])
        
        return hook_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from stdin: {e}")
        raise
    except ValueError as e:
        logger.error(f"Invalid hook input: {e}")
        raise


def read_transcript_file(transcript_path: str) -> Optional[Dict[str, Any]]:
    """
    Read transcript JSONL file and extract the last assistant message.
    
    Args:
        transcript_path: Path to the transcript JSONL file
        
    Returns:
        The last assistant message dict or None if not found
    """
    transcript_path = Path(transcript_path)
    
    # Check if file exists
    if not transcript_path.exists():
        logger.error(f"Transcript file not found: {transcript_path}")
        return None
    
    last_assistant_message = None
    
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON line
                    data = json.loads(line)
                    
                    # Check if this is an assistant message
                    if data.get('type') == 'assistant' and 'message' in data:
                        last_assistant_message = data
                        logger.debug(f"Found assistant message at line {line_num}")
                        
                except json.JSONDecodeError as e:
                    # Skip malformed lines
                    logger.debug(f"Skipping malformed JSON at line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error processing line {line_num}: {e}")
                    continue
    
    except Exception as e:
        logger.error(f"Error reading transcript file: {e}")
        return None
    
    if not last_assistant_message:
        logger.warning(f"No assistant message found in transcript: {transcript_path}")
    
    return last_assistant_message


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
    """
    metadata = {
        'output': None,
        'model': None,
        'input_tokens': None,
        'output_tokens': None,
        'service_tier': None
    }
    
    if not assistant_message or 'message' not in assistant_message:
        logger.warning("No message field in assistant_message")
        return metadata
    
    message = assistant_message['message']
    
    # Extract text content
    if 'content' in message and isinstance(message['content'], list):
        text_parts = []
        for content_item in message['content']:
            if isinstance(content_item, dict) and content_item.get('type') == 'text':
                text_parts.append(content_item.get('text', ''))
        
        if text_parts:
            metadata['output'] = '\n'.join(text_parts)
            logger.debug(f"Extracted output text of length {len(metadata['output'])}")
    
    # Extract model
    if 'model' in message:
        metadata['model'] = message['model']
        logger.debug(f"Extracted model: {metadata['model']}")
    
    # Extract usage statistics
    if 'usage' in message and isinstance(message['usage'], dict):
        usage = message['usage']
        
        if 'input_tokens' in usage:
            metadata['input_tokens'] = usage['input_tokens']
            logger.debug(f"Extracted input_tokens: {metadata['input_tokens']}")
        
        if 'output_tokens' in usage:
            metadata['output_tokens'] = usage['output_tokens']
            logger.debug(f"Extracted output_tokens: {metadata['output_tokens']}")
        
        if 'service_tier' in usage:
            metadata['service_tier'] = usage['service_tier']
            logger.debug(f"Extracted service_tier: {metadata['service_tier']}")
    
    return metadata


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