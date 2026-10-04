#!/usr/bin/env python3
"""Build, verify, and serve the pinned Bonsai 2 integration for a local project."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / "model.json").read_text())


def run(command, env=None):
    subprocess.run([str(x) for x in command], check=True, env=env)


def preflight(backend, workspace):
    if sys.platform != "linux":
        raise RuntimeError("This launcher targets Linux; use build.py directly on macOS")
    required = ["git", "cmake", "c++", "make"]
    if shutil.which("ninja"):
        required.remove("make")
    if backend == "cuda":
        required += ["nvcc", "nvidia-smi"]
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise RuntimeError("Required tools missing: " + ", ".join(missing) +
                           ". See PROJECT.md for Ubuntu prerequisites")
    env = os.environ.copy()
    if backend == "cuda":
        env.setdefault("CUDA_VISIBLE_DEVICES", "0")
        run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv"], env)
        run(["nvcc", "--version"], env)
    probe = workspace
    while not probe.exists():
        probe = probe.parent
    model = workspace / "models" / MODEL["file"]
    required_bytes = 8 * 1024**3 + (0 if model.exists() else MODEL["size"])
    if shutil.disk_usage(probe).free < required_bytes:
        raise RuntimeError("Insufficient disk space for the checkpoint, build, and evidence")
    return env


def setup(args):
    env = preflight(args.backend, args.workspace)
    args.workspace.mkdir(parents=True, exist_ok=True)
    checkout = args.workspace / "llama.cpp"
    binary = checkout / f"build-bonsai2-{args.backend}" / "bin" / "llama-server"
    model = args.workspace / "models" / MODEL["file"]
    run([sys.executable, ROOT / "scripts/build.py", "--directory", checkout,
         "--backend", args.backend, "--jobs", args.jobs], env)
    run([sys.executable, ROOT / "scripts/download_model.py", "--directory", model.parent], env)
    evidence = args.workspace / ("model-check-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run([sys.executable, ROOT / "scripts/verify_model.py", "--binary", binary,
         "--model", model, "--backend", args.backend, "--output", evidence,
         "--context", args.context, "--threads", args.threads], env)
    state = {"backend": args.backend, "binary": str(binary), "model": str(model),
             "model_sha256": MODEL["sha256"], "context": args.context,
             "threads": args.threads, "evidence": str(evidence),
             "cuda_visible_devices": env.get("CUDA_VISIBLE_DEVICES"),
             "source_revision": json.loads((ROOT / "source.json").read_text())["revision"],
             "verified_at": datetime.now(timezone.utc).isoformat()}
    temporary = args.workspace / "project-state.json.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(args.workspace / "project-state.json")
    print(f"Build, selected-backend tests, and real-model smoke checks passed. Evidence: {evidence}")
    print("Run project.py serve with the same --workspace to start your project's local API.")
    print("Comparative quality and GPU sanitizers remain separate gates in CODEX_UBUNTU_TASK.md.")


def serve(args):
    state_path = args.workspace / "project-state.json"
    if not state_path.exists():
        raise RuntimeError("Run project.py setup successfully before serving")
    state = json.loads(state_path.read_text())
    model = Path(state["model"])
    digest = hashlib.sha256()
    with model.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if model.stat().st_size != MODEL["size"] or digest.hexdigest() != MODEL["sha256"]:
        raise RuntimeError("Checkpoint changed since verification")
    backend = state["backend"]
    command = [state["binary"], "-m", str(model), "--host", "127.0.0.1",
               "--port", str(args.port), "--alias", "bonsai2", "-np", "1",
               "-c", str(state["context"]), "-t", str(state["threads"]),
               "-ngl", "0" if backend == "cpu" else "99", "--fit", "off",
               "--jinja", "--reasoning", "off", "--reasoning-budget", "0"]
    env = os.environ.copy()
    if backend == "cuda":
        env["CUDA_VISIBLE_DEVICES"] = state["cuda_visible_devices"]
        command += ["--device", "CUDA0"]
    print(f"Project API: http://127.0.0.1:{args.port}/v1; model: bonsai2", flush=True)
    os.execvpe(command[0], command, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    build = sub.add_parser("setup", help="Build, download, and run actual-model smoke checks")
    build.add_argument("--backend", choices=("cpu", "cuda"), default="cuda")
    build.add_argument("--jobs", type=int, default=4)
    build.add_argument("--context", type=int, default=2048)
    build.add_argument("--threads", type=int, default=4)
    server = sub.add_parser("serve", help="Serve a successfully verified installation on loopback")
    server.add_argument("--port", type=int, default=8080)
    for command in (build, server):
        command.add_argument("--workspace", type=Path, default=ROOT.parent / "bonsai2-workspace")
    args = parser.parse_args()
    args.workspace = args.workspace.expanduser().resolve()
    if args.action == "setup":
        if args.jobs < 1 or args.threads < 1 or args.context < 1024:
            parser.error("jobs/threads must be positive and context must be at least 1024")
        setup(args)
    else:
        if not 1 <= args.port <= 65535:
            parser.error("port must be between 1 and 65535")
        serve(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
