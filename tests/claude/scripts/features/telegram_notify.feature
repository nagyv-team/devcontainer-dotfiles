Feature: Telegram Notification Integration for Claude Code Hooks
  Sends formatted notifications to Telegram when Claude Code Stop or Notification hooks are triggered,
  enabling remote monitoring of Claude Code instances.

  Background:
    Given the telegram_notify.py script is located at "claude/.claude/scripts/telegram_notify.py"
    And the log directory "/var/log/claude_telegram_notifier/" exists
    And the Claude Code hooks are configured in "claude/.claude/settings.json"

  Scenario: Successfully send Telegram notification with valid configuration
    Given the environment variable "CLAUDE_TELEGRAM_BOT_ID" is set to "123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQr"
    And the environment variable "CLAUDE_TELEGRAM_CHAT_ID" is set to "-1001234567890"
    And Claude Code generates a transcript with assistant message content
    And the Telegram Bot API is accessible and responding
    When the Stop hook is triggered
    Then a Telegram message should be sent to the configured chat
    And the message should contain Claude's last response text
    And the message should include an ISO timestamp
    And the message should include the project directory path
    And the message should include the session ID if available
    And the message should be formatted using Markdown
    And the operation should be logged as successful

  Scenario: Successfully send Telegram notification via Notification hook
    Given the environment variable "CLAUDE_TELEGRAM_BOT_ID" is set to "123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQr"
    And the environment variable "CLAUDE_TELEGRAM_CHAT_ID" is set to "-1001234567890"
    And Claude Code generates a transcript with assistant message content
    And the Telegram Bot API is accessible and responding
    When the Notification hook is triggered
    Then a Telegram message should be sent to the configured chat
    And the message format should be identical to Stop hook messages
    And the operation should be logged as successful

  Scenario: Parse Claude transcript and extract last assistant message
    Given a Claude Code transcript in JSONL format
    And the transcript contains multiple entries with different message types
    And the last assistant message has content at "message.content[0].text" path
    When the script processes the transcript
    Then it should extract the text from the last assistant message
    And it should ignore user messages and tool results
    And it should handle the JSONL format correctly

  Scenario: Handle missing environment variables gracefully
    Given the environment variable "CLAUDE_TELEGRAM_BOT_ID" is not set
    When the script is executed
    Then it should exit silently without sending any notification
    And it should log the missing environment variable error
    And it should not interrupt Claude Code operations

  Scenario: Handle missing chat ID environment variable gracefully
    Given the environment variable "CLAUDE_TELEGRAM_BOT_ID" is set to "123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQr"
    And the environment variable "CLAUDE_TELEGRAM_CHAT_ID" is not set
    When the script is executed
    Then it should exit silently without sending any notification
    And it should log the missing chat ID error
    And it should not interrupt Claude Code operations

  Scenario: Handle Telegram API unavailability
    Given the environment variables are properly configured
    And Claude Code generates a valid transcript
    And the Telegram Bot API is unreachable or returning errors
    When the script attempts to send a notification
    Then it should fail silently without raising exceptions
    And it should log the API failure with detailed error information
    And it should not interrupt Claude Code operations