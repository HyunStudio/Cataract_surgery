# Retained blade-cut material-resolution failure

`blade-material-resolution.bin` is a61420-byte Godot4.7.2 Variant dictionary,
captured from `test_blade_closed.gd` using the real prepared capsule, limited
target motion and the default physical backend. It contains synthetic numerical
arrays only: the last pre-cut `state` and a valid geometric `cut`, with immutable
original material mesh and fine-face ancestry. No patient data or object handles.

The existing fine-node transfer rejects `mass_resolution`, including a node
whose retained lumped mass was1.0840033148863092e-13 under the captured transfer
implementation. After normalized scalar-double affine transfer, its reevaluated
minimum is1.0614949215861843e-13 and the same mass-resolution gate rejects it.
The cut has301 vertices and
482 faces. An original-material support construction has221 virtual controls,
minimum support mass3.632163119339842e-8 and total mass5.319326346740126. The
same geometry, real material areas and crack-bank edge identities are retained.

`test_embedded_failure.gd` checks the original rejection remains intact and that
the new support builder preserves mass without clamping or mutating physical
state. This is a discretization fixture, NOT proof of an accepted time step,
crack-tip enrichment, contact solve, whole closed incision or interactive FPS.
