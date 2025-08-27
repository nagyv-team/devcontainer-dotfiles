#!/usr/bin/env python3
"""
Unit tests for PostgreSQL integration functions in save_llm_output.py
"""
import os
import sys
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import pytest

# Add the scripts directory to the path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../claude/.claude/scripts'))

import save_llm_output


class TestGetPostgresConnection:
    """Test cases for get_postgres_connection function"""

    def test_connection_with_dsn(self, monkeypatch):
        """Test successful connection using DSN environment variable"""
        # Clear all postgres env vars first
        for key in ['CLAUDE_POSTGRES_SERVER_DSN', 'CLAUDE_POSTGRES_SERVER_HOST_PORT', 
                   'CLAUDE_POSTGRES_SERVER_USER', 'CLAUDE_POSTGRES_SERVER_PASS', 
                   'CLAUDE_POSTGRES_SERVER_DB_NAME']:
            monkeypatch.delenv(key, raising=False)
        
        # Set up environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DSN', 
                          'postgresql://user:pass@host:5432/dbname?sslmode=require')
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        mock_conn = Mock()
        mock_psycopg.connect.return_value = mock_conn
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result == mock_conn
            mock_psycopg.connect.assert_called_once()
            # Check that connect was called with proper arguments
            assert mock_psycopg.connect.call_args[1]['connect_timeout'] == 5
            call_args = mock_psycopg.connect.call_args[0][0]
            assert 'sslmode=require' in call_args

    def test_connection_with_dsn_adds_ssl(self, monkeypatch):
        """Test that SSL is added to DSN if not present"""
        # Set up environment without sslmode
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DSN', 
                          'postgresql://user:pass@host:5432/dbname')
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        mock_conn = Mock()
        mock_psycopg.connect.return_value = mock_conn
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert SSL was added
            assert result == mock_conn
            call_args = mock_psycopg.connect.call_args[0][0]
            assert 'sslmode=require' in call_args

    def test_connection_with_individual_env_vars(self, monkeypatch):
        """Test successful connection using individual environment variables"""
        # Clear all postgres env vars first
        for key in ['CLAUDE_POSTGRES_SERVER_DSN', 'CLAUDE_POSTGRES_SERVER_HOST_PORT', 
                   'CLAUDE_POSTGRES_SERVER_USER', 'CLAUDE_POSTGRES_SERVER_PASS', 
                   'CLAUDE_POSTGRES_SERVER_DB_NAME']:
            monkeypatch.delenv(key, raising=False)
        
        # Set up environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_HOST_PORT', 'localhost:5432')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_USER', 'testuser')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_PASS', 'testpass')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DB_NAME', 'testdb')
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        mock_conn = Mock()
        mock_psycopg.connect.return_value = mock_conn
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result == mock_conn
            call_args = mock_psycopg.connect.call_args[0][0]
            assert 'host=localhost' in call_args
            assert 'port=5432' in call_args
            assert 'dbname=testdb' in call_args
            assert 'user=testuser' in call_args
            assert 'password=testpass' in call_args
            assert 'sslmode=require' in call_args
            assert 'connect_timeout=5' in call_args

    def test_connection_with_host_only(self, monkeypatch):
        """Test connection with host only (no port specified)"""
        # Clear all postgres env vars first
        for key in ['CLAUDE_POSTGRES_SERVER_DSN', 'CLAUDE_POSTGRES_SERVER_HOST_PORT', 
                   'CLAUDE_POSTGRES_SERVER_USER', 'CLAUDE_POSTGRES_SERVER_PASS', 
                   'CLAUDE_POSTGRES_SERVER_DB_NAME']:
            monkeypatch.delenv(key, raising=False)
        
        # Set up environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_HOST_PORT', 'localhost')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_USER', 'testuser')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_PASS', 'testpass')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DB_NAME', 'testdb')
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        mock_conn = Mock()
        mock_psycopg.connect.return_value = mock_conn
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert default port is used
            assert result == mock_conn
            call_args = mock_psycopg.connect.call_args[0][0]
            assert 'host=localhost' in call_args
            assert 'port=5432' in call_args  # Default PostgreSQL port

    def test_no_postgres_config(self, monkeypatch):
        """Test when no PostgreSQL configuration is present"""
        # Clear all postgres env vars
        for key in list(os.environ.keys()):
            if 'CLAUDE_POSTGRES' in key:
                monkeypatch.delenv(key, raising=False)
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result is None

    def test_missing_individual_env_vars(self, monkeypatch):
        """Test when some individual env vars are missing"""
        # Clear all postgres env vars first
        for key in ['CLAUDE_POSTGRES_SERVER_DSN', 'CLAUDE_POSTGRES_SERVER_HOST_PORT', 
                   'CLAUDE_POSTGRES_SERVER_USER', 'CLAUDE_POSTGRES_SERVER_PASS', 
                   'CLAUDE_POSTGRES_SERVER_DB_NAME']:
            monkeypatch.delenv(key, raising=False)
        
        # Set up partial environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_HOST_PORT', 'localhost:5432')
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_USER', 'testuser')
        # Missing PASS and DB_NAME
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result is None

    def test_psycopg_not_installed(self, monkeypatch):
        """Test when psycopg module is not installed"""
        # Set up environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DSN', 
                          'postgresql://user:pass@host:5432/dbname')
        
        # Remove psycopg from modules to simulate it not being installed
        with patch.dict('sys.modules', {'psycopg': None}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result is None

    def test_connection_failure(self, monkeypatch):
        """Test when database connection fails"""
        # Set up environment
        monkeypatch.setenv('CLAUDE_POSTGRES_SERVER_DSN', 
                          'postgresql://user:pass@host:5432/dbname')
        
        # Create mock psycopg module
        mock_psycopg = Mock()
        mock_psycopg.connect.side_effect = Exception("Connection refused")
        
        # Mock the import of psycopg within the function
        with patch.dict('sys.modules', {'psycopg': mock_psycopg}):
            # Call function
            result = save_llm_output.get_postgres_connection()
            
            # Assert
            assert result is None


class TestExtractRepositoryFromGit:
    """Test cases for extract_repository_from_git function"""

    def test_extract_from_ssh_url(self, monkeypatch):
        """Test extracting repository from SSH URL"""
        # Mock subprocess.run
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'git@github.com:user/repo.git'
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result == 'github.com/user/repo'
            mock_run.assert_called_once_with(
                ['git', 'remote', 'get-url', 'origin'],
                cwd='/path/to/repo',
                capture_output=True,
                text=True,
                timeout=5
            )

    def test_extract_from_https_url(self):
        """Test extracting repository from HTTPS URL"""
        # Mock subprocess.run
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'https://github.com/user/repo.git'
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result == 'github.com/user/repo'

    def test_extract_from_https_url_without_git_suffix(self):
        """Test extracting repository from HTTPS URL without .git suffix"""
        # Mock subprocess.run
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'https://github.com/user/repo'
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result == 'github.com/user/repo'

    def test_extract_with_claude_project_dir(self, monkeypatch):
        """Test using CLAUDE_PROJECT_DIR when no cwd provided"""
        monkeypatch.setenv('CLAUDE_PROJECT_DIR', '/project/dir')
        
        # Mock subprocess.run
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'git@github.com:user/repo.git'
            mock_run.return_value = mock_result
            
            # Call function without cwd
            result = save_llm_output.extract_repository_from_git()
            
            # Assert
            assert result == 'github.com/user/repo'
            mock_run.assert_called_once_with(
                ['git', 'remote', 'get-url', 'origin'],
                cwd='/project/dir',
                capture_output=True,
                text=True,
                timeout=5
            )

    def test_no_cwd_or_env_var(self, monkeypatch):
        """Test when no cwd provided and CLAUDE_PROJECT_DIR not set"""
        monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)
        
        # Call function
        result = save_llm_output.extract_repository_from_git()
        
        # Assert
        assert result is None

    def test_git_command_failure(self):
        """Test when git command fails"""
        # Mock subprocess.run with failure
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'not a git repository'
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result is None

    def test_no_origin_remote(self):
        """Test when no origin remote is configured"""
        # Mock subprocess.run with empty output
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ''
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result is None

    def test_unparseable_url(self):
        """Test when git remote URL cannot be parsed"""
        # Mock subprocess.run with unusual URL
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'file:///local/repo.git'
            mock_run.return_value = mock_result
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result is None

    def test_git_command_timeout(self):
        """Test when git command times out"""
        # Mock subprocess.run with timeout
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('git', 5)
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result is None

    def test_unexpected_exception(self):
        """Test when an unexpected exception occurs"""
        # Mock subprocess.run with exception
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Unexpected error")
            
            # Call function
            result = save_llm_output.extract_repository_from_git('/path/to/repo')
            
            # Assert
            assert result is None


class TestSaveLlmOutputToPostgres:
    """Test cases for save_llm_output_to_postgres function"""

    def test_successful_save_with_all_fields(self):
        """Test successful save with all fields populated"""
        # Create mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Prepare test data
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test LLM output text',
            'session_id': 'test-session-123',
            'repository': 'github.com/user/repo',
            'input_tokens': 100,
            'output_tokens': 200,
            'model': 'claude-opus-4-1',
            'service_tier': 'standard'
        }
        
        # Call function
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        # Check SQL query
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        assert 'INSERT INTO llm_outputs' in query
        assert 'created_at, output, session_id, repository' in query
        assert 'input_tokens, output_tokens, model, service_tier' in query
        
        # Check parameters
        params = call_args[0][1]
        assert params[0] == llm_data['created_at']
        assert params[1] == llm_data['output']
        assert params[2] == llm_data['session_id']
        assert params[3] == llm_data['repository']
        assert params[4] == llm_data['input_tokens']
        assert params[5] == llm_data['output_tokens']
        assert params[6] == llm_data['model']
        assert params[7] == llm_data['service_tier']
        
        mock_conn.commit.assert_called_once()

    def test_successful_save_with_minimal_fields(self):
        """Test successful save with only required fields"""
        # Create mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Prepare test data with minimal fields
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test LLM output text'
        }
        
        # Call function
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        # Assert
        assert result is True
        
        # Check parameters - optional fields should be None
        params = mock_cursor.execute.call_args[0][1]
        assert params[0] == llm_data['created_at']
        assert params[1] == llm_data['output']
        assert params[2] is None  # session_id
        assert params[3] is None  # repository
        assert params[4] is None  # input_tokens
        assert params[5] is None  # output_tokens
        assert params[6] is None  # model
        assert params[7] is None  # service_tier

    def test_no_connection(self):
        """Test when no connection is provided"""
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test output'
        }
        
        # Call function with None connection
        result = save_llm_output.save_llm_output_to_postgres(None, llm_data)
        
        # Assert
        assert result is False

    def test_database_error(self):
        """Test when database operation fails"""
        # Create mock connection with error
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn = Mock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test output'
        }
        
        # Call function
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        # Assert
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_rollback_failure(self):
        """Test when both insert and rollback fail"""
        # Create mock connection with errors
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn = Mock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.rollback.side_effect = Exception("Rollback failed")
        
        llm_data = {
            'created_at': datetime.now(),
            'output': 'Test output'
        }
        
        # Call function
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        # Assert - should still return False
        assert result is False

    def test_parameterized_query(self):
        """Test that query uses parameterized values (prevents SQL injection)"""
        # Create mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Prepare test data with potential SQL injection attempt
        llm_data = {
            'created_at': datetime.now(),
            'output': "'; DROP TABLE llm_outputs; --",
            'session_id': "' OR '1'='1"
        }
        
        # Call function
        result = save_llm_output.save_llm_output_to_postgres(mock_conn, llm_data)
        
        # Assert
        assert result is True
        
        # Check that values are passed as parameters, not embedded in query
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        # Query should use placeholders
        assert '%s' in query
        assert "DROP TABLE" not in query
        assert "OR '1'='1" not in query
        
        # Dangerous values should be in parameters
        assert params[1] == "'; DROP TABLE llm_outputs; --"
        assert params[2] == "' OR '1'='1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])