"""Prompts for direct (non-DAG) execution."""

import json

DIRECT_EXECUTOR_PROMPT = """You are completing a task directly using available tools.

## Instructions
1. Analyze the task requirements carefully
2. Use available tools to complete the task
3. Save all outputs to the specified output directory
4. Use absolute paths when referencing files
"""


def build_working_dir_section(working_dir: str) -> str:
    """Build the working directory constraint section for prompts."""
    if not working_dir:
        return ""
    return f"""
## Working Directory
Your working directory is: {working_dir}
**IMPORTANT**: All file operations MUST be performed within this directory or its subdirectories.
Do NOT create or modify files outside of this directory.
"""


def build_direct_executor_prompt(task: str, output_dir: str, working_dir: str = "") -> str:
    """Build prompt for direct Claude execution without skills."""
    working_dir_section = build_working_dir_section(working_dir)

    return f"""{DIRECT_EXECUTOR_PROMPT}

## Task
{task}
{working_dir_section}
## Output Directory
Save all generated files to: {output_dir}

After completing the task, provide a summary in this format:
<execution_summary>
STATUS: SUCCESS or FAILURE
1. What was accomplished (or what went wrong if failed)
2. Key output files created
3. Any notes or recommendations
</execution_summary>

**Important**: Set STATUS to FAILURE only if the core task objective could not be achieved despite retries.
"""


def build_action_selection_prompt(
    *,
    task: str,
    action_catalog: list[dict],
    working_dir: str,
    output_dir: str,
    prior_steps: list[dict] | None = None,
    max_steps: int = 6,
) -> str:
    """Build a strict JSON prompt for selecting the next declared action."""

    working_dir_section = build_working_dir_section(working_dir)
    prior_steps = prior_steps or []
    catalog_json = json.dumps(action_catalog, indent=2, ensure_ascii=False)
    prior_steps_json = json.dumps(prior_steps, indent=2, ensure_ascii=False)

    return f"""You are selecting the next declared skill action for a task.

You MAY ONLY choose from the actions in the provided catalog.
You MUST NOT invent skills, actions, scripts, tools, or shell commands.
If the task is complete, return a finish decision.

## Task
{task}
{working_dir_section}
## Output Directory
Save all generated files to: {output_dir}

## Available Action Catalog
```json
{catalog_json}
```

## Prior Steps
```json
{prior_steps_json}
```

## Rules
1. Select at most one action.
2. Only use `skill_id` and `action_id` values present in the catalog.
3. `input` must be a JSON object.
4. If no more declared action is needed, return `status=finish`.
5. Never output prose outside JSON.
6. Keep the plan within {max_steps} total steps.

## Output Format
```json
{{
  "status": "select" | "finish",
  "skill_id": "skill-id",
  "action_id": "action-id",
  "input": {{}},
  "summary": "short reason"
}}
```
"""


def build_instruction_execution_prompt(
    *,
    task: str,
    instruction: str,
    output_dir: str,
    working_dir: str,
    artifacts_context: str = "",
) -> str:
    """Build prompt for executing an instruction action with regular tools only."""

    working_dir_section = build_working_dir_section(working_dir)
    artifacts_section = artifacts_context or "None"

    return f"""{DIRECT_EXECUTOR_PROMPT}

## Task
{task}
{working_dir_section}
## Output Directory
Save all generated files to: {output_dir}

## Instruction Payload
{instruction}

## Available Artifacts
{artifacts_section}

Follow the instruction payload exactly, using only declared tools and the files available in the working directory.

After completing the task, provide a summary in this format:
<execution_summary>
STATUS: SUCCESS or FAILURE
1. What was accomplished (or what went wrong if failed)
2. Key output files created
3. Any notes or recommendations
</execution_summary>
"""
