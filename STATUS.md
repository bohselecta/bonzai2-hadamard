# Validation status

Validated on 2026-10-03 on Linux x86_64, AMD EPYC 9V74, GCC 13.3, CMake 4.4.3. The execution environment has an 8 GiB memory limit and no CUDA or Metal device. See `evidence/environment.json` for host details. The base and all source/model pins are recorded in `source.json` and `model.json`.

## Completed

| Check | Actual result | Evidence |
| --- | --- | --- |
| Combined patch on a clean pinned upstream worktree | Applied; all 11 patched files match SHA-256 manifest | `patch-apply-check.log` |
| Applying the numbered patches in order | Applied; identical to the combined patch | `patch-series-check.log` |
| Repeat apply | Verified existing exact patch | `patch-apply-check.log` |
| Unrelated dirty checkout | Rejected; unrelated file preserved | `patch-dirty-check.log` |
| Packaged CPU build script | Completed; warnings treated as errors; all seven requested targets built | `package-build-test.log`, `incremental-build-check.log`, `fresh-cpu-build/` |
| Generated-model equivalence | 10/10 cases passed, with 224 logits checked per case | `fresh-cpu-build/fixtures-cpu.log` |
| Malformed metadata | 17/17 rejected with the intended error | `fresh-cpu-build/fixtures-cpu.log` |
| CTest registration | 1/1 `test-hadamard` passed | `ctest-hadamard.log` |
| Existing CPU Hadamard operator tests | 32/32 passed, including F16/F32 and widths through 8192 | `fresh-cpu-build/MUL_MAT_HADAMARD.log` |
| Existing CPU matrix multiplication tests | 1330/1330 passed | `fresh-cpu-build/MUL_MAT.log` |
| Existing GGUF tests | 101/101 passed | `fresh-cpu-build/gguf.log` |
| Address/undefined sanitizers, Debug build | All 27 generated-model checks passed, with no reported ASan/UBSan error | `sanitize-tests.log`, `configure-sanitize.log`, `build-sanitize.log` |
| Orphan-version negative control | Removing only the new guard caused the suite to fail; restored guard passed | `negative-control.log` plus final fixture log |
| GPU fixture request without a GPU | Rejected; did not run a CPU success in its place | `gpu-negative-control.log` |
| CUDA build request without nvcc | Rejected explicitly | `cuda-build-negative-check.log` |
| Official real checkpoint | Full SHA-256 verified; model loaded with 402 transforms, 1 inverse lookup, 1 rotation, and 3 sign vectors | `real-model/server.log`, `model.json` |
| Real-model exact marker | Returned `BONSAI_OK`, finish reason `stop` | `real-model/marker-response.json` |
| Real-model constrained JSON | Returned integer `sum: 43` for 17 + 26, finish reason `stop` | `real-model/json-arithmetic-response.json` |
| Downloader reuse/checksum path | Recognized and verified the existing pinned checkpoint | `download-script-check.log` |

Evidence paths in the table are relative to `evidence/`. Operator logs may include upstream cases reported as unsupported; the reported counts are the cases the CPU backend exercised successfully. The Hadamard CPU path is a dense reference and does not execute CUDA FWHT.

The unquantized logit comparisons have relative L2 errors below 0.00005. The Q2_0 comparison is about 0.00881 because CPU activation quantization is basis dependent; it passes the declared 0.03 bound. It is not a zero-error quantized equivalence claim.

LeakSanitizer could not inspect `/proc/.../task` in this environment and exited with an environment error. Address/undefined validation was rerun successfully with `ASAN_OPTIONS=detect_leaks=0` and `UBSAN_OPTIONS=halt_on_error=1`. Leak detection is not certified. The earlier disk-space failure was resolved before the successful sanitizer run.

The real-model checks took about 99 seconds and 159 seconds respectively, including their prompt processing. Compilation overlapped with these checks and the host was memory constrained. These recorded timings are observations for the smoke tests, not a performance comparison or a GPU estimate. The optional Systems Architect case was not run.

## Still required for an upstream readiness claim

- Compile and run this exact patch on CUDA and Metal hosts. CPU validation cannot validate their kernels, scheduler behavior, or device buffer ownership.
- Compare the exact checkpoint against a pinned Prism runtime on identical evaluation tokens, with matching context, batch, KV types, flash attention, and backend settings. Record perplexity and KLD rather than relying on generation fluency.
- Measure prompt processing, token generation, and memory on the intended hardware with comparable builds and settings.
- Review and validate multi-GPU split buffers before enabling split modes. Review LoRA adapter basis semantics before claiming adapter support. Broader architecture and MTP/speculative coverage are also separate gates.
- Have a human contributor coordinate with the existing PR authors, review every change, and own maintenance before any upstream submission.

The deliverable completes a usable, tested private CPU integration and supplies the exact code and host commands for the remaining GPU gates. No upstream merge, GPU execution, comparative quality result, or PR submission is claimed.

## Project integration and executable Ubuntu handoff (2026-10-04)

Added `scripts/project.py` to build, download, verify, and serve the local project API, and `scripts/submit_pr.py` to prepare a concrete Git handoff and submit it from an authenticated Ubuntu host. The selected destination is a new private `bohselecta/bonsai2-hadamard` repository. The publisher creates a draft PR with the full integration and remaining Ubuntu task; it does not submit upstream.

The unchanged combined patch was freshly applied to the exact pinned base and all 11 patched-file hashes matched. Six offline orchestration checks passed, including a real Git branch preparation, preservation of the patch, rejection of dirty work, account mismatch rejection, publication ordering/retry with simulated GitHub responses, selected CUDA device serving, checkpoint-change rejection, and no server installation state after failed verification. See `evidence/project-tools-check.log`. Simulated publication in those tests does not create a real repository or PR.

This session has no CUDA device/toolkit and no authenticated GitHub CLI, and its connected GitHub operations do not include repository creation. The script therefore has not published a real PR here. The previous CPU/model evidence remains authoritative for the runtime; this update does not claim another 27B run or GPU validation. See `PROJECT.md` for the executable project setup and submission commands.
