# Nix: Nemotron + Sortformer + gateway

One flake builds the same service interface for Apple Silicon macOS and
x86-64 Linux (including Red Hat Enterprise Linux 9.2). Nix produces native
artifacts for each platform; a macOS binary cannot run on Linux. The package
contains NeMo-Speech.cpp `riva_server`, pinned Q8 Nemotron streaming ASR and
Sortformer diarization GGUF files, and the Python `/stt` + `/bargein` gateway.
The gateway's optional ai-coustics SDK is in the Python closure.

| Platform | Nix package | Compute backend |
| --- | --- | --- |
| Apple Silicon macOS | `.#gateway-stack` | Metal |
| RHEL 9.2 x86-64, no NVIDIA GPU | `.#gateway-stack` | CPU |
| RHEL 9.2 x86-64, supported NVIDIA GPU | `.#gateway-stack-cuda` | CUDA |

The CUDA build requires a compatible NVIDIA **host driver** and GPU. Nix
bundles user-space CUDA libraries, not the kernel driver. Build this variant
on Linux or with an x86-64 Linux Nix builder. The CPU build is a functional
fallback but has not been benchmarked for live call latency. Intel macOS is
not a supported flake system. Red Hat 9.2 compatibility must be confirmed
with a build and smoke test on the target machine; evaluation on macOS alone
is not an installation test.

## Build and install

Install Nix with flakes enabled. From the repository root:

```sh
nix build .#gateway-stack
./result/bin/callevate-stack
```

On a Linux GPU host, substitute `.#gateway-stack-cuda`. To install a stable
profile path for a service:

```sh
sudo nix profile install --profile /opt/callevate/nemotron-gateway .#gateway-stack-cuda
/opt/callevate/nemotron-gateway/bin/callevate-stack
```

Use `.#gateway-stack` in that command for macOS or Linux CPU. The package
also exposes `callevate-riva` and `callevate-gateway` for independent
process supervision. Their defaults are Riva `127.0.0.1:50051` and gateway
`127.0.0.1:8765`. When changing the Riva port, set **both** `RIVA_BIND` and
`RIVA_SERVER` to the corresponding values before starting the stack.

```sh
RIVA_BIND=127.0.0.1:50061 RIVA_SERVER=127.0.0.1:50061 \
  BARGEIN_PORT=8766 ./result/bin/callevate-stack
./result/bin/callevate-smoke --riva 127.0.0.1:50061 \
  --gateway http://127.0.0.1:8766 --wav /path/to/speech-mono-16bit.wav
```

`callevate-smoke` checks gateway HTTP health and the Riva gRPC configuration
call. With a WAV it checks direct Riva recognition and the gateway's `/stt`
stream, including speaker tags. A successful `/health` response alone does not prove
Riva or ai-coustics is working. Run the WAV probe on each target host before
pointing a LiveKit agent at it.

## Runtime configuration

For ai-coustics Voice Focus and VAD, set these on the **gateway host**:

```dotenv
AIC_LICENSE_KEY=<SDK license, not the ai-coustics cloud API key>
AIC_MODELS_DIR=/var/cache/callevate/aic-models
GATEWAY_AIC_ENABLED=1
GATEWAY_AIC_VAD_ENABLED=1
GATEWAY_AIC_VAD_MODEL=vad-vf-2.0-s-16khz
LIVEKIT_INFERENCE_API_KEY=<shared gateway credential>
LIVEKIT_INFERENCE_API_SECRET=<shared gateway secret>
```

Keep credentials in a runtime environment file or secret manager, never in
`flake.nix` or a Nix store derivation. The pinned Nemotron and Sortformer
models are fetched and hash-verified **at build time** and need no model CDN
access at runtime. The ai-coustics SDK license activation and its model
download require outbound network access from the gateway on first use. The
agent itself needs only network access to the gateway and the services named
in its own configuration. `AI_COUSTIC_API_KEY` is not the SDK license accepted
by this gateway.

The gateway binds to loopback by default. Set `BARGEIN_HOST=0.0.0.0` only
with both shared inference credentials configured, and place TLS termination
or a private network between agent and gateway. The optional VAD veto is
**shadow only** by default; enabling `GATEWAY_AIC_VAD_GATE_THRESHOLD` is a
separate, corpus-calibrated rollout decision. See [gateway protocol and
settings](GATEWAY.md).

## Model provenance

The flake pins upstream NeMo-Speech.cpp, ggml and Riva protocol commits, the
Nix dependency graph, and exact Hugging Face model revisions and SHA-256
hashes. The [Nemotron model](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b)
uses the NVIDIA Open Model License; the [Sortformer model](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2)
uses CC BY 4.0. Review those terms for distribution of a binary
cache or installer. The Nix output contains model files via store references,
so copying only the top-level symlink directory without its closure is not a
complete offline installation.
