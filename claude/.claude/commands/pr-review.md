# Pull Request Review Instructions

Please conduct a comprehensive review of PR/MR $ARGUMENTS. Your task is to analyze the changes and provide detailed feedback on code quality, implementation scope, and testing strategy.

## Review Criteria

### 1. Implementation Scope Validation
- **Verify the PR/MR implements exactly what the issue requests** - no more, no less
- Check if any functionality outside the issue scope has been added or modified
- Ensure all requirements from the issue are addressed
- Flag any missing implementations or unnecessary additions

### 2. Test Quality Assessment
- **Eliminate redundant testing:**
  - Identify tests that cover the same scenarios (e.g., `test_empty_input` and `test_invalid_input` where empty is a subset of invalid)
  - Ensure each test case has a unique, meaningful purpose
  - Flag overlapping test coverage

- **Verify meaningful test implementation:**
  - Ensure tests actually exercise the code being tested
  - Identify over-mocked tests that bypass the actual implementation
  - Check that tests would fail if the implementation was broken
  - Validate that tests cover edge cases and error conditions

### 3. Code Quality and Duplication
- **Identify code duplication:**
  - Look for repeated logic that could be extracted into shared methods
  - Find similar patterns that could use common utilities or base classes
  - Suggest opportunities for code consolidation without sacrificing readability

- **Assess code organization:**
  - Verify appropriate separation of concerns
  - Check for consistent coding patterns and style
  - Ensure proper error handling and logging

## Review process

IMPORTANT: Following this process is non-negotiable. Your job depends on it.

1. Understand the scope of the issue, and use a dedicated agent to check whether the code changes address the scope. No more, no less. To fulfill "Review Criteria 1" from above.
2. Use the TodoWriter tool with dedicated agents to review every changed file in its own todo following the "Review Criteria 2-3" from above.
3. Post your findings as a comment to the PR/MR

## Review Output Format

Structure your review as a PR/MR comment with the following sections:

### 📋 Implementation Scope
- List whether the PR/MR fully implements the issue requirements
- Note any out-of-scope changes or missing functionality

### 🧪 Test Analysis
- Document any redundant or overlapping tests
- Identify tests that don't meaningfully exercise the code
- Suggest improvements for test coverage and quality

### 🔄 Code Quality
- Point out code duplication opportunities
- Recommend refactoring for better maintainability
- Note any architectural or design concerns

### 🎯 Overall Assessment
Conclude with one of:
- **✅ RECOMMENDED FOR MERGE**: The PR/MR meets all criteria and can be merged as-is
- **⚠️ CHANGES REQUIRED**: Specific issues must be addressed before merging

For "Changes Required" assessments, prioritize issues by impact:
- **Critical**: Must fix before merge (breaks functionality, major security issues)
- **Important**: Should fix before merge (code quality, maintainability)
- **Minor**: Could fix before merge (style, minor optimizations)

## Review Guidelines
- Be constructive and specific in feedback
- Provide code examples when suggesting improvements
- Consider the broader codebase context and patterns
- Focus on maintainability and long-term code health
- Do not modify any files - only provide commentary and suggestions
