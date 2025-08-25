#!/usr/bin/env python3
"""
Claude Code Hook: UserPromptSubmit
Saves user prompts to PostgreSQL database with YAML fallback
"""
import os
import sys
import json
import logging
import subprocess
from datetime import datetime
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_postgres_connection():
    """
    TODO for task 2: Establish PostgreSQL connection using environment variables
    - Check for CLAUDE_POSTGRES_SERVER_DSN first
    - Fall back to individual env vars (HOST_PORT, USER, PASS, DB_NAME)
    - Enable SSL/TLS
    - Return connection object or None on failure
    """
    return None


def save_to_postgres(connection, prompt_data: Dict[str, Any]) -> bool:
    """
    TODO for task 3: Insert prompt data into user_prompts table
    - Use parameterized queries
    - Handle all fields: created_at, prompt, session_id, repository
    - Return True on success, False on failure
    """
    return False


def extract_repository_from_git() -> Optional[str]:
    """
    TODO for task 3: Extract repository info from git context
    - Use CLAUDE_PROJECT_DIR environment variable
    - Run git remote get-url origin
    - Parse and normalize repository format (e.g., github.com/user/repo)
    - Return None if not in git repository
    """
    return None


def get_session_id() -> Optional[str]:
    """
    TODO for task 3: Get session ID from environment
    - Check for session_id in environment variables
    - Validate UUID format if present
    - Return None if not available
    """
    return None


def save_to_yaml(yaml_file: Path, timestamp: str, user_prompt: str, session_id: Optional[str] = None) -> bool:
    """
    Save prompt to YAML file (existing functionality refactored)
    """
    # Load existing data or create new structure
    if yaml_file.exists():
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error reading YAML file: {e}")
            return False
    else:
        data = {}

    # Ensure user_prompts key exists
    if 'user_prompts' not in data:
        data['user_prompts'] = {}

    # Add the new prompt with timestamp
    data['user_prompts'][timestamp] = {
        "session_id": session_id or os.getenv("CLAUDE_SESSION_ID", ""),
        "user_prompt": user_prompt,
    }

    # Write back to file
    try:
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False,
                      allow_unicode=True, indent=2, default_style='|')
        return True
    except Exception as e:
        logger.error(f"Error writing to YAML file: {e}")
        return False


def main():
    # Read the event data from stdin
    try:
        event_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract the user prompt from the event data
    user_prompt = event_data.get('prompt', '')
    if not user_prompt:
        print("No user prompt found in event data", file=sys.stderr)
        sys.exit(1)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    created_at = datetime.now()
    
    # Check if PostgreSQL configuration exists
    has_postgres_config = any([
        os.getenv('CLAUDE_POSTGRES_SERVER_DSN'),
        all([
            os.getenv('CLAUDE_POSTGRES_SERVER_HOST_PORT'),
            os.getenv('CLAUDE_POSTGRES_SERVER_USER'),
            os.getenv('CLAUDE_POSTGRES_SERVER_PASS'),
            os.getenv('CLAUDE_POSTGRES_SERVER_DB_NAME')
        ])
    ])
    
    saved_successfully = False
    
    if has_postgres_config:
        logger.info("PostgreSQL configuration detected, attempting database storage")
        
        # Try PostgreSQL storage
        connection = get_postgres_connection()
        
        if connection:
            # Prepare prompt data
            prompt_data = {
                'created_at': created_at,
                'prompt': user_prompt,
                'session_id': get_session_id(),
                'repository': extract_repository_from_git()
            }
            
            # Attempt to save to PostgreSQL
            if save_to_postgres(connection, prompt_data):
                saved_successfully = True
                logger.info("Successfully saved prompt to PostgreSQL")
            else:
                logger.warning("Failed to save to PostgreSQL, falling back to YAML")
            
            # Close the connection
            try:
                connection.close()
            except:
                pass
        else:
            logger.warning("Could not establish PostgreSQL connection, falling back to YAML")
    else:
        logger.info("No PostgreSQL configuration found, using YAML storage")
    
    # Fall back to YAML if PostgreSQL failed or wasn't configured
    if not saved_successfully:
        yaml_file = Path(os.getenv("CLAUDE_PROJECT_DIR"), "user_prompts.yaml")
        
        # Get session_id for YAML storage (might be different from PostgreSQL logic)
        session_id = get_session_id() or os.getenv("CLAUDE_SESSION_ID", "")
        
        if save_to_yaml(yaml_file, timestamp, user_prompt, session_id):
            logger.info(f"Prompt saved to YAML: {yaml_file}")
        else:
            logger.error("Failed to save prompt to YAML")
            sys.exit(1)


if __name__ == "__main__":
    main()
