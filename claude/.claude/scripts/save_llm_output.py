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
    
    try:
        # Read all lines at once for reverse iteration
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process lines in reverse to find the last assistant message
        for line_num, line in enumerate(reversed(lines), 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse JSON line
                data = json.loads(line)
                
                # Check if this is an assistant message and return immediately
                if data.get('type') == 'assistant' and 'message' in data:
                    logger.debug(f"Found last assistant message at line {len(lines) - line_num + 1}")
                    return data
                    
            except json.JSONDecodeError as e:
                # Skip malformed lines
                logger.debug(f"Skipping malformed JSON at line {len(lines) - line_num + 1}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing line {len(lines) - line_num + 1}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error reading transcript file: {e}")
        return None
    
    logger.warning(f"No assistant message found in transcript: {transcript_path}")
    return None


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
            logger.debug(
                "Attempting PostgreSQL connection using individual environment variables")
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
            logger.info(
                "Successfully connected to PostgreSQL using individual environment variables")
            return conn
        
        logger.debug(
            "No PostgreSQL configuration found in environment variables")
        return None
        
    except ImportError:
        logger.warning(
            "psycopg module not installed, PostgreSQL support unavailable")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to PostgreSQL: {e}")
        return None


def extract_repository_from_git(cwd: Optional[str] = None) -> Optional[str]:
    """
    Extract repository info from git context.
    
    Args:
        cwd: Working directory path, defaults to current directory
        
    Returns:
        Normalized repository format (e.g., github.com/user/repo) or None
    """
    # Use provided cwd or fall back to CLAUDE_PROJECT_DIR
    project_dir = cwd or os.getenv('CLAUDE_PROJECT_DIR')
    if not project_dir:
        logger.debug("No working directory specified and CLAUDE_PROJECT_DIR not set")
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
    """
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Prepare the INSERT query with parameterized values
            insert_query = """
                INSERT INTO llm_outputs (
                    created_at, output, session_id, repository,
                    input_tokens, output_tokens, model, service_tier
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Execute the query with the provided data
            cursor.execute(
                insert_query,
                (
                    llm_data.get('created_at'),
                    llm_data.get('output'),
                    llm_data.get('session_id'),
                    llm_data.get('repository'),
                    llm_data.get('input_tokens'),
                    llm_data.get('output_tokens'),
                    llm_data.get('model'),
                    llm_data.get('service_tier')
                )
            )
            
            # Commit the transaction
            connection.commit()
            
            logger.info("Successfully saved LLM output to PostgreSQL")
            return True
            
    except Exception as e:
        logger.warning(f"Failed to save LLM output to PostgreSQL: {e}")
        try:
            connection.rollback()
        except:
            pass
        return False


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
    """
    try:
        # Step 1: Parse hook input from stdin
        logger.info("Starting LLM output save process")
        hook_data = parse_hook_input()
        
        # Extract transcript path and session_id
        transcript_path = hook_data.get('transcript_path')
        session_id = hook_data.get('session_id')
        cwd = hook_data.get('cwd')
        
        if not transcript_path:
            logger.error("No transcript_path in hook data")
            sys.exit(1)
        
        logger.debug(f"Processing transcript: {transcript_path}")
        logger.debug(f"Session ID: {session_id}")
        
        # Step 2: Read transcript file and get last assistant message
        assistant_message = read_transcript_file(transcript_path)
        
        if not assistant_message:
            logger.info("No assistant message found in transcript, nothing to save")
            sys.exit(0)
        
        # Step 3: Extract LLM output and metadata
        llm_metadata = extract_llm_metadata(assistant_message)
        
        if not llm_metadata.get('output'):
            logger.warning("No output text found in assistant message, nothing to save")
            sys.exit(0)
        
        # Step 4: Get repository information from git context
        repository = extract_repository_from_git(cwd)
        logger.debug(f"Repository: {repository}")
        
        # Step 5: Prepare data for database
        llm_data = {
            'created_at': datetime.utcnow(),
            'output': llm_metadata['output'],
            'session_id': session_id,
            'repository': repository,
            'input_tokens': llm_metadata.get('input_tokens'),
            'output_tokens': llm_metadata.get('output_tokens'),
            'model': llm_metadata.get('model'),
            'service_tier': llm_metadata.get('service_tier')
        }
        
        # Step 6: Establish database connection
        connection = get_postgres_connection()
        
        if not connection:
            logger.error("Failed to establish PostgreSQL connection - no fallback mechanism")
            sys.exit(1)
        
        try:
            # Step 7: Save to PostgreSQL
            success = save_llm_output_to_postgres(connection, llm_data)
            
            if not success:
                logger.error("Failed to save LLM output to database")
                sys.exit(1)
            
            logger.info("LLM output saved successfully")
            sys.exit(0)
            
        finally:
            # Always close the database connection
            try:
                connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.debug(f"Error closing connection: {e}")
                
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid hook input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()