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
import re
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
    Establish PostgreSQL connection using environment variables
    - Check for CLAUDE_POSTGRES_SERVER_DSN first
    - Fall back to individual env vars (HOST_PORT, USER, PASS, DB_NAME)
    - Enable SSL/TLS
    - Return connection object or None on failure
    """
    try:
        import psycopg
        
        # Check for DSN first (takes precedence)
        dsn = os.getenv('CLAUDE_POSTGRES_SERVER_DSN')
        
        if dsn:
            logger.debug("Attempting PostgreSQL connection using DSN")
            # Ensure SSL is required
            if 'sslmode=' not in dsn:
                dsn += '?sslmode=require' if '?' not in dsn else '&sslmode=require'
            conn = psycopg.connect(dsn, connect_timeout=5)
            logger.info("Successfully connected to PostgreSQL using DSN")
            return conn
        
        # Fall back to individual environment variables
        host_port = os.getenv('CLAUDE_POSTGRES_SERVER_HOST_PORT')
        user = os.getenv('CLAUDE_POSTGRES_SERVER_USER')
        password = os.getenv('CLAUDE_POSTGRES_SERVER_PASS')
        db_name = os.getenv('CLAUDE_POSTGRES_SERVER_DB_NAME')
        
        if host_port and user and password and db_name:
            logger.debug("Attempting PostgreSQL connection using individual environment variables")
            # Parse host and port
            if ':' in host_port:
                host, port = host_port.split(':', 1)
            else:
                host = host_port
                port = '5432'  # Default PostgreSQL port
            
            # Build connection string
            conn_string = (
                f"host={host} "
                f"port={port} "
                f"dbname={db_name} "
                f"user={user} "
                f"password={password} "
                f"sslmode=require "
                f"connect_timeout=5"
            )
            
            conn = psycopg.connect(conn_string)
            logger.info("Successfully connected to PostgreSQL using individual environment variables")
            return conn
        
        logger.debug("No PostgreSQL configuration found in environment variables")
        return None
        
    except ImportError:
        logger.warning("psycopg module not installed, PostgreSQL support unavailable")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to PostgreSQL: {e}")
        return None


def save_to_postgres(connection, prompt_data: Dict[str, Any]) -> bool:
    """
    Insert prompt data into user_prompts table
    - Use parameterized queries
    - Handle all fields: created_at, prompt, session_id, repository
    - Return True on success, False on failure
    """
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Prepare the INSERT query with parameterized values
            insert_query = """
                INSERT INTO user_prompts (created_at, prompt, session_id, repository)
                VALUES (%s, %s, %s, %s)
            """
            
            # Execute the query with the provided data
            cursor.execute(
                insert_query,
                (
                    prompt_data.get('created_at'),
                    prompt_data.get('prompt'),
                    prompt_data.get('session_id'),
                    prompt_data.get('repository')
                )
            )
            
            # Commit the transaction
            connection.commit()
            
            logger.info("Successfully saved prompt to PostgreSQL")
            return True
            
    except Exception as e:
        logger.warning(f"Failed to save prompt to PostgreSQL: {e}")
        try:
            connection.rollback()
        except:
            pass
        return False


def extract_repository_from_git() -> Optional[str]:
    """
    Extract repository info from git context
    - Use CLAUDE_PROJECT_DIR environment variable
    - Run git remote get-url origin
    - Parse and normalize repository format (e.g., github.com/user/repo)
    - Return None if not in git repository
    """
    project_dir = os.getenv('CLAUDE_PROJECT_DIR')
    if not project_dir:
        logger.debug("CLAUDE_PROJECT_DIR not set, cannot extract repository")
        return None
    
    try:
        # Run git remote get-url origin in the project directory
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.debug(f"Git command failed: {result.stderr}")
            return None
        
        remote_url = result.stdout.strip()
        if not remote_url:
            logger.debug("No origin remote found")
            return None
        
        # Parse various git URL formats
        # SSH format: git@github.com:user/repo.git
        ssh_pattern = r'git@([^:]+):([^/]+)/(.+?)$'
        ssh_match = re.match(ssh_pattern, remote_url)
        if ssh_match:
            host = ssh_match.group(1)
            user = ssh_match.group(2)
            repo = ssh_match.group(3)
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            repository = f"{host}/{user}/{repo}"
            logger.debug(f"Extracted repository from SSH URL: {repository}")
            return repository
        
        # HTTPS format: https://github.com/user/repo.git or https://github.com/user/repo
        https_pattern = r'https?://([^/]+)/([^/]+)/(.+?)$'
        https_match = re.match(https_pattern, remote_url)
        if https_match:
            host = https_match.group(1)
            user = https_match.group(2)
            repo = https_match.group(3)
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            repository = f"{host}/{user}/{repo}"
            logger.debug(f"Extracted repository from HTTPS URL: {repository}")
            return repository
        
        logger.debug(f"Could not parse git remote URL: {remote_url}")
        return None
        
    except subprocess.TimeoutExpired:
        logger.debug("Git command timed out")
        return None
    except Exception as e:
        logger.debug(f"Failed to extract repository from git: {e}")
        return None


def get_session_id() -> Optional[str]:
    """
    Get session ID from environment
    - Check for session_id in environment variables
    - Validate UUID format if present
    - Return None if not available
    """
    # Check for CLAUDE_SESSION_ID in environment
    session_id = os.getenv('CLAUDE_SESSION_ID')
    
    if not session_id:
        logger.debug("No session ID found in environment")
        return None
    
    # Validate UUID format (UUID v4)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, session_id.lower()):
        logger.debug(f"Valid session ID found: {session_id}")
        return session_id
    else:
        logger.debug(f"Invalid session ID format: {session_id}")
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

    # TODO for task 4: Implement main execution flow with PostgreSQL/YAML routing
    # - Attempt PostgreSQL connection first
    # - If connection successful, prepare prompt_data:
    #   - Extract prompt from arguments/stdin
    #   - Get repository from git
    #   - Get session_id from environment
    #   - Add current timestamp
    # - Try save_to_postgres()
    # - On any failure, fall back to existing YAML logic
    # - Ensure YAML structure preservation
    # - Add comprehensive info-level logging throughout
    
    # For now, use existing YAML functionality
    yaml_file = Path(os.getenv("CLAUDE_PROJECT_DIR"), "user_prompts.yaml")
    
    if not save_to_yaml(yaml_file, timestamp, user_prompt):
        sys.exit(1)
    
    logger.info(f"Prompt saved to YAML: {yaml_file}")


if __name__ == "__main__":
    main()
