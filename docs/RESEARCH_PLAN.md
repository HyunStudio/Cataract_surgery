# Research plan — HSI and reproducible performance assessment

**Question:** Do adaptive, accessible visual interfaces improve performance on controlled *simulated* cataract microsurgery interaction tasks compared with a baseline UI?

## Research artifacts
- Fully specified simulation tasks and event seeds
- Deterministic action event logs (no patient data)
- Metrics: normalized path length, target error, task time, near-miss count, complication-alert recognition latency, pause decisions, IOL alignment score
- Accessibility conditions: baseline vs enlarged/high-contrast/reduced-motion layouts
- Plots, notebooks, preregistered hypotheses (when applicable), dataset dictionary and reproduction instructions

## Design sequence
1. Establish *instrument reliability*: repeated scripted sessions yield identical outputs.
2. Validate *content plausibility* with ophthalmology/HSI domain experts, recording disagreements.
3. Baseline models: unassisted UI with mouse movement tasks and scripted synthetic users.
4. If conducting real participant studies, seek institutional human-research/IRB determination **before recruitment or study data collection**.
5. For approved user studies, compare within-subject conditions with counterbalanced order, calibrated screen/input, predeclared primary metric, uncertainty intervals and limitations.
6. Report negative findings and dataset leakage checks. Do not claim improved surgery skill based solely on in-game scores.

## GitHub portfolio evidence
English README, annotated demo, reproducible synthetic data, CI tests, issue roadmap, commit history, design trade-off log and technically grounded failure analysis.

## Honest positioning
This is a computer-interaction research prototype and public software engineering project, **not** a validated surgery trainer or guarantee of PhD admissions advantage. No personal clinical history or protected health data should be in repository.

## v1.1 methodological improvement

### Hypotheses and primary endpoint (provisional)
H1: In a controlled *simulated* target-positioning task, adjustable high contrast and magnification alter normalized target error relative to baseline UI.
**Primary metric:** mean normalized endpoint error over identical scripted target trials, with error normalized to target radius. Do not select outcome after seeing data. **Secondary:** completion time, path efficiency, near-misses, missed alerts, subjective usability (only with appropriately approved recruitment).

### Bias control
Counterbalance condition order; use matched difficulty seeds and identical display/input device; separate practice and evaluation trials; log UI condition, scaling, resolution, input sampling rate and scenario version. Perform analysis on held-out scenario seeds, not seeds used to tune the scoring algorithm. Synthetic agents validate instrumentation only, NOT actual human benefits.

### Statistics and reproducibility
Document participant inclusion/exclusion, missingness, effect sizes and uncertainty intervals before collection; provide paired comparisons when design warrants. If no participant data exist, report only technical reliability and synthetic scenario results. Add a model card for any future AI scoring system: training provenance, risk of domain shift, evaluation split, failure modes and no clinical generalization claim.

### IRB and privacy
Seek research ethics determination before recruiting participants or collecting behavioral study data where required; do not assume public GitHub, anonymous telemetry or student status bypasses review. Local-only logs by default, opt-in study collection only after approvals and consent. Avoid collecting real medical histories.

## Implementation status (2026-10-24)

| Plan item | Implementation |
|---|---|
| Deterministic tasks, seeds, action logs | event traces, verified replays, `experiments.py` |
| Metrics | Normalized path length (`action_path`), target error (`endpoint_error_*`, normalized to target radius = **primary metric**), task time (`phase_time_s`), near misses, recognition latency, pause decisions, IOL alignment |
| Conditions | baseline vs enlarged (zoom/UI scale), high contrast, reduced motion, and the research condition `low_visibility`; all logged in `ui_conditions` |
| Practice vs evaluation, held-out seeds | `splits` in experiment configs, overlap rejected as leakage |
| Logging of UI condition, scaling, resolution, scenario version | `report.json → ui_conditions`, `scenario_version`, `session_id` |
| Instrument reliability (step 1) | every batch run verifies every replay; `examples/experiment_split.json` |
| Dataset dictionary | `docs/DATA_DICTIONARY.md` |
| Baseline strategies | scripted agents: ideal, careless, slow, unresponsive |

Not done (needs people): expert content review, IRB determination, any participant study.
