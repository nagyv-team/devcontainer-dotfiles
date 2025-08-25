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
from unittest.mock import Mock, patch, MagicMock
import tempfile

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

    def test_get_postgres_connection_with_dsn(self):
        """
        TODO for task 2: Test PostgreSQL connection using DSN
        - Mock environment variable CLAUDE_POSTGRES_SERVER_DSN
        - Mock psycopg3.connect
        - Verify SSL/TLS configuration
        - Assert connection object returned
        """
        pass

    def test_get_postgres_connection_with_individual_vars(self):
        """
        TODO for task 2: Test PostgreSQL connection using individual environment variables
        - Mock CLAUDE_POSTGRES_SERVER_HOST_PORT
        - Mock CLAUDE_POSTGRES_SERVER_USER
        - Mock CLAUDE_POSTGRES_SERVER_PASS
        - Mock CLAUDE_POSTGRES_SERVER_DB_NAME
        - Mock psycopg3.connect
        - Verify connection string construction
        - Assert connection object returned
        """
        pass

    def test_get_postgres_connection_dsn_precedence(self):
        """
        TODO for task 2: Test that DSN takes precedence over individual variables
        - Set both DSN and individual environment variables
        - Verify DSN is used
        """
        pass

    def test_get_postgres_connection_ssl_enabled(self):
        """
        TODO for task 2: Test that SSL/TLS is always enabled
        - Verify 'sslmode=require' in connection parameters
        """
        pass

    def test_get_postgres_connection_failure_handling(self):
        """
        TODO for task 2: Test connection failure handling
        - Mock connection to raise exception
        - Verify None is returned (not exception raised)
        """
        pass

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