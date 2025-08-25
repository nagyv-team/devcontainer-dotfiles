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


def setup_logging() -> logging.Logger:
    """
    Configure logging with rotation and proper error handling.
    
    Sets up TimedRotatingFileHandler for daily rotation with 3-day retention.
    Falls back to temp directory if /var/log/ is not writable.
    
    TODO for task 2: Implement logging infrastructure
    - Create log directory /var/log/claude_telegram_notifier/
    - Configure TimedRotatingFileHandler for daily rotation
    - Set 3-day retention with backupCount=3
    - Set appropriate log format with timestamps
    - Handle permission errors gracefully (fallback to temp directory)
    - Return logger instance
    """
    pass


def get_environment_config() -> Optional[Dict[str, str]]:
    """
    Read and validate environment variables for Telegram configuration.
    
    Returns:
        Dict with bot_id and chat_id if both are present, None otherwise
    """
    bot_id = os.environ.get('CLAUDE_TELEGRAM_BOT_ID')
    chat_id = os.environ.get('CLAUDE_TELEGRAM_CHAT_ID')
    
    if not bot_id or not chat_id:
        return None
    
    return {
        'bot_id': bot_id,
        'chat_id': chat_id
    }


def parse_claude_transcript(transcript_file: str) -> Optional[str]:
    """
    Parse Claude Code transcript JSONL and extract last assistant message.
    
    Args:
        transcript_file: Path to the transcript JSONL file
        
    Returns:
        Text content of the last assistant message, or None if not found
    """
    if not os.path.exists(transcript_file):
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
                                
                except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                    # Skip malformed lines
                    continue
    
    except (IOError, OSError):
        return None
    
    return last_assistant_message


def format_telegram_message(
    message_text: str,
    project_dir: Optional[str] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Format message with metadata for Telegram using Markdown.
    
    Args:
        message_text: The Claude assistant message text
        project_dir: The project directory path from CLAUDE_PROJECT_DIR
        session_id: The session ID if available
        
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
        message_text = message_text[:available_space - 3] + "..."
    
    parts.append(message_text)
    parts.append(f"```")
    
    return "\n".join(parts)


def send_telegram_notification(
    bot_id: str,
    chat_id: str,
    message: str
) -> bool:
    """
    Send formatted message to Telegram channel via Bot API.
    
    Args:
        bot_id: Telegram bot token
        chat_id: Telegram chat/channel ID
        message: Formatted message to send
        
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
    
    try:
        # Send POST request to Telegram API
        response = requests.post(url, json=payload, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False)
        else:
            return False
            
    except Exception:
        # Handle any network or parsing errors
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