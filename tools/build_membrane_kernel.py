"""Build the standalone numerical kernel using the verified portable compiler."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / ".tools/native"
out.mkdir(parents=True, exist_ok=True)
subprocess.run([str(ROOT / ".tools/zig-x86_64-windows-0.17.0/zig.exe"), "c++",
                "-std=c++17", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                "-shared", "-target", "x86_64-windows-gnu",
                str(ROOT / "native/membrane_kernel.cpp"),
                "-o", str(out / "membrane_kernel.dll")], check=True)
