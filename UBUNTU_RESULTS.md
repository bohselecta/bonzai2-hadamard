# Ubuntu acceptance results — 2026-10-04

All required private project acceptance gates passed on the actual RTX 3060. Evidence paths below are relative to `evidence/ubuntu/`. Original CPU evidence remains unchanged in `evidence/`; its older limitations describe that earlier host. No upstream readiness or Metal validation is claimed.

## Hardware, identities and reproducibility

Ubuntu 24.04.4 LTS, kernel 7.0.0-31-generic; Ryzen 5 4500 (6 cores/12 threads), 62 GiB installed RAM, 54 GiB available at the recorded check; RTX 3060 12288 MiB, driver/kernel 580.173.02. Recorded free disk 60 GiB. GCC 13.3.0, CMake 3.28.3, Ninja; local CUDA 12.8, nvcc V12.8.61, Compute Sanitizer 12.8. `nvidia-smi` reports driver CUDA compatibility 13.0, which is not the installed toolkit version. See `environment.log`, `toolkit.log`, `cuda-installer.log`. The working driver was preserved; only a user-local toolkit was installed. The desktop also uses this GPU.

Source base: `836d57176dc699a726c55418e4f96b8ca628e1bf`. Attributed Prism PR: `fc50db4300e04a3af12e5fd1b8042afa87b1f1b7`; wide CUDA PR: `7d9305fb51689840aa084eb0a60f4c03950c8988`. Separate pristine Prism reference: `2459f68b5c0eb26261fd5a81682004b93cd645ba`. Combined patch: `4348bcbc1f0cb28c7bf4bb16971b8590c55bd9f9e67e797dc99a9472f2bf7be6`. Original combined checksum `13ba6fececac6955791628c54c47939dfd30a6c7aa9c8e7acef2b4392f9d22db` retained in the original package/history. Patches 0001–0004 and the original generated-model assertion file remain unchanged.

Checkpoint revision: `2a263ef827a2e215f3ddd14c9871a5bd1800fcbc`, 7,626,008,928 bytes, SHA256 `4f99aed01b8a877e153f9aa6569a4440fe17c59701cc0953e36d7f460549e70e`. Reused for every model test/comparison. Model, corpus and large reference logits remain outside Git in `../bonsai2-workspace`.

GitHub CLI authenticated as `bohselecta`; private repository [bohselecta/bonsai2-hadamard](https://github.com/bohselecta/bonsai2-hadamard), handoff [PR #1](https://github.com/bohselecta/bonsai2-hadamard/pull/1). The publisher created it once; subsequent work used its generated `bonsai2-pr` checkout and normal Git/gh operations. No upstream PR was opened.

## Acceptance gates

| Gate | Result | Evidence / actual checks |
| --- | --- | --- |
| Initial package integrity before changes | passed | `package-initial-SHA256SUMS`, `package-initial-check.log` |
| Pinned clean application, series and combined | passed | `patch-application.log`; all 13 patched hashes match `source.json` |
| CUDA setup and seven build targets | passed | `setup-fixed.log`, `cuda-build/`; Release, CUDA sm86, warnings fatal |
| Generated CPU/CUDA fixtures | passed | `cuda-build/fixtures-cpu.log`, `fixtures-gpu.log`; 27 each: 10 numerical cases and 17 intended metadata rejections |
| Hadamard operators | passed | CPU and CUDA 38/38; `CPU-MUL_MAT_HADAMARD.log`, `cuda-build/MUL_MAT_HADAMARD.log` |
| Ordinary matrix multiplication | passed | CPU 1330/1330; CUDA 1304/1304 supported cases; `CPU-MUL_MAT.log`, `cuda-build/MUL_MAT.log` |
| GGUF and CTest | passed | 101/101 GGUF, CTest 1/1; `cuda-build/gguf.log`, `ctest-hadamard.log` |
| GPU memcheck | passed | `memcheck.log`: 16/16, error summary 0 |
| GPU racecheck | passed | `racecheck.log`: 16/16, zero hazards/errors/warnings |
| ASan, UBSan and supported leak detection | passed | Debug CPU, 27 generated checks and 38/38 scoped Hadamard operators; `sanitize-tests-fixed.log`, `sanitize-operators-fixed.log`; leak detection enabled |
| Exact actual checkpoint and full CUDA offload | passed | `real-model-cuda/`; 65/65 layers, 402 folded weights, one inverse lookup, one rotation, three signs |
| Actual-model smoke responses | passed | `real-model-cuda/`: BONSAI_OK and JSON sum 43, both finish `stop` |
| Pinned Prism comparative quality | passed | `quality-criteria.md`, `quality-results.json`, three final PPL/KLD logs; thresholds preregistered in commit `f2787ec` before execution |
| Correctness-first hardware benchmarks | passed | `*-bench.json`, `*-bench.log`, `*-bench-memory.json`, `benchmark-summary.json` |
| Project service | passed | `service-*.json`, `service.log`: health, models, real chat POST, malformed JSON 400, missing messages 400, unknown route 404 |
| Project tools | passed | `project-tools.log`: six tests, including real local Git preparation and account/publication safeguards; simulated GitHub unit tests are not hardware evidence |
| Repository checks | passed | final SHA256SUMS verification and `git diff --check`; no repository CI workflow/checks were configured |
| Metal / broader unsupported features | blocked | no Metal hardware; multi-GPU, RPC, adapters, vision, MTP/speculative and all allowlisted architectures remain unvalidated and outside this delivery |

## Commands and settings

See each `*-command.json` and `*-exit.json` for exact arguments, exit status and wall duration. Build entry command: `python3 scripts/project.py setup --backend cuda`, with `CUDA_VISIBLE_DEVICES=0`, toolkit `bin` on PATH and `lib64` on LD_LIBRARY_PATH. Both source workspaces are siblings in `../bonsai2-workspace`.

Wide checks: `compute-sanitizer --tool memcheck --error-exitcode 1 BIN/test-backend-ops test -b CUDA0 -o MUL_MAT_HADAMARD -p 'k=(1024|2048|4096|8192),'`, repeated with `--tool racecheck`. Each tested width has F16/F32 and one/seven rows; the wider operator suite also includes smaller widths and larger row counts.

CPU sanitizer configuration: Debug, `GGML_CUDA=OFF`, `GGML_METAL=OFF`, `LLAMA_SANITIZE_ADDRESS=ON`, `LLAMA_SANITIZE_UNDEFINED=ON`; runtime `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`. Run `test-hadamard` and `test-backend-ops test -b CPU -o MUL_MAT_HADAMARD`. These are scoped checks, not certification of all unrelated upstream operators.

Evaluation: eight 512-token chunks of Wikitext-2 raw test (2048 scored tokens), SHA256 `173c87a53759e0201f33e0ccf978e510c2042d7f2cb78229d9a50d79b9e7dd08`; provenance/license in `eval-source.json`. Both runtimes: context/batch 512, ubatch128, threads4, F16 K/V, flash attention on, CUDA0, `-ngl 99`, `--fit off`, `-lv 4`. The reference writes logits with its evaluation tokens; patched KLD consumes those exact tokens. All three final logs explicitly record 65/65 layers and transform coverage.

Predeclared acceptance: finite outputs, full offload/coverage, absolute relative PPL delta ≤1%, mean KLD ≤0.001 nats/token. Actual reference PPL **9.2812 ±0.54782**, patched **9.2855 ±0.54799**, delta **+0.04633%**; mean KLD **0.000139 ±0.000005**, maximum **0.003520**, RMS probability difference **0.298 ±0.016%**, same top token **99.412 ±0.169%**. Reference logits SHA256 `fd5098ca8e587104e6a23f3868c4d14feb0f116122ab5f4a131152a4078e3501`. The tool compresses reference logits; its base PPL 9.279635 and occasional tiny negative per-token KLD reflect that numerical approximation. These results certify this bounded corpus/checkpoint/settings comparison, not broad model capability or bitwise identity.

Original fixture bounds stay 0.0005 F32 and 0.03 quantized. Fixed GPU identity relative L2 is 2.7555e-7; Q2_0 0.00872038; MoE 8.593e-5; Qwen35 ≤9.44e-6. See full maximum-absolute/relative measurements in the fixture log.

## Measured performance after correctness

Release builds on the same GPU/toolkit, prompt512, generation128, five repetitions, batch512/ubatch128, threads4, F16 K/V, flash attention on, split mode none, ngl99, CUDA_VISIBLE_DEVICES=0. Server stopped during both runs; desktop GPU activity remains. Values are mean ± sample standard deviation in tokens/s. Memory is sampled approximately every 0.25 seconds through nvidia-smi; host RSS is /usr/bin/time maximum and includes mapped checkpoint pages. Sampled peaks may miss shorter spikes and total GPU usage includes the desktop.

| Runtime | Prompt512 tok/s | Generation128 tok/s | Sampled process MiB | Sampled total GPU MiB | Peak host RSS KiB |
| --- | --- | --- | --- | --- | --- |
| patched | 494.12 ± 8.38 | 30.84 ± 0.07 | 7400 | 7894 | 7803072 |
| reference | 527.81 ± 6.66 | 32.70 ± 0.27 | 7376 | 7894 | 7803208 |

Measurements do not establish a general speedup. Raw samples, source revisions and all settings are retained.

## Service and retained failures

The service uses `http://127.0.0.1:8080/v1`, model `bonsai2`, context2048, batch128/ubatch32, threads4, F16 KV and full GPU offload. Start/stop instructions are in `PROJECT.md`. Live logs: `../bonsai2-workspace/service.log`; PID: `service.pid`; installation: `project-state.json`. Evidence snapshot: `service.log`. No Ollama compatibility was implemented or claimed.

The unrelated container `jungle-trap-public` initially occupied 8080. The user explicitly approved stopping it, including its other ports 2222, 2323, 3005 and 8081–8084. It was stopped, not deleted. To restore it later, stop Bonsai first, then `docker start jungle-trap-public`.

Retained failures: initial F32 GPU identity relative L2 0.000618 exceeded the original 0.0005 assertion (`fixtures-gpu-initial-failed.log`). Environment TF32/F32 and fusion controls did not fix it. Patch0007 routes the approximate F32 MMF selection to cuBLAS with saved/restored pedantic F32 math; quantized paths and the actual FWHT remain. Final full setup and quality runs passed. Initial sanitizer operator construction encountered unrelated invalid image interpolation enum513 before filtering (`sanitize-operators-initial-failed.log`); patch0006 constructs only Hadamard cases for that exact filter, retaining all cases in the default suite. That unrelated image path remains outside certified scope. Initial reference linking lacked the local CUDA library search path; `reference-build-retry.log` records successful linking without changing reference source. Initial PPL/KLD logs lacked verbose loader/offload evidence, so final runs repeated identical settings with increased log verbosity. Initial service bind failure and successful reruns are retained. No failed or unavailable check is represented as a pass.
