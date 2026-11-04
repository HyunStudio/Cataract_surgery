"""Small shared provenance helpers for experimental native artifacts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024*1024), b""): digest.update(block)
    return digest.hexdigest()

def source_hashes(paths):
    # Local quoted headers are part of the proof even if a build script listed
    # only their parent. Pinned third-party angle includes remain git-pinned.
    root=ROOT.resolve();pending=list(paths);seen=set()
    native_suffixes={'.c','.cc','.cpp','.cxx','.h','.hh','.hpp','.hxx','.inc'}
    while pending:
        path=Path(pending.pop()).resolve()
        if not path.is_relative_to(root):raise ValueError('Build dependency leaves workspace: '+str(path))
        if path in seen:continue
        seen.add(path)
        if path.suffix.lower() not in native_suffixes:continue
        content=path.read_text(encoding='utf-8')
        for name in re.findall(r'^\s*#\s*include\s*"([^"\r\n]+)"',content,re.MULTILINE):
            dependency=(path.parent/name).resolve()
            if not dependency.is_relative_to(root):raise ValueError('Local include leaves workspace: '+name)
            if not dependency.is_file():raise FileNotFoundError('Missing local include: '+str(dependency))
            pending.append(dependency)
    return {str(path.relative_to(root)):sha256(path) for path in sorted(seen)}

def verify_sources(sources):
    if any(sha256(ROOT/name) != expected for name,expected in sources.items()):
        raise SystemExit("Native build inputs changed; refusing mismatched artifact provenance")

def compiler_identity(executable):
    version = subprocess.check_output([str(executable),"version"],text=True).strip()
    if version != "0.17.0": raise SystemExit("Expected verified Zig0.17.0 toolchain")
    return {"version":version,"executable":str(executable.relative_to(ROOT)),"executable_sha256":sha256(executable)}

def write_manifest(path, artifact, sources, compiler, dependencies, flags):
    verify_sources(sources)
    if sha256(ROOT/compiler["executable"]) != compiler["executable_sha256"]:
        raise SystemExit("Compiler changed during native build")
    for dependency, revision in dependencies.items():
        actual = subprocess.check_output(["git","-C",str(ROOT/dependency),"rev-parse","HEAD"],text=True).strip()
        dirty = subprocess.check_output(["git","-C",str(ROOT/dependency),"status","--porcelain"],text=True).strip()
        if actual != revision or dirty: raise SystemExit("Native dependency changed during build")
    data = {"artifact_sha256":sha256(artifact),"sources":sources,"compiler":compiler,
            "dependencies":dependencies,"flags":flags,
            "source_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "source_dirty":bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip())}
    path.write_text(json.dumps(data,indent=2),encoding="utf-8")
    return data
