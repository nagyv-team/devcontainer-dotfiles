# GitHub Issue Bugfix

Fix a specific GitHub issue following a structured workflow.

## Workflow

Your ONLY goal is to fix the specific issue provided. Do NOT work on side projects, additional features, or other bugs you might discover.

### 1. Issue Analysis
- Read and analyze the GitHub issue from `$ARGUMENTS`
- Extract the issue number and key details
- Understand the exact problem described
- Note any reproduction steps provided

### 2. Branch Creation
- Create a new branch: `issue-<id>` (where `<id>` is the GitHub issue number)
- Switch to this branch before making any changes

### 3. Issue Reproduction

Use a dedicated agent:

- Write minimal tests that reproduce the specific issue described
- Focus ONLY on the reported bug - do not test for other potential issues
- Ensure the test fails with the current codebase
- Commit the reproduction test with message: `test: reproduce issue #<id>`
- Push the reproduction code

### 4. Fix Proposal
- Analyze the root cause of the issue
- Create a detailed proposal for the fix
- Document your findings and approach

### 5. Documentation
- Update the GitHub issue with:
  - Confirmation that the issue has been reproduced
  - Root cause analysis
  - Proposed fix approach
  - Any relevant technical details

### 6. Approval Wait
- Wait for 30 minutes for user approval of the fix approach
- Continue automatically if:
  - User approves the approach, OR
  - 30 minutes pass without user feedback

### 7. Implementation

Use a dedicated agent:

- Implement the minimal fix for the specific issue
- Ensure your fix passes the reproduction test
- Run existing tests to verify no regressions
- Do NOT add extra features or fix unrelated issues

### 8. Final Steps
- Commit the fix with message: `fix: resolve issue #<id> - <brief description>`
- Push the fix
- Create a Pull Request with:
  - Clear title: "Fix: <issue title> (#<id>)"
  - Description linking to the original issue
  - Summary of changes made
  - Any future improvements noted (but not implemented)

## Important Constraints

- **STAY FOCUSED**: Only work on the specific bug reported
- **NO SIDE PROJECTS**: Don't fix other issues you discover
- **NO FEATURE ADDITIONS**: Don't add missing functionality
- **MINIMAL CHANGES**: Make the smallest change that fixes the issue
- **TEST ONLY THE BUG**: Write tests only for reproducing the reported issue

## Example

```bash
/bugfix #123
```

This will:
1. Analyze issue #123 related to the current repository
2. Create branch `issue-123`
3. Write reproduction test
4. Document findings in the issue
5. Wait for approval (30 min max)
6. Implement the fix
7. Create PR linking to issue #123

---

Remember: Your goal is surgical precision - fix the reported bug with minimal, focused changes.
