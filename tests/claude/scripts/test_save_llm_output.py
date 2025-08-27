#!/usr/bin/env python3
"""
Unit tests for save_llm_output.py script - Task 1 implementation
Tests core LLM output extraction logic without database dependencies
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock, call
import pytest
from io import StringIO
from datetime import datetime
import logging

# Add the scripts directory to the path
scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'claude', '.claude', 'scripts')
sys.path.insert(0, scripts_path)

import save_llm_output

class MockSaveLLMOutput:
    """Mock implementation for testing."""
    
    @staticmethod
    def parse_hook_input():
        """Mock parse_hook_input."""
        return {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "hook_event_name": "Stop",
            "cwd": "/workspaces/test"
        }
    
    @staticmethod
    def read_transcript_file(path):
        """Mock read_transcript_file."""
        return {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Test output"}]
            }
        }
    
    @staticmethod
    def extract_llm_metadata(msg):
        """Mock extract_llm_metadata."""
        return {
            "output": "Test output",
            "model": "claude-opus-4-1-20250805",
            "input_tokens": 100,
            "output_tokens": 200,
            "service_tier": "standard"
        }
    
    @staticmethod
    def get_postgres_connection():
        """Mock get_postgres_connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn
    
    @staticmethod
    def extract_repository_from_git(cwd=None):
        """Mock extract_repository_from_git."""
        return "github.com/test/repo"
    
    @staticmethod
    def save_llm_output_to_postgres(conn, data):
        """Mock save_llm_output_to_postgres."""
        return True
    
    @staticmethod
    def main():
        """Mock main."""
        pass


# Try to import actual functions, fall back to mocks
try:
    from save_llm_output import (
        parse_hook_input,
        read_transcript_file,
        extract_llm_metadata,
        get_postgres_connection,
        extract_repository_from_git,
        save_llm_output_to_postgres,
        main
    )
except ImportError:
    mock_impl = MockSaveLLMOutput()
    parse_hook_input = mock_impl.parse_hook_input
    read_transcript_file = mock_impl.read_transcript_file
    extract_llm_metadata = mock_impl.extract_llm_metadata
    get_postgres_connection = mock_impl.get_postgres_connection
    extract_repository_from_git = mock_impl.extract_repository_from_git
    save_llm_output_to_postgres = mock_impl.save_llm_output_to_postgres
    main = mock_impl.main


class TestParseHookInput:
    """Test parse_hook_input function."""
    
    def test_valid_input(self, monkeypatch):
        """Test parsing valid JSON input."""
        input_data = {
            "session_id": "abc123",
            "transcript_path": "/path/to/transcript.jsonl",
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "cwd": "/workspaces/project"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(input_data))):
            result = save_llm_output.parse_hook_input()
        
        assert result['session_id'] == 'abc123'
        assert result['hook_event_name'] == 'Stop'
        assert result['stop_hook_active'] is True
        assert result['cwd'] == '/workspaces/project'
        # Path should be expanded
        assert '~' not in result['transcript_path']
    
    def test_hook_input_minimal_required_fields(self):
        """Test parsing hook input with only required fields"""
        hook_data = {
            "transcript_path": "/path/to/transcript.jsonl",
            "hook_event_name": "Stop"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
            result = save_llm_output.parse_hook_input()
        
        assert result['transcript_path'] == '/path/to/transcript.jsonl'
        assert result['hook_event_name'] == 'Stop'
    
    def test_hook_input_missing_transcript_path(self):
        """Test parsing hook input without transcript_path"""
        hook_data = {
            "session_id": "abc123",
            "hook_event_name": "Stop"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
            with pytest.raises(ValueError, match="Missing required fields: transcript_path"):
                save_llm_output.parse_hook_input()
    
    def test_hook_input_missing_hook_event_name(self):
        """Test parsing hook input without hook_event_name"""
        hook_data = {
            "transcript_path": "/path/to/transcript.jsonl",
            "session_id": "abc123"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
            with pytest.raises(ValueError, match="Missing required fields: hook_event_name"):
                save_llm_output.parse_hook_input()
    
    def test_hook_input_wrong_event_type(self):
        """Test parsing hook input with wrong event type"""
        hook_data = {
            "transcript_path": "/path/to/transcript.jsonl",
            "hook_event_name": "Start"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
            with pytest.raises(ValueError, match="Expected Stop hook, got Start"):
                save_llm_output.parse_hook_input()
    
    def test_invalid_json(self):
        """Test parsing invalid JSON from stdin"""
        with patch('sys.stdin', StringIO("invalid json")):
            with pytest.raises(json.JSONDecodeError):
                save_llm_output.parse_hook_input()
    
    def test_path_expansion(self):
        """Test that tilde in paths is expanded"""
        hook_data = {
            "transcript_path": "~/test/transcript.jsonl",
            "hook_event_name": "Stop"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
            result = save_llm_output.parse_hook_input()
        
        assert '~' not in result['transcript_path']
        assert result['transcript_path'].startswith(os.path.expanduser('~'))


class TestReadTranscriptFile:
    """Test cases for read_transcript_file function"""
    
    def test_read_valid_transcript_with_assistant_message(self):
        """Test reading a transcript file with valid assistant message"""
        transcript_content = '''{"type": "user", "message": {"content": "Hello"}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "First response"}]}, "sessionId": "123"}
{"type": "user", "message": {"content": "Another question"}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Last response"}]}, "sessionId": "456"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(transcript_content)
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is not None
            assert result['type'] == 'assistant'
            assert result['sessionId'] == '456'
            assert result['message']['content'][0]['text'] == 'Last response'
        finally:
            os.unlink(temp_path)
    
    def test_read_transcript_no_assistant_messages(self):
        """Test reading a transcript file with no assistant messages"""
        transcript_content = '''{"type": "user", "message": {"content": "Hello"}}
{"type": "user", "message": {"content": "Another message"}}
{"type": "system", "message": {"content": "System message"}}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(transcript_content)
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_read_transcript_with_malformed_lines(self):
        """Test reading a transcript with some malformed JSON lines"""
        transcript_content = '''{"type": "user", "message": {"content": "Hello"}}
invalid json line
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Response"}]}}
{malformed json
{"type": "user", "message": {"content": "Question"}}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(transcript_content)
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is not None
            assert result['type'] == 'assistant'
            assert result['message']['content'][0]['text'] == 'Response'
        finally:
            os.unlink(temp_path)
    
    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist"""
        result = save_llm_output.read_transcript_file('/nonexistent/file.jsonl')
        assert result is None
    
    def test_read_empty_transcript_file(self):
        """Test reading an empty transcript file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_read_transcript_with_empty_lines(self):
        """Test reading a transcript with empty lines between valid data"""
        transcript_content = '''{"type": "user", "message": {"content": "Hello"}}

{"type": "assistant", "message": {"content": [{"type": "text", "text": "Response"}]}}

'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(transcript_content)
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is not None
            assert result['type'] == 'assistant'
        finally:
            os.unlink(temp_path)


class TestExtractLLMMetadata:
    """Test cases for extract_llm_metadata function"""
    
    def test_extract_full_metadata(self):
        """Test extracting complete metadata from assistant message"""
        assistant_message = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "This is the response text"},
                    {"type": "text", "text": "Additional text"}
                ],
                "model": "claude-opus-4-1-20250805",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 567,
                    "service_tier": "standard"
                }
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] == "This is the response text\nAdditional text"
        assert result['model'] == "claude-opus-4-1-20250805"
        assert result['input_tokens'] == 100
        assert result['output_tokens'] == 567
        assert result['service_tier'] == "standard"
    
    def test_extract_minimal_metadata(self):
        """Test extracting metadata with only text content"""
        assistant_message = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Simple response"}
                ]
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] == "Simple response"
        assert result['model'] is None
        assert result['input_tokens'] is None
        assert result['output_tokens'] is None
        assert result['service_tier'] is None
    
    def test_extract_with_partial_usage_data(self):
        """Test extracting metadata with partial usage statistics"""
        assistant_message = {
            "type": "assistant", 
            "message": {
                "content": [{"type": "text", "text": "Response"}],
                "model": "claude-3",
                "usage": {
                    "output_tokens": 50
                }
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] == "Response"
        assert result['model'] == "claude-3"
        assert result['input_tokens'] is None
        assert result['output_tokens'] == 50
        assert result['service_tier'] is None
    
    def test_extract_no_message_field(self):
        """Test extracting metadata when message field is missing"""
        assistant_message = {
            "type": "assistant"
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] is None
        assert result['model'] is None
        assert result['input_tokens'] is None
        assert result['output_tokens'] is None
        assert result['service_tier'] is None
    
    def test_extract_empty_content(self):
        """Test extracting metadata with empty content array"""
        assistant_message = {
            "type": "assistant",
            "message": {
                "content": []  # Empty content array
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] is None
        assert result['model'] is None
        assert result['input_tokens'] is None
        assert result['output_tokens'] is None
        assert result['service_tier'] is None


class TestReadTranscriptFile:
    """Test read_transcript_file function."""
    
    def test_read_valid_transcript(self, tmp_path):
        """Test reading a valid transcript file."""
        transcript = tmp_path / "test.jsonl"
        assistant_msg = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        }
        with open(transcript, 'w') as f:
            f.write(json.dumps({"type": "user", "message": "Hi"}) + "\n")
            f.write(json.dumps(assistant_msg) + "\n")
        
        result = read_transcript_file(str(transcript))
        assert result == assistant_msg
    
    def test_multiple_assistant_messages(self, tmp_path):
        """Test that only the last assistant message is returned."""
        transcript = tmp_path / "test.jsonl"
        msg1 = {"type": "assistant", "message": {"content": "First"}}
        msg2 = {"type": "assistant", "message": {"content": "Second"}}
        msg3 = {"type": "assistant", "message": {"content": "Last"}}
        
        with open(transcript, 'w') as f:
            f.write(json.dumps(msg1) + "\n")
            f.write(json.dumps({"type": "user", "message": "Question"}) + "\n")
            f.write(json.dumps(msg2) + "\n")
            f.write(json.dumps(msg3) + "\n")
        
        result = read_transcript_file(str(transcript))
        assert result == msg3
    
    def test_no_assistant_messages(self, tmp_path):
        """Test file with no assistant messages returns None."""
        transcript = tmp_path / "test.jsonl"
        with open(transcript, 'w') as f:
            f.write(json.dumps({"type": "user", "message": "Hi"}) + "\n")
            f.write(json.dumps({"type": "system", "message": "Info"}) + "\n")
        
        result = read_transcript_file(str(transcript))
        assert result is None
    
    def test_malformed_json_lines(self, tmp_path):
        """Test handling of malformed JSON lines."""
        transcript = tmp_path / "test.jsonl"
        assistant_msg = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Valid"}]}
        }
        
        with open(transcript, 'w') as f:
            f.write("not json\n")
            f.write("{broken json\n")
            f.write(json.dumps(assistant_msg) + "\n")
            f.write("more bad data\n")
        
        result = read_transcript_file(str(transcript))
        assert result == assistant_msg
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        result = read_transcript_file("/nonexistent/file.jsonl")
        assert result is None
    
    def test_empty_file(self, tmp_path):
        """Test handling of empty file."""
        transcript = tmp_path / "empty.jsonl"
        transcript.touch()
        
        result = read_transcript_file(str(transcript))
        assert result is None
    
    def test_expanded_home_path(self, tmp_path, monkeypatch):
        """Test that ~ in path is expanded."""
        monkeypatch.setenv("HOME", str(tmp_path))
        transcript = tmp_path / "test.jsonl"
        assistant_msg = {"type": "assistant", "message": "Test"}
        
        with open(transcript, 'w') as f:
            f.write(json.dumps(assistant_msg) + "\n")
        
        result = read_transcript_file("~/test.jsonl")
        assert result == assistant_msg


class TestExtractLLMMetadata:
    """Test extract_llm_metadata function."""
    
    def test_full_metadata_extraction(self):
        """Test extraction with all metadata present."""
        message = {
            "message": {
                "model": "claude-opus-4-1-20250805",
                "content": [
                    {"type": "text", "text": "This is the output text"}
                ],
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 250,
                    "service_tier": "premium"
                }
            }
        }
        
        result = extract_llm_metadata(message)
        assert result["output"] == "This is the output text"
        assert result["model"] == "claude-opus-4-1-20250805"
        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 250
        assert result["service_tier"] == "premium"
    
    def test_minimal_metadata(self):
        """Test extraction with minimal metadata."""
        message = {
            "message": {
                "content": [
                    {"type": "text", "text": "Minimal output"}
                ]
            }
        }
        
        result = extract_llm_metadata(message)
        assert result["output"] == "Minimal output"
        assert result.get("model") is None
        assert result.get("input_tokens") is None
        assert result.get("output_tokens") is None
        assert result.get("service_tier") is None
    
    def test_multiple_content_items(self):
        """Test extraction with multiple content items."""
        message = {
            "message": {
                "content": [
                    {"type": "text", "text": "Part 1"},
                    {"type": "text", "text": " Part 2"},
                    {"type": "other", "data": "ignored"}
                ]
            }
        }
        
        result = extract_llm_metadata(message)
        assert result["output"] == "Part 1 Part 2"
    
    def test_service_tier_in_usage(self):
        """Test service_tier inside usage object."""
        message = {
            "message": {
                "content": [{"type": "text", "text": "Test"}],
                "usage": {
                    "service_tier": "standard"
                }
            }
        }
        
        result = extract_llm_metadata(message)
        assert result["service_tier"] == "standard"
    
    def test_empty_content(self):
        """Test handling of empty content."""
        message = {
            "message": {
                "content": []
            }
        }
        
        result = extract_llm_metadata(message)
        
        assert result['output'] is None
        assert result['model'] is None
    
    def test_extract_non_text_content(self):
        """Test extracting metadata with non-text content types"""
        assistant_message = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "image", "url": "http://example.com/image.png"},
                    {"type": "text", "text": "Text content"},
                    {"type": "code", "code": "print('hello')"}
                ]
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] == "Text content"
    
    def test_extract_none_input(self):
        """Test extracting metadata with None input"""
        result = save_llm_output.extract_llm_metadata(None)
        
        assert result['output'] is None
        assert result['model'] is None
        assert result['input_tokens'] is None
        assert result['output_tokens'] is None
        assert result['service_tier'] is None
    
    def test_extract_usage_not_dict(self):
        """Test extracting metadata when usage is not a dictionary"""
        assistant_message = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Response"}],
                "usage": "invalid usage format"
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result['output'] == "Response"
        assert result['input_tokens'] is None
        assert result['output_tokens'] is None
        assert result['service_tier'] is None


class TestGetPostgresConnection:
    """Test get_postgres_connection function."""
    
    @patch('psycopg.connect')
    def test_dsn_connection(self, mock_connect, monkeypatch):
        """Test connection using DSN."""
        dsn = "postgres://user:pass@localhost:5432/dbname?sslmode=require"
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_DSN", dsn)
        
        get_postgres_connection()
        mock_connect.assert_called_once_with(dsn, connect_timeout=5)
    
    @patch('psycopg.connect')
    def test_individual_params_connection(self, mock_connect, monkeypatch):
        """Test connection using individual parameters."""
        # Ensure DSN is not set so individual params are used
        monkeypatch.delenv("CLAUDE_POSTGRES_SERVER_DSN", raising=False)
        
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_HOST_PORT", "localhost:5432")
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_USER", "testuser")
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_PASS", "testpass")
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_DB_NAME", "testdb")
        
        get_postgres_connection()
        mock_connect.assert_called_once()
        
        # The implementation builds a connection string, so check the first argument
        call_args = mock_connect.call_args[0]
        conn_string = call_args[0]
        assert "host=localhost" in conn_string
        assert "port=5432" in conn_string
        assert "user=testuser" in conn_string
        assert "password=testpass" in conn_string
        assert "dbname=testdb" in conn_string
        assert "sslmode=require" in conn_string
        assert "connect_timeout=5" in conn_string
    
    def test_missing_environment_variables(self, monkeypatch):
        """Test that missing env vars returns None."""
        # Clear all postgres env vars
        for var in ["CLAUDE_POSTGRES_SERVER_DSN", "CLAUDE_POSTGRES_HOST_PORT",
                    "CLAUDE_POSTGRES_USER", "CLAUDE_POSTGRES_PASS", "CLAUDE_POSTGRES_DB_NAME"]:
            monkeypatch.delenv(var, raising=False)
        
        result = get_postgres_connection()
        assert result is None
    
    @patch('psycopg.connect', side_effect=Exception("Connection failed"))
    def test_connection_failure(self, mock_connect, monkeypatch):
        """Test that connection failure returns None."""
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_DSN", "postgres://localhost/db")
        
        result = get_postgres_connection()
        assert result is None


class TestExtractRepositoryFromGit:
    """Test extract_repository_from_git function."""
    
    @patch('subprocess.run')
    def test_https_github_url(self, mock_run):
        """Test extraction from HTTPS GitHub URL."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/user/repo.git"
        )
        
        result = extract_repository_from_git("/some/path")
        assert result == "github.com/user/repo"
    
    @patch('subprocess.run')
    def test_ssh_github_url(self, mock_run):
        """Test extraction from SSH GitHub URL."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="git@github.com:user/repo.git"
        )
        
        result = extract_repository_from_git("/some/path")
        assert result == "github.com/user/repo"
    
    @patch('subprocess.run')
    def test_gitlab_url(self, mock_run):
        """Test extraction from GitLab URL."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://gitlab.com/group/subgroup/project.git"
        )
        
        result = extract_repository_from_git("/some/path")
        assert result == "gitlab.com/group/subgroup/project"
    
    @patch('subprocess.run')
    def test_no_git_remote(self, mock_run):
        """Test handling when no remote exists."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout=""
        )
        
        result = extract_repository_from_git("/some/path")
        assert result is None
    
    @patch('subprocess.run', side_effect=Exception("Git not found"))
    def test_git_command_failure(self, mock_run):
        """Test handling of git command failure."""
        result = extract_repository_from_git("/some/path")
        assert result is None


class TestSaveLLMOutputToPostgres:
    """Test save_llm_output_to_postgres function."""
    
    def test_successful_save(self):
        """Test successful save to database."""
        conn = Mock()
        cursor = Mock()
        # Make cursor support context manager protocol
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        conn.cursor.return_value = cursor
        
        data = {
            "output": "Test output",
            "session_id": "session123",
            "repository": "github.com/test/repo",
            "input_tokens": 100,
            "output_tokens": 200,
            "model": "claude-opus",
            "service_tier": "standard"
        }
        
        result = save_llm_output_to_postgres(conn, data)
        assert result is True
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
    
    def test_save_with_nulls(self):
        """Test save with nullable fields as None."""
        conn = Mock()
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        conn.cursor.return_value = cursor
        
        data = {
            "output": "Minimal output",
            "session_id": "session456",
            "repository": None,
            "input_tokens": None,
            "output_tokens": None,
            "model": None,
            "service_tier": None
        }
        
        result = save_llm_output_to_postgres(conn, data)
        assert result is True
        cursor.execute.assert_called_once()
        
        # Verify SQL contains all fields
        sql_call = cursor.execute.call_args[0][0]
        assert "output" in sql_call
        assert "session_id" in sql_call
        assert "repository" in sql_call
    
    def test_save_failure(self):
        """Test handling of save failure."""
        conn = Mock()
        cursor = Mock()
        cursor.execute.side_effect = Exception("Database error")
        conn.cursor.return_value = cursor
        
        data = {"output": "Test"}
        
        result = save_llm_output_to_postgres(conn, data)
        assert result is False
        conn.rollback.assert_called_once()
    
    def test_parameterized_query(self):
        """Test that parameterized queries are used."""
        conn = Mock()
        cursor = Mock()
        # Make cursor support context manager protocol
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        conn.cursor.return_value = cursor
        
        data = {"output": "'; DROP TABLE llm_outputs; --"}
        
        save_llm_output_to_postgres(conn, data)
        
        # Verify parameterized query is used (second argument to execute)
        assert cursor.execute.call_count == 1
        assert len(cursor.execute.call_args[0]) == 2  # SQL and params


class TestMainFunction:
    """Test the main function integration."""
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_successful_flow(self, mock_save, mock_repo, mock_conn,
                           mock_extract, mock_read):
        """Test successful end-to-end flow."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_conn.return_value = Mock()
        mock_repo.return_value = "github.com/test/repo"
        mock_save.return_value = True
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/missing.jsonl",
        "hook_event_name": "Stop"
    })))
    @patch('save_llm_output.read_transcript_file', return_value=None)
    def test_missing_transcript(self, mock_read):
        """Test handling of missing transcript file."""
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)
    
    @patch('sys.stdin', StringIO("invalid json"))
    def test_invalid_input(self):
        """Test handling of invalid input."""
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    def test_no_output_in_message(self, mock_extract, mock_read):
        """Test handling when no output text is found."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": None}  # No output text
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)  # Should exit gracefully
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    def test_no_assistant_message_found(self, mock_read):
        """Test handling when no assistant message is found."""
        mock_read.return_value = None
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)  # Should exit gracefully
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    def test_database_connection_failure(self, mock_conn, mock_extract, mock_read):
        """Test handling of database connection failure."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_conn.return_value = None  # Connection failed
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)  # Should exit with error
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_database_save_failure(self, mock_save, mock_repo, mock_conn,
                                  mock_extract, mock_read):
        """Test handling of database save failure."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_conn.return_value = Mock()
        mock_repo.return_value = "github.com/test/repo"
        mock_save.return_value = False  # Save failed
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)  # Should exit with error
    
    @patch('sys.stdin', StringIO(json.dumps({
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_missing_session_id(self, mock_save, mock_repo, mock_conn,
                               mock_extract, mock_read):
        """Test handling when session_id is missing (should still work)."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_conn.return_value = Mock()
        mock_repo.return_value = "github.com/test/repo"
        mock_save.return_value = True
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)  # Should succeed
            # Verify save was called with None session_id
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][1]
            assert saved_data['session_id'] is None
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_missing_cwd(self, mock_save, mock_repo, mock_conn,
                        mock_extract, mock_read):
        """Test handling when cwd is missing (repository should be None)."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_conn.return_value = Mock()
        mock_repo.return_value = None  # No repository info
        mock_save.return_value = True
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)  # Should succeed
            # Verify extract_repository was called with None
            mock_repo.assert_called_once_with(None)
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_connection_close_on_success(self, mock_save, mock_repo, mock_conn,
                                        mock_extract, mock_read):
        """Test that database connection is closed after successful save."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_connection = Mock()
        mock_conn.return_value = mock_connection
        mock_repo.return_value = "github.com/test/repo"
        mock_save.return_value = True
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(0)
            mock_connection.close.assert_called_once()
    
    @patch('sys.stdin', StringIO(json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/test.jsonl",
        "hook_event_name": "Stop",
        "cwd": "/workspaces/test"
    })))
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.extract_llm_metadata')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.extract_repository_from_git')
    @patch('save_llm_output.save_llm_output_to_postgres')
    def test_connection_close_on_failure(self, mock_save, mock_repo, mock_conn,
                                        mock_extract, mock_read):
        """Test that database connection is closed even after save failure."""
        mock_read.return_value = {"type": "assistant", "message": {}}
        mock_extract.return_value = {"output": "Test"}
        mock_connection = Mock()
        mock_conn.return_value = mock_connection
        mock_repo.return_value = "github.com/test/repo"
        mock_save.return_value = False  # Save fails
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)
            mock_connection.close.assert_called_once()  # Still closed


class TestPerformance:
    """Performance tests for large transcripts."""
    
    def test_large_transcript_performance(self, tmp_path):
        """Test performance with large transcript files."""
        transcript = tmp_path / "large.jsonl"
        
        # Create a large transcript file (10MB)
        with open(transcript, 'w') as f:
            for i in range(10000):
                msg = {
                    "type": "user" if i % 2 == 0 else "assistant",
                    "message": {"content": f"Message {i}" * 100}
                }
                f.write(json.dumps(msg) + "\n")
        
        import time
        start = time.time()
        result = read_transcript_file(str(transcript))
        duration = time.time() - start
        
        assert result is not None
        assert duration < 5.0  # Should process in under 5 seconds
    
    def test_memory_efficiency(self, tmp_path):
        """Test that memory usage is reasonable for large files."""
        transcript = tmp_path / "huge.jsonl"
        
        # Create a transcript with very large messages
        with open(transcript, 'w') as f:
            huge_text = "x" * 1000000  # 1MB text
            msg = {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": huge_text}]}
            }
            f.write(json.dumps(msg) + "\n")
        
        import tracemalloc
        tracemalloc.start()
        
        result = read_transcript_file(str(transcript))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        assert result is not None
        assert peak < 100 * 1024 * 1024  # Peak memory under 100MB
