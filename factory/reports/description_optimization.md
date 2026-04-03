# Root Description Optimization

Winner: `Current`

- current tokens: `65`
- winner tokens: `65`
- baseline tokens: `8`

## Winner

Create, refactor, evaluate, and package agent skills from workflows, prompts, transcripts, docs, or notes. Use when asked to create a skill, turn a repeated process into a reusable skill, improve an existing skill, add evals, or package a skill for team reuse.

## Candidate Ranking

| Candidate | Tokens | Dev FP | Dev FN | Dev Near | Holdout FP | Holdout FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Current` | 65 | 0 | 0 | 1.0 | 0 | 0 |
| `Minimal` | 41 | 2 | 1 | 0.857 | 0 | 0 |
| `Balanced` | 54 | 2 | 1 | 0.857 | 0 | 0 |
| `Artifact Aware` | 72 | 2 | 1 | 0.857 | 0 | 0 |
| `Boundary` | 78 | 2 | 1 | 0.857 | 0 | 0 |
| `Guardrail` | 50 | 5 | 1 | 0.429 | 2 | 0 |

## Acceptance Gates

| Gate | Winner FP | Winner FN | Current FP | Current FN | Baseline FP | Baseline FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Holdout | 0 | 0 | 0 | 0 | 0 | 0 |
| Blind Holdout | 0 | 0 | 0 | 0 | 0 | 0 |
| Judge Blind Holdout | 0 | 0 | 0 | 0 | 0 | 0 |
| Adversarial Holdout | 0 | 0 | 0 | 0 | 0 | 0 |

## Calibration

| Gate | Winner Gap | Winner Risk | Winner Boundary Rate | Current Gap | Baseline Gap |
| --- | ---: | --- | ---: | ---: | ---: |
| Holdout | 0.468 | healthy | 0.0 | 0.468 | 0.416 |
| Blind Holdout | 0.366 | watch | 0.333 | 0.366 | 0.369 |
| Adversarial Holdout | 0.834 | healthy | 0.0 | 0.834 | 0.845 |

## Judge Blind Summary

| Gate | Winner Agreement | Winner Mean Confidence | Current Agreement | Baseline Agreement |
| --- | ---: | ---: | ---: | ---: |
| Judge Blind Holdout | 1.0 | 0.66 | 1.0 | 1.0 |

## Family Health

| Gate | Winner Clean Families | Winner Weakest Family | Current Clean Families | Baseline Clean Families |
| --- | --- | --- | --- | --- |
| Holdout | 12/12 | workflow_to_skill (0 errors) | 12/12 | 12/12 |
| Blind Holdout | 6/6 | blind_operationalize (0 errors) | 6/6 | 6/6 |
| Judge Blind Holdout | 6/6 | blind_operationalize (0 errors) | 6/6 | 6/6 |
| Adversarial Holdout | 6/6 | adversarial_summary_translation_collision (0 errors) | 6/6 | 6/6 |

## Selection Logic

Ordered by:
- fewest false positives
- fewest false negatives
- highest near-neighbor pass rate
- highest negative pass rate
- highest precision
- highest recall
- shortest description
