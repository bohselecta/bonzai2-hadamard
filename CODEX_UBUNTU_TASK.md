# Current entry point

The Ubuntu private project handoff is complete. Start with `UBUNTU_RESULTS.md`, `PROJECT.md`, and the current `STATUS.md`. CUDA, sanitizer/leak, quality, benchmark and API gates passed on the recorded host. Preserve source/model pins, original CPU evidence and preregistered criteria; use ordinary Git in the existing private repository. Metal and broader unsupported features remain unvalidated. Do not publish another handoff or automated upstream contribution.

The original task/checklist below is preserved as historical context and reproducibility guidance; its statements about pending CUDA work describe the earlier handoff.

# Codex on Ubuntu: finish Bonsai 2 CUDA validation

## Task

Use the completed private integration in this package on the Ubuntu machine. Build and validate it on the NVIDIA GPU, compare the same checkpoint against the pinned Prism runtime, and retain reproducible evidence. Fix concrete defects found in scope without weakening assertions. Complete the local validation before claiming GPU readiness or proposing an upstream change.

The intended machine is Hayden's Ubuntu system with Ryzen 5 4500, RTX 3060 12 GB, and 64 GB RAM. Verify the actual host and device rather than assuming that configuration. No paid cloud GPU, API inference service, or model-weight upload is needed.

## Existing work

Start with `README.md`, `DESIGN.md`, `STATUS.md`, `NEXT_AGENT.md`, `source.json`, and `model.json`. All patches and the CPU evidence are included. The original combined patch checksum is `13ba6fececac6955791628c54c47939dfd30a6c7aa9c8e7acef2b4392f9d22db`.

The integration already passed 27 generated-model checks, 32 CPU Hadamard operator tests, 1330 CPU matrix multiplication tests, 101 GGUF tests, CTest, and address/undefined sanitizers. The exact official Q2_0 27B checkpoint produced the expected marker and arithmetic JSON on CPU. GPU execution, comparative KLD/perplexity, and leak detection on a suitable host remain pending.

The runtime patch is existing Prism PR #29600, pinned to `fc50db4300e04a3af12e5fd1b8042afa87b1f1b7`. The CUDA wide FWHT patch is existing PR #29100, pinned to `7d9305fb51689840aa084eb0a60f4c03950c8988`. Additional metadata guards and generated-model tests are separate patches. Preserve attribution and do not open a duplicate upstream runtime PR.

## Scope and acceptance

Validate text-only Q2_0 inference on one GPU. Keep the model and source revisions pinned. Do not add PQ2_0/PTQ1_0, vision, multi-GPU split modes, RPC, LoRA support, or speculative/MTP decoding. Do not silently substitute CPU when CUDA was requested. Preserve the fixture tolerances and check that nonzero operator suites actually ran on CUDA0.

Record the GPU, driver, CUDA toolkit, compiler, CMake, OS, available RAM, free disk, and exact source revisions. Verify `nvidia-smi` and `nvcc --version`. Use at least 25 GiB free disk for a checkpoint, two source builds, and evidence; allow more for evaluation logits. Check the actual workload size before downloading. Reuse a valid checkpoint rather than making extra copies. Never install or replace a working driver merely to match an assumed version; investigate an actual toolchain failure first.

## Build and device correctness

Run from this package directory. These commands use a separate checkout and preserve unrelated work:

```sh
export CUDA_VISIBLE_DEVICES=0
python3 scripts/build.py --directory ../llama-bonsai2-cuda --backend cuda --jobs 4
```

This applies the exact patch, builds all tools, runs CPU fixtures, runs the same fixtures with `--ngl 99`, and runs CUDA0 `MUL_MAT_HADAMARD` and `MUL_MAT` operator tests plus GGUF tests. Preserve `../llama-bonsai2-cuda/build-bonsai2-cuda/evidence/`. If a test fails, record the failing case, fix the cause, and rerun the affected checks.

Use NVIDIA Compute Sanitizer on the actual wide Hadamard kernels. The `memcheck`, `racecheck`, and `error-exitcode` options are documented in [NVIDIA's Compute Sanitizer manual](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html). Confirm the installed tool's syntax with `compute-sanitizer --help`:

```sh
compute-sanitizer --tool memcheck --error-exitcode 1 \
  ../llama-bonsai2-cuda/build-bonsai2-cuda/bin/test-backend-ops \
  test -b CUDA0 -o MUL_MAT_HADAMARD

compute-sanitizer --tool racecheck --error-exitcode 1 \
  ../llama-bonsai2-cuda/build-bonsai2-cuda/bin/test-backend-ops \
  test -b CUDA0 -o MUL_MAT_HADAMARD
```

Save both stdout and stderr for each run. Confirm widths 1024, 2048, 4096, and 8192, F16/F32 inputs, and multiple rows are exercised. A successful exit with zero selected tests is a failure of validation. Do not claim a tool result if the tool is unavailable; install the supported toolkit component when authorized and appropriate, or record that precise remaining gate.

## Actual checkpoint

```sh
python3 scripts/download_model.py --directory ../models-bonsai2

python3 scripts/verify_model.py \
  --binary ../llama-bonsai2-cuda/build-bonsai2-cuda/bin/llama-server \
  --model ../models-bonsai2/Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf \
  --backend cuda --output ../bonsai2-cuda-model-evidence --context 2048
```

The verifier selects CUDA0, requires the checkpoint checksum, checks the Hadamard load record and full layer offload, and saves requests, responses, usage, timing, and server logs. Both cases must return their expected values and finish normally. If 12 GB VRAM cannot sustain this exact configuration, record the memory breakdown and cause. A partially offloaded fallback may be useful for diagnosis but does not satisfy the full-offload gate.

## Comparative quality and performance

Follow `NEXT_AGENT.md` to build the reference Prism revision `2459f68b5c0eb26261fd5a81682004b93cd645ba` in a separate directory. Inspect its own repository instructions before modifying it. Run the same Q2_0 checkpoint in both builds with identical context, batch, KV types, flash attention, and device settings. Use a representative evaluation text that can legally be distributed, save its SHA-256, and compare perplexity plus KLD on the reference file's exact token sequence.

Before comparing, record a numerical acceptance criterion appropriate to the matched precision and runtime settings. Consult the existing integration's documented validation when available. Do not choose a permissive threshold after seeing a failure or treat two fluent answers as numerical equivalence. If a suitable full-model criterion has not been established, report the measured deltas and leave that gate unapproved.

After correctness, benchmark both builds on the same host and settings. Capture JSON from `llama-bench` and peak memory. Report actual observations; do not promise a speedup. Avoid unrelated GPU workloads during the comparison.

Run leak detection on a host where LeakSanitizer can inspect processes; retain any exact environmental limitation rather than labeling a disabled check as passed.

## Finish and handoff

Write an evidence-backed `UBUNTU_RESULTS.md` recording each gate as passed, failed, or blocked, its command, source revision, toolchain, and evidence path. Update `STATUS.md` with the new host results while preserving the original CPU evidence. If code changed, update the supplemental/combined patch, patched-file hashes, patch checksum, and `SHA256SUMS`; verify that the refreshed patch applies to the pinned base. Keep weight files and large generated logits out of Git. Retain their hashes and reproducible commands.

The chosen private project handoff destination is `bohselecta/bonsai2-hadamard`, with branch `work/bonsai2-ubuntu` against `main`. `scripts/submit_pr.py --publish` creates that private repository and opens the draft handoff PR from an authenticated Ubuntu host. If the PR already exists, work in its checkout and commit the completed validation there. Do not wait for another repository selection. Do not post to an existing upstream PR. The handoff PR transports the code and task; CUDA validation still requires actual hardware execution.

For llama.cpp upstream itself, its pinned `AGENTS.md` prohibits automated commits/submissions and AI-written submission text. Respect that project-specific process: a human must understand and own the changes, coordinate with the existing PR authors, and write their own upstream submission. The private handoff does not bypass those requirements.

## Prompt to start the local Codex session

Read `CODEX_UBUNTU_TASK.md`, `PROJECT.md`, and the referenced files. Use `scripts/project.py setup --backend cuda` for the initial build and checkpoint checks, then carry out the Ubuntu CUDA validation using the included pinned patches. Verify the actual GPU and toolchain, fix in-scope defects, run the recorded acceptance checks, and write `UBUNTU_RESULTS.md` with the raw evidence. Do not claim a GPU test or comparative quality result that was not run. Preserve existing attribution and repository instructions. Do not use a paid cloud service or automatically submit an upstream PR.
