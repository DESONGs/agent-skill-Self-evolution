#!/usr/bin/env python3
import argparse
from pathlib import Path


SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

## Workflow

1. Understand the request.
2. Execute the main task.
3. Validate the result.
"""


INTERFACE_TEMPLATE = """interface:
  display_name: "{title}"
  short_description: "{short_description}"
  default_prompt: "Use ${name} to ..."
compatibility:
  canonical_format: "agent-skills"
  adapter_targets:
    - "openai"
    - "claude"
    - "generic"
  activation:
    mode: "manual"
    paths: []
  execution:
    context: "inline"
    shell: "bash"
  trust:
    source_tier: "local"
    remote_inline_execution: "forbid"
    remote_metadata_policy: "allow-metadata-only"
  degradation:
    openai: "metadata-adapter"
    claude: "neutral-source-plus-adapter"
    generic: "neutral-source"
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a minimal skill package.")
    parser.add_argument("name", help="skill folder and frontmatter name")
    parser.add_argument("--description", default="Describe what the skill does and when to use it.")
    parser.add_argument("--title", default=None)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    title = args.title or args.name.replace("-", " ").title()
    root = Path(args.output_dir).resolve() / args.name
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "references").mkdir(exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=args.name, description=args.description, title=title), encoding="utf-8")
    (root / "agents" / "interface.yaml").write_text(
        INTERFACE_TEMPLATE.format(name=args.name, title=title, short_description=args.description[:80]),
        encoding="utf-8",
    )
    print(str(root))


if __name__ == "__main__":
    main()
