# Bonsai on this Mac

Double-click **Launch Bonsai.command**, or run:

```sh
cd /Users/home/Desktop/bonsai-mac-ollama
python3 scripts/mac_bonsai.py run
```

Open http://127.0.0.1:8765 . Keep the launcher terminal open. Press Ctrl+C in that terminal, double-click Stop Bonsai.command, or run `python3 scripts/mac_bonsai.py stop` to stop the client, Ollama daemon, and its inference runner. Launching again opens the running client instead of creating a second job.

The client streams answers, supports Stop, keeps your draft after a backend failure, and reconnects after the launcher restarts Ollama. Stopped/interrupted answers are labeled and are excluded from subsequent model context. Use New chat to clear the conversation. Reloading also clears it. Conversations are held in browser memory; the client does not save them to disk. Inference stays on this Mac, with Ollama cloud features disabled. The local server only serves the chat page, not workspace files.

This is a text-only client, using non-thinking responses, a 2,048-token context and a 768-token response limit. Older turns are dropped to keep the conversation short. A response that reaches its limit displays a continuation notice. Tool calling, vision, adapters, Desktop integration and full Desktop DL-24 acceptance are not qualified here.

## Runtime and model

This runs an actual separately built Ollama fork, not an API translation proxy. Ollama manages and launches Prism's llama-server inference runner, as specified by that fork's implementation. The existing /Applications/Ollama.app and its models remain unchanged.

- Ollama source: https://github.com/xInterlopeRx/ollama , commit 3db1d7c30173620d6adeda724dbea11c55ece88d (MIT).
- Native runner source: https://github.com/PrismML-Eng/llama.cpp , commit 9a9394a895b96003ca842a6041cb28ac49a108f7 (MIT with included vendor notices).
- Local patch: patches/mac-ollama-file-types.patch, adds truthful PQ2_0/PTQ1_0 names to Ollama's GGUF metadata and tests. No native-kernel changes.
- Model: official prism-ml/Ternary-Bonsai-2-27B-gguf PTQ1_0, revision b072e1d3b35a0a630cece372c2127528e0994386 (Apache-2.0).
- File: models/Ternary-Bonsai-2-27B-PTQ1_0.gguf, 5,946,648,928 bytes.
- SHA256: 53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3.
- Ollama model name: bonsai2:ptq1. Manifest digest: b7f85093ffae77520e44ba496a75154c98b51614d083dbb2a939041cdad1cefe.
- API: http://127.0.0.1:11435 . Separate model store: .state/models (hardlinks verified weights; no duplicate download).

The root model.json and Ubuntu commands still describe the older Q2_0 validation checkpoint. Use the Mac launcher for this PTQ1_0 model. Stock Ollama does not supply these fork-specific kernels.

For terminal chat while the launcher is running:

```sh
OLLAMA_HOST=127.0.0.1:11435 runtime/ollama-prism/build-mac/bin/ollama run bonsai2:ptq1 --think=false
```

## Rebuild and recover

Requires Apple Silicon macOS, Python 3.9+, Git, CMake, Go, and Xcode command line tools. Go automatically obtains the source-required 1.26 toolchain. All pinned sources and dependencies build locally; no cloud inference is needed.

Stop the running launcher before rebuilding or re-importing:

```sh
python3 scripts/mac_bonsai.py build
python3 scripts/mac_bonsai.py setup
python3 scripts/mac_bonsai.py run
```

The build checks source pins and preserves unexpected source changes. Setup verifies the full model checksum before importing. Launch also verifies the checksum and installed model digest. Occupied API/client ports are reported instead of stopping unrelated processes. One launcher is enforced by a local lock. A crashed daemon's process group is cleaned before restart; a backend/model failure preserves the user's draft, which must be retried explicitly rather than silently replayed.

Runtime data is in .state/ (excluded from Git). Troubleshooting logs: .state/ollama.log and the launcher terminal. These files remain local. Do not post logs containing private requests without inspection. Models and runtime build checkouts are also excluded from Git. No upstream submission, remote push, deployment, OS service or recurring automation was installed.

## Observed acceptance, October 4, 2026

Actual Apple M4, 16 GB unified memory, macOS 26.5.2:

- Metal build and Ollama GGUF/runner tests passed.
- Actual Ollama import reports PTQ1_0; all 65/65 layers offloaded to MTL0 (Apple M4), 402 Hadamard weights and one inverse lookup loaded.
- Exact marker BONSAI_OK and structured arithmetic sum=43 passed.
- Real API streaming passed with seven content chunks; browser chat streamed a coherent desk-organization response at about 9.3 tokens/second. These are smoke observations, not a controlled performance benchmark.
- Browser Stop triggered native task cancellation, slot release, and all-slots-idle; a new prompt returned READY_AFTER_STOP in about 2.2 seconds.
- SIGKILL during a browser response triggered daemon/runner cleanup and automatic API restart in about 2.2 seconds. Browser preserved its draft; post-recovery arithmetic returned 43.
- Ollama reported 6,279,282,031 bytes (~5.85 GiB) of model/runtime allocation at context 2048. Native model Metal buffer: 5,660.56 MiB; KV: 128 MiB; recurrent state: 149.62 MiB; compute: 50.21 MiB. Prompt cache is capped at 128 MiB and one context checkpoint.
- System-wide memory availability: ~20% loaded, ~62% unloaded in the observed workload. Swap: ~10.56 GB loaded / ~10.54 GB unloaded, including existing system use. No swap-free, isolated-process peak-memory, or general memory-headroom guarantee is claimed. Close other large applications if the Mac feels slow; stopping/unloading Bonsai releases its active allocation.
- Duplicate launch rejected; private-file URL returned 404; unexpected Host header returned 403.

Evidence is under evidence/mac/. The real-model checks verify this client/runtime path, not broad quantization quality parity or every Metal operator. Independent upstream kernel correctness/perplexity benchmarking remains outside this bounded client delivery.
