Feature: PostgreSQL-backed user prompt storage with YAML fallback

  Background:
    Given the save_user_prompt.py script exists
    And the user_prompts table exists in PostgreSQL with the correct schema
    And the script supports both PostgreSQL and YAML storage mechanisms

  Scenario: Successfully save prompt to PostgreSQL using DSN
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    And the CLAUDE_PROJECT_DIR is set to a git repository with origin remote "https://github.com/user/repo"
    When the script is executed with a user prompt "How do I implement authentication?"
    Then the prompt should be inserted into the user_prompts table
    And the created_at field should contain the current timestamp
    And the prompt field should contain "How do I implement authentication?"
    And the repository field should contain "github.com/user/repo"
    And the session_id field should be populated if available
    And the database connection should use SSL/TLS
    And an info-level log message should indicate successful PostgreSQL storage

  Scenario: Successfully save prompt to PostgreSQL using individual environment variables
    Given the CLAUDE_POSTGRES_SERVER_HOST_PORT environment variable is set to "localhost:5432"
    And the CLAUDE_POSTGRES_SERVER_USER environment variable is set to "testuser"
    And the CLAUDE_POSTGRES_SERVER_PASS environment variable is set to "testpass"
    And the CLAUDE_POSTGRES_SERVER_DB_NAME environment variable is set to "testdb"
    And the PostgreSQL server is available and accessible
    And the CLAUDE_PROJECT_DIR is set to a git repository with origin remote "https://gitlab.com/org/project"
    When the script is executed with a user prompt "Debug this function"
    Then the prompt should be inserted into the user_prompts table using parameterized queries
    And the repository field should contain "gitlab.com/org/project"
    And the database connection should use SSL/TLS
    And an info-level log message should indicate successful PostgreSQL storage

  Scenario: DSN takes precedence over individual environment variables
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the CLAUDE_POSTGRES_SERVER_HOST_PORT environment variable is also set
    And the CLAUDE_POSTGRES_SERVER_USER environment variable is also set
    And the PostgreSQL server is available and accessible
    When the script is executed with a user prompt "Test precedence"
    Then the script should use the DSN connection string
    And the prompt should be successfully stored in PostgreSQL
    And an info-level log message should indicate PostgreSQL storage was used

  Scenario: Fallback to YAML when PostgreSQL connection fails
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is not available or connection fails
    And the user_prompts.yaml file exists or can be created
    When the script is executed with a user prompt "This should fallback"
    Then the script should silently fall back to YAML storage
    And the prompt should be appended to user_prompts.yaml
    And the YAML structure should be preserved
    And an info-level log message should indicate fallback to YAML storage occurred
    And no error should be displayed to the user

  Scenario: Use YAML when no PostgreSQL environment variables are set
    Given no CLAUDE_POSTGRES_* environment variables are set
    And the user_prompts.yaml file exists or can be created
    When the script is executed with a user prompt "Default to YAML"
    Then the script should use YAML storage directly
    And the prompt should be appended to user_prompts.yaml
    And the existing YAML file structure should be preserved
    And an info-level log message should indicate YAML storage was used

  Scenario: Handle repository detection from git context
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    And the CLAUDE_PROJECT_DIR is set to a git repository
    And the git repository has an origin remote set to "git@github.com:owner/repo.git"
    When the script is executed with a user prompt "Test repository detection"
    Then the repository field should be extracted from the git remote
    And the repository field should contain "github.com/owner/repo"
    And the prompt should be successfully stored in PostgreSQL

  Scenario: Handle missing repository information gracefully
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    And the CLAUDE_PROJECT_DIR is not set or does not point to a git repository
    When the script is executed with a user prompt "No repository context"
    Then the repository field should be NULL or empty
    And the prompt should still be successfully stored in PostgreSQL
    And an info-level log message should indicate successful storage

  Scenario: Validate and handle long prompt text
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    When the script is executed with a user prompt containing 10,000 characters
    Then the prompt should be successfully stored in the text field without truncation
    And the data should be properly escaped to prevent SQL injection
    And an info-level log message should indicate successful storage

  Scenario: Handle special characters and SQL injection prevention
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    When the script is executed with a user prompt containing "'; DROP TABLE user_prompts; --"
    Then the prompt should be safely stored using parameterized queries
    And the malicious SQL should be treated as literal text in the prompt field
    And the user_prompts table should remain intact
    And an info-level log message should indicate successful storage

  Scenario: Handle session_id when provided
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    And a session_id "550e8400-e29b-41d4-a716-446655440000" is available in the environment
    When the script is executed with a user prompt "Session-aware prompt"
    Then the session_id field should contain "550e8400-e29b-41d4-a716-446655440000"
    And the prompt should be successfully stored in PostgreSQL
    And an info-level log message should indicate successful storage

  Scenario: Handle missing session_id gracefully
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server is available and accessible
    And no session_id is available in the environment
    When the script is executed with a user prompt "No session context"
    Then the session_id field should be NULL or empty
    And the prompt should still be successfully stored in PostgreSQL
    And an info-level log message should indicate successful storage

  Scenario: Maintain YAML fallback functionality during partial PostgreSQL failure
    Given the CLAUDE_POSTGRES_SERVER_DSN environment variable is set to a valid PostgreSQL connection string
    And the PostgreSQL server connection succeeds initially
    And the INSERT operation fails due to database constraints or temporary issues
    When the script is executed with a user prompt "Fallback on insert failure"
    Then the script should fall back to YAML storage
    And the prompt should be appended to user_prompts.yaml
    And an info-level log message should indicate fallback due to insert failure
    And no error should be displayed to the user

  Scenario: Preserve existing YAML structure during fallback operations
    Given an existing user_prompts.yaml file with multiple entries
    And the CLAUDE_POSTGRES_SERVER_DSN environment variable is set but PostgreSQL is unavailable
    When the script is executed with a user prompt "Preserve structure"
    Then the new prompt should be appended to the existing YAML file
    And the existing YAML entries should remain unchanged
    And the YAML file structure should be valid and parseable
    And an info-level log message should indicate YAML fallback was used