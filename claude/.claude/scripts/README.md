# Claude Code Scripts

This directory contains scripts that integrate with Claude Code hooks to provide additional functionality.

## Available Scripts

### telegram_notify.py

Sends notifications to Telegram when Claude Code sessions end or when notification events occur.

**Usage:**
- Automatically triggered by Stop and Notification hooks
- Can be run manually for testing: `python telegram_notify.py --test "Test message"`

**Requirements:**
- Environment variables: `CLAUDE_TELEGRAM_BOT_ID` and `CLAUDE_TELEGRAM_CHAT_ID`
- Python package: `requests`

**Documentation:** See [/docs/telegram-notifications.md](/docs/telegram-notifications.md) for detailed setup and usage instructions.

### save_user_prompt.py

Saves user prompts from Claude Code sessions for later analysis or review.

**Usage:**
- Automatically triggered by UserPromptSubmit hook
- Processes Claude Code transcript to extract and save user prompts

## Hook Configuration

Scripts are integrated via `claude/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${HOME}/.venv_dotfiles/bin/python ${HOME}/.claude/scripts/save_user_prompt.py"
          }
        ]
      }
    ],
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

## Development

### Testing

All Python scripts should have comprehensive tests:

```bash
# Run all script tests
python -m pytest tests/claude/scripts/

# Run tests for a specific script
python -m pytest tests/claude/scripts/test_telegram_notify.py
```

### Adding New Scripts

When adding new hook scripts:

1. **Create the script** in this directory
2. **Add tests** in `tests/claude/scripts/`
3. **Update hook configuration** in `settings.json`
4. **Document usage** in this README and/or dedicated docs
5. **Handle errors gracefully** - scripts should never interrupt Claude Code operations

### Best Practices

- **Silent failures**: Scripts should exit with appropriate codes without raising exceptions
- **Logging**: Use Python's logging module with rotation for long-running scripts
- **Environment variables**: Use for configuration rather than hardcoding values
- **Testing**: Include both unit tests and BDD tests where appropriate
- **Documentation**: Keep documentation up-to-date with any changes

## Troubleshooting

### Scripts not executing

1. Check hook configuration in `settings.json`
2. Verify script has execute permissions
3. Check Python virtualenv is properly set up
4. Review logs for error messages

### Common Issues

- **Module not found**: Ensure dependencies are installed in `~/.venv_dotfiles`
- **Permission denied**: Check file permissions and log directory access
- **Environment variables**: Verify required variables are set in your shell configuration