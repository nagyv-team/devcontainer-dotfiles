---
command: issue-breakdown-setup
description: Break down a refined issue into deliverable tasks with code skeletons
arguments:
  - name: issue-number
    description: The issue number to break down (e.g., 15 for issue #15)
    required: true
---

# Issue Breakdown and Setup

This command takes a refined GitHub/GitLab issue $ARGUMENTS, then breaks it down into deliverable tasks with code skeletons.

## Prerequisites

Before running this command, ensure the following exist:
- `./issues/issue-$ARGUMENTS/architect-plan.md` - The architectural plan for the issue

## Process

### 1. Create Dedicated Branch

First, create and checkout a dedicated branch for the issue:

```bash
git checkout -b issue-$ARGUMENTS
```

### 2. Analyze the Architectural Plan

IMPORTANT: This is a crucial step to succesfully follow the user's instructions!

Read and understand the architectural plan:

```bash
cat ./issues/issue-$ARGUMENTS/architect-plan.md
```

Remember ALL the details:
- Component structure and dependencies
- Method signatures and interfaces
- Data flow and integration points
- Testing requirements

IMPORTANT: You will need to use every information from the architect plan document. The contents of the architect plan document is VERY IMPORTANT!

### 3. Set Up Code Skeletons

Based on the architect plan, create code skeletons for all the new and modified codepaths with:
- Proper method signatures from the plan
- Comprehensive documentation (docstrings) for every method
- Type-compliant dummy implementations

Example skeleton structure:
```python
def process_receipt(receipt_data: ReceiptData) -> ProcessingResult:
    """
    Process uploaded receipt data and extract relevant information.
    
    Args:
        receipt_data: The receipt data to process
        
    Returns:
        ProcessingResult containing extracted information
        
    Raises:
        ValidationError: If receipt data is invalid
        ProcessingError: If processing fails
    """
    # Dummy return for type compliance
    return ProcessingResult(
        items=[],
        total=0.0,
        status="pending"
    )
```

### 4. Break Down into Deliverable Tasks

Analyze the architectural plan to create tasks that:
- Can be delivered within a day
- Can be reviewed in under 1 hour
- Own specific methods/classes from start to finish
- Have clear dependencies

Task criteria:
- **Size**: 1-3 files, 50-200 lines of code
- **Scope**: Single responsibility, clear boundaries
- **Testability**: Can be tested independently
- **Dependencies**: No coupling with other tasks

### 5. Create Delivery Plan

Generate `./issues/issue-$ARGUMENTS/delivery-plan.md` with:

<delivery-plan>
# Delivery Plan for Issue #$ARGUMENTS

## Task Breakdown

#### Task 1: [Task Name]
**Files**: `path/to/file.py`
**Methods/Classes**: 
- `ClassName.method_name()` - [Brief description]
- `function_name()` - [Brief description]

**Acceptance Criteria**:
- [ ] Implementation complete with all `TODO for task 1` implemented and removed from the codebase
- [ ] Unit tests pass with >95% coverage

**Estimated Time**: 4 hours

#### Task 2: [Task Name]
[Similar structure as Task 1]

#### Task 3: [Task Name]

[Task details...]

#### Task 4: [Task Name]

[Task details...]

#### Task 5: [Task Name]

[Task details for each...]

#### Task 6: [Task Name]

[Task details for each...]

#### Task 7: [Task Name]

[Task details for each...]

## Delivery Order (Bitshift Format)

```
Task_1 | Task_2
↓
Task_3 >> Task_4
↓
Task_5 | Task_6
↓
Task_7
```
</delivery-plan>

### 6. Assign code segments to tasks

IMPORTANT: Follow the task breakdown from the previous step!

Update all code skeletons with specific task assignments using `TODO for task X` comments

```python
def process_receipt(receipt_data: ReceiptData) -> ProcessingResult:
    """
    Process uploaded receipt data and extract relevant information.
    
    Args:
        receipt_data: The receipt data to process
        
    Returns:
        ProcessingResult containing extracted information
        
    Raises:
        ValidationError: If receipt data is invalid
        ProcessingError: If processing fails
    """
    # TODO for task 2: Implement receipt processing logic
    # - Parse receipt format
    # - Extract line items
    # - Calculate totals
    # - Validate data consistency
    
    # Dummy return for type compliance
    return ProcessingResult(
        items=[],
        total=0.0,
        status="pending"
    )
```

## Rules

Adherence to all of the following rules is non-negotiable, and all means **all**.

- **Understand the scope:**
  The scope is clearly defined with all the requirements in `./issues/issue-$ARGUMENTS/architect-plan.md`. Think hard to understand the scope of the work and where it should be implemented in the codebase.
- **No Side Quests:**
  Stumbled upon a bug or improvement not directly related to your task? Let the human know and decide what to do with it. Don't get distracted.
- **No Side Quests #2:**
  The requirements are defined in `./issues/issue-$ARGUMENTS/architect-plan.md`. Do not add any more user-facing functionality or requirements! Keep the scope of the issue.
- **Follow the architect:**
  Create, modify, remove files and methods only as described in the architect plan.
- **Single file output:**
  The only output created should be `./issues/issue-$ARGUMENTS/delivery-plan.md`. Do NOT write any other files!
- **Follow the process and the rules:**
  Follow the process from above and these rules to fulfill the user's request

## Example Usage

```bash
# For issue #15 about receipt upload validation
claude-code "/issue-breakdown-setup 15"
```

This will:
1. Create branch `issue-15`
2. Read `./issues/issue-15/architect-plan.md`
3. Create code skeletons based on the plan
4. Generate `./issues/issue-15/delivery-plan.md` with a description of the tasks and dependencies
