# Bonsai 2 Hadamard integration for llama.cpp

A reproducible private patch for the official Bonsai 2 27B **Q2_0 development checkpoint**. It combines Prism's existing runtime integration with the wide CUDA FWHT work, adds metadata guards and model-level regression tests, and supplies scripts to apply, build, and validate the result. The build scripts do not submit upstream. The optional `submit_pr.py --publish` script creates a private project handoff PR for Ubuntu validation.

The exact upstream base, pull request revisions, patch checksum, and patched-file checksums are in `source.json`. The checkpoint revision and SHA-256 are in `model.json`. This is a pinned development integration, not a claim that Bonsai 2 support is merged into mainline.

## Project quick start

See `PROJECT.md` for the executable Ubuntu setup, local project API, and private handoff PR submission. On the Ubuntu GPU host, run `python3 scripts/project.py setup --backend cuda`, then `python3 scripts/project.py serve`. The remaining GPU acceptance gates are in `CODEX_UBUNTU_TASK.md`.

## Use

Requires Python 3.9+, Git, CMake, a C/C++ compiler, and Ninja or Make. CUDA additionally needs the CUDA toolkit and an NVIDIA GPU. Metal needs an Apple Silicon macOS host with the Xcode command line tools. Builds and downloads run on your own machine.

From this directory, choose one backend:

```sh
python3 scripts/build.py --directory ../llama-bonsai2 --backend cpu --jobs 4
```

For an NVIDIA host use `--backend cuda`; for an Apple Silicon host use `--backend metal`. The script clones a separate pinned checkout, verifies and applies the combined patch, builds the tools, and runs the selected backend's operator and model tests. It refuses an unrelated dirty checkout. Repeating it with the exact patch already applied is supported. `--apply-only` skips compilation; `--cmake /path/to/cmake` and `--ninja /path/to/ninja` support nonstandard installations.

On a CUDA host with several cards, set `CUDA_VISIBLE_DEVICES=0` before running the build/test commands to keep the experiment on one GPU. The real-model verifier explicitly selects `CUDA0` or `MTL0` in GPU mode.

The build includes `llama-server`, `llama-cli`, `llama-perplexity`, and `llama-bench`. The tools are under `../llama-bonsai2/build-bonsai2-BACKEND/bin/`; test logs are in the adjacent `evidence/` directory. It disables the optional web UI download. The server still exposes its inference API.

Download the **7,626,008,928-byte** public Q2_0 checkpoint with an exact revision and checksum:

```sh
python3 scripts/download_model.py --directory ../models-bonsai2
```

Then exercise the actual model, substituting your backend and binary path as appropriate:

```sh
python3 scripts/verify_model.py \
  --binary ../llama-bonsai2/build-bonsai2-cpu/bin/llama-server \
  --model ../models-bonsai2/Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf \
  --backend cpu --output ../bonsai2-model-evidence
```

Verification starts a server on loopback, checks the checkpoint hash and transform load record, and tests an exact marker plus constrained JSON arithmetic. GPU mode also requires the requested device and full layer offload in the log. Requests, responses, timing, and server logs are retained. A fresh output directory is required to preserve previous evidence. It stops its server on exit. `--architect` optionally generates a longer Systems Architect prompt; that answer needs a human quality review. On a CPU the 27B checkpoint can be slow, and memory pressure makes timing unsuitable for a performance comparison.

For interactive local use after verification:

```sh
../llama-bonsai2/build-bonsai2-cpu/bin/llama-server \
  -m ../models-bonsai2/Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf \
  --host 127.0.0.1 -ngl 0 -c 2048 -np 1 --fit off \
  --jinja --reasoning off --reasoning-budget 0
```

Use `-ngl 99` with a CUDA/Metal binary on a host with enough device memory. The program's ordinary memory and context limits still apply.

## What is included

| File | Purpose |
| --- | --- |
| `patches/0001-prism-runtime.patch` | Existing Prism PR #29600: metadata, signs, graph transforms, inverse embedding lookup, tied output, grouped GDN, and transform coverage check |
| `patches/0002-cuda-wide.patch` | Existing PR #29100: CUDA FWHT widths 1024, 2048, 4096, and 8192 |
| `patches/0003-metadata-guards.patch` | Additional fail-closed metadata validation and bounded rotation allocation |
| `patches/0004-regression-tests.patch` | Standalone generated GGUF model tests, registered with CTest |
| `patches/bonsai2-combined.patch` | Complete patch used by the installer |
| `DESIGN.md` | Mathematical basis, ownership, graph integration, and test rationale |
| `STATUS.md`, `evidence/` | Actual validation results and limits |
| `NEXT_AGENT.md` | Remaining hardware and upstream review work |

The numbered patches may be applied in order instead of the combined patch. Do not apply both routes to one checkout.

## Scope

The supported experiment is the pinned text-only Q2_0 checkpoint, ordinary inference, and CPU or one CUDA/Metal GPU. Fork-specific `PQ2_0` and `PTQ1_0`, vision projectors, multi-GPU split modes, RPC, LoRA adapters, and speculative/MTP decoding are outside this package's validation. The source PR includes an MTP embedding path, but this package does not certify it.

Read `STATUS.md` before using a GPU build. Hardware tests and comparative perplexity/KLD are explicit outstanding review gates. Neither a fluent response nor a CPU test certifies an untested GPU kernel.

## Attribution and contribution

The runtime is based on [Prism's existing PR #29600](https://github.com/ggml-org/llama.cpp/pull/29600), pinned to `fc50db4300e04a3af12e5fd1b8042afa87b1f1b7`. The CUDA change is from [PR #29100](https://github.com/ggml-org/llama.cpp/pull/29100), pinned to `7d9305fb51689840aa084eb0a60f4c03950c8988`. The guards, regression tests, reproducibility scripts, and validation notes were prepared with substantial AI assistance for private use. Existing work is attributed, not presented as newly authored here.

llama.cpp's [AGENTS.md](https://github.com/ggml-org/llama.cpp/blob/836d57176dc699a726c55418e4f96b8ca628e1bf/AGENTS.md) prohibits automated commits and PR submissions, and states that private forks are exempt from its contributor requirements. This package takes the private-use route allowed by the request. If a human chooses to contribute later, they must understand and own the changes, coordinate with the existing PR authors, complete the hardware gates, disclose AI assistance as required, and write their own submission text. The optional publisher supplies private project handoff text only; it does not produce or submit an upstream contribution.

Code is distributed under the included MIT license; see `NOTICE`. Model weights are not bundled. The official model repository declares Apache-2.0, and its terms apply separately to downloaded weights.
