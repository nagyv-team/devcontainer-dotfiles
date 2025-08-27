Feature: Store LLM output in PostgreSQL database
  Store Claude Code assistant responses in a PostgreSQL database for analysis and monitoring purposes.
  The system should extract LLM outputs from transcript files, parse metadata, and persist to database
  when Stop hook is triggered.

  Background:
    Given a PostgreSQL database with llm_outputs table is available
    And the database connection is configured via environment variables
    And Claude Code generates transcript files in JSONL format
    And the Stop hook is configured to trigger the save_llm_output.py script

  Scenario: Successfully save LLM output with full metadata
    Given a transcript file exists with a valid assistant message
    And the assistant message contains text content and usage statistics
    And the PostgreSQL connection is available
    And all required environment variables are set
    When the Stop hook is triggered with the transcript path
    Then the LLM output should be saved to the llm_outputs table
    And the record should contain the assistant message text
    And the record should contain input_tokens from usage statistics
    And the record should contain output_tokens from usage statistics
    And the record should contain the model name
    And the record should contain the service_tier
    And the record should contain the session_id
    And the record should contain the repository information
    And the record should contain the current timestamp

  Scenario: Save LLM output with minimal required data
    Given a transcript file exists with an assistant message
    And the assistant message contains only text content without usage statistics
    And the PostgreSQL connection is available
    When the Stop hook is triggered with the transcript path
    Then the LLM output should be saved to the llm_outputs table
    And the record should contain the assistant message text
    And the optional fields (input_tokens, output_tokens, model, service_tier) should be null
    And the required fields (id, created_at, output) should be populated

  Scenario: Handle empty transcript file gracefully
    Given a transcript file exists but contains no assistant messages
    And the PostgreSQL connection is available
    When the Stop hook is triggered with the transcript path
    Then no record should be inserted into the llm_outputs table
    And the script should exit with success status
    And a warning should be logged about no assistant message found

  Scenario: Handle malformed transcript file
    Given a transcript file exists but contains invalid JSON
    And the PostgreSQL connection is available
    When the Stop hook is triggered with the transcript path
    Then no record should be inserted into the llm_outputs table
    And the script should continue processing valid lines
    And malformed lines should be skipped with debug logging

  Scenario: Handle missing transcript file
    Given the transcript file path does not exist
    When the Stop hook is triggered with the invalid transcript path
    Then no record should be inserted into the llm_outputs table
    And the script should exit with error status
    And an error should be logged about missing transcript file

  Scenario: Handle PostgreSQL connection failure
    Given a transcript file exists with a valid assistant message
    And the PostgreSQL connection configuration is invalid
    When the Stop hook is triggered with the transcript path
    Then the script should attempt database connection
    And the connection should fail with appropriate error logging
    And the script should exit with error status
    And no fallback mechanism should be attempted

  Scenario: Handle missing PostgreSQL environment variables
    Given a transcript file exists with a valid assistant message
    And no PostgreSQL environment variables are configured
    When the Stop hook is triggered with the transcript path
    Then the script should detect missing configuration
    And the script should exit with error status
    And an error should be logged about missing database configuration

  Scenario: Parse session_id from hook input
    Given a transcript file exists with a valid assistant message
    And the hook input JSON contains a session_id field
    And the PostgreSQL connection is available
    When the Stop hook is triggered
    Then the session_id from hook input should be used
    And the session_id should be saved in the database record

  Scenario: Extract repository information from git context
    Given a transcript file exists with a valid assistant message
    And the hook input JSON contains a cwd field pointing to a git repository
    And the git repository has a valid origin remote
    And the PostgreSQL connection is available
    When the Stop hook is triggered
    Then the repository information should be extracted from git remote
    And the repository should be saved in normalized format (host/user/repo)
    And the repository should be saved in the database record

  Scenario: Handle git repository without remote
    Given a transcript file exists with a valid assistant message
    And the hook input JSON contains a cwd field pointing to a git repository
    And the git repository has no origin remote configured
    And the PostgreSQL connection is available
    When the Stop hook is triggered
    Then the repository field should be null in the database record
    And the script should continue with successful execution

  Scenario: Process transcript with multiple assistant messages
    Given a transcript file exists with multiple assistant messages
    And each message has different content and metadata
    And the PostgreSQL connection is available
    When the Stop hook is triggered with the transcript path
    Then only the last assistant message should be saved
    And the database should contain exactly one record for this session