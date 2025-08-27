#!/usr/bin/env python3
"""
Unit tests for save_user_prompt.py
"""
import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import subprocess

# Add parent directory to path to import save_user_prompt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'claude', '.claude', 'scripts'))
import save_user_prompt
from save_user_prompt import (
    get_postgres_connection,
    save_to_postgres,
    extract_repository_from_git,
    get_session_id,
    save_to_yaml
)


class TestSaveUserPrompt:
    """Test class for save_user_prompt.py functions"""

    @patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db'})
    @patch('psycopg.connect')
    def test_get_postgres_connection_with_dsn(self, mock_connect):
        """Test PostgreSQL connection using DSN"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        result = get_postgres_connection()
        
        # Verify connection was attempted with DSN and SSL
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0][0]
        assert 'sslmode=require' in call_args
        assert 'postgresql://user:pass@localhost/db' in call_args
        assert result == mock_conn

    @patch.dict(os.environ, {
        'CLAUDE_POSTGRES_SERVER_HOST_PORT': 'localhost:5432',
        'CLAUDE_POSTGRES_SERVER_USER': 'testuser',
        'CLAUDE_POSTGRES_SERVER_PASS': 'testpass',
        'CLAUDE_POSTGRES_SERVER_DB_NAME': 'testdb'
    }, clear=False)
    @patch('psycopg.connect')
    def test_get_postgres_connection_with_individual_vars(self, mock_connect):
        """Test PostgreSQL connection using individual environment variables"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Clear DSN to ensure individual variables are used
        with patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_DSN': ''}, clear=False):
            result = get_postgres_connection()
        
        # Verify connection was attempted with correct parameters
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0][0]
        assert 'host=localhost' in call_args
        assert 'port=5432' in call_args
        assert 'dbname=testdb' in call_args
        assert 'user=testuser' in call_args
        assert 'password=testpass' in call_args
        assert 'sslmode=require' in call_args
        assert result == mock_conn

    @patch.dict(os.environ, {
        'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://dsnuser:dsnpass@dsnhost/dsndb',
        'CLAUDE_POSTGRES_SERVER_HOST_PORT': 'localhost:5432',
        'CLAUDE_POSTGRES_SERVER_USER': 'testuser',
        'CLAUDE_POSTGRES_SERVER_PASS': 'testpass',
        'CLAUDE_POSTGRES_SERVER_DB_NAME': 'testdb'
    })
    @patch('psycopg.connect')
    def test_get_postgres_connection_dsn_precedence(self, mock_connect):
        """Test that DSN takes precedence over individual variables"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        result = get_postgres_connection()
        
        # Verify DSN was used, not individual vars
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0][0]
        assert 'postgresql://dsnuser:dsnpass@dsnhost/dsndb' in call_args
        assert 'testuser' not in call_args
        assert result == mock_conn

    @patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db'})
    @patch('psycopg.connect')
    def test_get_postgres_connection_ssl_enabled(self, mock_connect):
        """Test that SSL/TLS is always enabled"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        result = get_postgres_connection()
        
        # Verify sslmode=require is added
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0][0]
        assert 'sslmode=require' in call_args
        assert result == mock_conn

    @patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db'})
    @patch('psycopg.connect')
    def test_get_postgres_connection_failure_handling(self, mock_connect):
        """Test connection failure handling"""
        mock_connect.side_effect = Exception("Connection failed")
        
        result = get_postgres_connection()
        
        # Verify None is returned on failure, not exception
        assert result is None
        mock_connect.assert_called_once()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_postgres_connection_no_config(self):
        """Test when no PostgreSQL configuration is present"""
        result = get_postgres_connection()
        assert result is None
    
    @patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_HOST_PORT': 'localhost'}, clear=False)
    @patch('psycopg.connect')
    def test_get_postgres_connection_default_port(self, mock_connect):
        """Test default port 5432 is used when not specified"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Set other required vars
        os.environ['CLAUDE_POSTGRES_SERVER_USER'] = 'user'
        os.environ['CLAUDE_POSTGRES_SERVER_PASS'] = 'pass'
        os.environ['CLAUDE_POSTGRES_SERVER_DB_NAME'] = 'db'
        
        # Clear DSN to ensure individual variables are used
        with patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_DSN': ''}, clear=False):
            result = get_postgres_connection()
        
        # Verify default port was used
        call_args = mock_connect.call_args[0][0]
        assert 'port=5432' in call_args
        assert result == mock_conn

    def test_save_to_postgres_success(self):
        """Test successful insert to PostgreSQL"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        prompt_data = {
            'created_at': datetime.now(),
            'prompt': 'Test prompt',
            'session_id': 'test-session-id',
            'repository': 'github.com/user/repo'
        }
        
        result = save_to_postgres(mock_conn, prompt_data)
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        # Verify parameterized query was used
        call_args = mock_cursor.execute.call_args
        assert 'INSERT INTO user_prompts' in call_args[0][0]
        assert call_args[0][1] == (
            prompt_data['created_at'],
            prompt_data['prompt'],
            prompt_data['session_id'],
            prompt_data['repository']
        )

    def test_save_to_postgres_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # Malicious SQL injection attempt
        prompt_data = {
            'created_at': datetime.now(),
            'prompt': "'; DROP TABLE user_prompts; --",
            'session_id': "'; DELETE FROM user_prompts; --",
            'repository': 'github.com/user/repo'
        }
        
        result = save_to_postgres(mock_conn, prompt_data)
        
        assert result is True
        # Verify parameterized query was used (not string concatenation)
        call_args = mock_cursor.execute.call_args
        # The SQL should not contain the malicious code directly
        assert "DROP TABLE" not in call_args[0][0]
        assert "DELETE FROM" not in call_args[0][0]
        # The malicious strings should be in the parameters tuple
        assert "'; DROP TABLE user_prompts; --" in call_args[0][1]
        assert "'; DELETE FROM user_prompts; --" in call_args[0][1]

    def test_save_to_postgres_null_fields(self):
        """Test handling of NULL optional fields"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        prompt_data = {
            'created_at': datetime.now(),
            'prompt': 'Test prompt',
            'session_id': None,
            'repository': None
        }
        
        result = save_to_postgres(mock_conn, prompt_data)
        
        assert result is True
        call_args = mock_cursor.execute.call_args
        # Verify None values are passed for optional fields
        assert call_args[0][1][2] is None  # session_id
        assert call_args[0][1][3] is None  # repository

    def test_save_to_postgres_failure_handling(self):
        """Test insert failure handling"""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)
        
        prompt_data = {
            'created_at': datetime.now(),
            'prompt': 'Test prompt',
            'session_id': 'test-session',
            'repository': 'github.com/user/repo'
        }
        
        result = save_to_postgres(mock_conn, prompt_data)
        
        assert result is False
        mock_conn.rollback.assert_called_once()
    
    def test_save_to_postgres_no_connection(self):
        """Test handling when connection is None"""
        result = save_to_postgres(None, {'prompt': 'test'})
        assert result is False

    @patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': '/test/project'})
    @patch('subprocess.run')
    def test_extract_repository_from_git_github(self, mock_run):
        """Test GitHub repository extraction"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='https://github.com/user/repo.git\n',
            stderr=''
        )
        
        result = extract_repository_from_git()
        
        assert result == 'github.com/user/repo'
        mock_run.assert_called_once_with(
            ['git', 'remote', 'get-url', 'origin'],
            cwd='/test/project',
            capture_output=True,
            text=True,
            timeout=5
        )

    @patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': '/test/project'})
    @patch('subprocess.run')
    def test_extract_repository_from_git_gitlab(self, mock_run):
        """Test GitLab repository extraction"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='https://gitlab.com/org/project\n',
            stderr=''
        )
        
        result = extract_repository_from_git()
        
        assert result == 'gitlab.com/org/project'

    @patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': '/test/project'})
    @patch('subprocess.run')
    def test_extract_repository_from_git_ssh_format(self, mock_run):
        """Test SSH format repository URL parsing"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='git@github.com:user/repo.git\n',
            stderr=''
        )
        
        result = extract_repository_from_git()
        
        assert result == 'github.com/user/repo'

    @patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': '/test/project'})
    @patch('subprocess.run')
    def test_extract_repository_from_git_no_origin(self, mock_run):
        """Test handling when no origin remote exists"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='fatal: No such remote origin'
        )
        
        result = extract_repository_from_git()
        
        assert result is None

    @patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': '/test/project'})
    @patch('subprocess.run')
    def test_extract_repository_from_git_not_repository(self, mock_run):
        """Test handling when not in git repository"""
        mock_run.return_value = Mock(
            returncode=128,
            stdout='',
            stderr='fatal: not a git repository'
        )
        
        result = extract_repository_from_git()
        
        assert result is None
    
    @patch.dict(os.environ, {}, clear=True)
    def test_extract_repository_from_git_no_project_dir(self):
        """Test when CLAUDE_PROJECT_DIR is not set"""
        result = extract_repository_from_git()
        assert result is None

    @patch.dict(os.environ, {'CLAUDE_SESSION_ID': '550e8400-e29b-41d4-a716-446655440000'})
    def test_get_session_id_valid_uuid(self):
        """Test valid UUID session ID extraction"""
        result = get_session_id()
        assert result == '550e8400-e29b-41d4-a716-446655440000'

    @patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'not-a-valid-uuid'})
    def test_get_session_id_invalid_format(self):
        """Test invalid session ID format handling"""
        result = get_session_id()
        assert result is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_session_id_not_present(self):
        """Test missing session ID handling"""
        result = get_session_id()
        assert result is None

    def test_save_to_yaml_new_file(self):
        """Test saving to new YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test_prompts.yaml"
            timestamp = "2024-01-01 12:00"
            prompt = "Test prompt"
            session_id = "test-session"
            
            result = save_to_yaml(yaml_file, timestamp, prompt, session_id)
            
            assert result is True
            assert yaml_file.exists()
            # TODO: Add more assertions about file content

    def test_save_to_yaml_existing_file(self):
        """Test appending to existing YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test_prompts.yaml"
            
            # Create initial file
            save_to_yaml(yaml_file, "2024-01-01 11:00", "First prompt", "session1")
            
            # Append second prompt
            result = save_to_yaml(yaml_file, "2024-01-01 12:00", "Second prompt", "session2")
            
            assert result is True
            # TODO: Verify both prompts exist in file

    def test_save_to_yaml_error_handling(self):
        """Test YAML save error handling"""
        # TODO: Test with read-only directory or other error conditions
        pass

    @patch.dict(os.environ, {
        'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db',
        'CLAUDE_PROJECT_DIR': '/test/project'
    })
    @patch('save_user_prompt.get_postgres_connection')
    @patch('save_user_prompt.save_to_postgres')
    @patch('save_user_prompt.get_session_id')
    @patch('save_user_prompt.extract_repository_from_git')
    @patch('sys.stdin')
    def test_main_execution_flow_postgres_success(self, mock_stdin, mock_extract_repo, 
                                                   mock_get_session, mock_save_postgres, 
                                                   mock_get_connection):
        """Test main flow when PostgreSQL is available"""
        # Setup mocks
        mock_stdin.read.return_value = json.dumps({'prompt': 'Test prompt'})
        mock_stdin.buffer = Mock()
        mock_stdin.buffer.read.return_value = json.dumps({'prompt': 'Test prompt'}).encode()
        
        mock_conn = Mock()
        mock_get_connection.return_value = mock_conn
        mock_save_postgres.return_value = True
        mock_get_session.return_value = 'test-session-id'
        mock_extract_repo.return_value = 'github.com/user/repo'
        
        # Run main
        with patch('sys.stdin', new=mock_stdin):
            with patch('builtins.print'):
                save_user_prompt.main()
        
        # Verify PostgreSQL path was taken
        mock_get_connection.assert_called_once()
        mock_save_postgres.assert_called_once()
        mock_conn.close.assert_called_once()
        
        # Verify prompt_data structure
        call_args = mock_save_postgres.call_args[0]
        assert call_args[0] == mock_conn
        prompt_data = call_args[1]
        assert prompt_data['prompt'] == 'Test prompt'
        assert prompt_data['session_id'] == 'test-session-id'
        assert prompt_data['repository'] == 'github.com/user/repo'
        assert 'created_at' in prompt_data

    @patch.dict(os.environ, {
        'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db',
        'CLAUDE_PROJECT_DIR': '/test/project',
        'CLAUDE_SESSION_ID': 'yaml-session-id'
    })
    @patch('save_user_prompt.get_postgres_connection')
    @patch('save_user_prompt.save_to_yaml')
    @patch('sys.stdin')
    def test_main_execution_flow_postgres_fallback(self, mock_stdin, mock_save_yaml, 
                                                    mock_get_connection):
        """Test fallback to YAML when PostgreSQL fails"""
        # Setup mocks
        mock_stdin.read.return_value = json.dumps({'prompt': 'Test prompt'})
        mock_stdin.buffer = Mock()
        mock_stdin.buffer.read.return_value = json.dumps({'prompt': 'Test prompt'}).encode()
        
        # PostgreSQL connection fails
        mock_get_connection.return_value = None
        mock_save_yaml.return_value = True
        
        # Run main
        with patch('sys.stdin', new=mock_stdin):
            with patch('builtins.print'):
                save_user_prompt.main()
        
        # Verify YAML fallback was used
        mock_save_yaml.assert_called_once()
        call_args = mock_save_yaml.call_args[0]
        assert str(call_args[0]) == '/test/project/user_prompts.yaml'
        assert call_args[2] == 'Test prompt'  # prompt
        # session_id should come from environment or function

    @patch.dict(os.environ, {
        'CLAUDE_PROJECT_DIR': '/test/project',
        'CLAUDE_SESSION_ID': 'yaml-session-id'
    }, clear=True)
    @patch('save_user_prompt.save_to_yaml')
    @patch('save_user_prompt.get_postgres_connection')
    @patch('sys.stdin')
    def test_main_execution_flow_no_postgres_config(self, mock_stdin, mock_get_connection, 
                                                     mock_save_yaml):
        """Test YAML-only mode when no PostgreSQL config"""
        # Setup mocks
        mock_stdin.read.return_value = json.dumps({'prompt': 'Test prompt'})
        mock_stdin.buffer = Mock()
        mock_stdin.buffer.read.return_value = json.dumps({'prompt': 'Test prompt'}).encode()
        
        mock_save_yaml.return_value = True
        
        # Ensure env vars are set correctly
        os.environ['CLAUDE_PROJECT_DIR'] = '/test/project'
        os.environ['CLAUDE_SESSION_ID'] = 'yaml-session-id'
        
        # Run main
        with patch('sys.stdin', new=mock_stdin):
            with patch('builtins.print'):
                save_user_prompt.main()
        
        # Verify PostgreSQL was not attempted
        mock_get_connection.assert_not_called()
        
        # Verify YAML was used directly
        mock_save_yaml.assert_called_once()
        call_args = mock_save_yaml.call_args[0]
        assert str(call_args[0]) == '/test/project/user_prompts.yaml'
        assert call_args[2] == 'Test prompt'
    
    @patch.dict(os.environ, {
        'CLAUDE_POSTGRES_SERVER_DSN': 'postgresql://user:pass@localhost/db',
        'CLAUDE_PROJECT_DIR': '/test/project'
    })
    @patch('save_user_prompt.get_postgres_connection')
    @patch('save_user_prompt.save_to_postgres')
    @patch('save_user_prompt.save_to_yaml')
    @patch('sys.stdin')
    def test_main_execution_flow_postgres_insert_failure(self, mock_stdin, mock_save_yaml,
                                                          mock_save_postgres, mock_get_connection):
        """Test fallback to YAML when PostgreSQL insert fails"""
        # Setup mocks
        mock_stdin.read.return_value = json.dumps({'prompt': 'Test prompt'})
        mock_stdin.buffer = Mock()
        mock_stdin.buffer.read.return_value = json.dumps({'prompt': 'Test prompt'}).encode()
        
        mock_conn = Mock()
        mock_get_connection.return_value = mock_conn
        mock_save_postgres.return_value = False  # Insert fails
        mock_save_yaml.return_value = True
        
        # Run main
        with patch('sys.stdin', new=mock_stdin):
            with patch('builtins.print'):
                save_user_prompt.main()
        
        # Verify both were attempted
        mock_get_connection.assert_called_once()
        mock_save_postgres.assert_called_once()
        mock_save_yaml.assert_called_once()
        mock_conn.close.assert_called_once()