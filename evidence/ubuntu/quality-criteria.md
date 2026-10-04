# Criteria fixed before comparative execution

Compare the pinned Q2_0 checkpoint on Wikitext-2 raw test text, eight 512-token chunks, identical tokens (reference KLD file), CUDA0, full layer offload, context/batch 512, ubatch 128, four threads, F16 KV and flash attention enabled.

Require finite outputs, complete transform coverage, absolute relative perplexity difference <= 1%, and mean KLD <= 0.001 nats/token. The perplexity bound limits cross-entropy displacement to approximately 0.01 nats/token; the KL bound implies an average distribution total-variation bound of about 2.24% by Pinsker and Jensen. These are private integration criteria, not an upstream endorsement or a fluency score. Record numerical probability/logit statistics from the KLD tool. Existing independent generated-model absolute and relative L2 tolerances remain 0.0005 (F32) and 0.03 (quantized cases). No adjustment after seeing results.

Benchmark only after these and device/sanitizer correctness gates pass. Use matched CUDA0, F16 KV, flash attention, prompt 512, generation 128, five repetitions.
