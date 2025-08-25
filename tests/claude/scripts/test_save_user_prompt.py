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

# Add parent directory to path to import save_user_prompt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'claude', '.claude', 'scripts'))
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
    })
    @patch('psycopg.connect')
    def test_get_postgres_connection_with_individual_vars(self, mock_connect):
        """Test PostgreSQL connection using individual environment variables"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
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
    
    @patch.dict(os.environ, {'CLAUDE_POSTGRES_SERVER_HOST_PORT': 'localhost'})
    @patch('psycopg.connect')
    def test_get_postgres_connection_default_port(self, mock_connect):
        """Test default port 5432 is used when not specified"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Set other required vars
        os.environ['CLAUDE_POSTGRES_SERVER_USER'] = 'user'
        os.environ['CLAUDE_POSTGRES_SERVER_PASS'] = 'pass'
        os.environ['CLAUDE_POSTGRES_SERVER_DB_NAME'] = 'db'
        
        result = get_postgres_connection()
        
        # Verify default port was used
        call_args = mock_connect.call_args[0][0]
        assert 'port=5432' in call_args
        assert result == mock_conn

    def test_save_to_postgres_success(self):
        """
        TODO for task 3: Test successful insert to PostgreSQL
        - Mock connection and cursor
        - Verify parameterized query used
        - Verify all fields inserted correctly
        - Assert True returned
        """
        pass

    def test_save_to_postgres_sql_injection_prevention(self):
        """
        TODO for task 3: Test SQL injection prevention
        - Provide malicious input in prompt_data
        - Verify parameterized query prevents injection
        """
        pass

    def test_save_to_postgres_null_fields(self):
        """
        TODO for task 3: Test handling of NULL optional fields
        - Provide prompt_data with None values for optional fields
        - Verify NULL values handled correctly
        """
        pass

    def test_save_to_postgres_failure_handling(self):
        """
        TODO for task 3: Test insert failure handling
        - Mock cursor.execute to raise exception
        - Verify False returned (not exception raised)
        """
        pass

    def test_extract_repository_from_git_github(self):
        """
        TODO for task 3: Test GitHub repository extraction
        - Mock subprocess.run to return GitHub URL
        - Verify correct parsing to github.com/user/repo format
        """
        pass

    def test_extract_repository_from_git_gitlab(self):
        """
        TODO for task 3: Test GitLab repository extraction
        - Mock subprocess.run to return GitLab URL
        - Verify correct parsing to gitlab.com/org/project format
        """
        pass

    def test_extract_repository_from_git_ssh_format(self):
        """
        TODO for task 3: Test SSH format repository URL parsing
        - Mock subprocess.run to return git@github.com:user/repo.git
        - Verify correct parsing
        """
        pass

    def test_extract_repository_from_git_no_origin(self):
        """
        TODO for task 3: Test handling when no origin remote exists
        - Mock subprocess.run to return error
        - Verify None returned
        """
        pass

    def test_extract_repository_from_git_not_repository(self):
        """
        TODO for task 3: Test handling when not in git repository
        - Mock subprocess.run to return error
        - Verify None returned
        """
        pass

    def test_get_session_id_valid_uuid(self):
        """
        TODO for task 3: Test valid UUID session ID extraction
        - Mock environment variable with valid UUID
        - Verify UUID returned
        """
        pass

    def test_get_session_id_invalid_format(self):
        """
        TODO for task 3: Test invalid session ID format handling
        - Mock environment variable with invalid UUID
        - Verify None returned
        """
        pass

    def test_get_session_id_not_present(self):
        """
        TODO for task 3: Test missing session ID handling
        - No session_id in environment
        - Verify None returned
        """
        pass

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

    def test_main_execution_flow_postgres_success(self):
        """
        TODO for task 4: Test main flow when PostgreSQL is available
        - Mock stdin with prompt data
        - Mock PostgreSQL connection success
        - Mock save_to_postgres success
        - Verify PostgreSQL path taken
        - Verify correct log messages
        """
        pass

    def test_main_execution_flow_postgres_fallback(self):
        """
        TODO for task 4: Test fallback to YAML when PostgreSQL fails
        - Mock stdin with prompt data
        - Mock PostgreSQL connection failure
        - Verify YAML fallback path taken
        - Verify correct log messages
        """
        pass

    def test_main_execution_flow_no_postgres_config(self):
        """
        TODO for task 4: Test YAML-only mode when no PostgreSQL config
        - Mock stdin with prompt data
        - No PostgreSQL environment variables set
        - Verify YAML path taken directly
        - Verify correct log messages
        """
        pass