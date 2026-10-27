"""Fetch unmodified, pinned native headers/bindings into the ignored tools directory."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
dependencies = [
    ("eigen-5.0.1", "5.0.1", "bc3b39870ecb690a623a3f49149a358b95c5781d", "https://gitlab.com/libeigen/eigen.git"),
    ("godot-cpp-4.5", "godot-4.5-stable", "e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77", "https://github.com/godotengine/godot-cpp.git"),
]
for name, tag, revision, url in dependencies:
    path = ROOT / ".tools" / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", tag, url, str(path)], check=True)
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True).strip()
    if actual != revision or dirty:
        raise SystemExit(f"{name} differs from pinned unmodified source; refusing to overwrite it")
    print(f"{name} verified at {actual}")
