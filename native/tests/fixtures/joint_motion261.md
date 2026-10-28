# Actual joint motion261

`joint_motion261.json` SHA256 `bf756095c5c0a4846b29ddea032bea4a5708a9bafd5f7702639b8ea6f794dc8e`.

The frozen extraction probe `.tools/membrane-validation-uy25_vez` accepted260 outer ticks and rejected the first substep of request261 at the legacy float32 body projection guard. Its saved binary `guard261.bin` SHA256 is `bae49d404fae4ffe75a5eca3bbe1ff79cd5b6c4b6a6a0c160f83bbd8c518f3f3`. HEAD at capture was38fa441 (same physical code as c617746).

The diagnostic exporter `.tools/export_guard261.gd` retained the saved previous/current packed64 tissue coordinates,924 triangle faces, and3 actual forceps body segments. Packets contain the recorded endpoint axes, physical radii, original full pose path and quaternion/local geometry. The global interval [0,.5] was reconstructed from the first of two physical substeps (native call521 after260 accepted outer ticks); the saved body dictionaries predate explicit interval metadata. Packet kind1 uses the original spherical path plus an affine correction to exactly match the recorded endpoint axes.

The static endpoint solver accepted with force4.283e-11 and penetration7.973e-11 under the original force1e-8/gap1e-9 gates. Legacy projected residual was1.744316e-8, with a position correction. Removing angular padding alone still produced1.791865e-8 and a correction, so that shortcut is not used.

The new standalone continuous guard certifies status0 with84 nearest queries,2772 visited face/body pairs,15 subdivisions and maximum depth15; minimum sampled gap is-7.973282624418321e-11. All input arrays remain unchanged. This fixture verifies a finite-arithmetic clearance certificate for this one captured interval, not complete extraction, exact-predicate CCD, clinical realism or realtime performance.

## Second substep: explicit uncertainty regression

`joint_motion261_second.json` SHA256 `f8f6d923019e7fce8f626500a2af707a794e4f7a0d01501e612a865e98c78587` comes from the next full replay `.tools/membrane-validation-yibw6k7v`. Rejected outer-state capture SHA256 is `ba5d9127e4754779e0aaa421ff3e41f448eed2441e2ab0b7c594253e002c70ef`. Diagnostic `replay_motion261.gd` captures the guard's actual packed request directly, including interval [.5,1]. No interval reconstruction is needed.

The guard returns status2, stats `[137,122,40,1,-1.23819e-10,70,17,1]`: face40/body1 exhausts its128 query budget, while the static candidate meets all original physical gates. A SciPy spherical-path interpolation diagnostic samples10001 times for this pair; all nearest queries are regular, minimum gap-1.2381908e-10 occurs at the end, and minimum absolute moving-plane gap is the same. Sampling is not continuous certification. Retain uncertainty and whole-outer rollback until a tighter bounded time-correlated certificate resolves the interval.
