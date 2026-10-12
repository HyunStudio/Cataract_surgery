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
