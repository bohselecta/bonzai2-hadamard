#!/usr/bin/env python3
"""Apply the pinned private patch, build, and check the selected backend."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=None, log=None):
    if log is None:
        subprocess.run([str(x) for x in args], cwd=cwd, check=True)
        return ""
    with log.open("w") as output:
        process = subprocess.run([str(x) for x in args], cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
    if process.returncode:
        raise RuntimeError(f"Command failed ({process.returncode}); see {log}")
    return log.read_text(errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("cpu", "cuda", "metal"), default="cpu")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--ninja")
    parser.add_argument("--apply-only", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    manifest = json.loads((ROOT / "source.json").read_text())
    directory = args.directory.expanduser().resolve()
    if not directory.exists():
        run(["git", "clone", "--no-checkout", "--depth=1", manifest["repository"], directory])
        run(["git", "fetch", "--depth=1", "origin", manifest["revision"]], directory)
        run(["git", "checkout", "-b", "work/bonsai2-hadamard", manifest["revision"]], directory)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
    if revision != manifest["revision"]:
        raise RuntimeError(f"Expected base {manifest['revision']}, found {revision}; use a separate directory")
    status = subprocess.check_output(["git", "status", "--porcelain", "-z"], cwd=directory).decode()
    modified = {entry[3:] for entry in status.split("\0") if entry}
    expected = manifest["patched_files"]
    applied = all((directory / path).is_file() and hashlib.sha256((directory / path).read_bytes()).hexdigest() == sha for path, sha in expected.items())
    if modified and (not applied or modified != set(expected)):
        raise RuntimeError("Directory contains other work or a different patch; no files were changed")
    if not applied:
        patch = ROOT / "patches" / "bonsai2-combined.patch"
        digest = hashlib.sha256(patch.read_bytes()).hexdigest()
        if digest != manifest["patch_sha256"]:
            raise RuntimeError("Combined patch checksum mismatch")
        run(["git", "apply", "--check", patch], directory)
        run(["git", "apply", patch], directory)
        for path, sha in expected.items():
            if hashlib.sha256((directory / path).read_bytes()).hexdigest() != sha:
                raise RuntimeError(f"Patched file checksum mismatch: {path}")
    run(["git", "diff", "--check"], directory)
    if args.apply_only:
        print(f"Applied and verified at {directory}; no commit or push was made")
        return

    cmake = shutil.which(args.cmake)
    if not cmake:
        raise RuntimeError("cmake is required; install it or pass --cmake /absolute/path")
    if args.backend == "metal" and sys.platform != "darwin":
        raise RuntimeError("Metal requires an Apple Silicon macOS host")
    if args.backend == "cuda" and not shutil.which("nvcc"):
        raise RuntimeError("CUDA compilation requires nvcc from the CUDA toolkit; no CPU substitution was made")
    ninja = shutil.which(args.ninja or "ninja")
    build = directory / f"build-bonsai2-{args.backend}"
    logs = build / "evidence"
    logs.mkdir(parents=True, exist_ok=True)
    configure = [cmake, "-S", directory, "-B", build, "-DCMAKE_BUILD_TYPE=Release",
                 "-DLLAMA_FATAL_WARNINGS=ON", "-DLLAMA_BUILD_TESTS=ON", "-DLLAMA_OPENSSL=OFF",
                 "-DLLAMA_BUILD_UI=OFF", "-DLLAMA_USE_PREBUILT_UI=OFF",
                 "-DGGML_CUDA=" + ("ON" if args.backend == "cuda" else "OFF"),
                 "-DGGML_METAL=" + ("ON" if args.backend == "metal" else "OFF")]
    if ninja:
        configure += ["-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=" + ninja]
    else:
        configure += ["-G", "Unix Makefiles"]
    run(configure, log=logs / "configure.log")
    targets = ["test-hadamard", "test-backend-ops", "test-gguf", "llama-server", "llama-cli", "llama-perplexity", "llama-bench"]
    run([cmake, "--build", build, "--parallel", args.jobs, "--target", *targets], log=logs / "build.log")
    binary = build / "bin"
    run([binary / "test-hadamard"], cwd=build, log=logs / "fixtures-cpu.log")
    if args.backend != "cpu":
        run([binary / "test-hadamard", "--ngl", "99"], cwd=build, log=logs / "fixtures-gpu.log")
    backend = {"cpu": "CPU", "cuda": "CUDA0", "metal": "MTL0"}[args.backend]
    for op in ("MUL_MAT_HADAMARD", "MUL_MAT"):
        output = run([binary / "test-backend-ops", "test", "-b", backend, "-o", op], cwd=build, log=logs / f"{op}.log")
        clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
        counts = re.findall(r"(\d+)/(\d+) tests passed", clean)
        if f": {backend}\n" not in clean or not counts or any(int(p) != int(n) or int(n) == 0 for p, n in counts):
            raise RuntimeError(f"Backend {backend} was not exercised successfully for {op}; see {logs}")
    run([binary / "test-gguf"], cwd=build, log=logs / "gguf.log")
    print(f"Build and selected-backend checks passed. Binaries: {binary}. Evidence: {logs}")
    print("The 27B checkpoint and host performance require scripts/verify_model.py next.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
