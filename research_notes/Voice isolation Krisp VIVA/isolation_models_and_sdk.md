# Krisp VIVA voice isolation models and the Krisp audio SDK (`krisp_audio`): a technical note for a self-hosted LiveKit Agents 1.8.3 voice agent (state as of 2026-09-26)

**Method and evidence labels.** The egress proxy blocked these domains for curl and WebFetch alike: krisp.ai, sdk-docs.krisp.ai, cdn.krisp.ai (the Doxygen API reference), help.krisp.ai, docs.livekit.io, community.livekit.io, docs.pipecat.ai, businesswire.com, ai-coustics.com and callsphere.ai. Every fact from those sites is a WebSearch snippet, marked **(snippet)**. Treat snippets as vendor claims that have not been checked against the full page. **(verified)** marks facts I read directly:
- Source code cloned from GitHub: `krispai/Krisp-SDK-Sample-Apps` @ `krisp-sdk-v9` 2026-08-28, `krispai/gst-krisp-audio` @ 2026-05-04, `pipecat-ai/pipecat` @ `main` 2026-09-26, `pipecat-ai/docs` @ 2026-09-25.
- Wheels downloaded from PyPI and inspected: `livekit-plugins-krisp` 0.4.3, `livekit-plugins-krisp-internal` 0.1.0 and 0.2.0, and `livekit-plugins-noise-cancellation` 0.2.5 and 0.2.6.
- Binary inspection: I ran `strings`, parsed the embedded JSON and computed SHA-1 hashes of the embedded model blobs.

**(inference)** marks my own reasoning. This note deliberately goes deeper than `research_notes/Огляд рішень voice isolation/krisp.md` and does not repeat its licensing and LiveKit-Cloud material.

---

## 1. Model lineup and version history 2024–2026: names (.kef), purpose, SIP vs WebRTC choice, sizes, dates, what "VIVA" means

### Takeaway
"VIVA" stands for **Voice Isolation for Voice AI**. The product line has three platform releases:
- VIVA (SDK plus server-side voice isolation), launched 2025-07-16.
- VIVA 2.0 (2026-05-06): VI v3, Turn Prediction v3, Interruption Prediction v1, TTS/perception detectors and VAD.
- VIVA 2.5 (2026-08-12): VI 2.5 and VI lite 2.5.

The voice-isolation models ship as two families:
- **`krisp-viva-tel-*`**: 16 kHz, telephony and anything up to 16 kHz. Versions v1, lite-v1, v2, v2.1 and 2.5.
- **`krisp-viva-pro-*`**: up to 32 kHz, WebRTC.

Inspecting the binary shows what these actually are:
- LiveKit's bundled **VIVA PRO v1 is byte-identical to Krisp's older "BVC" headset model `hs.c6.f.m.75df8f`**.
- **VIVA TEL v2 is a retrained *inbound* BVC model**, `inb.bvc.blocked.laughter.hs.c6.w.s.5272a6`, the successor of LiveKit's `BVCTelephony`.

Both are GRU networks of about 7 M float32 parameters (about 28–29 MB each). Both use a 30 ms analysis window with a 15 ms hop, at a working rate of 32 kHz (PRO) or 16 kHz (TEL). For 8 kHz SIP, use a **tel** model: v2.1 and later are described as "optimized for 8–16 kHz telephony".

### Cited Findings

**Name and product scope**
- "Voice Isolation for Voice AI (VIVA) models are designed for Voice AI and deployed on servers in front of the VAD to improve turn-taking, false interrupts and sometimes WER, removing background voices and noise from TV, music, kids, cars…" (snippet, undated) — [sdk-docs: Voice Isolation](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)
- **VIVA (1.0) launch, 2025-07-16.** "Krisp announced the launch of VIVA, its voice isolation AI model and SDK built for Voice AI agents". It reached 1 B minutes of voice-AI processing per month, "improving turn-taking, enhancing VAD, and preventing false interruptions", and delivers "server-side voice isolation by seamlessly integrating into an application's audio path" (snippet). — [BusinessWire 2025-07-16](https://www.businesswire.com/news/home/20250716580385/en/Krisp-Launches-VIVA-SDK-and-Surpasses-1B-Minutes-of-Voice-AI-Processing-per-Month-Milestone); [Krisp blog](https://krisp.ai/blog/krisp-launches-viva-sdk-and-surpasses-1b-minutes-of-voice-ai-processing-per-month-milestone/)
- **VIVA 2.0, 2026-05-06** (snippets):
  - It bundles "voice isolation, turn prediction, interruption prediction, signal detectors, and voice activity detection into one package that sits before your STT, runs on CPU, with 15 ms latency".
  - Krisp calls **Voice Isolation v3** "a ground-up rebuild of Krisp's core engine" that isolates the primary speaker "from everything else — background noise, other voices, room echo, and codec artifacts".
  - Krisp says VIVA runs at ">12 billion minutes of voice AI agent traffic a year" inside ">130 voice AI products (Daily, Vapi, LiveKit, Ultravox, Telnyx…)".
  - Sources: [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/); [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- **TTS Detector (VIVA 2.0).** It "detects synthetic speech in real time. The primary use case is for an outbound voice AI agent to recognize when an inbound voice AI agent or IVR picks up a call". It runs on CPU, audio only, and is "bundled into existing VIVA pricing" (snippet). — [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents); [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)
- **VIVA 2.5 / VI 2.5, 2026-08-12** (snippets):
  - Krisp calls VI 2.5 "latest and most advanced general-purpose voice isolation model for conversational AI".
  - It ships in "two sizes: the full VI 2.5, and a lite version for CPU-constrained and edge deployments".
  - Krisp claims isolation "has been running in production for 2 years, across 1B+ minutes … a month".
  - Sources: [x.com/davitb](https://x.com/davitb/status/2087555112810250608); [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)

**Model names in docs and changelogs** (all dates are publication dates of the source)

| Model name (as documented) | Purpose / claim | Source |
|---|---|---|
| `krisp-viva-tel-v1` | "industry-leading, bi-directional, Voice Isolation model designed for Conversational AI use-cases, such as Voice bots" (snippet) | [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai) |
| `krisp-viva-tel-lite-v1` | "3.5x smaller" VI model. Predecessor `krisp-bvc-o-lite-v2`. "better background noise and secondary voice suppression, adds support for inbound telephony use cases … within the same CPU footprint" (snippet) | [Krisp blog small VI model](https://krisp.ai/blog/small-voice-isolation-model/) |
| `krisp-viva-tel-v2.kef` / `krisp-viva-vi-tel-v2.kef` | Both spellings appear in Pipecat's setup guide. "`krisp-viva-tel`: Telephony, Cellular, Landline, Mobile, Desktop, Browser (up to 16kHz)" (verified) | [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) |
| `krisp-viva-pro` | "Mobile, Desktop, Browser (WebRTC, up to 32kHz)" (verified) | same |
| `krisp-viva-vi-tel-v2.1` | VIVA Go SDK v1.4.0 (2026-07-08): "new … 16 kHz Voice Isolation model, optimized for 8-16KHz telephony applications … reduces voice suppression in certain scenarios and improves WER accuracy compared to its predecessor, krisp-viva-vi-tel-v2" (snippet) | [sdk-docs changelog Go v1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140) |
| VI v3 | VIVA 2.0 (2026-05-06), "ground-up rebuild". One snippet says it is "3.5x smaller than its predecessor and can improve WER by 20-40% on real-world calls". That snippet may be mixing in the lite-model blog (snippet) | [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/) |
| VI 2.5 and VI lite 2.5 | 2026-08-12. "15 ms of algorithmic latency … entirely on CPU", "supports narrowband audio and telephony streams". Lite is "roughly 3.5× smaller parameter size", "3.5x less compute" (snippet) | [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/) |
| Turn `krisp-viva-tt-v2.kef` → `krisp-viva-tp-v3.kef`; IP `krisp-viva-ip-v1.kef`; VAD `krisp-viva-vad-v2.kef` (8–48 kHz) | Non-isolation VIVA models (verified from the docs) | [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) |
| Python SDK v1.0.0 | "new near-field inbound 16kHz BVC (background voice cancelation) model optimized for Telephony, Cellular, Landline and for WebRTC" (snippet) | [sdk-docs changelog Python v1.0.0](https://sdk-docs.krisp.ai/changelog/python-sdk-v100) |

**What LiveKit's bundled models actually are (verified: wheel and binary inspection)**

`livekit-plugins-krisp-internal` 0.2.0 (2026-07-22; "bundles the Krisp VIVA SDK"; the Krisp license is baked into the wheel):
- The native library is 110 MB on Linux x86_64 and 68 MB on macOS arm64.
- It contains Rust symbols `plugins_krisp::models::KRISP_VIVA_PRO_V1` and `…KRISP_VIVA_TEL_V2`, and two embedded model packages. Each package has a JSON manifest; the `fileUid` of each blob equals the SHA-1 of its bytes, which I checked.
  - **PRO v1:** `pnc.thw` (28,772,541 B, uid `0e0d98f0…`), `csd.thw` (644,148 B, uid `99486b37…`) and `FrameProcessorCfg.json` (16,395 B).
  - **TEL v2:** `inb.bvc.blocked.laughter.hs.c6.w.s.5272a6.thw` (28,030,666 B, uid `5013b6aa…`, `"encrypted": false`) and `FrameProcessorCfg.json` (9,072 B).
- Python API: `VivaMode.VOICE_ISOLATION` / `VOICE_ISOLATION_TELEPHONY`.
- Source: [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)

`livekit-plugins-krisp-internal` 0.1.0 (2026-07-06):
- Modes were `VOICE_ISOLATION` and `NOISE_CANCELLATION`.
- Models were `KRISP_VIVA_PRO_V1` (same `pnc` + `csd` hashes) and `KRISP_VIVA_SS_V1`, a DeepFilterNet ONNX model `df.c8.f.m.528d1f.ort` (21,517,136 B).
- 0.2.0 replaced the NC mode with the TEL isolation model.
- Source: [PyPI livekit-plugins-krisp-internal 0.1.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.1.0/)

`livekit-plugins-noise-cancellation` 0.2.6 (2026-06-26), the Cloud-only NC/BVC/BVCTelephony package:
- **BVC** `hs.c6.f.m.75df8f.kef` contains the *same* `pnc.thw`, `csd.thw` and `FrameProcessorCfg.json` UIDs as VIVA PRO v1. The `pnc.thw` bytes are byte-identical at offset 1014 of the `.kef`. The `.kef` header ID `15a7c3c52a…` also appears in the internal library's "Error authorizing model use" string.
- **BVCTelephony** `inb.bvc.hs.c6.w.s.23cdb3.kef` wraps `bvc_wb_inbound_7M_cmpr_2.thw`, i.e. "BVC wideband inbound 7M [params], compress-rate 2".
- **NC** `c8.f.s.026300-1.0.0_3.1.kef` has `"isDeepFilterNet": true`, engine `ONNX`, and an encrypted `m.ort`, running at 32 kHz with a 30 ms frame and step 480.
- Source: [PyPI livekit-plugins-noise-cancellation 0.2.6](https://pypi.org/project/livekit-plugins-noise-cancellation/0.2.6/)

TEL v2 vs the old BVCTelephony:
- The embedded `FrameProcessorCfg.json` of TEL v2 has exactly the same 36 keys and values as the one in the old `BVCTelephony` `.kef`. Only the 120-dim feature-normalisation mean/SD vectors differ (verified; same PyPI sources as above).

**Architecture facts from the embedded configs and weights (verified)**

| | VIVA PRO v1 (= LiveKit BVC) | VIVA TEL v2 (≈ retrained BVCTelephony) |
|---|---|---|
| `workingSampleRate` | 32000 | 16000 |
| `workingFrameDuration` / `step` | 30.0 ms / 480 samples (= **15 ms hop**) | 30.0 ms / 240 samples (= **15 ms hop**) |
| FFT bins (`coefficientNumber`) | 481 | 241 |
| Feature dim (`normalizationParams` length) / `compressRate` | 150 / 3 | 120 / 2 |
| `frameCount` | 4 | 4 |
| `backgroundSpeakerFix` | `cutStartDB` 10.0, `cutEndDB` 5.0, `runFrameCount` 40, `runMinLen` 2, `utteranceLen` 2, `varWindMode` true | identical |
| `pnc` block | `freezeLowEnThr` 700, `freezeHighEnThr` 710, `halfLifeInSec` −1 | identical |
| Extra sub-model | `csdEnabled: true`: 0.64 MB `csd.thw` (90-dim features, `compressRate` 4, `frameCount` 1) | none |
| Weights | `PNC_0.0.1` container, float32 tensors `WeightLinear`, `WeightGRU`, `WeightGRU_reset`, `WeightNonLinear`… → ≈7.2 M params | `PNC_0.0.1`, `WeightLinear`, `WeightGRU` → ≈7.0 M params |

- The Krisp source paths compiled into the binary include:
  - `inference-engine/.../gru/krisp_gru_{layer_norm,mini,mini_lora,modify,modify_vad,sep_dense}_executable_network.cpp`
  - `frame_processors/nc/src/deep_filter_net/krisp_nc_df_{pre,post,}processor.cpp`
  - `krisp_nc_maincleaner.cpp`
  - `inference-engine/src/onnxruntime/…`
  - Source (verified): [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)

**Model-selection rules (Krisp docs; snippets)**
- "Krisp standard outbound NC models are designed to work with sampling rates above 8kHz … For 8KHz and lower sampling rates, narrowband Krisp NC models should be used."
- BVC requires "the sampling rate of the voice … above 8kHz" and "a headset or compatible device". It "is incompatible with Narrow Band devices with sampling rates of <=8KHz". It "works best with wired USB headsets with a boom microphone and is also compatible with most Bluetooth headsets, including AirPods".
- "Krisp inbound tech is not designed for multiple simultaneous voices on the same microphone. Inbound models are trained to handle multiple voices, each voice with its own mic…"
- Source: [sdk-docs Model Selection Guide BVC & NC](https://sdk-docs.krisp.ai/docs/rtc-model-guide-bvc-nc)
- "VI models … support audio sampling rates up to 16 kHz … Krisp Audio SDK will automatically resample the audio input to match the sampling rate of the model" (snippet). — [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)
- Pipecat Cloud exposes only two VI choices, `audio_filter = "tel"` (up to 16 kHz) or `"pro"` (up to 32 kHz) (verified). — [pipecat-ai/docs pipecat-cloud/guides/krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)

### Inferences
- **Decoding the file names** (high confidence where the config confirms it, otherwise a guess):
  - `inb` = inbound (far-end/received stream).
  - `bvc` = background voice cancellation.
  - `hs` = headset/near-field.
  - `f` = full-band (32 kHz working rate) and `w` = wideband (16 kHz). Both are confirmed by `workingSampleRate`.
  - `s`/`m` = small/medium.
  - `c6`/`c8` = architecture family. `c8` is the DeepFilterNet/ONNX family; `c6` is the native GRU family.
  - The trailing hex is a build hash.
  - `blocked.laughter` suggests a training-target change for laughter, but it cannot be told whether laughter is now removed or now preserved. It needs a listening test.
- **What "VIVA voice isolation" is in the LiveKit/Pipecat era (2025 – mid-2026):** Krisp's BVC technology re-branded. `pro` is the outbound/headset BVC model and `tel` is the inbound near-field BVC model. VI v3 (May 2026) and VI 2.5 (Aug 2026) are said to be "ground-up rebuilds". I could not see their `.kef` names or configs; they are only in Krisp's portal.
- **VI v3 vs VI 2.5 naming conflict.** The May 2026 press calls the new model "Voice Isolation v3". The August blog calls the newest model "VI 2.5" and benchmarks it against "v2.1" (see §5), not against v3. Two readings are possible: (a) "v3" was the press name for the model later released as 2.5, or (b) v3 is a different, possibly higher-cost variant. The public sources do not settle this. Ask Krisp which `.kef` corresponds to each.
- **Choice for the user's stack** (Nemotron streaming ASR runs at 16 kHz; SIP is 8 or 16 kHz; WebRTC is 48 kHz):
  - The **tel** family (v2.1, or VI 2.5-tel/lite if offered) is the natural choice for *both* SIP and WebRTC callers. It works internally at 16 kHz, the ASR's rate, and Krisp lists "Mobile, Desktop, Browser" under tel.
  - **pro** (32 kHz, headset BVC) gains nothing for a 16 kHz ASR. Its model is explicitly headset-oriented (`hs`), so it is riskier for laptop or speakerphone WebRTC users.
- **Model memory:** about 28–29 MB of float32 weights per loaded model. Krisp says one loaded model is shared by all streams (see §2), so the per-session cost is mainly the recurrent state and buffers.

### Gaps
- No `.kef` names, sizes, configs or release dates could be obtained for VI v3, VI 2.5, VI lite 2.5, `krisp-viva-tel-v1`, `tel-lite-v1` or `v2.1`; all are behind the Krisp portal.
- The full sdk-docs changelog (https://sdk-docs.krisp.ai/changelog) was unreadable. Only titles and snippets were seen: Python SDK v1.0.0, Go SDK v1.0.0 (2025-11-13, "built on Krisp Server SDK v9.4.0"), VIVA Go SDK v1.4.0 (2026-07-08), VIVA C/C++ SDK v9.20.0, Node.js SDK v1.7.0 and JS SDK v1.4.4 "Inbound NC & BVC".
- No parameter count for VI 2.5 full or lite was confirmed. A snippet says "~9M parameters and 30 MB footprint", but it appears in turn and interruption contexts too, so it is ambiguous which model it describes.
- It is unknown whether any 8 kHz-native (narrowband) VI model exists, beyond "v2.1 optimized for 8–16 kHz" and "VI 2.5 supports narrowband".

---

## 2. SDK API and runtime (`krisp_audio` Python and C++ `Krisp::AudioSdk`): classes, rates, frames, formats, threading, sessions, scaling, platforms, versions, licensing behaviour

### Takeaway
Three API layers exist:
- The **C++ "Krisp Audio SDK" v9.x** (`Krisp::AudioSdk`, desktop and server builds; v9.0 in 2024-08, v9.20 by September 2026).
- A **Python binding `krisp_audio` 1.x**, not on PyPI and downloaded from Krisp's portal. It used pybind11 up to 1.10 and nanobind from 1.11/1.12 (2026-08, `cp312-abi3` wheels).
- Go, Node and Rust bindings.

The model is:
1. one process-wide `globalInit(workingPath, licenseKey, licensingCallback, logCallback, logLevel)`;
2. per-stream sessions created from a config (`NcSessionConfig`, `VadSessionConfig`, `TtSessionConfig`, `IpSessionConfig`, `TtsDetectionSessionConfig`) with a `.kef` `ModelInfo`;
3. synchronous `process(frame, level)` calls on fixed-size mono frames of 10/15/20/30/32 ms at 8–48 kHz (the C++ layer also takes 88.2/96 kHz), in int16 or float32.

License validation is **asynchronous and over the network (libcurl)**. According to Krisp's own GStreamer README, on failure the SDK **passes audio through unprocessed after a grace period**. That is a silent-failure mode that matters for a no-cloud deployment.

### Cited Findings

**C++ API (verified from Krisp's public sample apps, SDK ≥ v9.9)**
- Headers: `krisp-audio-sdk.hpp`, `krisp-audio-sdk-nc.hpp`, `krisp-audio-sdk-vad.hpp`, `krisp-audio-sdk-ar.hpp` (accent) and `krisp-audio-api-definitions.hpp`. Library: `libkrisp-audio-sdk.{a,so,dylib,lib}`, static or dynamic. — [Krisp-SDK-Sample-Apps native-cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/tree/krisp-sdk-v9/native-cpp); [gst-krisp-audio README](https://github.com/krispai/gst-krisp-audio)
- NC session flow:
  1. `globalInit(L"")`.
  2. `ModelInfo.path` (wide string). `ModelInfo.blob` (pointer, size) also exists for in-memory models.
  3. `NcSessionConfig{inRate, FrameDuration, outRate, &modelInfo, withStats, ringtoneCfg*}`.
  4. `Nc<int16_t|float>::create(cfg)` returns a `shared_ptr`.
  5. `process(in, inSize, out, outSize, noiseSuppressionLevel, PerFrameStats*)`.
  6. Optional `getSessionStats(SessionStats*)`, reporting no/low/medium/high-noise ms and `talkTimeMs`, plus per-frame `energy.noiseEnergy/voiceEnergy`.
  7. Reset the session *before* `globalDestroy()`.

  The sample default suppression level is 100. — [sample-nc/main.cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/sample-nc/main.cpp)
- The `RingtoneCfg` ("Ringtone model cfg for inbound", a second `.kef`) was added to the NC sample on 2025-11-26 (verified). — [commit 95c0eca](https://github.com/krispai/Krisp-SDK-Sample-Apps/commit/95c0eca759dc8c2c97801f3410ab337afa904940)
- VAD: `VadSessionConfig{rate, frameDuration, &modelInfo}`, then `Vad<T>::create`, then `process(in, size, &float prob)` for per-frame speech probability (verified). — [sample-vad/main.cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/sample-vad/main.cpp)
- Licensing build: `globalInit(L"", licenseKey, licensingErrorCallback(LicensingError, msg), logCallback, LogLevel::Off)` under `ENABLE_LICENSING` (verified). `ENABLE_LICENSING` adds `libcurl.a`; OpenSSL is always linked. — [wav-cli/main.cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/wav-cli/main.cpp); [krisp.third.party.linux.x64.cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.third.party.linux.x64.cmake)
- **Legacy APIs (2024).** SDK v7.0.2 and v8.0.x used a C API (`krispAudioSetModel`, `krispAudioNcCreateSession[Int16|Float]`) with rates up to 96 kHz. The v9.0 C++ API appears in the 2024-08-30 commit "NC sample for v9.0 API" (verified). — [branch krisp-sdk-v7](https://github.com/krispai/Krisp-SDK-Sample-Apps/tree/krisp-sdk-v7); [branch krisp-sdk-v8.1.0](https://github.com/krispai/Krisp-SDK-Sample-Apps/tree/krisp-sdk-v8.1.0)
- **Static dependencies of the server SDK** (Linux x64 and aarch64, verified): onnxruntime (session/mlas/…), onnx, protobuf, abseil, re2, flatbuffers, nsync, cpuinfo, **OpenBLAS**, libresample, OpenSSL, libcurl (licensing). On macOS the GStreamer build links `Accelerate` ("cblas/vDSP in XNNPACK / MLAS") and `Security`/`SystemConfiguration` ("libcurl proxy detection"). — [krisp.third.party.linux.aarch64.cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.third.party.linux.aarch64.cmake); [gst-krisp-audio README](https://github.com/krispai/gst-krisp-audio)
- **Server SDK package naming** (verified): `krisp-audio-sdk-9.9.0-server-lin_x64` and `krisp-audio-sdk-9.11.0-win_x64_{mt,mtd,md,mdd}-nc`. The sample README targets "Krisp SDK Desktop/Server v9.9 or later on Linux (x64, arm64) GCC 9.4+, macOS (x64, arm64) Clang 15+, Windows (x64, arm64) VS 2019+". — [native-cpp/README.md](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/README.md)
- **SDK version timeline from the sample repo history** (verified):

  | Date | Change |
  |---|---|
  | 2024-05 | v7.0.2 / v8.0.1 / v8.0.2 |
  | 2024-08-30 | v9.0 |
  | 2025-02-18 | v9.2 with 24 kHz support |
  | 2025-06-20 | `getVersion` API added |
  | 2025-09-18 | Linux aarch64 support, v9.9 |
  | 2026-02-17 | v9.14 with Voice Translation samples |

  Source: [commit log](https://github.com/krispai/Krisp-SDK-Sample-Apps/commits/krisp-sdk-v9)
- A snippet (2026-09) shows "VIVA C/C++ SDK v9.20.0" and "VIVA Node.js SDK v1.7.0" as recent changelog entries. — [sdk-docs changelog](https://sdk-docs.krisp.ai/changelog)

**Python `krisp_audio` API** (verified from Krisp's sample and from Pipecat code written by Krisp engineers, `gharutyunyan@krisp.ai`)
- `krisp_audio.globalInit("")`, `getVersion()` returning `.major/.minor/.patch/.build`, and `globalDestroy()`.
- Enums: `SamplingRate.Sr8000Hz|Sr16000Hz|Sr24000Hz|Sr32000Hz|Sr44100Hz|Sr48000Hz` and `FrameDuration.Fd10ms|Fd15ms|Fd20ms|Fd30ms|Fd32ms`.
- NC sessions: `ModelInfo().path`, then `NcSessionConfig` (`inputSampleRate`, `inputFrameDuration`, `outputSampleRate`, `modelInfo`), then `NcInt16.create(cfg)` or `NcFloat.create(cfg)`, then `session.process(frame_ndarray, suppression_level)` returns the processed frame.
- The sample reads mono PCM16 or FLOAT WAV only and requires `krisp_audio>=1.0.0`.
- Source: [python/krisp_audio_test.py](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/python/krisp_audio_test.py); [python/requirements.txt](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/python/requirements.txt)
- Other session types used by Pipecat (verified, 2026-09-26):
  - `VadSessionConfig` → `VadFloat.create`, `process(float32)` returns a probability.
  - `TtSessionConfig` → `TtFloat.create`, `process(frame, is_speech, False)` returns an end-of-turn probability. Default 20 ms frames, threshold 0.5.
  - `IpSessionConfig` → `IpFloat.create`, `process(frame, speech_active)` returns an interruption probability. Default 20 ms frames, threshold 0.5.
  - `TtsDetectionSessionConfig` → `TtsDetectorFloat.create`, `process(float32 frame)` returns a TTS probability.
  - Sources: [krisp_viva_ip_user_turn_start_strategy.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py); [krisp_viva_turn.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/krisp_viva_turn.py); [krisp_viva_vad.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/vad/krisp_viva_vad.py); [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py)
- **Licensed init signature (SDK ≥ 1.6.1):** `globalInit("", key, license_callback(error, msg), log_callback(msg, level), LogLevel.Off)`. Older builds used `globalInit("", log_callback, LogLevel.Off)`, and Pipecat falls back on `TypeError`. Pipecat added the key on 2026-03-02 (v0.0.104) "for Krisp SDK v1.6.1+ licensing" (verified). — [krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py); [Pipecat CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md)
- **Binding change:**
  - "Krisp SDK switched its Python bindings from pybind11 to nanobind starting in 1.11.0", which "changed the noise suppression level argument from int to float and requires writable … ndarray input" (verified; Pipecat PR #5302 by Krisp staff, merged 2026-08-13, released in Pipecat 1.8.0 on 2026-08-26). — [krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py); [pipecat PR #5302](https://github.com/pipecat-ai/pipecat/pull/5302)
  - A user issue (2026-08-24) reports `krisp_audio` **1.12.0 (cp312-abi3)** nanobind wheels. These "reject read-only NumPy arrays and plain Python lists". Pipecat's filter caught the exception and "noise cancellation is silently disabled — no crash, no warning, just unfiltered audio". — [pipecat issue #5413](https://github.com/pipecat-ai/pipecat/issues/5413)
- **Python SDK platforms:**
  - Python SDK v1.0.0 supports "Python versions 3.10, 3.11, 3.12, and 3.13, with OS support for Linux x64, Windows x64, and Mac arm64" (snippet). — [sdk-docs changelog Python v1.0.0](https://sdk-docs.krisp.ai/changelog/python-sdk-v100)
  - Documented wheel example: `krisp-viva-uar-python-sdk-1.8.0/dist/krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl` (verified). — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- **"UAR" builds:** VIVA Go SDK v1.4.0 (2026-07-08) "separat[es] Go SDK UAR (usage auto reporting) and non UAR builds" (snippet). The Python SDK download folder is named `krisp-viva-uar-python-sdk-*` (verified in the Pipecat docs). — [sdk-docs Go v1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)

**Threading, lifecycle, per-session state, scaling**
- **Async licensing** (Krisp's own GStreamer plugin, 2026-04): "The server SDK validates the license key on its own internal thread after `globalInit` returns. Any licensing error is stored and surfaced … The pipeline keeps running — the SDK passes audio through after its grace period." The SDK log callback "is called on the SDK's internal thread; must be thread-safe". `globalInit` is ref-counted, process-wide and shared by all elements (verified). — [gst-krisp-audio README](https://github.com/krispai/gst-krisp-audio); [src/krisp_session.hpp](https://github.com/krispai/gst-krisp-audio/blob/main/src/krisp_session.hpp)
- **Global state:** "The SDK's global state is shared by every Krisp session in the process … destroying it while any session is still alive leaves that session reading freed memory". This fixed a `SIGSEGV` in `libkrisp-audio-sdk` on teardown, in Pipecat 1.8.0 (2026-08-26). Also, "`api_key` is read only by the call that initializes the SDK, so a process serving sessions under different Krisp licenses uses the first one for all of them" (verified). — [Pipecat CHANGELOG 1.8.0](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md); [PR #5411](https://github.com/pipecat-ai/pipecat/pull/5411)
- **Fixed frames and wrapper buffering:**
  - Sessions need fixed-size frames. Krisp's GStreamer wrapper uses an input/output "carry-buffer FIFO … The only cost is up to one frame (<= frameDurationMs) of startup latency" and zero-fills until primed.
  - Pipecat's filter accumulates bytes and returns `b""` until a full frame exists.
  - LiveKit's license-mode wrapper emits whatever processed audio is ready, "never zero-padded".
  - Sources (verified): [krisp_session.hpp](https://github.com/krispai/gst-krisp-audio/blob/main/src/krisp_session.hpp); [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py); [PyPI livekit-plugins-krisp 0.4.3](https://pypi.org/project/livekit-plugins-krisp/0.4.3/)
- Sessions are created per sample rate. LiveKit's backends recreate the session if the frame rate changes, and they pass mono only: multi-channel frames "are passed through unprocessed" (verified). — [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)
- "Krisp VIVA SDK supports the real-time processing of multiple audio streams using a single model loaded into memory" (snippet). — [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)
- **Supported I/O in Krisp's GStreamer element** (verified): `S16LE` or `F32LE`, mono only, at 8, 16, 24, 32, 44.1, 48, 88.2 or 96 kHz. `frame-duration` is one of {10, 15, 20, 30, 32} ms, default 10. `noise-suppression-level` is 0–100, default 100. — [gst-krisp-audio README](https://github.com/krispai/gst-krisp-audio)

**Suppression-level defaults (verified)**

| Integration | Default level |
|---|---|
| Krisp samples | 100 |
| GStreamer element | 100 |
| Pipecat `KrispVivaFilter` | 100.0 |
| LiveKit `livekit-plugins-krisp` | 75 |
| LiveKit internal Cloud backend | 90 (constructor default) |

Sources: files cited above.

**CPU and SIMD**
- The x86_64 native library contains AVX2, FMA3 and AVX-512 (FP, BF) kernel strings, and the arm64 build contains NEON/XNNPACK/fp16 components (verified by `strings` and the license list). — [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)
- VIVA Go SDK v1.4.0 (2026-07-08): "CPU consumption for Voice Isolation models was reduced by 30–40% on armv8a hardware by using FP16 SIMD instructions if available" (snippet). — [sdk-docs Go v1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)
- A snippet attributes "VIVA-VC adds approximately 6-10% single-core CPU per stream" to a search result. Its source page is most likely the third-party callsphere.ai article, which I could not read. It is unclear what "VIVA-VC" refers to, so **do not rely on it**. — [callsphere.ai (blocked)](https://callsphere.ai/blog/vw9h-build-voice-agent-krisp-audio-filter-viva-2026)
- VI 2.5 lite has "3.5x less compute" than full VI 2.5; "If CPU per stream is what has kept isolation off most of your traffic, this is the version that removes the objection" (snippet). — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- The LiveKit NC README recommends `OPENBLAS_CORETYPE=Haswell` for AMD crashes. The native plugin sets `OPENBLAS_NUM_THREADS=1` (verified in an earlier session; see the earlier krisp.md). — [PyPI livekit-plugins-noise-cancellation](https://pypi.org/project/livekit-plugins-noise-cancellation/)

### Inferences
- **Dev and prod platforms.**
  - macOS arm64 is covered by a documented wheel.
  - Linux x86_64 is covered.
  - Linux aarch64 is certainly supported by the C++ server SDK (2025-09) and by LiveKit's `manylinux_2_28_aarch64` build of the VIVA SDK. A Python `krisp_audio` aarch64 wheel is **not** confirmed; the v1.0.0 list omitted it.
  - `cp312-abi3` (1.12.0) implies one wheel for Python ≥ 3.12. Earlier wheels were per-version (`cp312-cp312`).
- **Threading plan for LiveKit Agents.**
  - `session.process` is synchronous CPU work. In LiveKit's `FrameProcessor` it runs on the audio path, so per-frame cost adds directly to input latency.
  - Use one session per participant track. Share one `globalInit` per worker process and never call `globalDestroy` while any session is alive.
  - With LiveKit's default job-per-process model this is automatic, since each job process inits once.
- **Pin the frame size.** Set `AudioInputOptions(frame_size_ms=10|20)` and Krisp `frame_duration_ms` to a divisor of it. That keeps buffering to at most one Krisp frame and avoids the 50 ms/Silero issue (livekit/agents#3894).
- **Silent pass-through risks for the user, in order of likelihood:**
  1. License validation fails. For example, an air-gapped prod host cannot reach Krisp's licensing endpoint. The SDK then *passes audio through* after a grace period, and only a callback or log reveals it.
  2. A nanobind/pybind11 mismatch in wrapper code (Pipecat #5413).
  3. Non-mono frames are passed through.

  Any A/B test should assert that the output differs from the input. It should also log the license callback.
- **No-cloud requirement.** Audio is processed locally, but the "UAR" (usage auto-reporting) Python SDK plus libcurl licensing means **outbound network calls to Krisp** (license validation and usage counts). Nothing indicates audio is uploaded. The user should ask Krisp for a non-UAR/offline-licensed Python build; one exists for Go.

### Gaps
- There is no public Python API reference: cdn.krisp.ai and sdk-docs.krisp.ai were blocked. The exact behaviour of `process()` under concurrent calls from multiple threads on *different* sessions is not documented in the reachable sources. Pipecat and LiveKit call it from one audio thread per stream.
- Per-session memory (recurrent state plus buffers) was not measured, because I had no `krisp_audio` wheel or `.kef`.
- No published RTF or "streams per core" figure from Krisp for any VIVA model. The only number seen (6–10% of a core per stream) is from an unverified third-party source.
- The grace-period length and the licensing endpoint hostnames are unknown.
- Whether `krisp_audio` wheels exist for Linux aarch64 and for Python 3.13 under the abi3 scheme is unverified.

---

## 3. Algorithmic latency and look-ahead per model

### Takeaway
Krisp publishes **15 ms algorithmic latency** only for VI 2.5, and "15 ms latency" for the VIVA 2.0 bundle. The embedded configs of the models LiveKit ships (VIVA PRO v1 = BVC, VIVA TEL v2 = inbound BVC) and of Krisp NC all use a **30 ms analysis window with a 15 ms hop**. The model sees `frameCount` 4 frames. Nothing in the configs indicates future-frame look-ahead. Wrapper framing adds up to one SDK frame (10 ms by default).

### Cited Findings
- "Voice Isolation 2.5 adds only 15 ms of algorithmic latency while running entirely on CPU, with no GPU required" (snippet, 2026-08-12). — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- VIVA 2.0 "runs on CPU, with 15 ms latency" (snippet, 2026-05-06). — [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/)
- The embedded configs are listed below (verified). — [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/); [PyPI livekit-plugins-noise-cancellation 0.2.6](https://pypi.org/project/livekit-plugins-noise-cancellation/0.2.6/)
  - VIVA PRO v1 / BVC: `workingFrameDuration` 30 ms, `step` 480 @ 32 kHz (15 ms), `frameCount` 4.
  - VIVA TEL v2 / BVCTelephony: 30 ms, `step` 240 @ 16 kHz (15 ms), `frameCount` 4.
  - NC `c8.f.s` (DeepFilterNet): 30 ms, `step` 480 @ 32 kHz.
- The SDK I/O frame is 10/15/20/30/32 ms. Default is 10 ms in Krisp samples, GStreamer, Pipecat's filter and LiveKit, and 20 ms for turn and IP. GStreamer's FIFO costs "up to one frame (<= frameDurationMs) of startup latency" (verified). — [gst-krisp-audio krisp_session.hpp](https://github.com/krispai/gst-krisp-audio/blob/main/src/krisp_session.hpp)
- **Turn Prediction v3:** "pushes end-of-turn latency below 200ms". "At the recommended threshold (0.5), 69% of true turn-shifts are detected within 200 ms of silence", up from 47% with v2 (snippet, 2026-05). — [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462); [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- **TTS gate latency in Pipecat** (verified): after TTS is last detected, the filter waits `_TTS_CLEARED_COOLDOWN = 0.5` s before starting isolation. If TTS is never detected it starts after `tts_detection_timeout` (default 3.0 s). — [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py)

### Inferences
- With a 15 ms hop and a 30 ms window, the intrinsic delay is at least 15 ms. It is up to about 30 ms if a standard overlap-add synthesis is used. Krisp's "15 ms" figure is consistent with the hop and suggests a low-delay synthesis window. **End-to-end added delay** in a LiveKit pipeline is then roughly as follows (inference, unmeasured):
  - algorithmic 15–30 ms
  - SDK frame buffering, 0–10 ms at 10 ms frames
  - LiveKit `frame_size_ms` re-chunking
  - compute time per frame
- I found no statement of look-ahead for BVC, VI v3 or VI 2.5. The configs expose only past-context `frameCount`.
- For barge-in, 15–40 ms of added delay is small compared with VAD `min_speech` and endpointing windows. The one-shot 0.5–3 s TTS gate is a much larger behavioural latency (§4), but it applies only at session start.

### Gaps
- There are no published latency figures for NC, BVC, VI v3 or VI-tel v2/v2.1. The numbers above come from configs, not Krisp statements.
- The synthesis window type, and therefore the true algorithmic latency, is not visible.
- Per-frame compute time on specific CPUs (Apple M-series, Xeon/EPYC, Graviton) is unmeasured.

---

## 4. How isolation picks the primary speaker, and behaviour and failure modes

This section covers speakerphone, TV louder than the caller, a silent caller with the TV on, overlap, backchannels, quiet callers, music/hold, and TTS echo together with the Pipecat TTS gate.

### Takeaway
Krisp's isolation is **enrollment-free** and picks the primary speaker from **proximity and level cues**: the near-field, loud, consistent voice. It was designed around headsets and handsets. This is the root of every documented failure mode:
- quiet or far-field and speakerphone callers get suppressed (community reports for BVCTelephony; Krisp itself says v2.1 "reduces voice suppression in certain scenarios" relative to v2);
- a TV or nearby talker that is closer or louder can win;
- inbound models are "not designed for multiple simultaneous voices on the same microphone".

The embedded configs show a level-based **`backgroundSpeakerFix`** post-processor (10 dB → 5 dB cut thresholds over 40-hop ≈ 0.6 s runs) and a `pnc` block with an infinite half-life (`halfLifeInSec: -1`), consistent with a stateful primary-speaker estimate.

Pipecat's TTS gate is **one-shot at session start**. It is not a mid-call echo guard. The code comment points to iPhone call screening, and Krisp positions its TTS detector for outbound calls answered by an IVR or bot. So the gate exists because isolation can lock onto an initial synthetic voice and then suppress the human who follows.

### Cited Findings

**Selection mechanism**
- BVC "detects the primary speaker using speaker-to-microphone proximity cues", "does not require user voice enrollment", and "removes background noises and reverberation" (snippet; this was in the earlier note). — [Krisp contact-center BVC blog](https://krisp.ai/blog/contact-center-background-voice-cancellation/)
- The Krisp help centre says a boom microphone "keeps the microphone close to your mouth, so your voice stays loud and consistent", which helps it identify the primary speaker. The model "requires that the user speak close to the microphone" (snippet). — [help.krisp.ai: Headset and audio recommendations](https://help.krisp.ai/hc/en-us/articles/27985368822556-Headset-and-audio-recommendations-for-Krisp); [help.krisp.ai: Voice Isolation-compatible devices](https://help.krisp.ai/hc/en-us/articles/7270378194972-Voice-Isolation-compatible-devices)
- Outbound BVC needs a headset or compatible device, otherwise "regular NC models should be used". "Krisp inbound tech is not designed for multiple simultaneous voices on the same microphone" (snippet). — [sdk-docs Model Selection Guide](https://sdk-docs.krisp.ai/docs/rtc-model-guide-bvc-nc)
- **Config evidence (verified)** from the same two models:
  - `backgroundSpeakerFix {cutStartDB: 10.0, cutEndDB: 5.0, runFrameCount: 40, runMinLen: 2, utteranceLen: 2, varWindMode: true}`
  - `pnc {freezeLowEnThr: 700, freezeHighEnThr: 710, halfLifeInSec: -1}`
  - PRO additionally runs a `csd` sub-network (`csdEnabled: true`).
  - Source: [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)

**Reported failures and fixes**
- LiveKit community (Feb 2026): a user says "BVCTelephony can be overly aggressive and occasionally cancels out quiet callers" and proposes applying gain before it (snippet). — [community.livekit.io/t/300](https://community.livekit.io/t/audio-gain-before-bvctelephony/300)
- LiveKit community thread "Unexpected Audio Degradation After Enabling BVC…". The snippet summary names two causes: 50 ms frame forcing and double processing ("don't also enable Krisp on the frontend or your SIP trunk") (snippet). — [community.livekit.io/t/745](https://community.livekit.io/t/unexpected-audio-degradation-after-enabling-bvc-noise-cancellation-in-livekit-voice-agent/745)
- Krisp changelog (2026-07-08): `krisp-viva-vi-tel-v2.1` "reduces voice suppression in certain scenarios … compared to … krisp-viva-vi-tel-v2" (snippet). — [sdk-docs Go v1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)
- The VI 2.5 blog says it "lowers WER against no processing on every engine tested", with "no harm on clean audio" and "largest gains in reverberant conditions" (snippet). — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- The newer lite/tel model "exhibits significantly stronger performance in narrow-band and codec-degraded conditions … critical for inbound telephony" (snippet). — [Krisp blog small VI model](https://krisp.ai/blog/small-voice-isolation-model/)

**The TTS-detection gate in Pipecat** (verified, code by Krisp staff, PR #4668 merged 2026-06-30)
- The docstring reads: "Optionally supports TTS detection (iPhone screening feature is standalone model) to delay voice isolation until bot speech playback has stopped, preventing later real human speech suppression artifacts."
- Logic:
  1. On `start()`, a `TtsDetectorFloat` session is created.
  2. While `_tts_detection_active`, frames are **returned unmodified**. Each frame is scored.
  3. Once any frame exceeds `tts_threshold` (0.5), isolation starts 0.5 s after the last TTS frame.
  4. If no TTS is ever seen, isolation starts after `tts_detection_timeout` (3.0 s).
  5. After that, "noise cancellation activates for the remainder of the session". The gate never re-arms.
- The docs phrase it as preventing the filter "from suppressing real human speech that immediately follows bot TTS playback".
- Sources: [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py); [krisp-viva-filter.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/krisp-viva-filter.mdx); [pipecat PR #4668](https://github.com/pipecat-ai/pipecat/pull/4668)
- The Krisp TTS Detector's "primary use case is for an outbound voice AI agent to recognize when an inbound voice AI agent or IVR picks up a call" (snippet). — [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)

**Backchannels**
- Krisp addresses backchannels with a separate model, **Interruption Prediction v1**: an "audio-only classifier that … distinguishes intent-to-take-the-floor from backchannel speech like 'yes' or 'mhm'", with "under 6% false positives at the recommended threshold" (snippet). — [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- In Pipecat, IP runs only while VAD reports speech. It triggers a user turn when `ip_prob >= threshold` (0.5, 20 ms frames) and is meant to sit alongside `TranscriptionUserTurnStartStrategy` as a fallback (verified). — [krisp_viva_ip_user_turn_start_strategy.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py)
- A production team on Pipecat Cloud with the Krisp VI `tel` filter enabled measured the following across 153 real phone calls: "34% contained a reply aborted by a false turn-start inside the caller's own sentence, 6.5% … degenerated into a loop". They could not enable the IP model on Pipecat Cloud (issue opened 2026-07-09, since closed). — [pipecat issue #4994](https://github.com/pipecat-ai/pipecat/issues/4994)

**Music, hold and ringtones**
- The C++ `NcSessionConfig` has a `RingtoneCfg` "for inbound" that takes a separate ringtone `.kef` (sample added 2025-11-26, verified). LiveKit's older NC binary linked a `krisp-ringtone-processor` (see earlier note). — [Krisp-SDK-Sample-Apps commit 95c0eca](https://github.com/krispai/Krisp-SDK-Sample-Apps/commit/95c0eca759dc8c2c97801f3410ab337afa904940)
- The VIVA docs list "TV, music, kids, cars" among removed sources (snippet). — [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)

### Inferences
- **Speakerphone or far-field caller while a TV plays nearby.** This is the worst case. Neither voice is near-field. The model's proximity and level cues may keep the TV dialogue, which is often mastered loud and dry, or may gate both. I expect intermittent attenuation of the caller: the documented "quiet caller" symptom.
- **TV louder than the caller.** The 10 dB / 5 dB `backgroundSpeakerFix` thresholds suggest segments well below the dominant voice's level get cut. A caller 10 dB below a TV could be treated as background (speculative; the semantics of the thresholds are unknown).
- **Caller silent while the TV talks.** If the TV voice is the only and loudest voice, especially at call start, an enrollment-free, level-driven model may keep it as "primary" and pass it to VAD and ASR. That produces false barge-ins, which is exactly what the user wants to avoid.
  - The `pnc.halfLifeInSec: -1` field hints at a non-decaying running statistic. If that is a primary-speaker profile, an early lock-on to the wrong voice could persist for the whole call.
  - This is the likely reason Krisp built the start-of-session TTS gate: for outbound calls answered by iPhone Call Screening, an IVR or a voicemail greeting.
  - This is inference, not documented.
- **The agent's own TTS echo mid-call** is *not* handled by the Pipecat gate, which is one-shot. SIP echo is usually low, and WebRTC clients run AEC. Isolation may even help by treating residual far-field echo as background. Echo suppression of the user's barge-in must still be tested.
- **Backchannels.** Short, soft "mm-hmm" sounds are the most exposed class:
  - `backgroundSpeakerFix` works on runs of `runMinLen`/`utteranceLen` = 2 hops (about 30 ms) and level differences.
  - Suppression level 100 is the most aggressive. LiveKit defaults to 75.

  The user should measure backchannel recall after filtering at levels 60, 75 and 100. They should consider Krisp IP (or LiveKit's own interruption logic) as the backchannel classifier rather than relying on isolation.
- **Laughter.** The TEL v2 name `blocked.laughter` suggests laughter handling changed between BVCTelephony and TEL v2. Laughter often co-occurs with backchannels, so it needs checking.
- **Overlap.** Krisp's own "competing speakers" category improved from 35.92% to 10.90% WER (§5). Overlap is the case VI 2.5 targets. Earlier models (PRO v1 / TEL v2) have no published overlap numbers.

### Gaps
- There is no official description of the selection algorithm beyond "proximity cues". The meaning of `backgroundSpeakerFix`, `pnc` freezing and the `csd` sub-model (competing-speaker detection?) is unknown.
- There is no data on speakerphone or car-kit callers, TV-louder-than-caller, backchannel recall or music-on-hold behaviour for any VIVA model.
- The full text of the LiveKit community threads (/t/300, /t/745) and any staff replies could not be read.
- It is unknown whether VI v3 / VI 2.5 changed the selection approach (for example, to embedding-based tracking). Krisp calls v3 a "ground-up rebuild" but gives no mechanism.

---

## 5. Quality evidence and methodology (Krisp benchmarks, NVIDIA STT, WER reconciliation, VAD false triggers, third-party comparisons)

### Takeaway
All quantitative evidence is **vendor-produced**. The strongest items:
- **VI 2.5 (2026-08-12):** 10 STT systems from 7 vendors, including NVIDIA. Mean WER **15.35% → 8.22% (−46.4%)**. "Competing speakers" **35.92% → 10.90% (−69.7%)**. "No harm on clean audio". Against the previous VI v2.1 on hard recordings, 15.42% → 11.61%.
- **BVC turn-taking study (2025-05-13):** AMI with Silero VAD and Whisper v3. **3.5× fewer VAD false positives**, VAD precision up by more than a quarter, and more than 2× lower WER.

The conflicting "17.9% → 10.2% (−43%) across 11 engines" snippet is a *second, internally consistent* figure (17.9 → 10.2 = −43.0%). It is probably an earlier or alternative aggregate: 11 vs 10 engines, or a different blog revision. It is not a typo of the 46.4% figure. The NVIDIA model used was not named in anything I could read.

The only third-party comparison found comes from competitor ai-coustics. It claims a Krisp NC product *raised* WER by more than 10 pp on English competing speech. That test targeted plain NC, not VIVA isolation.

### Cited Findings

**VI 2.5 benchmark** (snippets; blog dated 2026-08-12)
- "Voice Isolation 2.5 achieves a 46.4% WER reduction on average, dropping from 15.35% on untouched audio to 8.22% … On competing speech, there are 69.7% fewer errors." — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- "On calls with competing speakers, word error rate falls from 35.92% to 10.90%." — same
- "benchmarked … across 10 streaming and non-streaming STT systems from Deepgram, NVIDIA, Soniox, ElevenLabs, AssemblyAI, Google, and Cartesia", "lowers WER against no processing on every engine tested, with its largest gains in reverberant conditions", and it is "STT-agnostic". — same
- "On challenging recordings with complex acoustic environments, WER dropped from v2.1's 15.42% to 11.61%." — same
- Conflicting aggregate: "cuts average word error rate 43% (17.9% → 10.2%) across 11 speech-to-text engines". — same
- Test set, from an earlier snippet recorded in the previous note: "1,685 real-world recordings (about 7 hours of audio)". — same
- One search summary mentioned "NVIDIA Parakeet". It appears to echo my query terms rather than quote the blog, so **the NVIDIA model is unverified**. — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)

**BVC turn-taking study** (snippets; blog dated 2025-05-13)
- "With Krisp BVC, false-positive triggers in VAD … were reduced by 3.5x on average". Method: "latest version of open-source SileroVAD" and "Whisper V3 (base version)", with BVC applied upstream on the **AMI** meeting corpus. "The precision after Krisp BVC increases by over a quarter". WER on Whisper v3 on AMI shows "more than a 2x improvement". — [Krisp blog: Improving turn-taking with BVC](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/)

**VIVA 2.0 claims** (snippets, 2026-05-06)
- VI v3 "can improve word error rate by 20-40% on real-world calls" and is "3.5x smaller than its predecessor". The attribution is uncertain; see §1.
- Turn Prediction v3 raises the share of turn-shifts detected within 200 ms from 47% to 69%. Krisp says its accuracy curve "sat below LiveKit's built-in and Deepgram Flux's across the operating range" in May 2026 benchmarks.
- Interruption Prediction v1 has "under 6% false positives at the recommended threshold".
- Sources: [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents); [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)
- "Teams using VIVA have seen 3.5x better turn-taking accuracy" (snippet, marketing). — [Krisp | VIVA](https://krisp.ai/developers/viva/)

**Third-party and competitor evidence** (snippets)
- ai-coustics blog "Comparing Krisp and ai-coustics real-time audio enhancement" (2025-11-10). "Krisp noise cancellation raised WER by over 10pp on English competing speech, while ai-coustics' Voice Focus reduced WER by 4.23pp at full intensity and up to 6.96pp at its optimal 0.75 setting". Also "Quail Multi Speaker achieves up to ~20% relative WER reduction … compared to raw audio and perceptual denoisers like Krisp". This is competitor marketing; the Krisp product and model tested are unspecified. — [ai-coustics blog](https://ai-coustics.com/blog/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you); [ai-coustics benchmarks](https://ai-coustics.com/benchmarks-quantitative)
- LiveKit's `noise-canceller` example tool can compute WER before and after NC, BVC, BVCTelephony, `viva-voice-isolation` and `viva-voice-isolation-telephony`. It needs LiveKit Cloud minutes (verified in the earlier session). — [livekit-examples/noise-canceller](https://github.com/livekit-examples/noise-canceller)
- There are no academic or independent (non-vendor) evaluations of Krisp BVC or VIVA. Searches of arXiv and GitHub issues (livekit/agents, pipecat-ai/pipecat) returned only operational bugs (frame size, nanobind, cloud model provisioning), not quality studies. — [GitHub search: livekit/agents BVC issues](https://github.com/livekit/agents/issues?q=BVC); [pipecat #5413](https://github.com/pipecat-ai/pipecat/issues/5413); [pipecat #4994](https://github.com/pipecat-ai/pipecat/issues/4994)

### Inferences
- **Reconciling the WER numbers.** Both pairs are arithmetically self-consistent: 15.35 → 8.22 is −46.4%, and 17.9 → 10.2 is −43.0%. They differ in engine count (10 vs 11). That points to two aggregates, perhaps a headline/meta figure and a body figure, or a pre- and post-revision set. Report both with their engine counts. The 69.7% competing-speaker figure goes with the 10-engine set (35.92 → 10.90).
- **Relevance to NVIDIA Nemotron streaming ASR plus Sortformer.**
  - The benchmark includes an unnamed NVIDIA engine. That makes it the closest published evidence, but its baseline WERs (15%+) come from hard, noisy conditions.
  - For a Nemotron + Sortformer pipeline the more important metrics are not reported anywhere: VAD false-trigger rate, diarization confusion, and backchannel recall.
  - The user needs an in-house A/B on their own TV and crosstalk corpus, per §4.
- **The ai-coustics result is not evidence against VIVA isolation.** The model tested was probably Krisp NC, which does not remove voices. It is also self-interested. It does show that plain NC (the `c8` DeepFilterNet class) should not be expected to help on competing speech.
- **Maturity signal.** Krisp's own engineers maintain the Pipecat integration (commits from `gharutyunyan@krisp.ai`), so the Pipecat code is the closest thing to a public reference implementation.

### Gaps
- No per-engine WER table, no name for the NVIDIA model, no per-condition breakdown other than "competing speakers" and "reverberant", no dataset release, and no confidence intervals.
- No false-VAD-trigger or barge-in metrics for VI v3 / VI 2.5; the 3.5× figure is for 2025 BVC on AMI with Silero.
- No independent DNSMOS/PESQ or target-speaker-preservation metric (e.g. SI-SDR on the primary speaker, or backchannel recall) for any Krisp model.
- The full text of the VI 2.5 blog, the VIVA 2.0 blog and the ai-coustics comparison could not be read, because all three domains were blocked.
