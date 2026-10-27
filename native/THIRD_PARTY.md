# Native numerical build dependencies

Eigen5.0.1, unmodified official source at commit `bc3b39870ecb690a623a3f49149a358b95c5781d`:

- Repository/source: https://gitlab.com/libeigen/eigen/-/tree/5.0.1
- License: primarily Mozilla Public License2.0, with compatible notices in individual files. Original notices are retained in the fetched headers. Build defines `EIGEN_MPL2_ONLY`.
- License copies: `licenses/Eigen-COPYING.MPL2`, `licenses/Eigen-COPYING.BSD`, `licenses/Eigen-COPYING.APACHE`, `licenses/Eigen-COPYING.MINPACK`, `licenses/Eigen-COPYING.README`.
- Setup: `python tools/setup_native_dependencies.py`; fetches to ignored `.tools/eigen-5.0.1`. No Eigen source modifications are required. This dependency is compiled into the experimental DLL; there is no external Eigen runtime DLL.

The current Windows product release does not contain this experimental kernel. Any future release that includes it must also include these notices and applicable compiler-runtime notices; it must retain access to the corresponding unmodified Eigen source above.

The isolated Godot test extension additionally compiles unmodified godot-cpp4.5stable bindings at `e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77`, under the MIT license. Source: https://github.com/godotengine/godot-cpp/tree/godot-4.5-stable. Original copyright notices are preserved in the fetched sources; see `licenses/godot-cpp-LICENSE.md`.
