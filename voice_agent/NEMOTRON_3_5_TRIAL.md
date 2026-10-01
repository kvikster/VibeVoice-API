# Nemotron 3.5 streaming ASR: five-call trial (2026-10-01)

## Scope and result

We downloaded NVIDIA's `nemotron-3.5-asr-streaming-0.6b` Q8 GGUF and ran it
alongside the existing English-only `nemotron-speech-streaming-en-0.6b`. Both
were tested with the same NeMo-Speech.cpp CLI and through separate Riva-compatible
`riva_server` processes. The new server ran on `127.0.0.1:50052`; the existing
English server remained on `127.0.0.1:50051`. Both servers had Sortformer
diarization enabled. The LiveKit path was
`livekit-plugins-nvidia -> MultiSpeakerAdapter`, with the same settings.

**Decision: keep the English-only model as the primary English STT.** In this
small, selected sample the 3.5 model returned no text for two short caller
phrases that the existing model recognized, both before and after ai-coustics
Voice Focus. The omitted phrases also remained empty with CPU decoding, offline
decoding, and maximum streaming right context in the new CLI. This is a result
for the tested Q8 GGUF/runtime/settings, not a general ranking of the models.

The 3.5 model remains a candidate for multilingual calls. NVIDIA's model card
recommends the existing English-only model for English-only use:
<https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b>.

## Frozen trial inputs

Five `customer-original` 16 kHz mono PCM excerpts were taken from the latest
staging calls in the existing five-call corpus. The exact WAVs and machine
outputs are in `/Users/vkey/Documents/_/workspaces/nemotron35-eval/five-streaming/`.
These excerpts are not a disjoint, human-transcribed accuracy set; quotes below
are model outputs, not ground truth.

| Call ID prefix | Seconds | Existing English model, raw | Nemotron 3.5, raw | Nemotron 3.5, Voice Focus |
| --- | ---: | --- | --- | --- |
| `4e42b620` | 7–14 | “Yeah, hello Ahmed, how do you do” | “Yeah hello Ahmed how do you do” | “Yeah, hello Pnight how do you do” |
| `7eaff530` | 8–23 | “Yeah, tell me, tell me please how many” | “I'm doing” | “I may not be repeated” |
| `474a0f17` | 7–15 | “Yeah, yeah, tell me” | *(empty)* | *(empty)* |
| `11100418` | 8–16 | “Uh yeah, tell me” | *(empty)* | *(empty)* |
| `83d6e9d7` | 72–78 | “I have a question Does this cost anything” | “Evaquation does this cost anything” | “Question does this cost anything” |

Voice Focus used the gateway's `quail_vf_l` FrameProcessor on 20 ms frames.
It changed PCM samples in all five excerpts. It did not rescue either empty
transcript. The existing model recognized both phrases after Voice Focus as
well. Complete CLI results are in `five-streaming/summary.json` and the
per-model JSON files; the `.aic.wav` files and `.aic.json` outputs hold the
enhanced pair. The license key is only read locally at runtime and is absent
from this report and the outputs.

## Real-time LiveKit/Riva replay

`local_voice_agent.tools.replay_stt` fed each raw and enhanced excerpt at
real-time pace to both servers. It logged raw STT and adapter events from each
single recognition pass in `five-streaming/*.replay.jsonl`, with metadata
sidecars. The adapter passed the final transcripts it received in these short
excerpts; the 3.5 omissions occurred **before** speaker suppression.
`474a0f17` and `11100418` produced no raw final transcript from the new
server, while the English server returned the phrases shown above. The new
server reported `head=rnnt backend=MTL0 diarization=on` at startup and served
the pinned 3.5 GGUF. A clean JFK test WAV decoded correctly with the same new
model, so loading and decoding were functional.

This trial does not measure word error rate, background-speaker separation,
interruption timing, multilingual accuracy, or Linux/CUDA parity. The short
clips do not contain enough adjudicated speaker overlap to score Sortformer.
End-to-end replay wall time includes real-time feeding and tail silence; it is
not a model latency benchmark.

## Reproducibility

- NeMo-Speech.cpp CLI source: `a5f19be31c7e7dda40cd3bbcee17083b2b88ba85`
  (2026-10-01), `metal-asr` preset, Apple Silicon.
- Nemotron 3.5 Hugging Face revision:
  `ea30d66debe3740a08b573244286791d423d6b3e`.
- GGUF SHA-256:
  `3fc991d3badad7277c11030a7519832cddaf2057aafed6d4b25147e953a070b1`.
- New Riva server config:
  `/Users/vkey/Documents/_/workspaces/nemotron35-eval/asr.n35-sidecar.yaml`,
  port `50052`, `rnnt_right_context: 1`, endpointing enabled, Sortformer.
- CLI commands used `nemo-speech transcribe INPUT --model MODEL --stream
  --language en-US --format json`; paired runs changed only `MODEL` and input
  WAV. CPU, offline, and right-context checks used the new CLI for the two
  empty clips.

## Next acceptance gate

For an English replacement decision, score a frozen, human-labeled corpus
including short turn starts, background voices, overlap, silence, and accents.
Run the same audio through both Riva servers at real-time pace, with and
without Voice Focus, then compare missed caller turns, WER, speaker attribution,
first interim/final latency, and interruption decisions. Include a Linux/CUDA
run before making a server deployment claim. Until those gates pass, keep 3.5
as a separate opt-in endpoint and keep the existing English server as default.
