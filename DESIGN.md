# Design and verification rationale

## Why the existing FWHT operator is insufficient

Bonsai 2 stores selected weight rows in a signed, blockwise Hadamard basis. Knowing the Q2_0 quantization type lets a loader read bytes, but does not restore the function computed by those weights. Correct inference needs both the checkpoint's explicit signs and transforms at every affected graph edge, including embedding lookup and grouped recurrent head geometry.

This package reuses PR #29600's model integration rather than inventing a second metadata contract. It adds the separate wide CUDA transform work because the checkpoint uses block size 1024. At the pinned upstream base, CUDA F16 input support and Metal's wide/F16 transform support already exist.

## Basis convention

Use column activations `x` and conventional weight matrix `W` (output rows, input columns). Let `H` be the block diagonal normalized Sylvester Walsh-Hadamard matrix and `S` be the diagonal matrix of explicit signs. `H` is symmetric and `H H = I`; `S S = I`. For ordinary folded weights:

```text
W_fold = W S H
x_fold = H S x
W_fold x_fold = W x
```

The forward graph therefore multiplies signs **before** applying Hadamard. It must not exchange the two operations.

A stored embedding row, considered as a column, is `z = H S e`. Lookup recovery is:

```text
e = S H z
```

The inverse lookup applies Hadamard **before** signs. Version 2 marks a tied embedding/output table explicitly: lookup uses the inverse path, while the output head consumes the forward-transformed activation. The output tensor must be absent in the file and its runtime alias must match the embedding.

With grouped GDN metadata, the recurrent output activation arrives in tiled feature order `[hd, nk, rep]` and the checkpoint's folded `ssm_out` expects `[hd, rep, nk]`. The graph makes the tensor contiguous, reshapes, permutes the key and repeat axes, then applies signs and Hadamard. The test fixture uses 2 key heads and 3 repeats so exchanging these axes cannot accidentally be an identity.

## Metadata and ownership

The loader accepts the existing `prism.hadamard` contract: version, block size, transform name, input axis, sign mode, affected weights, optional inverse lookup weights, optional sign arrays, and GDN grouping. It limits architectures and tensor names to paths handled by the graph helpers. The graph coverage check runs before backend scheduling inserts copies.

Rotation and sign tensors live in the model's persistent context/buffer ownership, alongside weights. A rotation is reused for each `(block_size, backend buffer type)`; signs are reused for each `(input_width, backend buffer type)`. CPU repacking buffer types are normalized to ordinary CPU buffers. Forward/inverse tensor-to-transform maps are supplied to graph construction; ordinary models have no transforms. A graph-local memo avoids repeated rotation for projections sharing the same activation and rotation.

The graph uses `llama_mul_mat_hadamard`, which carries the existing `GGML_HINT_SRC0_IS_HADAMARD` convention. CPU can compute the dense matrix reference. CUDA and Metal can select FWHT. No new public API or quantization type is introduced.

Additional validation in this package:

- Reject any orphan `prism.hadamard.*` key when `version` is absent. Otherwise a partially damaged header silently turns a folded model into an untransformed model.
- Reject zero, non-power-of-two, or greater-than-8192 block size before computing the persistent dense rotation's square. This private profile deliberately caps the allocation at the tested wide-kernel ceiling. The checkpoint's 1024 block is unaffected; a hypothetical larger valid block is outside this profile.
- Reject repeated sign widths. Verify available sign elements using remaining length rather than overflow-prone addition.
- If `inverse_weight_names` exists, require a correctly typed array; an absent optional array remains valid. A wrong scalar type must not silently skip embedding recovery.

These checks do not constitute a general memory budget for arbitrary models or all possible combinations of backend buffers. At the maximum block size the dense fallback rotation alone is 256 MiB per buffer type. Multi-GPU split buffer ownership needs separate work and validation.

## CUDA wide blocks

PR #29100 adds one row per 256-thread block for widths 1024 through 8192. Each thread holds `N/256` elements in registers. Stages within a warp use XOR shuffles, stages crossing warps use a shared-memory exchange with barriers, and stages above the block width pair registers in the same thread. Values are normalized by `1/sqrt(N)` once. Inputs may be F16 or F32; outputs are F32. The old 64 through 512 path is retained.

The wide FWHT patch is carried verbatim from its identified commit. Ubuntu validation now exercises all four widths with F16/F32 and multiple rows under memcheck/racecheck; see UBUNTU_RESULTS.md. Supplemental patch0007 avoids TF32 basis-dependent rounding for ordinary F32 MMF selection by using pedantic cuBLAS F32 math and restoring the prior handle mode. It leaves the FWHT dispatch and quantized kernels intact. Patch0006 limits construction to Hadamard fixtures for the exact sanitizer filter; the default suite retains all original cases.

## Regression tests

`tests/test-hadamard.cpp` generates tiny complete GGUF models in C++, using existing gguf/ggml/llama APIs. It needs no model download, Python dependency, or network. Its dense double-accumulation Sylvester reference folds rows independently of runtime FWHT.

For every valid case it compares the ordinary and folded models across a four-token prefill and three one-token decode calls, collecting all 224 vocabulary logits. Every value must be finite. Both maximum absolute error and relative L2 error must pass. F32 cases use tolerance 0.0005; Q2_0 and Q8 KV cases use 0.03 because activation/cache quantization introduces legitimate basis-dependent error. Tolerances are explicit, not selected from a real-model fluency score.

| Case | Failure it can detect |
| --- | --- |
| Identity signs | Missing/incorrect normalized block rotation |
| Explicit signs | Incorrect sign application or order |
| Inverse lookup | Failure to restore the embedding basis |
| Tied output v2 | Incorrect lookup/head dual use |
| Q2_0 | Official quantization path with exactly representable rotated trits |
| Q8 KV | Interaction with upstream's existing KV basis transforms and flash attention |
| MoE matmul ID | Expert projections bypassing the common transform path |
| Qwen35 hybrid | Recurrent and full-attention layers in the same model |
| Grouped GDN | Key/repeat feature permutation, with asymmetric geometry |
| Block 128 | Reusing a hard-coded block size |

Seventeen malformed fixtures must fail model loading with their intended error, rather than merely fail at an unrelated missing tensor. They cover metadata version, block geometry, transform/axis/sign mode, sign value/type/length/duplicate width, weight existence/whitelist, optional inverse type/name, and tied-output tagging.

A negative control removed the orphan-version guard only. The suite then failed because the malformed model was accepted; restoring the guard returned it to green. This checks that the regression detects the added behavior. It does not assert mutation coverage of every validation branch.

`--ngl 99` permits the same fixtures to run with GPU layers but rejects the absence of a GPU. The build script separately filters backend operator tests and verifies that the selected backend actually ran a nonzero passing suite. A zero-test successful process cannot pass that gate. The real-model verifier also checks full layer offload in GPU mode. These checks still require a real CUDA/Metal host.

## Boundaries

This is a text inference integration of the official Q2_0 development file. It does not upstream `PQ2_0`, `PTQ1_0`, or a multimodal projector. Multi-GPU split modes, RPC, LoRA basis compatibility, speculative/MTP decoding, every admitted Qwen architecture, remain outside the completed evidence. A bounded same-token Prism comparison is recorded in UBUNTU_RESULTS.md; it establishes tolerance-based agreement, not exact equality. The architecture allowlist comes from the source PR; the new tests exercise Llama and Qwen35, not every allowlisted architecture.

Real-model marker/arithmetic checks establish basic operation only. Perplexity/KLD comparisons on identical tokens and host backend testing are necessary before a claim of full upstream readiness.
