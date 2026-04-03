---
name: github-pr-review
description: Review GitHub pull requests and produce actionable feedback when the user asks for PR review.
version: 1.0.0
tags:
  - github
  - review
category: code-review
owner: platform-agent-team
status: active
---

# GitHub PR Review

Review pull requests with a bounded workflow.

## Router Rules

- Use when the user asks to review a GitHub pull request.
- Do not use for issue triage or release planning.

## Compact Workflow

1. Inspect the pull request context.
2. Run the declared review action.
3. Produce a concise review summary.

## Output Contract

- Return findings with file references.
- Return a short risk summary.
