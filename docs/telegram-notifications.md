# Telegram Notifications for Claude Code

This document describes the Telegram notification integration for Claude Code hooks.

## Overview

The `telegram_notify.py` script sends notifications to a Telegram chat when Claude Code sessions end (Stop hook) or when notifications are triggered (Notification hook). This provides real-time updates about your Claude Code sessions directly to your Telegram.

## Features

- **Automatic notifications** on session end with Claude's last response
- **Rich message formatting** with Markdown support
- **Session context** including timestamp, project directory, and session ID
- **Graceful error handling** that won't interrupt Claude Code operations
- **Daily log rotation** with automatic cleanup
- **CLI support** for standalone testing and debugging

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "Claude Code Notifier")
4. Choose a username for your bot (must end in `bot`, e.g., `claude_code_notify_bot`)
5. Save the bot token provided by BotFather

### 2. Get Your Chat ID

1. Start a conversation with your new bot
2. Send any message to the bot
3. Open your browser and go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for the `"chat":{"id":` field - this is your chat ID

### 3. Configure Environment Variables

Add these to your shell configuration (`.bashrc`, `.zshrc`, etc.):

```bash
export CLAUDE_TELEGRAM_BOT_ID="your_bot_token_here"
export CLAUDE_TELEGRAM_CHAT_ID="your_chat_id_here"

# Optional: Set these if you want them in notifications
export CLAUDE_PROJECT_DIR="$PWD"  # Current project directory
export CLAUDE_SESSION_ID="custom_session_id"  # Session identifier
```

### 4. Install Dependencies

The script requires the `requests` library, which is installed automatically via the DevPod setup:

```bash
# If you need to install manually:
pip install requests
```

## Usage

### Automatic Hook Integration

Once configured, the script runs automatically when:
- A Claude Code session ends (Stop hook)
- A notification event occurs (Notification hook)

No manual intervention is required - notifications will be sent to your Telegram chat automatically.

### Manual/CLI Usage

You can also run the script manually for testing:

```bash
# Test with a custom message
python ~/.claude/scripts/telegram_notify.py --test "Test message from Claude Code"

# Process a specific transcript file
python ~/.claude/scripts/telegram_notify.py --transcript /path/to/transcript.jsonl

# Enable debug logging
python ~/.claude/scripts/telegram_notify.py --debug

# Show help
python ~/.claude/scripts/telegram_notify.py --help
```

## Message Format

Notifications appear in Telegram with the following format:

```
🤖 Claude Code Session Update

📝 Message:
[Claude's last response or your test message]

⏰ Time: 2024-12-20T15:30:45Z
📁 Project: /home/user/my-project
🔖 Session: session-123
```

## Logging

Logs are written to:
- Primary: `/var/log/claude_telegram_notifier/telegram_notify.log`
- Fallback: `~/claude_telegram_notifier.log` (if primary location isn't writable)

Logs rotate daily and are kept for 7 days. The logging system handles permission errors gracefully.

## Troubleshooting

### No notifications received

1. **Check environment variables:**
   ```bash
   echo $CLAUDE_TELEGRAM_BOT_ID
   echo $CLAUDE_TELEGRAM_CHAT_ID
   ```

2. **Test manually:**
   ```bash
   python ~/.claude/scripts/telegram_notify.py --test "Debug test"
   ```

3. **Check logs:**
   ```bash
   # Check primary log location
   tail -f /var/log/claude_telegram_notifier/telegram_notify.log
   
   # Or fallback location
   tail -f ~/claude_telegram_notifier.log
   ```

### Common Issues

- **Missing environment variables**: The script will exit silently. Check that both `CLAUDE_TELEGRAM_BOT_ID` and `CLAUDE_TELEGRAM_CHAT_ID` are set.
- **Network errors**: The script handles network failures gracefully and logs errors without interrupting Claude Code.
- **Invalid bot token**: Verify your bot token with BotFather.
- **Wrong chat ID**: Ensure you're using the correct chat ID from the getUpdates API.

## Security Considerations

- **Keep your bot token secret**: Never commit it to version control
- **Use environment variables**: Don't hardcode credentials in scripts
- **Restrict bot access**: Consider making your bot private or limiting who can interact with it
- **Review logs regularly**: Check for any unusual activity or errors

## Technical Details

### Hook Integration

The script is integrated via `claude/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${HOME}/.venv_dotfiles/bin/python ${HOME}/.claude/scripts/telegram_notify.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${HOME}/.venv_dotfiles/bin/python ${HOME}/.claude/scripts/telegram_notify.py"
          }
        ]
      }
    ]
  }
}
```

### Transcript Processing

The script:
1. Reads Claude Code transcripts in JSONL format
2. Extracts the last assistant message
3. Formats it with context information
4. Sends to Telegram via Bot API

### Error Handling

All errors are handled gracefully:
- Missing environment variables → Silent exit (code 1)
- Network failures → Logged and exit (code 1)
- Malformed transcripts → Logged and exit (code 1)
- No errors interrupt Claude Code operations

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/claude/scripts/

# Run unit tests only
python -m pytest tests/claude/scripts/test_telegram_notify.py

# Run BDD tests only
python -m pytest tests/claude/scripts/steps/

# Run with coverage
python -m pytest tests/claude/scripts/ --cov=claude/.claude/scripts/telegram_notify
```

### Contributing

When modifying the script:
1. Maintain backward compatibility
2. Add tests for new features
3. Update this documentation
4. Ensure silent failure behavior is preserved

## License

This integration is part of the Claude Code dotfiles configuration and follows the same license as the parent repository.