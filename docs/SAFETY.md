# Safety, medical realism and release boundaries

OphthoSim-AI is an **educational interactive simulation**. It is not a medical device, clinical decision support system, operator credentialing tool, validated skill assessment or source of surgical instructions.

- All patient values, waveforms, complication likelihoods and tissue responses are synthetic abstractions.
- No anesthesia drug selection/dosing, actual surgical incision dimensions, device energy/flow parameters, procedural troubleshooting, or invasive clinical step-by-step instructions.
- Serious complications cause a pause and simulated escalation/abort options; no clinical rescue algorithms.
- Avoid interpreting "Winning" as patient outcome. Display "Simulation completed" and detailed synthetic metrics.
- Use no real patient records/images/identifiers without documented lawful rights, approvals and privacy review.
- Source all anatomical assets; verify content creator, licensing and redistribution rights.
- Clinical plausibility and educational value require subject matter expert review and prospective validation; keep an explicit unresolved assumptions log.
- Future human subject research needs appropriate ethics/IRB determination. Repository access does not constitute consent.

## v1.1 release review and escalation

- At every screen label synthetic data and interaction feedback clearly enough that real clinical numbers or advice cannot be mistaken for the simulator.
- Error handling must offer **pause / synthetic assistance / safe abort**; it must not punish cautious responses by automatically failing a case.
- Public demos should not present modeled complications or score as validated patient-outcome predictions.
- Third-party anatomical models, clinical images and audio require a provenance/licensing check before commit.
- New procedural realism requests go through scope review to ensure they remain educational abstractions rather than clinical operating instructions.

## v2 game rules and safety (2026-10-24)

- The timed safety hold penalizes only **inaction**. Assessing (A) or a safe abort (X) always stops the timer, and a safe abort is reported as a positive outcome. Tutorial mode has no timer. This follows the rule that cautious responses must never be punished.
- New events (pupil constriction, corneal haze, IOL decentration, wound-leak hold) present recognition tasks only. Their hints name game actions ("assess", "re-centre", "re-check"), never clinical procedures.
- Instrument names are labels for stage-bound game tools; no device behaviour, energy or flow settings exist.
- Score weights, tolerances and timers are design hypotheses. The results screen states that no patient outcome or clinical skill is implied.

## v3 additions (2026-10-24)

- The vitreous event and the capsule events are recognition tasks only: assessing them escalates to a safe stop. No rescue procedure is modelled or taught.
- Help requests are always available, logged, and never change the score.
- The `low_visibility` research condition is a study manipulation, kept separate from accessibility aids. It is recorded with every export.
- The synthetic patient card uses seeded identifiers (`SYN-####`) and labels ("Synthetic IOL A/B"). It contains no real names, measurements or lens powers.
