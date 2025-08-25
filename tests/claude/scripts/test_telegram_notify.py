#!/usr/bin/env python3
"""
Unit tests for telegram_notify.py

Tests all functionality of the Telegram notification script including:
- Environment variable configuration
- Transcript parsing
- Message formatting
- Telegram API integration
- Logging infrastructure
- Main entry point logic
"""

import sys
import os
# Add the claude scripts directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../claude/.claude/scripts')))

import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import directly from the module
from telegram_notify import (
    get_environment_config,
    parse_claude_transcript,
    format_telegram_message,
    send_telegram_notification,
)


@pytest.fixture
def sample_transcript():
    """Provide sample Claude transcript data."""
    return [
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "First assistant message"}]}
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "Some result"}]}
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Last assistant message here"}]}
        }
    ]


@pytest.fixture
def mock_telegram_api():
    """Mock Telegram API responses."""
    with patch('telegram_notify.requests') as mock_requests:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}
        mock_requests.post.return_value = mock_response
        yield mock_requests


class TestEnvironmentConfig:
    """Test environment variable configuration."""
    
    def test_both_variables_present(self):
        """Test with both BOT_ID and CHAT_ID present."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot_id',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            config = get_environment_config()
            assert config is not None
            assert config['bot_id'] == 'test_bot_id'
            assert config['chat_id'] == 'test_chat_id'
    
    def test_bot_id_missing(self):
        """Test with BOT_ID missing."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat_id'
        }, clear=True):
            config = get_environment_config()
            assert config is None
    
    def test_chat_id_missing(self):
        """Test with CHAT_ID missing."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot_id'
        }, clear=True):
            config = get_environment_config()
            assert config is None
    
    def test_both_missing(self):
        """Test with both variables missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_environment_config()
            assert config is None


class TestTranscriptParsing:
    """Test Claude transcript parsing."""
    
    def test_valid_transcript_with_assistant_message(self, sample_transcript, tmp_path):
        """Test with valid transcript containing assistant message."""
        transcript_file = tmp_path / "transcript.jsonl"
        
        # Write JSONL format
        with open(transcript_file, 'w') as f:
            for entry in sample_transcript:
                f.write(json.dumps(entry) + '\n')
        
        result = parse_claude_transcript(str(transcript_file))
        assert result == "Last assistant message here"
    
    def test_transcript_with_only_user_messages(self, tmp_path):
        """Test with transcript containing only user messages."""
        transcript_file = tmp_path / "transcript.jsonl"
        
        user_only = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "User 1"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "User 2"}]}}
        ]
        
        with open(transcript_file, 'w') as f:
            for entry in user_only:
                f.write(json.dumps(entry) + '\n')
        
        result = parse_claude_transcript(str(transcript_file))
        assert result is None
    
    def test_empty_transcript(self, tmp_path):
        """Test with empty transcript file."""
        transcript_file = tmp_path / "transcript.jsonl"
        transcript_file.touch()
        
        result = parse_claude_transcript(str(transcript_file))
        assert result is None
    
    def test_malformed_json(self, tmp_path):
        """Test with malformed JSON lines."""
        transcript_file = tmp_path / "transcript.jsonl"
        
        with open(transcript_file, 'w') as f:
            f.write('{"type": "assistant", broken json\n')
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Valid message"}]}}\n')
        
        result = parse_claude_transcript(str(transcript_file))
        assert result == "Valid message"
    
    def test_missing_message_content_path(self, tmp_path):
        """Test with missing message.content path."""
        transcript_file = tmp_path / "transcript.jsonl"
        
        entries = [
            {"type": "assistant", "message": {}},  # No content
            {"type": "assistant", "message": {"content": []}},  # Empty content
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Good message"}]}},
        ]
        
        with open(transcript_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        result = parse_claude_transcript(str(transcript_file))
        assert result == "Good message"
    
    def test_extracts_last_assistant_message(self, tmp_path):
        """Test extraction of last assistant message from multiple."""
        transcript_file = tmp_path / "transcript.jsonl"
        
        entries = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "First"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "User"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Second"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Third and last"}]}},
        ]
        
        with open(transcript_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        result = parse_claude_transcript(str(transcript_file))
        assert result == "Third and last"
    
    def test_nonexistent_file(self):
        """Test with nonexistent file."""
        result = parse_claude_transcript("/nonexistent/file.jsonl")
        assert result is None


class TestMessageFormatting:
    """Test Telegram message formatting."""
    
    def test_basic_formatting_with_all_parameters(self):
        """Test basic formatting with all parameters."""
        with patch('telegram_notify.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00"
            
            result = format_telegram_message(
                "Test message",
                project_dir="/home/user/project",
                session_id="abc123"
            )
            
            assert "🤖 *Claude Code Notification*" in result
            assert "⏰ *Time:* `2024-01-15T10:30:00`" in result
            assert "📁 *Project:* `/home/user/project`" in result
            assert "🔖 *Session:* `abc123`" in result
            assert "Test message" in result
            assert "```" in result  # Markdown code block
    
    def test_without_project_dir(self):
        """Test formatting without project_dir."""
        result = format_telegram_message(
            "Test message",
            session_id="abc123"
        )
        
        assert "Test message" in result
        assert "📁 *Project:*" not in result
        assert "🔖 *Session:* `abc123`" in result
    
    def test_without_session_id(self):
        """Test formatting without session_id."""
        result = format_telegram_message(
            "Test message",
            project_dir="/home/user/project"
        )
        
        assert "Test message" in result
        assert "📁 *Project:* `/home/user/project`" in result
        assert "🔖 *Session:*" not in result
    
    def test_message_truncation_for_long_messages(self):
        """Test message truncation for messages exceeding Telegram limit."""
        long_message = "A" * 5000  # Exceeds 4096 char limit
        
        result = format_telegram_message(long_message)
        
        assert len(result) <= 4096
        assert result.endswith("...\n```")
        assert "AAA" in result  # Part of original message
    
    def test_markdown_formatting(self):
        """Test that markdown formatting is preserved."""
        message_with_markdown = "This has *bold* and _italic_ text"
        
        result = format_telegram_message(message_with_markdown)
        
        assert "*bold*" in result
        assert "_italic_" in result
    
    def test_iso_timestamp_inclusion(self):
        """Test ISO timestamp is included."""
        with patch('telegram_notify.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T10:30:00.123456"
            
            result = format_telegram_message("Test")
            
            assert "2024-01-15T10:30:00.123456" in result


class TestTelegramIntegration:
    """Test Telegram API integration."""
    
    def test_successful_send(self, mock_telegram_api):
        """Test successful send with mocked requests."""
        result = send_telegram_notification(
            "test_bot_id",
            "test_chat_id",
            "Test message"
        )
        
        assert result is True
        mock_telegram_api.post.assert_called_once()
        
        call_args = mock_telegram_api.post.call_args
        assert "https://api.telegram.org/bottest_bot_id/sendMessage" in call_args[0]
        assert call_args[1]['json']['chat_id'] == 'test_chat_id'
        assert call_args[1]['json']['text'] == 'Test message'
        assert call_args[1]['json']['parse_mode'] == 'Markdown'
    
    def test_api_failure_handling(self):
        """Test API failure handling."""
        with patch('telegram_notify.requests') as mock_requests:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_requests.post.return_value = mock_response
            
            result = send_telegram_notification(
                "test_bot_id",
                "test_chat_id",
                "Test message"
            )
            
            assert result is False
    
    def test_network_error_handling(self):
        """Test network error handling."""
        with patch('telegram_notify.requests') as mock_requests:
            mock_requests.post.side_effect = Exception("Network error")
            
            result = send_telegram_notification(
                "test_bot_id",
                "test_chat_id",
                "Test message"
            )
            
            assert result is False
    
    def test_markdown_parse_mode_usage(self, mock_telegram_api):
        """Test that markdown parse_mode is used."""
        send_telegram_notification(
            "test_bot_id",
            "test_chat_id",
            "*Bold* message"
        )
        
        call_args = mock_telegram_api.post.call_args
        assert call_args[1]['json']['parse_mode'] == 'Markdown'
    
    def test_url_construction(self, mock_telegram_api):
        """Test correct URL construction."""
        bot_id = "123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQr"
        
        send_telegram_notification(
            bot_id,
            "test_chat_id",
            "Test"
        )
        
        expected_url = f"https://api.telegram.org/bot{bot_id}/sendMessage"
        call_args = mock_telegram_api.post.call_args
        assert expected_url in call_args[0]


class TestLogging:
    """Test logging infrastructure."""
    
    # TODO for task 2: Implement tests for setup_logging()
    # - Test log directory creation
    # - Test rotation configuration
    # - Test permission error handling
    # - Test fallback to temp directory
    # - Test log format
    pass


class TestMainFunction:
    """Test main entry point."""
    
    # TODO for task 3: Implement tests for main()
    # - Test successful flow end-to-end
    # - Test with missing environment variables
    # - Test with transcript parsing failure
    # - Test with Telegram send failure
    # - Test silent failure behavior
    # - Test logging of all operations
    pass


class TestCLISupport:
    """Test CLI argument parsing and standalone mode."""
    
    # TODO for task 3: Implement tests for CLI functionality
    # - Test --help option
    # - Test standalone execution
    # - Test hook mode vs standalone mode
    pass