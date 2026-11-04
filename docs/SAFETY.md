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

## v3 instruments, bleeding and patient model (2026-10-24)

Owner decision (2026-10-24): the procedure is to be **implemented like real surgery**:
the real step order, the real instrument for each step and situation, bleeding, and a
synthetic patient with conditions and drug classes. This supersedes the v2 rule that
hints name only game actions. Boundaries that still apply:

- No device energy, vacuum, flow or bottle-height values, and no drug names with doses.
  Patient charts list drug *classes* only (anticoagulant, alpha-1 blocker).
- Management is shown as "which instrument, where". There are no clinical rescue
  algorithms, timings or thresholds that could be read as treatment guidance.
- Every patient is synthetic. Vital-sign targets and bleeding severity are game
  hypotheses and are not calibrated to clinical data.
- Calling senior help (`B`) and stopping safely (`X`) are always available. A safe stop
  remains a positive outcome. A failure happens only after an unattended hold, or when
  the surgeon carries on through a major complication.
- Third-party 3D models load only with a manifest naming the source, author and a
  redistributable licence (`assets/models/README.md`). Non-commercial or
  no-derivatives licences are refused.

## v4 3D operating room (2026-10-24)

- Equipment is generic. No manufacturer names, logos or product designs (microscope,
  phaco console, monitors) are reproduced.
- The phaco console shows relative bars for irrigation, ultrasound, vacuum and flow. It
  shows no power, vacuum or flow numbers; a test checks that the console text contains
  no digits.
- The scene, people and displays only read the Game. Changing the view never changes
  rules, scores or replays, and mouse surgery is accepted only in the microscope view.
- Renders are synthetic procedural images, not photographs or clinical imagery.
