# devcontainer-dotfiles

A dotfiles repository used with DevPod to initialize the user environment for development

## Workflow

DevPod:
1. builds the devcontainer
2. runs `./install.sh` as the container user

## Claude Code configuration

Configures various hooks, commands and agents

### Hook scripts

Scripts for the hooks are under `./claude/.claude/scripts`. Related tests are under `./tests/claude/scripts`. 

Python scripts might need various Python packages. Maintain a single `./requirements.txt` file for all the scripts.
Create a virtualenv in the home directory, under `~/.venv_dotfiles`.

## Testing

- Bash scripts don't need testing
- Python files need to be tested
  - unit tests with pytest
  - BDD tests with pytest-bdd
  - use `./requirements-dev.txt` for development-only packages
