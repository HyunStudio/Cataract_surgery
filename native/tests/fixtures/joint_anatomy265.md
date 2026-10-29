# New consistent-history265 anatomy request

This is distinct from the older joint_trajectory265_boundary.json whose prior
state was already penetrating the actual iris. Full optional extraction
uvp7et92 on c70f532 accepts264ticks with the new unilateral model, then265
rejects atomically at100outer iterations (native_joint_solve/status1).
Retained area5.31932634674013, zero cut loss, broken edges and accepted
uncertainty; integration_steps remains264. Extension force3.29753427e-6,
energy1.04255175e-6, gap~1e-14/complementarity~4e-14. No physical gate was relaxed.

The exact checkpoint SHA256 is
496c8d12ee68e0e2173b696fa8b474020f2fd6a8721dc0c252cbe6221bffc3b3;
full log SHA256 is
66d705a743e989d6bd483728c024a7b183c63591dd9f95302e216aee05d42b1e.
Source-bound full validation terminates1/unqualified after all hash audits.

Capture-only replay bwkezn0x restores that checkpoint, runs the original initial
history checks and preceding static/trajectory calls, and writes anatomy request16
before executing it. Sentinel-98 deliberately stops that diagnostic; it is NOT
a reproduced numerical failure or accepted step. Request SHA256:
f3667fb46cebc4e8e084503056c58d2a86dc262f642e7a342173843067baf881.
It contains745vertices,924faces,3bodies, selected times[.5,1], one endpoint
iris constraint at vertex663/face252 and engineering radius.004. Predictor,
previous positions, material, pins and tolerances are unchanged.

Standalone instrumented replay h8bdirmj then actually executes this request:
solve1at100outer, force5.439475852737881e-6, energy1.042447929446706e-6,
gap3.084199562408685e-15, complementarity2.541034408986405e-14,
evaluations3207, inner3029/factors3177. It reproduces work exhaustion and force
stagnation; its floating trajectory is not bitwise identical to the differently
compiled Godot extension. No accepted XYZ/reactions are published.

The final local model is saved as terminal_model.bin (SHA256
fbc81b66b34b6dd2dd801ae5ee7708700ae287f3e656e196b5c94cd3c1b70751):2124free
coordinates,5545pairs,3active, rho223645.80104086135,34398H_L entries,
18279model-J entries, regular contact-curvature model. Independent local
gradient reconstruction differs by only5.26e-18. Initial linear diagnostics
suggest excessive tangent regularization from the active penalty diagonal;
they do not certify positive curvature, nonlinear descent or a repaired solve.
This remains an explicit heavy convergence failure, not a passing whole step.
