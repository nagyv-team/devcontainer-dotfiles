"""Comprehensive unit tests for save_llm_output.py."""
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import logging
from io import StringIO

import pytest

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'claude', '.claude', 'scripts'))

# Create mock implementations for now since the functions aren't implemented yet
# These will be replaced with actual imports once implementation is complete
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
        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(input_data)))
        
        result = parse_hook_input()
        assert result == input_data
    
    def test_missing_required_fields(self, monkeypatch):
        """Test missing required fields raises ValueError."""
        input_data = {"session_id": "abc123"}
        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(input_data)))
        
        with pytest.raises(ValueError, match="required field"):
            parse_hook_input()
    
    def test_invalid_json(self, monkeypatch):
        """Test invalid JSON raises JSONDecodeError."""
        monkeypatch.setattr('sys.stdin', StringIO("not json"))
        
        with pytest.raises(json.JSONDecodeError):
            parse_hook_input()
    
    def test_empty_input(self, monkeypatch):
        """Test empty input raises error."""
        monkeypatch.setattr('sys.stdin', StringIO(""))
        
        with pytest.raises((json.JSONDecodeError, ValueError)):
            parse_hook_input()


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
        assert result["output"] == ""
    
    def test_missing_message_key(self):
        """Test handling of missing message key."""
        message = {"other": "data"}
        
        result = extract_llm_metadata(message)
        assert result["output"] == ""
        assert result.get("model") is None


class TestGetPostgresConnection:
    """Test get_postgres_connection function."""
    
    @patch('psycopg2.connect')
    def test_dsn_connection(self, mock_connect, monkeypatch):
        """Test connection using DSN."""
        dsn = "postgres://user:pass@localhost:5432/dbname?sslmode=require"
        monkeypatch.setenv("CLAUDE_POSTGRES_SERVER_DSN", dsn)
        
        get_postgres_connection()
        mock_connect.assert_called_once_with(dsn)
    
    @patch('psycopg2.connect')
    def test_individual_params_connection(self, mock_connect, monkeypatch):
        """Test connection using individual parameters."""
        monkeypatch.setenv("CLAUDE_POSTGRES_HOST_PORT", "localhost:5432")
        monkeypatch.setenv("CLAUDE_POSTGRES_USER", "testuser")
        monkeypatch.setenv("CLAUDE_POSTGRES_PASS", "testpass")
        monkeypatch.setenv("CLAUDE_POSTGRES_DB_NAME", "testdb")
        
        get_postgres_connection()
        mock_connect.assert_called_once()
        
        call_args = mock_connect.call_args[1]
        assert call_args["host"] == "localhost"
        assert call_args["port"] == 5432
        assert call_args["user"] == "testuser"
        assert call_args["password"] == "testpass"
        assert call_args["database"] == "testdb"
    
    def test_missing_environment_variables(self, monkeypatch):
        """Test that missing env vars returns None."""
        # Clear all postgres env vars
        for var in ["CLAUDE_POSTGRES_SERVER_DSN", "CLAUDE_POSTGRES_HOST_PORT",
                    "CLAUDE_POSTGRES_USER", "CLAUDE_POSTGRES_PASS", "CLAUDE_POSTGRES_DB_NAME"]:
            monkeypatch.delenv(var, raising=False)
        
        result = get_postgres_connection()
        assert result is None
    
    @patch('psycopg2.connect', side_effect=Exception("Connection failed"))
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
        cursor.close.assert_called_once()
    
    def test_save_with_nulls(self):
        """Test save with nullable fields as None."""
        conn = Mock()
        cursor = Mock()
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
            mock_exit.assert_called_once_with(1)
    
    @patch('sys.stdin', StringIO("invalid json"))
    def test_invalid_input(self):
        """Test handling of invalid input."""
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)


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