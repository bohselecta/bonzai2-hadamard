# Bonsai 2 — Mac client and native runtime integration

This repository keeps two verified platform paths together, with separate model and runtime pins. Choose the path for your machine before building or downloading a model.

| Platform | Model | Runtime | Start here |
| --- | --- | --- | --- |
| Apple Silicon Mac | Official PTQ1_0, 5.95 GB | Separate patched Ollama with Prism Metal runner | [Mac client](MAC_CLIENT.md) |
| Ubuntu / NVIDIA | Pinned Q2_0 development checkpoint, 7.63 GB | Patched native llama.cpp, CUDA | [Ubuntu setup](PROJECT.md), [recorded results](UBUNTU_RESULTS.md) |
| CPU / native integration development | Same pinned Q2_0 checkpoint | Patched native llama.cpp | [Native integration guide](docs/NATIVE_INTEGRATION.md) |

The Mac path has actual M4 Metal inference, streaming, cancellation, restart recovery and memory observations. The Ubuntu evidence records completed RTX 3060 qualification on its original host. These checks apply to their respective model/runtime combinations; they do not transfer automatically between platforms.

## Mac chat

On the prepared Mac, double-click **Launch Bonsai.command** or run:

```sh
python3 scripts/mac_bonsai.py run
```

Open http://127.0.0.1:8765 . To stop this client and its dedicated backend, use **Stop Bonsai.command** or `python3 scripts/mac_bonsai.py stop`. First-time build/setup instructions, required model bytes and limits are in [MAC_CLIENT.md](MAC_CLIENT.md).

The installed Ollama app is preserved. This client uses its own source build, local port and model store. Model weights and generated runtime files are excluded from Git.

## Ubuntu native service

On the selected authorized Ubuntu GPU host:

```sh
python3 scripts/project.py setup --backend cuda
python3 scripts/project.py serve
```

Read [PROJECT.md](PROJECT.md) for host prerequisites and recovery. This launcher targets Linux; it is not the Mac/Ollama launcher. Preserve the original hardware/source evidence in [UBUNTU_RESULTS.md](UBUNTU_RESULTS.md).

## Repository and branches

Canonical repository: [bohselecta/bonzai2-hadamard](https://github.com/bohselecta/bonzai2-hadamard).

- `main`: the integrated, documented package containing both completed platform paths. It remains the default checkout.
- `work/bonsai2-mac-ollama`: the accepted Mac implementation checkpoint, starting from the completed Ubuntu source and adding the isolated Ollama/Metal client.
- `work/bonsai2-ubuntu`: the preserved native CUDA qualification checkpoint. Mac delivery does not overwrite its history.

Use the platform branches to resume work within that platform's scope; integrate verified changes back into `main`. Branch presence is not proof of new hardware qualification. Keep new platform evidence separate and preserve the accepted model/runtime identities.

## File organization and pins

| Area | Contents |
| --- | --- |
| `client/`, Launch/Stop commands, `scripts/mac_bonsai.py` | Mac chat surface and lifecycle |
| `mac-runtime.json`, `evidence/mac/model.json` | Exact Mac Ollama, Prism and PTQ1_0 model pins |
| `scripts/project.py`, `build.py`, `download_model.py`, `verify_model.py` | Native Q2_0 build/download/service/verification |
| `source.json`, `model.json`, numbered runtime patches | Native Q2_0 source/model contract; preserved for Ubuntu reproducibility |
| `patches/mac-ollama-file-types.patch` | Small Mac Ollama metadata-label correction |
| `evidence/mac/`, `evidence/ubuntu/` | Platform-specific observed evidence |
| Root legacy `evidence/` | Original CPU integration evidence |
| `docs/NATIVE_INTEGRATION.md`, `DESIGN.md`, `STATUS.md` | Native implementation details and scoped validation history |
| `MAC_RUN.md` | Mac execution checkpoint and acceptance/recovery record |
| `SHA256SUMS` | Packaged source/document/evidence integrity |
| Ignored `runtime/`, `models/`, `.state/` | Local build checkouts, downloaded weights and runtime state |

Script paths and the original manifests remain stable so the recorded native reproduction commands continue to work. Historical private-handoff publisher instructions are retained in PROJECT.md for provenance; ordinary work now uses this repository and its existing branches. Do not rerun the publisher to create duplicate repositories.

## License and scope

Repository code is MIT; attribution is in [NOTICE](NOTICE). Model weights are downloaded separately under their official Apache-2.0 terms. Native integration details and upstream contribution boundaries are in [the native guide](docs/NATIVE_INTEGRATION.md).

The Mac deliverable is bounded text chat. Tools, vision, adapters and full Desktop integration are not qualified. Read the platform documentation for precise PASS, NOT_RUN and hardware limitations.
