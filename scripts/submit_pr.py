#!/usr/bin/env python3
"""Prepare the project handoff; publish it to a new private repo with --publish."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "work/bonsai2-ubuntu"
TITLE = "Add pinned Bonsai 2 integration and Ubuntu CUDA validation"
BODY = """The official Bonsai 2 Q2_0 checkpoint needs Prism Hadamard runtime support to run in the pinned llama.cpp base. This handoff supplies the attributed runtime and wide CUDA patches, additional metadata guards, generated-model regression tests, and reproducible build/model verification scripts.

CPU validation and actual-checkpoint smoke-test evidence are included in STATUS.md. CUDA execution, Compute Sanitizer, and comparative KLD/perplexity have not been run on the target GPU. This draft is the work item for Codex on Ubuntu, not an upstream readiness claim.

Read CODEX_UBUNTU_TASK.md and PROJECT.md. Run the included CUDA setup, finish the hardware and numerical gates, fix defects without weakening assertions, and commit UBUNTU_RESULTS.md with reproducible evidence before marking this PR ready.

Existing Prism PR #29600 and CUDA PR #29100 are attributed and pinned in source.json. Supplemental code and this private handoff were prepared with substantial AI assistance. No model weights are included. This PR does not submit or duplicate a change to ggml-org/llama.cpp.
"""


def command(args, cwd=None, capture=False):
    env = os.environ.copy()
    env["GH_HOST"] = "github.com"
    result = subprocess.run([str(x) for x in args], cwd=cwd, check=True,
                            text=True, capture_output=capture, env=env)
    return result.stdout.strip() if capture else ""


def package_files():
    files = {}
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        sha, name = line.split("  ", 1)
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix == ".gguf":
            raise RuntimeError("Unexpected package manifest path")
        path = ROOT / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise RuntimeError(f"Package checksum mismatch: {name}")
        files[name] = path.read_bytes()
    files["SHA256SUMS"] = (ROOT / "SHA256SUMS").read_bytes()
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode() + b"\0" + data)
    return files, digest.hexdigest()


def prepare(directory):
    files, digest = package_files()
    state_path = directory / ".git" / "bonsai2-handoff.json"
    if directory.exists():
        if not state_path.is_file():
            raise RuntimeError("Destination already exists and is not this prepared handoff")
        state = json.loads(state_path.read_text())
        if state["package_sha256"] != digest:
            raise RuntimeError("Package changed; prepare in a new directory to preserve existing work")
        if command(["git", "status", "--porcelain"], directory, True):
            raise RuntimeError("Prepared handoff contains uncommitted work")
        for ref, key in [("main", "base"), (BRANCH, "head")]:
            if command(["git", "rev-parse", ref], directory, True) != state[key]:
                raise RuntimeError("Prepared commits changed; use normal Git/gh workflow")
        return state, state_path
    if not command(["git", "config", "user.name"], capture=True) or not command(
            ["git", "config", "user.email"], capture=True):
        raise RuntimeError("Set your Git author name and email before preparing the handoff")
    directory.mkdir(parents=True)
    command(["git", "init", "-b", "main"], directory)
    (directory / "README.md").write_text(
        "# Bonsai 2 project integration\n\nThe integration and Ubuntu GPU validation task are supplied in the handoff PR.\n")
    command(["git", "add", "README.md"], directory)
    command(["git", "commit", "-m", "Initialize private Bonsai 2 project handoff"], directory)
    base = command(["git", "rev-parse", "HEAD"], directory, True)
    command(["git", "checkout", "-b", BRANCH], directory)
    for name, data in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    command(["git", "add", "--all"], directory)
    command(["git", "commit", "-m", TITLE], directory)
    state = {"package_sha256": digest, "base": base,
             "head": command(["git", "rev-parse", "HEAD"], directory, True)}
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    return state, state_path


def publish(args, state, state_path):
    if not shutil.which("gh"):
        raise RuntimeError("Install GitHub CLI and run gh auth login on Ubuntu, then rerun with --publish")
    login = command(["gh", "api", "--hostname", "github.com", "user", "--jq", ".login"], capture=True)
    if login.lower() != args.owner.lower():
        raise RuntimeError(f"GitHub CLI is authenticated as {login}; select {args.owner} before publishing")
    repo = f"{args.owner}/{args.name}"
    if state.get("repository") and state["repository"] != repo:
        raise RuntimeError("This prepared handoff was already published to a different repository")
    if not state.get("repository"):
        # Creation must succeed: never reuse or overwrite an unrelated existing repository.
        command(["git", "checkout", "main"], args.directory)
        command(["gh", "repo", "create", repo, "--private", "--source", args.directory,
                 "--remote", "origin", "--description", "Pinned Bonsai 2 integration and Ubuntu GPU validation handoff"])
        state["repository"] = repo
        state_path.write_text(json.dumps(state, indent=2) + "\n")
    metadata = json.loads(command(["gh", "api", "--hostname", "github.com", "repos/" + repo], capture=True))
    if not metadata["private"] or metadata["owner"]["login"].lower() != args.owner.lower():
        raise RuntimeError("Repository owner/privacy does not match this private handoff")
    expected_remote = f"https://github.com/{repo}.git"
    remote = command(["git", "remote", "get-url", "--push", "origin"], args.directory, True)
    if remote not in (expected_remote, f"git@github.com:{repo}.git"):
        raise RuntimeError("Prepared repository has an unexpected push destination")
    # Credential helper applies only to this command, without changing global configuration.
    command(["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
             "push", expected_remote, "main:main", f"{BRANCH}:{BRANCH}"], args.directory)
    command(["gh", "repo", "edit", repo, "--default-branch", "main"])
    command(["git", "checkout", BRANCH], args.directory)
    body = args.directory / ".git" / "bonsai2-pr-body.md"
    body.write_text(BODY)
    existing = json.loads(command(["gh", "pr", "list", "--repo", repo, "--head", BRANCH,
                                   "--base", "main", "--state", "open", "--json", "url"], capture=True))
    if existing:
        url = existing[0]["url"]
    else:
        url = command(["gh", "pr", "create", "--repo", repo, "--base", "main", "--head", BRANCH,
                       "--draft", "--title", TITLE, "--body-file", body], args.directory, True)
    if not re.fullmatch(r"https://github\.com/" + re.escape(repo) + r"/pull/\d+", url):
        raise RuntimeError("GitHub did not return the expected PR URL; inspect the repository")
    state["pull_request"] = url
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(f"Submitted private Ubuntu handoff PR: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT.parent / "bonsai2-pr")
    parser.add_argument("--owner", default="bohselecta")
    parser.add_argument("--name", default="bonsai2-hadamard")
    parser.add_argument("--publish", action="store_true", help="Create a private repository, push, and open the draft PR")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.owner) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.name):
        parser.error("Invalid repository owner or name")
    if args.owner.lower() == "ggml-org":
        parser.error("This script creates private project handoffs, not upstream submissions")
    args.directory = args.directory.expanduser().resolve()
    if args.directory == ROOT or ROOT in args.directory.parents:
        parser.error("Use a separate directory outside the source package")
    state, state_path = prepare(args.directory)
    if args.publish:
        publish(args, state, state_path)
    else:
        print(f"Prepared {BRANCH} against main in {args.directory}. No remote submission was made.")
        print("Rerun this command with --publish on your authenticated Ubuntu host to submit the PR.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
