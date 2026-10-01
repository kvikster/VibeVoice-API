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
decoding, and every supported streaming right context tested in the new CLI.
The follow-up below reproduced the omission with NVIDIA's original unquantized
checkpoint in Transformers. This is a result for these short English turns, not
a general ranking of the models.

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

## Why the two short turns disappeared

The in-call Deepgram transcript also recorded `11100418` as “Yeah. Tell me.”
and `474a0f17` as “Yeah. Yeah. Tell me.” Their customer PCM tracks contain
roughly 1–1.5 seconds of speech, starting about 0.75 seconds into the trial
WAVs. Peak levels are −18.3 and −14.4 dBFS respectively; the WAVs are not
silent or clipped. The English-only model recognizes both.

We kept the **identical 0.75–2.50 s speech samples** from each trial WAV and
changed only zero-valued PCM padding. The following outcome repeated for both
calls with `en-US`:

| Silence before speech | Silence after speech | Nemotron 3.5 GGUF | Original NVIDIA safetensors in Transformers |
| ---: | ---: | --- | --- |
| 0 ms | 1.5 s | recognized | recognized |
| 0 ms | 5.5 s | recognized | recognized |
| 250 ms | 1.5 s | empty | empty |
| 750 ms | 1.5 s | empty | empty |

The old English GGUF recognized both phrases with 0, 240, and 750 ms of
leading silence. A finer 40–750 ms sweep showed that the 3.5 output can be
correct, garbled, or empty depending on the speech position; it is especially
fragile for these short turns. Adding +6/+12 dB, Voice Focus, CPU instead of
Metal, or changing the supported streaming right context (`0`, `1`, `3`, `6`,
`13`) did not reliably restore the two original WAVs. Long **trailing** silence
was not the cause: with speech at stream start, 5.5 s of trailing silence still
produced text.

The original unquantized checkpoint was tested with `transformers==5.18.0`,
`torch==2.14.1`, and NVIDIA's documented `AutoProcessor` / `AutoModelForRNNT`
`generate()` path on Apple MPS. For each original WAV it produced exactly 102
RNNT tokens, all the model's blank ID `13087`, so there were no lexical tokens
for a later layer to hide. Removing leading silence yielded text in the same
runtime. This places the failure **inside the model inference path** for these
inputs. It rules out a GGUF-only quantization/conversion defect and the Riva,
Sortformer, LiveKit, and ai-coustics postprocessing layers as the sole cause.
The data do not identify which learned component or training choice creates
this onset sensitivity.

Full `customer-original` audio from call start through 40 seconds confirmed
this is not an artifact of the 8-second trial crop: 3.5 omitted the first
short answer in both calls, then recognized later longer caller speech.
Conversely, real-time Riva replay on speech-aligned crops yielded raw and
post-adapter final transcripts for both phrases. The available crop-start
window was narrow (around 0.65–0.80 s into the 8-second WAV); cutting later
also lost the words. A server-side VAD restart must therefore retain the
speech onset accurately and be tested on the full corpus before use.

An opt-in `/stt` speech-onset trim now buffers 20 ms frames after optional
Voice Focus enhancement. With a −50 dBFS RMS threshold, two-frame confirmation,
and 160 ms pre-roll, real-time Riva replay of the two original WAVs on the
3.5 sidecar changed from **no final event** to “Uh yeah, tell me” (`11100418`)
and “Yeah yeah tell me” (`474a0f17`), both with speaker `S1`. This validates a
remedy for these two excerpts; it does not establish a safe threshold or
pre-roll for other calls. The feature remains disabled by default.
With Voice Focus enabled on the server before the same trim, the two final
texts were “Uh yeah tell me” and “Yeah yeah tell me.” The other three original
excerpts were also replayed through the raw-audio trim: `4e42b620` produced
“Yeah hello Ahmed how do you do”; `7eaff530` produced “Yeah” followed by
“tell me tell me please”; `83d6e9d7` produced “Evaquation” followed by
“does this cost anything.” Those are model outputs, not verified ground truth.
The follow-up still needs quiet-caller and background-only negatives, timing
measurement, and a larger labeled corpus before enabling live traffic.

Reproduction artifacts are in `short-turn-probes/`, `silence-axis-probes/`,
`lead-threshold-probes/`, `context-probes/`, `full-start-probes/`, and
`native-transformers-results.json` under the evaluation directory above.

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
- Native Transformers comparison used the original `model.safetensors` from
  the same pinned Hugging Face revision and `probe_native_transformers.py` in
  the evaluation directory. The synthetic padding tests used exact copies of
  speech PCM samples, so the comparison changes only their position in time.

## Next acceptance gate

For an English replacement decision, score a frozen, human-labeled corpus
including short turn starts, background voices, overlap, silence, and accents.
Run the same audio through both Riva servers at real-time pace, with and
without Voice Focus, then compare missed caller turns, WER, speaker attribution,
first interim/final latency, and interruption decisions. Include a Linux/CUDA
run before making a server deployment claim. Until those gates pass, keep 3.5
as a separate opt-in endpoint and keep the existing English server as default.
If testing a VAD-gated 3.5 stream, score both missed first words and accidental
background-triggered streams, because simply trimming silence by a fixed
amount fails on these two calls.
