# Evals

This directory makes trigger quality and packaging quality more reproducible.

Contents:

- `trigger_cases.json`: full regression set with `family` labels
- `train/`, `dev/`, `holdout/`: split trigger suites for iterative tuning and final verification
- `blind_holdout/`: description-optimization acceptance prompts that do not participate in candidate ranking
- `adversarial/`: harder route-collision prompts for description optimization, including noisy positives and deceptive non-trigger requests
- `confusion/`: sibling-skill routing prompts used to catch route theft and false `no_route` decisions
- `semantic_config.json`: local semantic-intent concepts, exclusions, and weights
- `promotion_policy.md`: formal rules for when a route is promotable
- `baseline_description.txt`: intentionally weaker trigger description
- `improved_description.txt`: current stronger trigger description
- `../reports/description_optimization*.{json,md}`: generated route-optimization reports for the root skill
- `failure-cases.md`: current weak spots and regression targets
- `packaging_expectations.json`: required packaging behaviors for supported targets
- `../reports/`: generated suite JSON plus the homepage-visible family summary panel source

Use:

```bash
python3 scripts/trigger_eval.py --description-file evals/improved_description.txt --cases evals/trigger_cases.json
python3 scripts/trigger_eval.py --description-file evals/improved_description.txt --cases evals/trigger_cases.json --baseline-description-file evals/baseline_description.txt
python3 scripts/run_eval_suite.py
python3 scripts/judge_blind_eval.py --description-file SKILL.md --cases evals/blind_holdout/trigger_cases.json --semantic-config evals/semantic_config.json
python3 scripts/run_description_optimization_suite.py --history-snapshot-output evals/history/description_optimization/YYYY-MM-DD-adversarial-calibration-and-family-drift.json --snapshot-date YYYY-MM-DD --snapshot-id adversarial-calibration-and-family-drift --snapshot-label "Adversarial Calibration And Family Drift"
python3 scripts/build_confusion_matrix.py --history-snapshot-output evals/history/YYYY-MM-DD-route-scorecard-foundation.json --snapshot-date YYYY-MM-DD --snapshot-id route-scorecard-foundation --snapshot-label "Route Scorecard Foundation"
python3 scripts/render_eval_dashboard.py
python3 scripts/render_description_drift_history.py
python3 scripts/render_iteration_ledger.py
python3 tests/verify_description_optimization.py
python3 tests/verify_route_confusion.py
python3 tests/verify_failure_regressions.py
python3 scripts/cross_packager.py . --platform openai --platform claude --expectations evals/packaging_expectations.json --zip
python3 tests/verify_packager_failures.py
```

Regression scope now includes:

- direct positives
- direct negatives
- near neighbors
- long-context positives
- mixed-intent negatives
- explicit "do not build a skill" negatives
- semantic exclusion cases such as one-off, document-only, and future-outline prompts
- paraphrase families that avoid the original wording while preserving the same trigger intent
- long-context contamination cases where build intent or no-build intent appears after unrelated setup text
- family-based reporting across workflow-to-skill, iterate-existing-skill, document-only, one-off, and future-outline cases
- holdout verification
- description optimization reports that compare baseline, current, and optimized route wording across dev, holdout, blind holdout, and adversarial holdout gates
- judge-backed blind-holdout verification that adds a rubric-based second opinion for blind prompts
- calibration summaries that surface score gaps, threshold margins, and risk bands for each acceptance gate
- family-level drift history that records which blind and adversarial families stay clean over time
