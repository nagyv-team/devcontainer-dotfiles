---
name: implement-task-with-minimal-context
description: Implement a task from a task.md file
---

# Implement Task with Minimal Context

## Usage
```bash
claude "/implement-task-with-minimal-context task N of issue X"
```

## Instructions

You are tasked with implementing the exact scope described in $ARGUMENTS. Follow these strict guidelines:

### 1. Branch Management

Your are expected to work on a dedicated task branch in the form of `tasks/issue-X-task-N`

- Switch to the task branch before starting any work if you are not there already

### 2. Implementation Requirements
- Read $ARGUMENTS using the issues MCP tool - it describes what you need to implement
- **Deliver EXACTLY what is specified** in the task - nothing more, nothing less
- Implement all files and methods listed under **Files** and **Methods/Classes**
- Implement all realted `TODO for task X` comments and remove the TODO comments as you implement them
- Complete ALL acceptance criteria listed
- Do NOT edit any other code, or you'll likely cause merge conflicts and a lot of headaches for others
- Use dedicated agents to implement single changes

### 3. Testing Strategy
- **Write tests alongside implementation** - not after
- Follow **London-school TDD**:
  - Mock all external dependencies in unit tests
  - Test behavior, not implementation details
  - Use test doubles (mocks, stubs) for collaborators
- Ensure test coverage meets the requirements (typically >95% for unit tests)
- Run tests frequently during development

IMPORTANT: All unit tests should pass!

### 4. Code Quality Standards
- **Error handling**: Add proper try-catch blocks and error logging
- **Logging**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- **Code style**: Match the existing codebase conventions
  - Use the known linters for code formatting
  - Follow existing patterns for similar components
- **Type hints**: Add proper type annotations where applicable

### 5. Validation Steps
Before considering the task complete:
1. Run all tests and ensure they pass:
   Example:
   ```bash
   pytest tests/ -v --cov=src --cov-report=term
   ```
2. Run code quality checks
3. Verify all acceptance criteria are met
4. Confirm all TODOs for the task are removed

### 6. Git Workflow
1. **Commit regularly** with clear, descriptive messages
2. **Push the task branch** to remote:
   ```bash
   git push -u origin {task-branch-name}
   ```
3. **Create a Pull/Merge Request** targeting the issue branch:
   - Title: "Task {number}: {brief description}"
   - Description: List completed acceptance criteria
   - Target branch: `issue-<issue number>`
   - **DO NOT MERGE** the PR

### 7. Task Boundaries
- **ONLY implement what's in the task file**
- Do not refactor unrelated code
- Do not add features not specified
- Do not fix bugs outside the task scope
- If dependencies on other tasks exist, mock them appropriately

### Example Workflow
```bash
# 1. Start on issue branch
git checkout issue-11

# 2. Create task branch
git checkout -b tasks/issue-11-task-2

# 3. Implement the task following TDD in sub-agents
- Write failing test
- Implement minimal code to pass
- Refactor if needed
- Repeat

# 4. Run tests frequently
pytest tests/unit/test_hook_data_service.py -v

# 5. Check code quality
black src/ tests/
mypy src/ tests/

# 6. Commit and push
git add .
git commit -m "Implement hook data service layer with filtering and pagination"
git push -u origin issue-10-task-2

# 7. Create PR/MR
glab mr create --title "Task 2: Hook Data Service Implementation" \
  --description "Implemented service layer for hook data access with filtering" \
  --target-branch issue-10
```

## Important Notes
- Each task is independent and should be completed in isolation
- Focus on delivering exactly what's specified - no more, no less
- Tests are not optional - they're part of the implementation
- The PR is for review purposes - merging is handled separately
- If blocked by dependencies, use mocks rather than waiting or adding dummy implementations

## Task File Structure Reference
Task files typically contain:
- **Files**: List of files to create/modify
- **Methods/Classes**: Specific components to implement
- **Acceptance Criteria**: Checklist of requirements
- **Estimated Time**: Reference for scope
- **Notes**: Additional context or constraints

Focus on completing all acceptance criteria while maintaining high code quality and test coverage.
