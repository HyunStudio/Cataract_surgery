# Actual264 combined tool and iris contact request

`joint_anatomy264.json` is exact request38 from the frozen failed-step replay
`.tools/joint-failure-replay-c77pa78w`. Its SHA256 is
`ef55945a85d0d975d968fa5d53aeb4687b4dfc89c9d4f8a538e985d4eed08f96`.
It preserves predictor, previous positions, pins, material, tool packets and the
original physical tolerances. It contains745vertices,924faces,3tool bodies,
times[.5,.75,.875,1], and one endpoint iris constraint for vertex663/face252.
The radius.004 is the existing engineering boundary margin, not a measured
clinical thickness.

The source full replay `.tools/membrane-validation-ttc652cp` on3a1c95b is
terminal/unqualified:263outer ticks accepted,264rolled back with
`native_joint_solve`/status2. Retained area5.31932634674013, zero cut loss,
broken edges and accepted uncertainty. Checkpoint SHA256
`6ed9a47e720ed6d1b8a310bbd6d599cd817f5d6149f7ce7ca52444eb8b107cdb`;
full log SHA256
`4175292381c1077500869c69c719a320987c98c12d9e76812b7a5157f79d9c5a`.

The replay restores that saved state without rerunning the full prefix. Initial
iris checks clear. After the tool guard clears, iris call37 finds face252 at
t1 with gap-.00053156585597; call38 attempts the combined solve and rejects.
This history is distinct from the earlier legacy265 already-penetrating state.
The replay log SHA256 is
`7bf39f938727eeefc3bb8ecf0f9c06efe7f1fcd01035c030bf8e582f8df96e0b`.

`python tools/check_anatomy_capture.py` is an explicit heavy convergence gate.
Its baseline is RED:status2, with positions and reaction buffers unchanged.
Rejection is never a passing mechanical solve. A future status0 must also pass
independent force, gap, complementarity, energy and pin checks. Even a passing
capture remains a selected-time mechanical test; continuous guards, extraction,
default input, realtime performance and complete surgery remain separate gates.

Frozen trace `.tools/anatomy264-line-trace-3f__oy1q` captures the final failed
direction and32represented trial vectors. All trial geometries remain valid;
the final line search fails to establish Armijo descent. Trace source/artifact
hashes and original compiler flags are recorded in `proof.json`. Numerical
cause is under investigation; no tolerance or work-budget increase is adopted.
