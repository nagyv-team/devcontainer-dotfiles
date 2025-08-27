#!/usr/bin/env python3
"""
End-to-end tests for save_llm_output.py Stop hook script
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "claude" / ".claude" / "scripts"))

import save_llm_output


class TestParseHookInput:
    """Test the parse_hook_input function"""
    
    def test_parse_valid_hook_input(self):
        """Test parsing valid hook input with all fields"""
        hook_data = {
            "session_id": "abc123",
            "transcript_path": "~/.claude/projects/test.jsonl",
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "cwd": "/workspaces/project-dir"
        }
        
        with patch('sys.stdin', io.StringIO(json.dumps(hook_data))):
            result = save_llm_output.parse_hook_input()
            
        assert result["session_id"] == "abc123"
        assert result["hook_event_name"] == "Stop"
        assert result["stop_hook_active"] is True
        assert result["cwd"] == "/workspaces/project-dir"
        # Transcript path should be expanded
        assert "~" not in result["transcript_path"]
    
    def test_parse_missing_required_fields(self):
        """Test parsing hook input with missing required fields"""
        hook_data = {
            "session_id": "abc123",
            "stop_hook_active": True
        }
        
        with patch('sys.stdin', io.StringIO(json.dumps(hook_data))):
            with pytest.raises(ValueError, match="Missing required fields"):
                save_llm_output.parse_hook_input()
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON input"""
        with patch('sys.stdin', io.StringIO("not valid json")):
            with pytest.raises(json.JSONDecodeError):
                save_llm_output.parse_hook_input()


class TestReadTranscriptFile:
    """Test the read_transcript_file function"""
    
    def test_read_valid_transcript(self):
        """Test reading a valid transcript file with assistant messages"""
        transcript_content = [
            '{"type": "user", "message": {"content": "Hello"}}',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}}',
            '{"type": "user", "message": {"content": "How are you?"}}',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "I am doing well!"}]}}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('\n'.join(transcript_content))
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is not None
            assert result["type"] == "assistant"
            assert "I am doing well!" in json.dumps(result)
        finally:
            os.unlink(temp_path)
    
    def test_read_transcript_with_malformed_lines(self):
        """Test reading transcript with some malformed JSON lines"""
        transcript_content = [
            '{"type": "user", "message": {"content": "Hello"}}',
            'this is not valid json',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}}',
            '{ broken json',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Final message"}]}}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('\n'.join(transcript_content))
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is not None
            assert "Final message" in json.dumps(result)
        finally:
            os.unlink(temp_path)
    
    def test_read_missing_transcript(self):
        """Test reading a non-existent transcript file"""
        result = save_llm_output.read_transcript_file("/non/existent/file.jsonl")
        assert result is None
    
    def test_read_transcript_no_assistant_messages(self):
        """Test reading transcript with no assistant messages"""
        transcript_content = [
            '{"type": "user", "message": {"content": "Hello"}}',
            '{"type": "user", "message": {"content": "Anyone there?"}}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('\n'.join(transcript_content))
            temp_path = f.name
        
        try:
            result = save_llm_output.read_transcript_file(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)


class TestExtractLLMMetadata:
    """Test the extract_llm_metadata function"""
    
    def test_extract_full_metadata(self):
        """Test extracting metadata from a complete assistant message"""
        assistant_message = {
            "message": {
                "content": [
                    {"type": "text", "text": "First part"},
                    {"type": "text", "text": "Second part"}
                ],
                "model": "claude-opus-4-1-20250805",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "service_tier": "standard",
                    "cache_creation_input_tokens": 50,
                    "cache_read_input_tokens": 25
                }
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result["output"] == "First part\nSecond part"
        assert result["model"] == "claude-opus-4-1-20250805"
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 200
        assert result["service_tier"] == "standard"
    
    def test_extract_minimal_metadata(self):
        """Test extracting metadata from a minimal assistant message"""
        assistant_message = {
            "message": {
                "content": [{"type": "text", "text": "Simple response"}]
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
        assert result["output"] == "Simple response"
        assert result["model"] is None
        assert result["input_tokens"] is None
        assert result["output_tokens"] is None
        assert result["service_tier"] is None
    
    def test_extract_no_text_content(self):
        """Test extracting from message with no text content"""
        assistant_message = {
            "message": {
                "content": [{"type": "image", "url": "http://example.com/img.jpg"}]
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        assert result["output"] is None
    
    def test_extract_empty_message(self):
        """Test extracting from empty or malformed message"""
        result = save_llm_output.extract_llm_metadata({})
        assert result["output"] is None
        assert result["model"] is None


class TestPostgreSQLIntegration:
    """Test PostgreSQL connection and save functions"""
    
    @patch('os.getenv')
    def test_get_postgres_connection_with_dsn(self, mock_getenv):
        """Test connecting with DSN"""
        mock_getenv.side_effect = lambda key: {
            'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@host:5432/db'
        }.get(key)
        
        with patch('psycopg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            result = save_llm_output.get_postgres_connection()
            
            assert result == mock_conn
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args[0][0]
            assert 'sslmode=require' in call_args
    
    @patch('os.getenv')
    def test_get_postgres_connection_with_env_vars(self, mock_getenv):
        """Test connecting with individual environment variables"""
        mock_getenv.side_effect = lambda key: {
            'CLAUDE_POSTGRES_SERVER_DSN': None,
            'CLAUDE_POSTGRES_SERVER_HOST_PORT': 'localhost:5432',
            'CLAUDE_POSTGRES_SERVER_USER': 'testuser',
            'CLAUDE_POSTGRES_SERVER_PASS': 'testpass',
            'CLAUDE_POSTGRES_SERVER_DB_NAME': 'testdb'
        }.get(key)
        
        with patch('psycopg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            result = save_llm_output.get_postgres_connection()
            
            assert result == mock_conn
            mock_connect.assert_called_once()
    
    @patch('os.getenv')
    def test_get_postgres_connection_no_config(self, mock_getenv):
        """Test connection with no configuration"""
        mock_getenv.return_value = None
        
        result = save_llm_output.get_postgres_connection()
        assert result is None
    
    def test_save_llm_output_to_postgres_success(self):
        """Test successful save to PostgreSQL"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test output',
            'session_id': 'test-session',
            'repository': 'github.com/user/repo',
            'input_tokens': 100,
            'output_tokens': 200,
            'model': 'claude-3',
            'service_tier': 'standard'
        }
        
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    def test_save_llm_output_to_postgres_no_output(self):
        """Test save with no output text"""
        mock_conn = Mock()
        
        llm_data = {
            'created_at': datetime.now(),
            'output': None,
            'session_id': 'test-session'
        }
        
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        assert result is False
    
    def test_save_llm_output_to_postgres_exception(self):
        """Test save with database exception"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        mock_cursor.execute.side_effect = Exception("Database error")
        
        llm_data = {
            'output': 'Test output',
            'session_id': 'test-session'
        }
        
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        assert result is False
        mock_conn.rollback.assert_called_once()


class TestExtractRepositoryFromGit:
    """Test git repository extraction"""
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_extract_ssh_repository(self, mock_exists, mock_run):
        """Test extracting repository from SSH URL"""
        mock_exists.return_value = True
        mock_run.return_value = Mock(
            returncode=0,
            stdout='git@github.com:user/repo.git\n',
            stderr=''
        )
        
        result = save_llm_output.extract_repository_from_git('/some/path')
        assert result == 'github.com/user/repo'
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_extract_https_repository(self, mock_exists, mock_run):
        """Test extracting repository from HTTPS URL"""
        mock_exists.return_value = True
        mock_run.return_value = Mock(
            returncode=0,
            stdout='https://github.com/user/repo\n',
            stderr=''
        )
        
        result = save_llm_output.extract_repository_from_git('/some/path')
        assert result == 'github.com/user/repo'
    
    @patch('subprocess.run')
    def test_extract_repository_no_remote(self, mock_run):
        """Test extracting repository with no remote"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='fatal: not a git repository'
        )
        
        result = save_llm_output.extract_repository_from_git('/some/path')
        assert result is None


class TestMainIntegration:
    """Test the main function integration"""
    
    @patch('sys.stdin')
    @patch('save_llm_output.read_transcript_file')
    @patch('save_llm_output.get_postgres_connection')
    @patch('save_llm_output.save_llm_output_to_postgres')
    @patch('save_llm_output.extract_repository_from_git')
    def test_main_successful_flow(self, mock_git, mock_save, mock_conn, mock_read, mock_stdin):
        """Test successful end-to-end flow"""
        # Setup mocks
        hook_data = {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "hook_event_name": "Stop",
            "cwd": "/workspaces/test"
        }
        
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = hook_data
            
            assistant_message = {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Test output"}],
                    "model": "claude-3",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 200,
                        "service_tier": "standard"
                    }
                }
            }
            mock_read.return_value = assistant_message
            
            mock_connection = Mock()
            mock_conn.return_value = mock_connection
            
            mock_git.return_value = "github.com/user/repo"
            mock_save.return_value = True
            
            # Run main
            with patch('sys.exit') as mock_exit:
                save_llm_output.main()
                mock_exit.assert_called_with(0)
            
            # Verify calls
            mock_read.assert_called_once_with("/tmp/test.jsonl")
            mock_conn.assert_called_once()
            mock_save.assert_called_once()
            mock_connection.close.assert_called_once()
            
            # Check save data
            save_call_args = mock_save.call_args[0]
            assert save_call_args[0] == mock_connection
            llm_data = save_call_args[1]
            assert llm_data['output'] == "Test output"
            assert llm_data['session_id'] == "test-session"
            assert llm_data['repository'] == "github.com/user/repo"
            assert llm_data['input_tokens'] == 100
            assert llm_data['output_tokens'] == 200
    
    @patch('sys.stdin')
    @patch('save_llm_output.read_transcript_file')
    def test_main_no_assistant_message(self, mock_read, mock_stdin):
        """Test main when no assistant message is found"""
        hook_data = {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "hook_event_name": "Stop"
        }
        # Use io.StringIO for stdin mock
        import io
        mock_stdin.read = Mock(return_value=json.dumps(hook_data))
        
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = hook_data
            mock_read.return_value = None
            
            with patch('sys.exit') as mock_exit:
                # Mock sys.exit to prevent actual exit but raise exception to stop flow
                mock_exit.side_effect = SystemExit(0)
                
                try:
                    save_llm_output.main()
                except SystemExit as e:
                    assert e.code == 0  # Should exit with 0 (success)
                    
                mock_exit.assert_called_once_with(0)
    
    @patch('sys.stdin')
    @patch('save_llm_output.get_postgres_connection')
    def test_main_database_connection_failure(self, mock_conn, mock_stdin):
        """Test main when database connection fails"""
        # Create a valid transcript file for this test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test"}]}}')
            temp_path = f.name
        
        hook_data = {
            "session_id": "test-session",
            "transcript_path": temp_path,
            "hook_event_name": "Stop"
        }
        
        try:
            with patch('json.load') as mock_json_load:
                mock_json_load.return_value = hook_data
                mock_conn.return_value = None
                
                with patch('sys.exit') as mock_exit:
                    save_llm_output.main()
                    mock_exit.assert_called_with(1)  # Should exit with error
        finally:
            os.unlink(temp_path)
    
    @patch('sys.stdin')
    def test_main_invalid_hook_event(self, mock_stdin):
        """Test main with wrong hook event type"""
        hook_data = {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "hook_event_name": "Start"  # Wrong event type
        }
        
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = hook_data
            
            with patch('sys.exit') as mock_exit:
                save_llm_output.main()
                # Should return without error but not process
                if mock_exit.called:
                    assert False, "Should not call sys.exit for wrong hook event"


# Import io for StringIO
import io


if __name__ == "__main__":
    pytest.main([__file__, "-v"])