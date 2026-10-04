# Current entry point

The Ubuntu private project handoff is complete. Start with `UBUNTU_RESULTS.md`, `PROJECT.md`, and the current `STATUS.md`. CUDA, sanitizer/leak, quality, benchmark and API gates passed on the recorded host. Preserve source/model pins, original CPU evidence and preregistered criteria; use ordinary Git in the existing private repository. Metal and broader unsupported features remain unvalidated. Do not publish another handoff or automated upstream contribution.

The original task/checklist below is preserved as historical context and reproducibility guidance; its statements about pending CUDA work describe the earlier handoff.

# Handoff for host validation and human review

The private CPU integration is implemented and has passed the recorded synthetic and real-model checks. Start with `STATUS.md`, `DESIGN.md`, and `source.json`. Reuse the pinned patch and the existing upstream work; do not open a duplicate feature PR.

## CUDA or Metal host

1. Run the packaged `scripts/build.py` with `--backend cuda` or `--backend metal` in a fresh checkout directory. Preserve its `evidence/` directory. It runs CPU fixtures, GPU fixtures, Hadamard operator tests, ordinary matrix multiplication tests, and GGUF tests. It requires a nonzero passing operator suite for the named GPU backend.
2. Run `scripts/download_model.py` and `scripts/verify_model.py` with the same backend. The real-model verifier requires the model's exact checksum, a Hadamard transform load record, the requested GPU device, and full layer offload. Preserve the raw server log and requests/responses. This tests one GPU and does not certify split modes.
3. On CUDA, use the toolchain's memory/race tools on `MUL_MAT_HADAMARD`, especially widths 1024 and 8192 with multiple rows, before treating the wide kernel as verified. Use `test-backend-ops --help` from the built revision for available backend and parameter filters.
4. Compare performance only after correctness. Record driver/toolkit/OS, GPU, source revisions, compiler flags, context, batch, KV types, flash attention, and peak memory. `llama-bench -m MODEL -ngl 99 -p 512 -n 128 -r 5 -o json` is a starting point on a sufficiently provisioned single GPU. Run the same workload on the reference fork.

## Quality comparison against Prism

The inspected Prism fork was `https://github.com/PrismML-Eng/llama.cpp`, branch `prism`, revision `2459f68b5c0eb26261fd5a81682004b93cd645ba`. Pin a reference build and record its exact revision rather than selecting an unknown prebuilt binary. Use the same Q2_0 file and a representative, legally available UTF-8 evaluation text with enough tokens for the requested chunks. Record its SHA-256. Use matching tokenizer, context, threads, batch, KV types, and flash-attention settings.

With the pinned upstream version, the following flags exist; confirm equivalent flags in the reference fork before running:

```sh
REFERENCE_PERPLEXITY -m MODEL -f eval.txt -c 512 -b 512 -ngl 99 \
  --chunks 8 --save-all-logits reference.logits

PATCHED_PERPLEXITY -m MODEL -c 512 -b 512 -ngl 99 \
  --kl-divergence --kl-divergence-base reference.logits

PATCHED_PERPLEXITY -m MODEL -f eval.txt -c 512 -b 512 -ngl 99 --chunks 8
```

`REFERENCE_PERPLEXITY`, `PATCHED_PERPLEXITY`, and `MODEL` above are placeholders for actual executable/model paths. The KLD file contains the reference evaluation tokens; its comparison uses those tokens rather than retokenizing an unrelated prompt. For CPU comparison use `-ngl 0` in both runs. Explicitly match additional runtime settings rather than assuming their defaults agree. These comparative runs were not performed in the completed work.

Require finite outputs, a justified numerical tolerance and reviewed quality deltas, and complete transform coverage before approving a backend. A constrained JSON response alone is not a quality comparison. Agree the numerical acceptance threshold with the existing integration authors; no full-model KLD threshold was invented here.

## Review boundaries

- The loader changes added here are a small extension to Prism's existing contract. Review the 8192 block cap as an intentional private profile decision before adopting it upstream.
- The generated-model suite has an independent Sylvester reference and an asymmetric GDN fixture. Preserve these properties; do not loosen assertions merely to pass a backend.
- The architecture allowlist is inherited from PR #29600. This suite verifies Llama and Qwen35 paths; it does not prove every allowlisted model architecture.
- Multi-GPU rotations must not inherit an unsuitable split weight buffer. This package does not resolve the reported split-buffer problem. Treat multi-GPU tests and any fix as separate work.
- LoRA adapters may be authored in a different basis from folded weights. Review the common matmul helpers and adapter basis before enabling them. MTP/speculative, vision, and fork-specific quantization formats are also outside the completed evidence.
- Leak detection remains pending on a host where LeakSanitizer can inspect processes.

## Upstream conduct

Read the pinned repository's `AGENTS.md`, `CONTRIBUTING.md`, and `skills/code-review/SKILL.md`. The repository prohibits automated commits, AI-written submission text, and automated PR submissions; private forks are exempt from contributor requirements. A human must choose and defend the design, understand the code without AI help, own maintenance, disclose substantial AI assistance, and write any submission or review response themselves. No commit, push, PR description, or upstream message was made or prepared here.

Coordinate with the existing runtime PR #29600 and CUDA PR #29100. Their exact source commits are in `source.json` and attributed in `NOTICE`. The two small supplemental patches are separable from their work. Recheck current PR status and base revisions before proposing any human-owned upstream delta.
