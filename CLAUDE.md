# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a dotfiles repository for DevPod environments that configures Claude Code with custom hooks, commands, and agents for enhanced development workflows.

## Installation and Setup

The repository is designed to be installed via DevPod, which runs `./install.sh` as the container user. The installation:
- Copies dotfiles to the home directory via `bin/copy_dotfiles.sh`
- Installs Claude Code docs and project index tools
- Sets up git global configuration
- Sets up a Python virtualenv for the Python scripts

## Project Structure

- `bin/` - Shell scripts for setup and requirements management
- `claude/.claude/` - Claude Code configuration files
  - `agents/` - Custom agent definitions (python-backend-architect, bdd-test-engineer, react-native-architect)
  - `commands/` - Custom slash commands for various workflows
  - `scripts/` - Hook scripts (e.g., save_user_prompt.py, telegram_notify.py)
  - `settings.json` - Hook configurations
- `docs/` - Documentation for features and integrations
  - `telegram-notifications.md` - Setup guide for Telegram notifications
- `home/` - User home directory configurations

## Python Development

- Python scripts require packages maintained in `./requirements.txt`
- Development packages go in `./requirements-dev.txt`
- Use virtualenv at `~/.venv_dotfiles` for script dependencies

## Testing Requirements

- Bash scripts: No testing required
- Python files: Must include tests
  - Unit tests using pytest
  - BDD tests using pytest-bdd
  - Test files go under `./tests/claude/scripts/`

## Key Commands

```bash
# Run installation (typically done by DevPod)
./install.sh

# Copy dotfiles to home directory
bash ./bin/copy_dotfiles.sh
```

## Hook System

The repository configures Claude Code hooks via `claude/.claude/settings.json`:
- UserPromptSubmit hook: Saves user prompts using `save_user_prompt.py`
- Notification hook: Uses `say` command for audio notifications and sends Telegram notifications via `telegram_notify.py`
- Stop hook: Sends Telegram notifications when sessions end using `telegram_notify.py`

## Important Guidelines

When working on deliverable tasks, always use a dedicated sub-agent to verify completion through appropriate validation methods (tests, Puppeteer, etc.).