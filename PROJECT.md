# Use Bonsai 2 in your project

This project contains the verified CPU and single RTX 3060 CUDA integration of the official pinned Q2_0 checkpoint. All required Ubuntu gates passed; see `UBUNTU_RESULTS.md`.

## Ubuntu setup and local API

Install Python 3, Git, a C++ build toolchain, CMake, and Ninja. On Ubuntu, the ordinary package prerequisites can be installed with `sudo apt-get install python3 git build-essential cmake ninja-build`. CUDA additionally requires a working NVIDIA driver and CUDA toolkit with `nvcc`; do not replace a working driver just for this package. Allow roughly 25 GiB free disk. Check the real GPU and VRAM before running the full 27B model.

On this machine use the generated Git checkout and user-local toolkit:

```sh
cd /home/pr4nz/dev/bonsai2-hadamard-ubuntu/bonsai2-pr
export PATH=/home/pr4nz/dev/bonsai2-hadamard-ubuntu/bonsai2-workspace/cuda-12.8/bin:$PATH
export LD_LIBRARY_PATH=/home/pr4nz/dev/bonsai2-hadamard-ubuntu/bonsai2-workspace/cuda-12.8/lib64:${LD_LIBRARY_PATH:-}
export CUDA_VISIBLE_DEVICES=0
```

Setup is already complete here. On a fresh machine run setup first; start the verified installation with serve:

```sh
python3 scripts/project.py setup --backend cuda
python3 scripts/project.py serve
```

Use `--backend cpu` for the validated CPU path. Setup creates a separate `../bonsai2-workspace` directory, applies the checksum-verified patches to the pinned llama.cpp revision, builds and runs regression tests, downloads or verifies the checkpoint, and runs two actual-model smoke checks. CUDA mode requires actual CUDA tests and full layer offload; failures stop setup. Successful setup writes a local installation record, and `serve` uses that record and rechecks the model checksum. Both commands accept `--workspace /absolute/project/path` if you want a different location.

The server listens on loopback at `http://127.0.0.1:8080`. Your project's OpenAI-compatible client can use base URL `http://127.0.0.1:8080/v1` and model name `bonsai2`. The local server requires no API key. For example:

```sh
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"bonsai2","messages":[{"role":"user","content":"Reply with BONSAI_OK"}],"temperature":0,"max_tokens":32}'
```

Stop a foreground server with Ctrl-C. The retained background instance can be stopped with `python3 ../bonsai2-workspace/service-run.py stop`; this checks its recorded PID belongs to this llama-server before sending SIGTERM. Restart with `python3 ../bonsai2-workspace/service-run.py start`, or use the foreground serve command above. Live logs are `../bonsai2-workspace/service.log`; PID and installation records are `service.pid` and `project-state.json` in that workspace.

The separate sanitizer and PPL/KLD comparisons have passed on this host; setup itself performs the basic regression/model checks. Preserve `evidence/ubuntu/quality-criteria.md` before any new comparison. This is an OpenAI-compatible local API; Ollama integration is unvalidated. The approved stop of `jungle-trap-public` frees port8080; restoring that container requires stopping Bonsai first.

## Existing GitHub work item

The private repository and handoff PR already exist: [repository](https://github.com/bohselecta/bonsai2-hadamard), [PR #1](https://github.com/bohselecta/bonsai2-hadamard/pull/1). Resume ordinary Git work in `bonsai2-pr`; do not run the publisher again or create duplicate handoffs. The following original publication instructions are retained for provenance.

## Original private handoff publication

The default destination is a new private `bohselecta/bonsai2-hadamard` repository. This is a project integration repository; it does not modify llama.cpp upstream. Install GitHub CLI (`gh`) and authenticate it as `bohselecta`. Ensure Git has your author name and email configured. Then run:

```sh
python3 scripts/submit_pr.py --publish
```

The script verifies every packaged file, prepares `main` plus `work/bonsai2-ubuntu` in a separate `../bonsai2-pr` checkout, creates the private repository, pushes the branches, and opens the draft handoff PR. It prints the real PR URL only after GitHub returns it. A mismatched account, pre-existing unrelated repository, changed prepared commits, or publication failure stops the operation. No model weights are committed. Without `--publish`, it only prepares the local branches for review.

The PR is deliberately a work item for Ubuntu hardware validation. Give Codex in that checkout this instruction:

> Read CODEX_UBUNTU_TASK.md and PROJECT.md. Complete the CUDA and numerical validation, fix defects found within scope, preserve the existing CPU evidence, and commit UBUNTU_RESULTS.md with the raw evidence paths. Keep the PR draft until its hardware acceptance gates pass.

Publication uses the documented [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create) and [draft PR creation](https://cli.github.com/manual/gh_pr_create) commands. Supplemental scripts and private PR text were prepared with AI assistance; existing Prism/CUDA patches remain attributed in `NOTICE` and `source.json`.
