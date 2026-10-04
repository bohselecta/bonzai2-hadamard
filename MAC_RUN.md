# Mac Bonsai / Ollama job

Checkpoint: October 4, 2026 (America/Chicago).
State: VERIFIED — bounded text-only Mac client through actual patched Ollama/Metal.

## Identity and scope

- Repository: https://github.com/bohselecta/bonzai2-hadamard (public).
- Checkout: /Users/home/Desktop/bonsai-mac-ollama.
- Chat: 01a106de-b395-74e0-8a8e-979a937a4064; executor Haydens-MacBook-Pro-2.local.
- Branch: work/bonsai2-mac-ollama; starting HEAD addfbe01ddad653582f5312f88017f07aa9a0512.
- Origin default branch: work/bonsai2-ubuntu, unchanged.
- GitHub CLI active identity: corgi-verse; bohselecta also authenticated. Repository read/clone succeeded. No remote mutation attempted.
- Objective: usable Mac Bonsai client through actual Ollama, M4 Metal evidence, streaming, cancellation, recovery, memory observations.
- Current mutation scope: Mac launcher/client/config/docs, evidence/mac/, local package tests/checksums, and the small Ollama file-type metadata patch. Ignored runtime/ source/build checkouts and .state/ belong to this single job. Prism native source is unchanged.
- Authority: user's clone/start request and attached handoff. One coding worker; no other queue repository work started.
- Publication: no push, merge, release, deployment, upstream contribution or model download. No CI configuration found in this checkout; downstream effects need inventory before publication.

## Baseline evidence

- PASS: cloned source branch at handoff anchor; clean initial checkout; no open repository PRs reported; one local worktree.
- PASS: Apple M4, 10 CPU cores, 16 GB unified RAM, 10 GPU cores, Metal 4, macOS 26.5.2 arm64. Identifying hardware serials are intentionally omitted.
- PASS: existing Ollama app/process, CLI version 0.32.0. Listed models are nomic-embed-text, qwen2.5-coder:3b and gemma3:4b; no Bonsai model listed.
- PASS: CMake and Xcode command line tools present. Ninja not found.
- PASS after repair: python3 tests/test-project-tools.py, 7 tests. Log: evidence/mac/project-tools-check.log. Original six-test suite failed one Linux-specific expectation on macOS. The repaired test mocks Linux for the missing-nvcc case; a separate test verifies macOS rejection remains intact. Production launcher unchanged; package checksum refreshed.
- NOT_RUN: model inference, Metal runtime tests, client streaming/cancellation/recovery, measured inference memory.
- Model selector/reasoning/service tier: not exposed by the tools used; no setting change or verified cost claim.

## Concrete dependency

The handoff asks for an intended roughly 5 GB model and patched Ollama/client lineage. This repository instead pins prism-ml/Ternary-Bonsai-2-27B-gguf-dev at 2a263ef827a2e215f3ddd14c9871a5bd1800fcbc, file Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf, size 7,626,008,928 bytes, SHA256 4f99aed01b8a877e153f9aa6569a4440fe17c59701cc0953e36d7f460549e70e. Its backend is patched llama.cpp; PROJECT.md explicitly says Ollama integration is unvalidated. No Ollama patch or client is contained here. GitHub owner repository-name search found only this Bonsai repository. Local targeted filename search did not locate another Bonsai model/source manifest; that is not proof none exists.

The handoff explicitly requires a decision for a material artifact/backend mismatch. Pending question requests the intended model artifact and patched Ollama/client source, or explicit selection of the 7.63 GB checkpoint. Selecting that checkpoint alone does not prove Ollama compatibility. No substitute backend/model has been chosen.

## Resume

Read this checkpoint and the user's answer, run git status --short and git rev-parse HEAD, then inspect the supplied exact artifact/runtime/client sources and applicable AGENTS.md before widening permitted paths. Reuse installed Ollama and any verified existing model bytes. Re-run affected checks after changes. Do not run project.py setup on this Mac: it is a Linux launcher and would target the different checkpoint. The native build.py Metal route is available as a component check but cannot satisfy Ollama acceptance by itself.

## Model resolution (October 4, 2026)

User corrected the estimated model size and authorized finding/downloading the right model. Official Prism model card identifies PTQ1_0 as its compact 5.95 GB language-model packing. Selected official artifact: prism-ml/Ternary-Bonsai-2-27B-gguf, revision b072e1d3b35a0a630cece372c2127528e0994386, Ternary-Bonsai-2-27B-PTQ1_0.gguf, 5,946,648,928 bytes, SHA256 53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3, Apache-2.0. API metadata retained in evidence/mac/model.json. The legacy model.json remains unchanged because it defines the Ubuntu regression checkpoint. No adapters or optional vision projector selected.

Official sources inspected: https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf and https://github.com/PrismML-Eng/Bonsai-demo . These require custom Prism ternary runtime kernels. The demo README currently describes llama.cpp and MLX, with no Ollama setup found. This resolves the download choice; it does not establish actual Ollama support or authorize a silent backend replacement.

Download target: models/Ternary-Bonsai-2-27B-PTQ1_0.gguf (ignored model weights); transfer uses a preserved .part file, with size and checksum verification required before rename. Download log: evidence/mac/download.log. Available disk before download: 108 GiB.

## Download completion

PASS: official PTQ1_0 model downloaded and verified at October 4, 2026, 7:35 AM America/Chicago. Actual size 5,946,648,928 bytes, SHA256 53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3, GGUF header confirmed. Final path: /Users/home/Desktop/bonsai-mac-ollama/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf. Evidence: evidence/mac/model-download-result.json. Downloaded bytes are ignored by Git. No inference run or Ollama import claimed.

Next safe action: reconcile actual Ollama source/runtime support for PTQ1_0 and Hadamard transforms against the official Prism lineage. Inspect existing client sources before implementation; do not pass the file to an incompatible stock runtime or replace Ollama with llama.cpp without resolving the backend requirement.

## Mac client completion checkpoint

The earlier model/backend dependency is RESOLVED for this bounded client: the compact official model is running through a real Ollama fork (xInterlopeRx/ollama at 3db1d7c30173620d6adeda724dbea11c55ece88d), which manages its pinned Prism runner (9a9394a895b96003ca842a6041cb28ac49a108f7) on M4 Metal. Stock installed Ollama is preserved. The fork documents its installer as Linux-only; its existing CMake Apple path built and ran here. One small patch labels custom quantization metadata correctly; native source/kernel code is unchanged.

PASS: build and repeat-build via scripts/mac_bonsai.py build; GGUF/runner Go suites; seven package orchestration tests; three launcher safety tests; model size/SHA256; real exact-marker/structured-arithmetic responses; 65/65 Metal offload and 402 Hadamard weights; API and browser streaming; native cancellation and immediate reuse; daemon failure cleanup/restart with retained browser draft and successful new inference; graceful shutdown without orphan runner or effect on installed Ollama; explicit Stop command; duplicate launch and HTTP private-path/Host protections; final launch/inference. Evidence under evidence/mac/; details and memory limits in MAC_CLIENT.md.

The first repeat-build attempt safely refused its own generated build-mac directory as unrelated work. The launcher now excludes only that owned build output in the nested checkout; repeat-build passed. Other dirty source remains rejected.

Usable path: http://127.0.0.1:8765, currently served by this job. Double-click Launch Bonsai.command to launch/open; Stop Bonsai.command stops this owned instance. Terminal alternatives and clean rebuild/setup commands are in MAC_CLIENT.md. .state/launcher.pid and .state/backend.json identify the running owned processes. No scheduler, OS service, global Ollama replacement or portfolio continuation was installed.

Scope limits/NOT_RUN: tools, vision, adapters, full Desktop integration/DL-24, broad quantization quality benchmarking, standalone all-operator Metal suite, physical accessibility/installer acceptance. Text chat uses non-thinking mode, context 2048 and response limit 768. Real workload memory allocation is ~6.28 GB; observed system memory availability ~20% loaded/~62% unloaded, with heavy existing swap use. No swap-free or isolated peak-memory claim.

No remaining human action for using this bounded local client. No remote push, PR, merge or deployment performed. Origin has only work/bonsai2-ubuntu as its default branch; no main was invented or Ubuntu branch overwritten. Local Mac source is reviewable on work/bonsai2-mac-ollama. Latest local revision is the Git HEAD of that branch; source/runtime/model identities above remain pinned independently.

Safe resume: inspect git status/log and this checkpoint; use the launch/stop commands for runtime checks. Rebuild only if source changes require it. Do not continue another portfolio repository without resolving that next unit's task/checkout/authority.
