# Static material separation before scalar witness proposals

Inline investigation, full simulator scope unchanged. Current full native blade
route session21538 is frozen at d665ac5 and must not be modified/restarted.
Rejected local face-reuse prototype did not reliably improve owned179 after
complete request/result ownership. Need fewer expensive scalar proposals.

Proposed certificate: every fine face is a positive normalized convex combination
of three original control points. For a face/body pair, if one axis of the
control hull is farther from both finite-axis endpoints than radius +0.02 plus
conservative rounding enclosure, the rounded proposal gap cannot seed the
normal candidate (gap<0.02) or violate original gap1e-9. Still validate every
source face/material row and all body inputs; never skip malformed/degenerate
far geometry. No dynamic cache. No omitted full-motion or original-force checks.

Before production changes: independent review of the numerical enclosure and
failure behavior. A bare heuristic epsilon is insufficient. Derive a rigorous
finite-input operation bound or use outward/exact interval operations. Test
threshold boundary/cancellation, malformed far geometry and last-body cases;
compare every accepted/rejected pair to Fraction/high-precision geometry and
existing scalar proposals. Only integrate if owned complete state/results stay
bitwise identical and repeated measured cost improves materially.

This plan is investigation, not a passing certificate or an adopted optimization.
All original force/gap/complementarity/work limits and complete-case gates stay.

Read-only review confirms unresolved proof obligations: native rounded affine
coordinates can exceed exact control hull; relative native degeneracy is
stronger than Godot area>0; separation does not automatically preserve scalar
status on ill-conditioned cases. DEFERRED, no production filtering adopted.
Next implemented approach will batch unchanged scalar queries for all pairs,
so it needs no omitted-pair certificate and preserves existing failure gates.
