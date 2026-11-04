# Submission review reconciliation and implementation

Source: local repository C:/tmpcs/kind, commit39481ff. The supplied review
commits are real but were not present on origin when first checked. They are
now preserved as local-review/kind in the primary repository. Improvements
start in an isolated feat/submission-improvements worktree; no history rewrite
or automatic merge into the unfinished Godot engine branch.

## Verified findings and priorities

1. Preserve the review's leak-depth, caching, background-save and localized HUD
   fixes. Re-run current tests; historical876 and RTX measurements are review
   evidence, not new measurements. Automatic educational depth snapping does
   not establish physical instrument motion in the Godot simulator.
2. Harden background autosave shutdown: drain pending work on all exit paths,
   stop workers and expose write errors. Test with an intentionally blocked
   disk and an unwritable location before implementation.
3. Deliver a Windows folder build with a single entry point, bundled assets,
   Korean font support and writable user save directory. Validate from an unrelated
   working directory, without a development Python installation. Building an
   executable alone is insufficient: launch and real input must be checked.
4. Connect realistic microscope rendering to interaction through a common
   camera transform. First verify projection/ray inverse and viewport/HUD
   exclusion. Preserve correct tool depth and deliberate tool choice; do not
   accept arbitrary clicks by substituting target coordinates. Do not relabel
   the observation camera as interactive without those tests.
5. Reconcile branch changes explicitly, run CI on the actual integration and
   retain GPU evidence by hardware/driver. Existing NVIDIA evidence does not
   establish AMD compatibility. Expert validation and clinical calibration
   remain unavailable; describe models as synthetic.

The professional Godot goal remains active. Its qualified numerical kernel
is a separate milestone; default full-surgery mechanics, runtime throughput,
actual input and Windows release still require end-to-end qualification.

## Execution evidence

- Shutdown regression: two failures for missing close(), then five shutdown
  and existing background-save tests pass after implementation.
- Tests use --rootdir=. --confcutdir=. to avoid an unrelated broken parent
  directory junction; no user files were removed or repaired.
- Full Python suite:878 passed after shutdown change,881 passed including the
  first launcher tests. The later explicit-relative-resume regression failed
  before its fix, then all four launcher tests passed.
- Read-only review confirmed queue shutdown and identified the relative-resume
  defect, now fixed. Build recipe force-added because generic *.spec is ignored.
- First system-Python package lacked optional3D dependencies despite a successful
  PyInstaller exit. Rejected that artifact. Added mandatory dependency preflight
  and rebuilt from a dedicated build environment with pygame/moderngl/glcontext.
- Qualified-path folder build launches from outside the source directory.
  Windows UI observation confirmed Korean glyphs,3D rendering, pointer response
  and close. Automated Space/F3 did not visibly act; keyboard input remains
  unqualified, not silently marked passing. No whole-case/newFPS/AMD/clean-machine
  or complete-release claim. Fonts remain Windows system fonts, not bundled.
- Fresh source GPU smoke passed on RTX3070Laptop; this is not the frozen-input
  test. The packaged preview ZIP contains118 files (~15.4MB compressed), with
  per-file SHA256 evidence in WINDOWS_BUILD_VALIDATION_2026-11-04.json.

Final source suite with3D dependencies installed:882 passed in100.45s. No actual frozen full-surgery claim.
