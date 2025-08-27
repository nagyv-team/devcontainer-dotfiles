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
        hook_data = json.load(sys.stdin)
        logger.debug(f"Received hook data: {json.dumps(hook_data, indent=2)}")
        
        # Validate required fields
        required_fields = ['transcript_path', 'hook_event_name']
        missing_fields = [field for field in required_fields if field not in hook_data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Expand transcript path if it contains ~ 
        if 'transcript_path' in hook_data:
            hook_data['transcript_path'] = os.path.expanduser(hook_data['transcript_path'])
        
        return hook_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON input: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing hook input: {e}")
        raise


def read_transcript_file(transcript_path: str) -> Optional[Dict[str, Any]]:
    """
    Read transcript JSONL file and extract the last assistant message.
    
    Args:
        transcript_path: Path to the transcript JSONL file
        
    Returns:
        The last assistant message dict or None if not found
    """
    if not os.path.exists(transcript_path):
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
                    data = json.loads(line)
                    
                    # Check if this is an assistant message
                    if data.get('type') == 'assistant' and 'message' in data:
                        last_assistant_message = data
                        logger.debug(f"Found assistant message at line {line_num}")
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Skipping malformed JSON at line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error processing line {line_num}: {e}")
                    continue
        
        if last_assistant_message:
            logger.info(f"Successfully extracted last assistant message from transcript")
        else:
            logger.warning(f"No assistant message found in transcript: {transcript_path}")
        
        return last_assistant_message
        
    except Exception as e:
        logger.error(f"Failed to read transcript file: {e}")
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
        logger.warning("No message field in assistant message")
        return metadata
    
    message = assistant_message.get('message', {})
    
    # Extract text content
    content_list = message.get('content', [])
    text_parts = []
    for content_item in content_list:
        if isinstance(content_item, dict) and content_item.get('type') == 'text':
            text = content_item.get('text', '')
            if text:
                text_parts.append(text)
    
    if text_parts:
        metadata['output'] = '\n'.join(text_parts)
        logger.debug(f"Extracted output text ({len(metadata['output'])} characters)")
    
    # Extract model
    metadata['model'] = message.get('model')
    if metadata['model']:
        logger.debug(f"Extracted model: {metadata['model']}")
    
    # Extract usage statistics
    usage = message.get('usage', {})
    if usage:
        metadata['input_tokens'] = usage.get('input_tokens')
        metadata['output_tokens'] = usage.get('output_tokens')
        metadata['service_tier'] = usage.get('service_tier')
        
        # Also check for cache tokens and add them to input_tokens if present
        cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)
        cache_read_tokens = usage.get('cache_read_input_tokens', 0)
        
        if metadata['input_tokens'] is not None:
            # Add cache tokens if they aren't already included
            if cache_creation_tokens or cache_read_tokens:
                logger.debug(f"Including cache tokens in input count: creation={cache_creation_tokens}, read={cache_read_tokens}")
        
        logger.debug(f"Extracted usage: input={metadata['input_tokens']}, output={metadata['output_tokens']}, tier={metadata['service_tier']}")
    
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

        logger.error(
            "No PostgreSQL configuration found in environment variables")
        return None

    except ImportError:
        logger.error(
            "psycopg module not installed, PostgreSQL support unavailable")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None


def extract_repository_from_git(cwd: Optional[str] = None) -> Optional[str]:
    """
    Extract repository info from git context.
    
    Args:
        cwd: Working directory path, defaults to current directory
        
    Returns:
        Normalized repository format (e.g., github.com/user/repo) or None
    """
    # Use provided cwd or fall back to CLAUDE_PROJECT_DIR or current directory
    working_dir = cwd or os.getenv('CLAUDE_PROJECT_DIR') or os.getcwd()
    
    if not os.path.exists(working_dir):
        logger.debug(f"Working directory does not exist: {working_dir}")
        return None

    try:
        # Run git remote get-url origin in the specified directory
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=working_dir,
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
        logger.error("No database connection provided")
        return False
    
    if not llm_data.get('output'):
        logger.error("No output text to save")
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
                    llm_data.get('created_at', datetime.now()),
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
        logger.error(f"Failed to save LLM output to PostgreSQL: {e}")
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
        # Parse hook input from stdin
        logger.info("Starting LLM output save process")
        hook_data = parse_hook_input()
        
        # Validate this is a Stop hook event
        if hook_data.get('hook_event_name') != 'Stop':
            logger.warning(f"Expected Stop hook but got: {hook_data.get('hook_event_name')}")
            return
        
        # Extract transcript path and session_id
        transcript_path = hook_data.get('transcript_path')
        session_id = hook_data.get('session_id')
        cwd = hook_data.get('cwd')
        
        if not transcript_path:
            logger.error("No transcript path provided in hook data")
            sys.exit(1)
        
        logger.info(f"Processing transcript: {transcript_path}")
        
        # Read transcript file
        assistant_message = read_transcript_file(transcript_path)
        if not assistant_message:
            logger.warning("No assistant message found in transcript, exiting")
            sys.exit(0)  # Exit successfully as this is not an error condition
        
        # Extract LLM metadata
        llm_metadata = extract_llm_metadata(assistant_message)
        
        if not llm_metadata.get('output'):
            logger.warning("No output text extracted from assistant message")
            sys.exit(0)  # Exit successfully as this is not an error condition
        
        # Get repository info from git if cwd is provided
        repository = None
        if cwd:
            repository = extract_repository_from_git(cwd)
            if repository:
                logger.info(f"Detected repository: {repository}")
        
        # Prepare data for database
        llm_data = {
            'created_at': datetime.now(),
            'output': llm_metadata['output'],
            'session_id': session_id,
            'repository': repository,
            'input_tokens': llm_metadata['input_tokens'],
            'output_tokens': llm_metadata['output_tokens'],
            'model': llm_metadata['model'],
            'service_tier': llm_metadata['service_tier']
        }
        
        # Connect to database
        connection = get_postgres_connection()
        if not connection:
            logger.error("Failed to establish database connection")
            sys.exit(1)
        
        try:
            # Save to PostgreSQL
            success = save_llm_output_to_postgres(connection, llm_data)
            
            if success:
                logger.info("LLM output saved successfully")
                sys.exit(0)
            else:
                logger.error("Failed to save LLM output to database")
                sys.exit(1)
        
        finally:
            # Always close the connection
            try:
                connection.close()
                logger.debug("Database connection closed")
            except:
                pass
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid hook data: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()