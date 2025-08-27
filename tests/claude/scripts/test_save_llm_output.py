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
from unittest.mock import Mock, patch, mock_open, MagicMock
import pytest
from io import StringIO

# Add the script directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'claude' / '.claude' / 'scripts'))

import save_llm_output


class TestParseHookInput:
    """Test cases for parse_hook_input function"""
    
    def test_valid_hook_input(self):
        """Test parsing valid hook input with all fields"""
        hook_data = {
            "session_id": "abc123",
            "transcript_path": "~/.claude/projects/test/transcript.jsonl",
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "cwd": "/workspaces/project"
        }
        
        with patch('sys.stdin', StringIO(json.dumps(hook_data))):
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
                "content": []
            }
        }
        
        result = save_llm_output.extract_llm_metadata(assistant_message)
        
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


class TestIntegration:
    """Integration tests for the complete extraction flow"""
    
    def test_full_extraction_flow(self):
        """Test the complete flow from hook input to metadata extraction"""
        # Create a transcript file
        transcript_content = '''{"type": "user", "message": {"content": "Test question"}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test response"}], "model": "claude-3", "usage": {"input_tokens": 10, "output_tokens": 20, "service_tier": "standard"}}, "sessionId": "test-session"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(transcript_content)
            temp_path = f.name
        
        try:
            # Simulate hook input
            hook_data = {
                "session_id": "test-session",
                "transcript_path": temp_path,
                "hook_event_name": "Stop"
            }
            
            with patch('sys.stdin', StringIO(json.dumps(hook_data))):
                parsed_hook = save_llm_output.parse_hook_input()
            
            # Read transcript
            assistant_message = save_llm_output.read_transcript_file(parsed_hook['transcript_path'])
            assert assistant_message is not None
            
            # Extract metadata
            metadata = save_llm_output.extract_llm_metadata(assistant_message)
            assert metadata['output'] == "Test response"
            assert metadata['model'] == "claude-3"
            assert metadata['input_tokens'] == 10
            assert metadata['output_tokens'] == 20
            assert metadata['service_tier'] == "standard"
            
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])