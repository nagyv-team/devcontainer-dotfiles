#!/usr/bin/env python3
"""
Telegram Notification Script for Claude Code Hooks

This script sends formatted messages to a Telegram channel when Claude Code 
triggers Stop or Notification hooks. It enables remote monitoring of Claude Code
instances by notifying users when Claude is ready and waiting for input.

Usage:
    1. Set environment variables:
       - CLAUDE_TELEGRAM_BOT_ID: Your Telegram bot token
       - CLAUDE_TELEGRAM_CHAT_ID: Your Telegram chat/channel ID
    2. Configure in claude/.claude/settings.json for Stop and Notification hooks
    3. For testing: python telegram_notify.py

The script reads Claude Code transcript, extracts the last assistant message,
and sends it to Telegram with metadata (timestamp, project directory, session ID).
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import requests
import tempfile
from logging.handlers import TimedRotatingFileHandler


def setup_logging() -> logging.Logger:
    """
    Configure logging with rotation and proper error handling.
    
    Sets up TimedRotatingFileHandler for daily rotation with 3-day retention.
    Falls back to temp directory if /var/log/ is not writable.
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('claude_telegram_notifier')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Define log format with timestamps
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Try to create log directory in /var/log/
    log_dir = '/var/log/claude_telegram_notifier'
    log_file = None
    
    try:
        # Attempt to create the log directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Test if we can write to the directory
        test_file = os.path.join(log_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        log_file = os.path.join(log_dir, 'telegram_notify.log')
        
    except (OSError, IOError, PermissionError):
        # Fall back to temp directory if /var/log/ is not writable
        temp_dir = tempfile.gettempdir()
        log_dir = os.path.join(temp_dir, 'claude_telegram_notifier')
        
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'telegram_notify.log')
        except (OSError, IOError):
            # If even temp directory fails, use current directory
            log_file = 'telegram_notify.log'
    
    # Create TimedRotatingFileHandler for daily rotation with 3-day retention
    try:
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',  # Rotate at midnight
            interval=1,       # Every 1 day
            backupCount=3,    # Keep 3 days of backups
            encoding='utf-8'
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
        
        # Also add console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        logger.addHandler(console_handler)
        
    except (OSError, IOError) as e:
        # If file handler fails, at least use console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
        logger.error(f"Failed to create file handler: {e}")
    
    # Log the logging configuration
    logger.info(f"Logging initialized. Log file: {log_file if log_file else 'console only'}")
    
    return logger


def get_environment_config(logger: Optional[logging.Logger] = None) -> Optional[Dict[str, str]]:
    """
    Read and validate environment variables for Telegram configuration.
    
    Args:
        logger: Optional logger instance for logging operations
    
    Returns:
        Dict with bot_id and chat_id if both are present, None otherwise
    """
    bot_id = os.environ.get('CLAUDE_TELEGRAM_BOT_ID')
    chat_id = os.environ.get('CLAUDE_TELEGRAM_CHAT_ID')
    
    if logger:
        logger.info("Checking environment variables for Telegram configuration")
    
    if not bot_id:
        if logger:
            logger.warning("CLAUDE_TELEGRAM_BOT_ID environment variable is not set")
        return None
    
    if not chat_id:
        if logger:
            logger.warning("CLAUDE_TELEGRAM_CHAT_ID environment variable is not set")
        return None
    
    if logger:
        logger.info("Environment variables successfully loaded")
    
    return {
        'bot_id': bot_id,
        'chat_id': chat_id
    }


def parse_claude_transcript(transcript_file: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Parse Claude Code transcript JSONL and extract last assistant message.
    
    Args:
        transcript_file: Path to the transcript JSONL file
        logger: Optional logger instance for logging operations
        
    Returns:
        Text content of the last assistant message, or None if not found
    """
    if logger:
        logger.info(f"Parsing transcript file: {transcript_file}")
    
    if not os.path.exists(transcript_file):
        if logger:
            logger.warning(f"Transcript file does not exist: {transcript_file}")
        return None
    
    last_assistant_message = None
    
    try:
        with open(transcript_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Check if this is an assistant message
                    if entry.get('type') == 'assistant':
                        # Navigate to message.content[0].text
                        message = entry.get('message', {})
                        content = message.get('content', [])
                        if content and isinstance(content, list) and len(content) > 0:
                            first_content = content[0]
                            if isinstance(first_content, dict) and 'text' in first_content:
                                last_assistant_message = first_content['text']
                                
                except (json.JSONDecodeError, KeyError, TypeError, IndexError) as e:
                    # Skip malformed lines
                    if logger:
                        logger.debug(f"Skipping malformed JSON line: {e}")
                    continue
    
    except (IOError, OSError) as e:
        if logger:
            logger.error(f"Error reading transcript file: {e}")
        return None
    
    if logger:
        if last_assistant_message:
            logger.info(f"Successfully extracted assistant message ({len(last_assistant_message)} chars)")
        else:
            logger.warning("No assistant message found in transcript")
    
    return last_assistant_message


def format_telegram_message(
    message_text: str,
    project_dir: Optional[str] = None,
    session_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> str:
    """
    Format message with metadata for Telegram using Markdown.
    
    Args:
        message_text: The Claude assistant message text
        project_dir: The project directory path from CLAUDE_PROJECT_DIR
        session_id: The session ID if available
        logger: Optional logger instance for logging operations
        
    Returns:
        Formatted message string with metadata
    """
    # Get current ISO timestamp
    timestamp = datetime.now().isoformat()
    
    # Build the formatted message
    parts = []
    parts.append(f"🤖 *Claude Code Notification*")
    parts.append(f"")
    parts.append(f"⏰ *Time:* `{timestamp}`")
    
    if project_dir:
        parts.append(f"📁 *Project:* `{project_dir}`")
    
    if session_id:
        parts.append(f"🔖 *Session:* `{session_id}`")
    
    parts.append(f"")
    parts.append(f"💬 *Message:*")
    parts.append(f"```")
    
    # Calculate available space for message (4096 char limit minus metadata)
    metadata_length = sum(len(part) for part in parts) + 10  # Extra for newlines and closing ```
    available_space = 4096 - metadata_length - 50  # Safety margin
    
    # Truncate message if needed
    if len(message_text) > available_space:
        original_length = len(message_text)
        message_text = message_text[:available_space - 3] + "..."
        if logger:
            logger.info(f"Message truncated from {original_length} to {len(message_text)} characters")
    
    parts.append(message_text)
    parts.append(f"```")
    
    formatted_message = "\n".join(parts)
    
    if logger:
        logger.info(f"Message formatted successfully ({len(formatted_message)} chars total)")
    
    return formatted_message


def send_telegram_notification(
    bot_id: str,
    chat_id: str,
    message: str,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Send formatted message to Telegram channel via Bot API.
    
    Args:
        bot_id: Telegram bot token
        chat_id: Telegram chat/channel ID
        message: Formatted message to send
        logger: Optional logger instance for logging operations
        
    Returns:
        True if successful, False otherwise
    """
    # Construct Telegram Bot API URL
    url = f"https://api.telegram.org/bot{bot_id}/sendMessage"
    
    # Prepare the payload
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    if logger:
        logger.info(f"Sending message to Telegram chat {chat_id}")
    
    try:
        # Send POST request to Telegram API
        response = requests.post(url, json=payload, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            success = result.get('ok', False)
            if success:
                if logger:
                    logger.info("Message sent successfully to Telegram")
            else:
                if logger:
                    logger.error(f"Telegram API returned ok=False: {result}")
            return success
        else:
            if logger:
                logger.error(f"Telegram API returned status code {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        # Handle any network or parsing errors
        if logger:
            logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)
        return False


def main():
    """
    Main entry point for the script.
    
    Orchestrates the flow: logging setup -> config check -> transcript parse ->
    message format -> Telegram send. Fails silently with logging on any error.
    
    TODO for task 3: Implement main entry point
    - Set up logging first
    - Check for environment variables
    - Parse transcript
    - Format and send message
    - Log all operations
    - Exit silently on any error
    
    TODO for task 3: Add CLI argument parsing
    - --help for usage information
    """
    pass


# TODO for task 3: Add if __name__ == "__main__": block for direct execution