# Packaging Contracts

`cross_packager.py` is not just an export helper. It defines and validates platform contracts.

## Current Targets

- `openai`
- `claude`
- `generic`

## Contract Shape

Each target contract defines:

- required output fields
- required output files
- field mapping from the neutral source metadata
- portable execution metadata
- trust-boundary metadata
- degradation strategy metadata

## Failure Handling

When `--expectations` is provided:

- missing required files cause exit code `2`
- missing required fields cause exit code `2`
- validation failures are emitted in the JSON report

## Source Of Truth

The neutral source remains:

- `SKILL.md`
- `agents/interface.yaml`

Target-specific metadata is generated at packaging time.

## Portability Model

The packaging layer now preserves four portable semantics from the neutral source:

- activation
- execution
- trust
- degradation

This means portability is not just "can it export a file?" but also "does the exported target preserve the source package's activation and safety assumptions?"
