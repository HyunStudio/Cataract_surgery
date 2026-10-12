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
