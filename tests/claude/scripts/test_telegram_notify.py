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
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import directly from the module
from telegram_notify import (
    get_environment_config,
    parse_claude_transcript,
    format_telegram_message,
    send_telegram_notification,
    setup_logging,
    main,
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
    
    def test_log_directory_creation(self, tmp_path):
        """Test that log directory is created successfully."""
        with patch('telegram_notify.os.makedirs') as mock_makedirs:
            with patch('telegram_notify.open', create=True) as mock_open:
                with patch('telegram_notify.os.remove'):
                    logger = setup_logging()
                    
                    # Check that makedirs was called
                    assert mock_makedirs.called
                    assert logger is not None
                    assert logger.name == 'claude_telegram_notifier'
    
    def test_rotation_configuration(self):
        """Test that TimedRotatingFileHandler is configured correctly."""
        with patch('telegram_notify.TimedRotatingFileHandler') as mock_handler:
            # Configure the mock to have required attributes
            mock_instance = Mock()
            mock_instance.level = logging.INFO
            mock_instance.setFormatter = Mock()
            mock_handler.return_value = mock_instance
            
            with patch('telegram_notify.os.makedirs'):
                with patch('telegram_notify.open', create=True):
                    with patch('telegram_notify.os.remove'):
                        setup_logging()
                        
                        # Check handler was created with correct parameters
                        mock_handler.assert_called_once()
                        call_args = mock_handler.call_args
                        assert call_args[1]['when'] == 'midnight'
                        assert call_args[1]['interval'] == 1
                        assert call_args[1]['backupCount'] == 3
    
    def test_permission_error_handling(self, tmp_path):
        """Test fallback to temp directory on permission errors."""
        with patch('telegram_notify.os.makedirs') as mock_makedirs:
            # First call raises PermissionError, second succeeds
            mock_makedirs.side_effect = [PermissionError("No permission"), None]
            
            with patch('telegram_notify.tempfile.gettempdir') as mock_tempdir:
                mock_tempdir.return_value = str(tmp_path)
                
                logger = setup_logging()
                
                # Should have tried /var/log first, then temp dir
                assert mock_makedirs.call_count >= 2
                assert logger is not None
    
    def test_fallback_to_current_directory(self):
        """Test fallback to current directory if both /var/log and temp fail."""
        with patch('telegram_notify.os.makedirs') as mock_makedirs:
            # All makedirs calls fail
            mock_makedirs.side_effect = PermissionError("No permission")
            
            with patch('telegram_notify.TimedRotatingFileHandler') as mock_handler:
                # Configure the mock to have required attributes
                mock_instance = Mock()
                mock_instance.level = logging.INFO
                mock_instance.setFormatter = Mock()
                mock_handler.return_value = mock_instance
                
                logger = setup_logging()
                
                # Should create handler with local file
                mock_handler.assert_called_once()
                call_args = mock_handler.call_args
                assert call_args[1]['filename'] == 'telegram_notify.log'
                assert logger is not None
    
    def test_log_format(self):
        """Test that log format is set correctly."""
        logger = setup_logging()
        
        # Check that handlers have been added
        assert len(logger.handlers) > 0
        
        # Check that at least one handler has a formatter
        has_formatter = False
        for handler in logger.handlers:
            if handler.formatter:
                has_formatter = True
                # Check format string contains expected elements
                format_str = handler.formatter._fmt
                assert '%(asctime)s' in format_str
                assert '%(levelname)s' in format_str
                assert '%(message)s' in format_str
        
        assert has_formatter
    
    def test_logger_info_level(self):
        """Test that logger is set to INFO level."""
        logger = setup_logging()
        assert logger.level == logging.INFO
    
    def test_console_handler_added(self):
        """Test that console handler is added for warnings."""
        logger = setup_logging()
        
        # Check for StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) > 0
    
    def test_logging_with_functions(self):
        """Test that functions properly use the logger."""
        logger = Mock()
        
        # Test get_environment_config with logger
        with patch.dict(os.environ, {}, clear=True):
            get_environment_config(logger=logger)
            logger.warning.assert_called()
        
        # Test parse_claude_transcript with logger
        parse_claude_transcript("/nonexistent/file", logger=logger)
        logger.warning.assert_called()
        
        # Test format_telegram_message with logger
        long_msg = "A" * 5000
        format_telegram_message(long_msg, logger=logger)
        logger.info.assert_called()
        
        # Test send_telegram_notification with logger
        with patch('telegram_notify.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            send_telegram_notification("bot", "chat", "msg", logger=logger)
            logger.error.assert_called()


class TestMainFunction:
    """Test main entry point."""
    
    def test_successful_flow_end_to_end(self, tmp_path):
        """Test successful end-to-end flow."""
        # Create a test transcript
        transcript_file = tmp_path / "test.jsonl"
        with open(transcript_file, 'w') as f:
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test message"}]}}\n')
        
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat',
            'CLAUDE_PROJECT_DIR': '/test/project',
            'CLAUDE_SESSION_ID': 'test_session'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--transcript', str(transcript_file)]):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'ok': True}
                    mock_post.return_value = mock_response
                    
                    result = main()
                    assert result == 0
                    mock_post.assert_called_once()
    
    def test_with_missing_environment_variables(self):
        """Test with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.argv', ['telegram_notify.py']):
                result = main()
                assert result == 1
    
    def test_with_transcript_parsing_failure(self, tmp_path):
        """Test with transcript parsing failure."""
        # Create empty transcript
        transcript_file = tmp_path / "empty.jsonl"
        transcript_file.touch()
        
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--transcript', str(transcript_file)]):
                result = main()
                assert result == 1
    
    def test_with_telegram_send_failure(self, tmp_path):
        """Test with Telegram send failure."""
        # Create a test transcript
        transcript_file = tmp_path / "test.jsonl"
        with open(transcript_file, 'w') as f:
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test"}]}}\n')
        
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--transcript', str(transcript_file)]):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_post.side_effect = Exception("Network error")
                    
                    result = main()
                    assert result == 1
    
    def test_silent_failure_behavior(self):
        """Test that failures are silent (logged but don't raise)."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('telegram_notify.parse_claude_transcript') as mock_parse:
                    mock_parse.side_effect = Exception("Unexpected error")
                    
                    # Should not raise, just return error code
                    result = main()
                    assert result == 1
    
    def test_logging_of_all_operations(self, tmp_path):
        """Test that all operations are logged."""
        transcript_file = tmp_path / "test.jsonl"
        with open(transcript_file, 'w') as f:
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test"}]}}\n')
        
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--transcript', str(transcript_file), '--debug']):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'ok': True}
                    mock_post.return_value = mock_response
                    
                    with patch('telegram_notify.setup_logging') as mock_logging:
                        mock_logger = Mock()
                        mock_logger.handlers = []
                        mock_logging.return_value = mock_logger
                        
                        main()
                        
                        # Check that logging was called
                        assert mock_logger.info.called
                        assert mock_logger.debug.called or mock_logger.info.called


class TestCLISupport:
    """Test CLI argument parsing and standalone mode."""
    
    def test_help_option(self):
        """Test --help option."""
        with patch('sys.argv', ['telegram_notify.py', '--help']):
            with patch('sys.exit') as mock_exit:
                try:
                    main()
                except SystemExit:
                    pass
                # Help should cause exit with code 0
                mock_exit.assert_called()
    
    def test_test_message_option(self):
        """Test --test-message option."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--test-message', 'Hello Test']):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'ok': True}
                    mock_post.return_value = mock_response
                    
                    result = main()
                    assert result == 0
                    
                    # Check that the test message was sent
                    call_args = mock_post.call_args
                    assert 'Hello Test' in call_args[1]['json']['text']
    
    def test_transcript_option(self, tmp_path):
        """Test --transcript option."""
        transcript_file = tmp_path / "custom.jsonl"
        with open(transcript_file, 'w') as f:
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Custom"}]}}\n')
        
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--transcript', str(transcript_file)]):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'ok': True}
                    mock_post.return_value = mock_response
                    
                    result = main()
                    assert result == 0
                    
                    # Check that custom transcript was used
                    call_args = mock_post.call_args
                    assert 'Custom' in call_args[1]['json']['text']
    
    def test_debug_option(self):
        """Test --debug option enables debug logging."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--test-message', 'Debug test', '--debug']):
                with patch('telegram_notify.requests.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'ok': True}
                    mock_post.return_value = mock_response
                    
                    with patch('telegram_notify.setup_logging') as mock_logging:
                        mock_logger = Mock()
                        mock_handler = Mock(spec=logging.StreamHandler)
                        mock_logger.handlers = [mock_handler]
                        mock_logging.return_value = mock_logger
                        
                        result = main()
                        assert result == 0
                        
                        # Check that debug logging was enabled
                        mock_logger.setLevel.assert_called_with(logging.DEBUG)
                        mock_handler.setLevel.assert_called_with(logging.DEBUG)
    
    def test_stdin_empty(self):
        """Test when stdin is empty."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.return_value = ''
                    
                    result = main()
                    assert result == 1  # Should fail when stdin is empty
    
    def test_stdin_invalid_json(self):
        """Test when stdin contains invalid JSON."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.return_value = 'not valid json'
                    
                    result = main()
                    assert result == 1  # Should fail with invalid JSON
    
    def test_stdin_missing_transcript_path(self):
        """Test when stdin JSON doesn't contain transcript_path."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.return_value = json.dumps({
                        'session_id': 'test123',
                        'cwd': '/test/dir'
                        # missing transcript_path
                    })
                    
                    result = main()
                    assert result == 1  # Should fail without transcript_path
    
    def test_stdin_error(self):
        """Test when reading from stdin fails."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.side_effect = Exception("Cannot read stdin")
                    
                    result = main()
                    assert result == 1  # Should fail gracefully
    
    def test_stdin_overrides_environment(self):
        """Test that stdin JSON data overrides environment variables."""
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat',
            'CLAUDE_PROJECT_DIR': '/env/project',
            'CLAUDE_SESSION_ID': 'env_session'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.return_value = json.dumps({
                        'session_id': 'stdin_session',
                        'transcript_path': '/tmp/transcript.jsonl',
                        'cwd': '/stdin/project',
                        'hook_event_name': 'Notification'
                    })
                    with patch('telegram_notify.parse_claude_transcript') as mock_parse:
                        mock_parse.return_value = "Test message"
                        with patch('telegram_notify.format_telegram_message') as mock_format:
                            mock_format.return_value = "Formatted message"
                            with patch('telegram_notify.send_telegram_notification') as mock_send:
                                mock_send.return_value = True
                                
                                result = main()
                                assert result == 0
                                
                                # Check that format was called with stdin values, not env values
                                mock_format.assert_called_once()
                                call_args = mock_format.call_args
                                assert call_args[1]['project_dir'] == '/stdin/project'
                                assert call_args[1]['session_id'] == 'stdin_session'
    
    def test_hook_mode_vs_standalone(self):
        """Test difference between hook mode and standalone execution."""
        # Hook mode (no arguments, reads JSON from stdin)
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py']):
                with patch('sys.stdin') as mock_stdin:
                    mock_stdin.read.return_value = json.dumps({
                        'session_id': 'abc123',
                        'transcript_path': '/tmp/transcript.jsonl',
                        'cwd': '/test/project',
                        'hook_event_name': 'Notification',
                        'message': 'Task completed successfully'
                    })
                    with patch('telegram_notify.parse_claude_transcript') as mock_parse:
                        mock_parse.return_value = "Hook message"
                        with patch('telegram_notify.send_telegram_notification') as mock_send:
                            mock_send.return_value = True
                            
                            result = main()
                            assert result == 0
                            # Check that parse was called with the transcript path from JSON
                            assert mock_parse.called
                            assert mock_parse.call_args[0][0] == '/tmp/transcript.jsonl'
        
        # Standalone mode (with explicit arguments)
        with patch.dict(os.environ, {
            'CLAUDE_TELEGRAM_BOT_ID': 'test_bot',
            'CLAUDE_TELEGRAM_CHAT_ID': 'test_chat'
        }):
            with patch('sys.argv', ['telegram_notify.py', '--test-message', 'Standalone']):
                with patch('telegram_notify.send_telegram_notification') as mock_send:
                    mock_send.return_value = True
                    
                    result = main()
                    assert result == 0
                    # Should use test message, not parse transcript
                    call_args = mock_send.call_args
                    assert 'Standalone' in call_args[0][2]