# Krisp voice isolation (NC / BVC / VIVA) and LiveKit's Krisp-based noise cancellation, as a candidate for a self-hosted LiveKit Agents 1.8.3 stack (state as of 2026-09-26)

Method note: krisp.ai, sdk-docs.krisp.ai, docs.livekit.io, livekit.com, community.livekit.io, docs.pipecat.ai, vapi.ai and businesswire.com were blocked by this environment's egress proxy. Facts from those domains come from WebSearch result snippets. They are labelled "(search snippet)" and should be treated as less reliable than a full-page read. Facts labelled "(wheel inspection)" come from my own reading of the wheels downloaded from PyPI into the scratch area: Python source, plus `strings` on the native `.so`. The Pipecat docs and source were read in full from raw.githubusercontent.com.

## 1. What Krisp models exist for server-side / voice-agent use, and what does BVC actually do?

### Takeaway
In 2025–2026 Krisp's agent-facing family is called **VIVA**. It covers Voice Isolation (VI, noise plus background-voice removal, with "pro" up to 32 kHz and "tel" up to 16 kHz variants), classic NC, BVC and its telephony/inbound variant, VAD, audio-only Turn Prediction (v3), Interruption Prediction v1 (backchannel vs. real barge-in), TTS detection, "perception" models and accent conversion. BVC and VI use no enrollment: they keep the voice that sounds closest to the microphone. That works well for headset or handset callers and is a known weak spot for speakerphone or far-field callers. All of these models run on CPU. Krisp publishes 15 ms algorithmic latency for VI 2.5. I found no published CPU-cost figures.

### Cited Findings
**Model line-up and release timeline**
- VIVA 2.0 launched 2026-05-06 at Twilio Signal. Krisp describes it as "the voice AI infrastructure layer for voice agents, IVRs, and conversational AI" with "small, real-time models that improve WER, predict when users finish speaking, classify interruptions, and read perceptual signals like synthetic speech, gender, and accent." (search snippet) — [BusinessWire, 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents); [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/)
- VIVA 2.0 components (search snippets):
  - Turn Prediction v3, a "multilingual model that predicts end-of-turn from audio alone, no transcription needed".
  - Voice Isolation v3.
  - Interrupt Prediction v1, an "audio-only classifier that predicts when a user is intending to interrupt the agent, and distinguishes intent-to-take-the-floor from backchannel speech like 'yes' or 'mhm'".
  - Sources: [SMEStreet](https://smestreet.in/technology/krisp-viva-20-enhances-voice-ai-turn-prediction-11808381); [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- Voice Isolation 2.5 blog post, dated 2026-08-12 (search snippet). It "adds only 15 ms of algorithmic latency while running entirely on CPU, with no GPU required", is "built for real-time server-side deployments and supports narrowband audio and telephony streams". A "VI lite 2.5" variant "matches the full model on specs and integration at roughly 3.5× smaller parameter size" with "much lower CPU computational cost". — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/); [Krisp blog small VI model](https://krisp.ai/blog/small-voice-isolation-model/)
- The Krisp CEO's X post refers to "VIVA 2.5, with our most advanced models yet" (title only, not read). — [x.com/davitb](https://x.com/davitb/status/2087555112810250608)
- Model files named in the Pipecat docs (full read):
  - Voice isolation: `krisp-viva-pro` ("Mobile, Desktop, Browser (WebRTC, up to 32kHz)") and `krisp-viva-tel` ("Telephony, Cellular, Landline, Mobile, Desktop, Browser (up to 16kHz)"). An example file name is `krisp-viva-vi-tel-v2.kef`.
  - Turn: `krisp-viva-tp-v3.kef`. The turn reference page still shows `krisp-viva-tt-v2.kef`.
  - Interruption prediction: `krisp-viva-ip-v1.kef`.
  - VAD: `krisp-viva-vad-v2.kef`, covering 8–48 kHz.
  - Source: [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- An optional Krisp **TTS-detection model** (`KRISP_VIVA_TTS_MODEL_PATH`) exists. Pipecat uses it to "delay voice isolation until bot speech playback has stopped, preventing later real human speech suppression artifacts". The code comment mentions an "iPhone screening feature". — [pipecat krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py)
- Accent Conversion SDK: listener-side accent conversion for "Meetings CX and Voice AI Agents" was announced 2026-03-03 (title only). — [BusinessWire 2026-03-03](https://www.businesswire.com/news/home/20260303945269/en/Krisp-Launches-Listener-Side-Accent-Conversion-for-Meetings-CX-and-Voice-AI-Agents); [Krisp blog accent conversion SDK](https://krisp.ai/blog/accent-conversion-sdk/)

**What BVC does and how it picks the primary speaker**
- BVC is "developed to cancel all background voices, removes background noises and reverberation, and does not require user voice enrollment or training on user voice data". It "detects the primary speaker using speaker-to-microphone proximity cues" (search snippet). — [Krisp contact-center BVC blog](https://krisp.ai/blog/contact-center-background-voice-cancellation/); [Krisp help: BVC](https://help.krisp.ai/hc/en-us/articles/15856897420444-Background-Voice-Cancellation-with-Krisp-AI-Meeting-Assistant)
- "BVC-o models are designed for microphone (outbound/uplink) audio stream to remove other voices near the primary speaker wearing a headset or ear buds and all other noises." (search snippet) — [sdk-docs: BVC & NC](https://sdk-docs.krisp.ai/docs/krisp-rtc-bvc-nc)
- Krisp's model selection guide (search snippet):
  - Models are specific to either the outbound (microphone) or the inbound (speaker) stream, and "outbound models should not be used on inbound streams" and vice versa.
  - BVC requires that the voice's sampling rate be "above 8kHz". Audio above 32 kHz is downsampled.
  - A headset or compatible device should be used; "regular NC models should be used if requirements are unmet".
  - Source: [sdk-docs: Model Selection Guide BVC & NC](https://sdk-docs.krisp.ai/docs/rtc-model-guide-bvc-nc)
- VI models (snippet about the conversational-AI VI page) "support audio sampling rates up to 16 kHz" and "Krisp Audio SDK will automatically resample the audio input to match the sampling rate of the model". — [sdk-docs: Voice Isolation](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)

**Sample rates and frame sizes (SDK API)**
- The public `krisp_audio` Python SDK accepts input at 8, 16, 24, 32, 44.1 and 48 kHz, with frame durations of 10, 15, 20, 30 or 32 ms. Pipecat's filter defaults to 10 ms frames and suppression level 100. KrispVivaTurn defaults to 20 ms frames and threshold 0.5. — [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py); [krisp-viva-turn.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/utilities/turn-detection/krisp-viva-turn.mdx)
- The Krisp SDK switched its Python bindings from pybind11 to nanobind in 1.11.0. As a result the suppression level became a float and input arrays must be writable. — [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)

**Turn-taking and interruption models**
- Turn-taking v1 (2025): "audio-only, 6M weights", "6.1M params … 65MB … CPU-optimized". It uses prosodic/acoustic features and is claimed to be "5–10x smaller" than comparable models with a better latency/accuracy trade-off (search snippet). — [Krisp blog: turn-taking](https://krisp.ai/blog/turn-taking-for-voice-ai/); [Turn-taking v2](https://krisp.ai/blog/krisp-turn-taking-v2-voice-ai-viva-sdk/)
- Krisp's claims for Turn Prediction v3 (search snippet):
  - It "pushes end-of-turn latency below 200ms".
  - The share of fast responses (<200 ms) rose "from 47% to 69%" compared with v2 "without increasing the risk of interrupting the user".
  - Krisp says its May 2026 accuracy curve "sat below LiveKit's built-in and Deepgram Flux's".
  - Source: [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- The Krisp Tt (turn v3) API "accepts an external VAD flag alongside audio frames". — [pipecat krisp_viva_turn.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/krisp_viva_turn.py)

**Internals of LiveKit's bundled Krisp build (wheel inspection of livekit-plugins-noise-cancellation 0.3.2)**
- The native library links these Krisp components:
  - `krisp-nc-processor 4.0.9`, with source files named `deep-filter-net/krisp_nc_df_processor.cpp`
  - `krisp-inference-engine 2.2.23`, with GRU networks, including `gru_modify_vad`
  - a `krisp-ringtone-processor`
  - `onnxruntime 1.18.1` built CPU-only (the strings say "CUDA execution provider is not enabled in this build")
  - Source: [PyPI livekit-plugins-noise-cancellation 0.3.2](https://pypi.org/project/livekit-plugins-noise-cancellation/0.3.2/)
- Bundled model files and sizes:

  | Model | File | Size |
  |---|---|---|
  | NC | `c8.f.s.026300-1.0.0_3.1.kef` | 6.6 MB |
  | BVC | `hs.c6.f.m.75df8f.kef` | 29.4 MB |
  | BVCTelephony | `inb.bvc.hs.c6.w.s.23cdb3.kef` | 28.0 MB |

  The native `.so` is 41 MB. The model files are byte-for-byte the same size in 0.2.5 (2025-06-30), 0.2.6, 0.3.0 and 0.3.2 (2026-09-15). — [PyPI](https://pypi.org/project/livekit-plugins-noise-cancellation/)

### Inferences
- The BVCTelephony file name contains "inb." and "hs", and Krisp's guide separates inbound from outbound models. BVCTelephony is therefore most likely an **inbound** BVC model, meant for the far end of a phone call as received by a server. That matches a server-side agent receiving a caller's audio. The "w" in the name plausibly means wideband (16 kHz), and "f" in the BVC/NC names plausibly means full-band. This reading of Krisp's naming is not confirmed.
- LiveKit's bundled BVC/NC models have apparently not changed since mid-2025. The newer VIVA VI v2/v3/2.5 models reach LiveKit users only through the separate `livekit-plugins-krisp` package (see §3) or through a direct Krisp license.
- BVC chooses the primary speaker by proximity, not by speaker identity. A TV or a nearby person that is louder or closer to the phone than the caller, or a caller on speakerphone, can be treated as the primary speaker, and then the real caller gets attenuated. That is directly relevant to the user's goal of removing TV and nearby people.
- Pipecat added a TTS-detection gate, and Krisp states the goal as preventing "later real human speech suppression artifacts". This implies Krisp VI can lock onto a synthetic or bot voice that leaks into the uplink (echo, or phone call screening) and then suppress the real human. That is a known failure mode, and it matters for barge-in.
- Everything points to CPU-only inference (onnxruntime without CUDA, GRU networks, Krisp's own statement of no GPU). A GPU does not help.

### Gaps
- I found no published CPU cost (e.g. % of a core per stream, or real-time factor) for NC, BVC or VI on x86 or ARM. Also missing: algorithmic latency for BVC or VI v3, parameter counts for BVC/VI, and exact frame hop. sdk-docs.krisp.ai was blocked.
- I could not verify how BVC behaves on non-headset, speakerphone or car-kit phone calls beyond Krisp's "use NC instead" guidance.
- No public accuracy numbers for Interrupt Prediction v1 (backchannel precision/recall) were found.

## 2. Krisp SDK (Server SDK / "AI Voice SDK" / VIVA SDK): availability, platforms, languages, licensing, pricing, offline use

### Takeaway
The VIVA server SDK is a proprietary, application-gated commercial SDK. You download a Python wheel (`krisp_audio`, not on PyPI) and `.kef` models from Krisp's developer portal and initialize it with an API/license key (required since SDK v1.6.1). It runs fully in-process on CPU, so caller audio never leaves the host. Pricing is not published: a third-party profile reports per-minute volume pricing. Pipecat Cloud resells it at $0.0015/min after 10k free minutes. Whether the license key phones home (online validation or metering) is not documented publicly.

### Cited Findings
- **Getting the SDK (Pipecat docs, full read):** "you will need access to a Krisp developers account, where you can download the Python SDK, models, and generate an API key". The steps: log in to the portal (`https://sdk.krisp.ai/`), open the "Server SDK Version" tab, download the Python SDK plus the Voice Isolation and Turn Detection models, then install the wheel from `dist/`. The example wheel is `krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl` from `krisp-viva-uar-python-sdk-1.8.0`. — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- **API key:** "The `KRISP_VIVA_API_KEY` is required for Krisp SDK v1.6.1 and later." The SDK is initialized once per process, and only the first component's key is used. — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- **Init call:** the SDK is initialized with `krisp_audio.globalInit("", key, license_callback, log_callback, LogLevel.Off)`, and a `license_callback` reports "Krisp licensing error". Older SDKs took no key. — [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)
- **License terms:** "Krisp SDK is a commercial product … need to obtain a commercial license from Krisp Technologies, Inc … apply for a license on Krisp developer website" (search snippet). — [sdk-docs: Licensing](https://sdk-docs.krisp.ai/docs/licensing-information)
- **Pricing and access (third-party):** a third-party profile says the Voice AI SDK is "mostly application-gated, with an Early-stage startup track and an Enterprise track quoted via volume pricing", and that the license model is "per-minute via SDK token with volume tiers down to ~$0.001/min at scale" (search snippet; not a Krisp primary source). — [UsagePricing: Krisp](https://www.usagepricing.com/blueprint/krisp); [api-evangelist/krisp](https://github.com/api-evangelist/krisp)
- **Platforms and bindings (third-party profile, full read):** the SDK family covers "Windows, macOS, Linux, Web (JS/WASM), iOS, and Android with C++, Python, Node.js, Go, Rust, and JavaScript bindings". The same profile lists a developer dashboard `developers.krisp.ai`, a playground `lab.krisp.ai`, and a "programmatic SDK/model download API". — [api-evangelist/krisp README](https://github.com/api-evangelist/krisp)
- **Krisp's public GitHub org:**
  - `Krisp-SDK-Sample-Apps` (C++, default branch `krisp-sdk-v9`, updated 2026-08-28)
  - `gst-krisp-audio` (C++, a GStreamer element, created 2026-04-14)
  - `WebRTC-Integration` (Python)
  - `webrtc-android-krisp-module`
  - `vt-js-sdk`
  - Source: [github.com/krispai](https://github.com/krispai)
- **Legacy path (2024–2025):** `pipecat-ai-krisp` 0.4.0 (BSD-2) was a pybind11 wrapper around Krisp's "Desktop SDK (in C++) that supports Linux, Windows, and macOS". You downloaded it from `sdk.krisp.ai/sdk/desktop` and built it locally. — [PyPI pipecat-ai-krisp](https://pypi.org/project/pipecat-ai-krisp/)
- **Resold price (Pipecat Cloud):** "First 10,000 minutes per month: Free; Additional minutes: $0.0015 per minute", billed on active session minutes. The same page says "Krisp cannot be used in local development environments, as it requires a proprietary SDK and model which can only be distributed on Pipecat Cloud". That applies to the Pipecat-Cloud-bundled path, not to a direct Krisp license. — [pipecat-ai/docs pipecat-cloud/guides/krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)
- **Separate self-serve product:** Krisp's Voice Translation API "went fully self-serve in July 2026". It is a cloud API with Starter ($249/mo) and Advanced ($799/mo) tiers, so it is irrelevant for local isolation (search snippet). — [api-evangelist/krisp](https://github.com/api-evangelist/krisp)

### Inferences
- **Platform fit.** A macOS arm64 cp312 wheel is documented, so Apple Silicon development is covered. Linux x86_64 is certainly supported. Linux aarch64 is likely: LiveKit's Krisp-based wheels ship `manylinux_2_28_aarch64`. It is not confirmed for the public `krisp_audio` wheel.
- **Self-hosting.** Processing is local, so caller audio stays on the user's servers. The open questions are whether the v1.6.1+ key triggers network license checks or usage metering, and whether an offline or air-gapped license exists. These need to be asked of Krisp sales.
- **Cost.** It is not free. Budget per-minute pricing: third-party reports say about $0.001–0.0015/min at volume. The cost comparison with open-source options (DTLN, RNNoise, DeepFilterNet-class models) is therefore real.

### Gaps
- No official Krisp price list for the VIVA server SDK was found; sdk-docs.krisp.ai and krisp.ai were blocked.
- Unknown whether an offline/on-prem license exists, and whether `globalInit` with a key contacts Krisp servers (activation, heartbeat, usage reporting).
- The supported platforms page ([sdk-docs: Platforms](https://sdk-docs.krisp.ai/docs/supported-platforms)) could not be read, so the list of Linux distros, glibc/manylinux level and ARM builds for the server Python SDK is unconfirmed.
- The Python version matrix for `krisp_audio` wheels is unknown beyond the cp312 example.

## 3. LiveKit's Krisp-based offerings: are they usable with self-hosted (OSS) LiveKit?

### Takeaway
There are two LiveKit packages:
- **`livekit-plugins-noise-cancellation`** (NC / BVC / BVCTelephony). It is **LiveKit Cloud-only.** The native plugin calls the LiveKit server's `/settings` endpoint with the room token, checks a project flag `enhancedNoiseCancellation`, and reports per-participant usage minutes. On an OSS server it logs "unavailable" and passes audio through unfiltered. BVC became a paid add-on on LiveKit Cloud from 2026-05-01.
- **`livekit-plugins-krisp`** (new April 2026, Apache-2.0, requires livekit-agents ≥ 1.8.3). It exposes Krisp **VIVA voice isolation** as a FrameProcessor. Its default backend authenticates through LiveKit Cloud. It also has an explicit **`krisp.auth.krisp_license(...)` mode for "Livekit OSS server"**, which uses your own Krisp `krisp_audio` wheel, license key and `.kef` model.

The second package is the only official LiveKit path to Krisp on a self-hosted stack, and it plugs directly into `AudioInputOptions(noise_cancellation=...)` in Agents 1.8.3.

### Cited Findings
**livekit-plugins-noise-cancellation (NC / BVC / BVCTelephony)**
- The README says "Requires LiveKit Cloud". License: "SEE LICENSE IN https://livekit.io/legal/terms-of-service". It runs server-side on inbound audio. The models are `NC()`, `BVC()` ("NC + removes non-primary voices that would confuse transcription or turn detection") and `BVCTelephony()`. The README also says: "Noise cancellation only needs to be applied once … disable noise cancellation / Krisp filter in your frontend clients". For crashes on AMD CPUs it suggests `OPENBLAS_CORETYPE=Haswell`. — [PyPI livekit-plugins-noise-cancellation](https://pypi.org/project/livekit-plugins-noise-cancellation/)
- Release history (PyPI JSON):
  - 0.1.0 on 2025-03-03 (macOS x86_64/arm64, manylinux_2_28 x86_64)
  - 0.2.0 on 2025-03-19 (adds manylinux aarch64)
  - 0.2.2 on 2025-05-01 (adds win_amd64)
  - 0.2.5 on 2025-06-30
  - 0.2.6 on 2026-06-26
  - 0.3.0 on 2026-07-17
  - 0.3.2 on 2026-09-15
  - Source: [PyPI JSON](https://pypi.org/pypi/livekit-plugins-noise-cancellation/json)
- **How the Cloud-only check works (wheel inspection):**
  - Present in 0.2.5 and 0.3.2: the native plugin deserializes `KrispGlobalOptions {url, token}` and `LivekitServerSettings {enhancedNoiseCancellation}`. It makes an HTTP request to `/settings` with a `Bearer` token. It sends `feature_usage` reports with the fields `KRISP_NOISE_CANCELLATION` / `KRISP_BACKGROUND_VOICE_CANCELLATION`, `room_name`, `room_id`, `participant_identity`, `participant_id`, `time_ranges` and `started_at`.
  - Added in 0.3.x: explicit log strings, including:
    - "noise cancellation is not enabled for this project"
    - "noise cancellation is not authorized for this connection"
    - "noise cancellation unavailable"
    - "noise cancellation availability check failed; will retry"
    - "noise cancellation stopped for this stream; audio continues unfiltered"
    - "usage report was rejected"
  - It also supports an `LK_NC_PLUGIN_PATH` override and sets `OPENBLAS_NUM_THREADS=1` by default.
  - Source: [PyPI 0.3.2](https://pypi.org/project/livekit-plugins-noise-cancellation/0.3.2/)
- LiveKit's own example tool `livekit-examples/noise-canceller` says: "**Requires LiveKit Cloud**: As noise cancellation is a feature of paid LiveKit Cloud accounts, this tool consumes real connection minutes while in use (even though it runs locally)." Its filter list includes NC, BVC, BVCTelephony, `viva-voice-isolation`, `viva-voice-isolation-telephony` (through `livekit-plugins-krisp`), ai-coustics QUAIL variants and WebRTC NS. It can also compute WER before and after processing. — [livekit-examples/noise-canceller](https://github.com/livekit-examples/noise-canceller)
- Issue livekit/livekit#4029 "How to implement BVC in a self-hosted LiveKit server" (2025-10-25) was closed as not planned with no staff answer. — [GitHub #4029](https://github.com/livekit/livekit/issues/4029)
- Issue livekit/agents#5507 (2026-04-21) proposes `livekit-plugins-rnnoise` for self-hosters. It quotes "Krisp BVC usage will incur an additional cost beginning May 1, 2026" and says upstream NC "requires LiveKit Cloud access". The only OSS option it lists is `aloware/livekit-plugins-dtln`. No staff response was visible. — [GitHub agents#5507](https://github.com/livekit/agents/issues/5507)
- LiveKit Cloud pricing (search snippet, not verified on the page): "voice isolation" includes 100 min on Build, 1,000 on Ship and 10,000 on Scale, then "$0.0012/min". — [livekit.com/pricing](https://livekit.com/pricing); [checkthat.ai summary](https://checkthat.ai/brands/livekit/pricing)
- A community thread titled "Noise Cancelling Features with Self-Hosted Agents" exists but was blocked. The search summary says BVC "requires LiveKit Cloud and is not viable for self-hosters", and that ai-coustics can be used on a self-hosted server "by providing your own key". — [community.livekit.io/t/1227](https://community.livekit.io/t/noise-cancelling-features-with-self-hosted-agents/1227)

**livekit-plugins-krisp (Krisp VIVA voice isolation)**
- Releases: 0.1.1 on 2026-04-16, then roughly weekly up to 0.4.3 on 2026-09-23. It is Apache-2.0 and requires `livekit-agents>=1.8.3`, `livekit-plugins-krisp-internal==0.2.0` and `livekit>=1.0.23`. — [PyPI livekit-plugins-krisp](https://pypi.org/pypi/livekit-plugins-krisp/json)
- README (PyPI, full read):
  - Default: "authenticates through LiveKit Cloud using the room's credentials — no separate SDK download, license key, or model file is required."
  - Alternative: "running the public Krisp SDK directly with your own Krisp license — **for example, when using Livekit OSS server**. This path uses the public `krisp_audio` wheel together with a Krisp license key and a `.kef` model file that you obtain from Krisp." The environment variables are `KRISP_VIVA_SDK_LICENSE_KEY` and `KRISP_VIVA_FILTER_MODEL_PATH`.
  - API: `voice_isolation()` and `voice_isolation_telephony()`, with `noise_suppression_level` 0–100 (default 75) and runtime `enabled` / `noise_suppression_level` setters.
  - Supported rates: "8000, 16000, 24000, 32000, 44100, 48000 Hz". Input frames of any size are buffered.
  - Source: [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)
- `livekit-plugins-krisp-internal` (proprietary, LiveKit ToS) ships cp310-abi3 wheels for macOS x86_64/arm64, manylinux_2_28 x86_64/aarch64 and win_amd64 (0.1.0 on 2026-07-06, 0.2.0 on 2026-07-22). The README says it "bundles the Krisp VIVA SDK". — [PyPI livekit-plugins-krisp-internal](https://pypi.org/pypi/livekit-plugins-krisp-internal/json)
- **Code facts (wheel inspection of 0.4.3):**
  - License mode is auto-selected when both environment variables are set.
  - In license mode the plugin calls `krisp_audio.globalInit("", license_key, …)` and creates an `NcInt16` session with `NcSessionConfig` (input rate = output rate, default 10 ms frames, `ModelInfo.path` = your `.kef`).
  - The `voice_isolation` vs `voice_isolation_telephony` mode is **ignored** in license mode: the `.kef` you pass determines the model.
  - The Cloud backend gets the room JWT via `_on_credentials_updated(token, url)`.
  - Source: [PyPI livekit-plugins-krisp 0.4.3](https://pypi.org/project/livekit-plugins-krisp/0.4.3/)

**LiveKit Agents 1.8.3 integration points (wheel inspection)**
- `room_io.AudioInputOptions` has these fields:
  - `sample_rate=24000`
  - `frame_size_ms=50`
  - `noise_cancellation: rtc.NoiseCancellationOptions | NoiseCancellationSelector | rtc.FrameProcessor[rtc.AudioFrame] | None`. A callable selector receives `NoiseCancellationParams(participant, track)`, so a model can be chosen per participant (e.g. telephony vs WebRTC).
  - `auto_gain_control`: "If not given, disabled when noise cancellation is configured directly."
  - Source: [PyPI livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)
- Issue agents#3894 (2025-11-11): RoomIO hard-coded 50 ms frames when BVC was enabled, which made Silero VAD process 800-sample windows and log "inference is slower than realtime". Fix PR #3899. In 1.8.3, `frame_size_ms` is a user-settable field. — [GitHub agents#3894](https://github.com/livekit/agents/issues/3894)
- Issue agents#4369 reports "failed to initialize the audio filter" with `noise_cancellation.BVC()` in Kubernetes (title and summary only). — [GitHub agents#4369](https://github.com/livekit/agents/issues/4369)

### Inferences
- With the user's self-hosted livekit-server, `noise_cancellation.BVC()` / `BVCTelephony()` will not produce an error the user can fix. The plugin will fail its `/settings` availability check and forward **unfiltered** audio. This is a silent no-op, so it could mislead A/B tests. I infer this from the binary's log strings and README, not from a run.
- For the user's stack, the only Krisp route that stays self-hosted and inside LiveKit Agents is `livekit-plugins-krisp` in `krisp_license` mode, using a Krisp VIVA SDK license and `.kef` models bought directly from Krisp. Because license mode runs any `.kef` through the generic `NcInt16` session, Krisp's BVC or VI-tel models should also load there, but I have not confirmed that. The plugin's minimum `livekit-agents>=1.8.3` exactly matches the user's version.
- Placement: the filter runs in RoomIO before VAD, STT and turn detection. In the user's pipeline it would sit before the NVIDIA riva STT, Sortformer diarization and the MultiSpeakerAdapter. Once background voices are removed, Sortformer should rarely see a second speaker. The RMS-based primary-speaker pick then becomes mostly a fallback.
- `frame_size_ms` (default 50) should be tuned with VAD latency in mind. The Krisp license backend re-buffers to 10 ms internally anyway.

### Gaps
- The full text of the LiveKit docs pages ("Noise & echo cancellation", "Enhanced noise cancellation") and the LiveKit blog could not be read. That leaves unconfirmed: what LiveKit says about VAD/turn-detector interplay with BVC, any explicit statement on self-hosting, the exact 2026 price per minute, and whether VIVA voice isolation is billed like BVC.
- I did not run the plugin against an OSS server, so the "passes audio unfiltered" behaviour is inferred from the binary strings.

## 4. Pipecat integration (KrispFilter, KrispVivaFilter, KrispVivaTurn, Interruption Prediction)

### Takeaway
Pipecat has the most complete open-source integration of Krisp VIVA:
- `KrispVivaFilter`, for voice isolation with an optional TTS-detection gate
- `KrispVivaTurn`, for streaming end-of-turn with turn v3
- `KrispVivaIPUserTurnStartStrategy`, for backchannel-aware barge-in
- `KrispVivaVadAnalyzer`

All of them need the same proprietary `krisp_audio` wheel, `.kef` models and API key from Krisp's developer portal. The BSD-2 wrappers are readable reference code that could be ported to a LiveKit Agents FrameProcessor or to the Agents turn-handling hooks.

### Cited Findings
- Pipecat lists four VIVA capabilities: Voice Isolation, Turn Detection, Interruption Prediction ("Distinguish genuine user interruptions from backchannels (e.g. 'uh-huh', 'yeah')") and VAD (8–48 kHz). They can be combined. Install with `uv add "pipecat-ai[krisp]"`, plus the Krisp wheel from the portal. — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx); [supported-services.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/supported-services.mdx)
- `KrispVivaFilter(model_path, frame_duration=10, noise_suppression_level=100.0, api_key, tts_model_path, tts_threshold=0.5, tts_detection_timeout=3.0)`. It supports `FilterEnableFrame` to toggle at runtime. With TTS detection, "the filter passes audio through unmodified until bot speech clears or the timeout expires. This prevents the noise cancellation filter from suppressing real human speech that immediately follows bot TTS playback." — [krisp-viva-filter.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/krisp-viva-filter.mdx); [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py)
- `KrispVivaIPUserTurnStartStrategy`: "When VAD detects user speech, this strategy feeds audio frames into the Krisp VIVA IP model … A user turn is triggered only when this probability exceeds the configured threshold." It is designed to sit alongside `TranscriptionUserTurnStartStrategy` as a fallback, and uses the environment variable `KRISP_VIVA_IP_MODEL_PATH`. — [krisp_viva_ip_user_turn_start_strategy.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py)
- `KrispVivaTurn`: "processes audio frame-by-frame in real time using Krisp's streaming model". This contrasts with Smart Turn, which runs in batches on VAD pauses. It is configured as `TurnAnalyzerUserTurnStopStrategy(turn_analyzer=KrispVivaTurn())`. — [krisp-viva-turn.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/utilities/turn-detection/krisp-viva-turn.mdx)
- Reference example: `examples/voice/voice-krisp-viva.py` combines the filter, Turn and IP with Silero VAD ("or KrispVivaVadAnalyzer"). — [voice-krisp-viva.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/voice/voice-krisp-viva.py)
- Pipecat Cloud offers a managed toggle: `[krisp_viva] audio_filter = "tel"` (up to 16 kHz) or `"pro"` (up to 32 kHz), in the `dailyco/pipecat-base` image ≥ 0.1.8. — [pipecat-cloud/guides/krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)
- Pipecat's CLI templates only enable `KrispVivaFilter` when `ENV != "local"`, which reflects the Pipecat Cloud distribution constraint. — [pipecat code search: bot_cascade.py.jinja2](https://github.com/pipecat-ai/pipecat/tree/main/src/pipecat/cli/templates/server)
- Environment-variable naming differs between integrations: Pipecat uses `KRISP_VIVA_API_KEY`, while `livekit-plugins-krisp` uses `KRISP_VIVA_SDK_LICENSE_KEY`. — [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py); [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)

### Inferences
- LiveKit's `livekit-plugins-krisp` wraps only voice isolation. With a direct Krisp license, the user could port the IP model (the backchannel filter) and turn v3 from Pipecat's BSD-2 code into LiveKit Agents. That would mean a custom turn detector or interruption hook, since LiveKit Agents has its own turn detector and interruption logic. This is the most relevant Krisp capability for keeping "yeah" and "mm-hmm" from triggering barge-in, and it works on the **isolated** audio.
- One process-wide `globalInit` with a single key is shared by all Krisp components. Filter, turn and IP could therefore run in one agent worker process without extra init cost.

### Gaps
- There is no public head-to-head of KrispVivaTurn against LiveKit's turn-detector model or Pipecat Smart Turn, apart from Krisp's own claim.
- The IP model's latency (how much audio it needs before deciding) is not documented in the sources read.

## 5. Quality evidence and known failure modes

### Takeaway
Nearly all the quantitative evidence is Krisp's own:
- BVC: about 3.5× fewer VAD false positives and more than 2× lower Whisper-v3 WER on AMI.
- VI 2.5: 43–46% average WER reduction across 10–11 STT engines (including NVIDIA), 69.7% on background-speech audio, and "no harm on clean audio".

I found no independent benchmark or substantive community reports, positive or negative, in the reachable sources. The failure modes that are documented or implied are:
- proximity-based primary selection, which fails for speakerphone callers and loud close-by talkers
- mis-locking onto bot TTS or echo, which Krisp addresses with a TTS-detection gate
- the headset requirement for outbound BVC
- a silent no-op on OSS LiveKit

### Cited Findings
- **BVC for voice agents (Krisp blog, search snippet).** "With Krisp BVC, false-positive triggers in VAD … were reduced by 3.5x on average". BVC "reduces the Word Error Rate (WER) of Whisper V3 models on the AMI dataset — achieving more than a 2x improvement". "The precision after Krisp BVC increases by over a quarter." — [Krisp blog: Improving turn-taking with BVC](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/)
- **VI 2.5 (Krisp blog, search snippets). The snippets conflict:**
  - One says: "cuts average word error rate 43% (17.9% → 10.2%) across 11 speech-to-text engines".
  - Another says: "46.4% average reduction in WER versus unprocessed audio (15.35% → 8.22%)", "across 10 STT engines from 7 vendors: 46.4% fewer word errors, 69.7% fewer on background speech (the hardest case), with no harm on clean audio".
  - Test set: "1,685 real-world recordings (about 7 hours of audio)"; vendors "Deepgram, NVIDIA, Soniox, ElevenLabs, AssemblyAI, Google, and Cartesia".
  - Source: [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- **Turn Prediction v3 claims:** see §1 (47%→69% of responses under 200 ms; Krisp says it beats LiveKit's built-in model and Deepgram Flux on its own benchmark). — [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)
- **Failure mode (documented by Pipecat):** the risk that NC/VI will be "suppressing real human speech that immediately follows bot TTS playback", mitigated by the TTS-detection model. — [krisp-viva-filter.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/krisp-viva-filter.mdx)
- **Failure mode (documented by Krisp):** BVC outbound models assume a headset or compatible device, "regular NC models should be used if requirements are unmet", and inbound and outbound models must not be swapped. — [sdk-docs Model Selection Guide](https://sdk-docs.krisp.ai/docs/rtc-model-guide-bvc-nc)
- **Operational issues in LiveKit's packaging:**
  - Crashes on AMD CPUs from OpenBLAS CPU detection (workaround `OPENBLAS_CORETYPE=Haswell`) — [PyPI README](https://pypi.org/project/livekit-plugins-noise-cancellation/)
  - 50 ms frame forcing causing VAD slowdowns (2025-11) — [agents#3894](https://github.com/livekit/agents/issues/3894)
  - Filter init failures in Kubernetes — [agents#4369](https://github.com/livekit/agents/issues/4369)
- LiveKit's `noise-canceller` tool can compute WER before and after NC/BVC/VIVA/ai-coustics for a local A/B test, but it consumes LiveKit Cloud minutes. — [livekit-examples/noise-canceller](https://github.com/livekit-examples/noise-canceller)
- A search for Reddit/GitHub reports of BVC cutting off user speech on speakerphone or far-field audio returned nothing relevant. — [WebSearch, no relevant results]

### Inferences
- The VI 2.5 evaluation includes NVIDIA STT. That makes it the closest published evidence for the user's Nemotron/riva ASR, but it is vendor-run and the exact NVIDIA model is unknown.
- Backchannels. Nothing suggests VI or BVC deliberately removes short primary-speaker utterances. However:
  - Quiet, brief "mm-hmm" sounds are the type of low-energy, low-SNR speech that neural suppressors attenuate most, especially at suppression level 100 (Pipecat's default) as opposed to 75 (LiveKit's default).
  - A caller who is farther from the mic than a TV is at risk under BVC's proximity heuristic.
  - These need local A/B testing with the user's own recordings, measuring detection recall on backchannels before and after the filter.
- Keep the in-app WebRTC NS/AGC and Krisp from double-processing the stream. LiveKit's README warns to apply NC only once. Agents 1.8.3 disables AGC when NC is configured directly.

### Gaps
- No independent (non-Krisp) benchmark: no DNSMOS, no background-speaker suppression rate, and no WER impact on NVIDIA Nemotron/Parakeet specifically.
- No data on the rate at which Krisp removes backchannels, or on false suppression of the primary speaker for far-field or speakerphone callers.
- Reddit, HN and community.livekit.io discussions could not be reached or returned nothing relevant.

## 6. Maturity signals: platforms embedding Krisp for voice agents

### Takeaway
Krisp is a very widely deployed commercial engine, embedded by Twilio, Vapi, Pipecat Cloud and LiveKit Cloud. That shows maturity and makes it the de facto reference for "background voice cancellation" in voice agents. Every hosted integration, though, is either a cloud feature or requires a direct Krisp commercial license.

### Cited Findings
- **Twilio:** Krisp and Twilio partnered to remove "unwanted background noise and voices from calls using the Krisp plug-in for Twilio Programmable Voice" (search snippet). — [Krisp blog: Twilio](https://krisp.ai/blog/krisp-delivers-leading-ai-noise-cancellation-to-twilio-voice-customers/)
- **Vapi:** "Smart Denoising uses Krisp's AI-powered technology to remove background noise in real-time", complemented by Vapi's own adaptive background-speech filter (search snippet). — [Vapi docs: background speech denoising](https://docs.vapi.ai/documentation/assistants/conversation-behavior/background-speech-denoising); [Vapi blog](https://vapi.ai/blog/how-we-built-adaptive-background-speech-filtering-at-vapi)
- **Pipecat Cloud** (managed VIVA, $0.0015/min after 10k free minutes) and **LiveKit Cloud** (NC/BVC; BVC paid from 2026-05-01; VIVA VI via `livekit-plugins-krisp`). — [Pipecat Cloud guide](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx); [agents#5507](https://github.com/livekit/agents/issues/5507)
- **Scale claims:** "real-time speech-enhancement models run on over 200 million devices, licensed by Discord, Twilio, and VMware among others" (third-party profile). — [api-evangelist/krisp](https://github.com/api-evangelist/krisp)
- **Retell** markets "Advanced Denoising". I found no source confirming it is Krisp-based. — [builtwithagents.ai](https://www.builtwithagents.ai/blog/best-ai-voice-agents-background-noise-cancellation)

### Inferences
- The hosted integrations are mature, which lowers technical risk. The blocker for this project is commercial and privacy-related (license terms, metering or phone-home), not technical.

### Gaps
- Retell's denoising vendor could not be confirmed.
- No public list of self-hosted or on-prem Krisp VIVA server customers was found.

## 7. Integration paths and fit for this stack (LiveKit Agents 1.8.3 self-hosted, NVIDIA riva ASR + Sortformer, Mac dev and Linux prod)

### Takeaway
The only realistic Krisp path is **`livekit-plugins-krisp` in `krisp_license` mode**, backed by a direct Krisp VIVA SDK license (the `krisp_audio` wheel plus a VI-tel, VI-pro or BVC `.kef`). It drops into `AudioInputOptions(noise_cancellation=...)` unchanged. Two other options do not work for a self-hosted stack: `livekit-plugins-noise-cancellation` (BVC) is unusable on OSS LiveKit, and LiveKit's default Krisp backend needs LiveKit Cloud. Krisp's IP (backchannel) and turn-v3 models would need a custom port from Pipecat's BSD-2 wrappers. Before committing, Krisp has to confirm three things: licensing cost, whether the key phones home, and Linux aarch64 availability.

### Cited Findings
- License mode exists "for example, when using Livekit OSS server" and needs `pip install krisp-audio` (Krisp's wheel), `KRISP_VIVA_SDK_LICENSE_KEY` and `KRISP_VIVA_FILTER_MODEL_PATH`. — [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)
- `livekit-plugins-krisp` requires `livekit-agents>=1.8.3`. — [PyPI JSON](https://pypi.org/pypi/livekit-plugins-krisp/json)
- In Agents 1.8.3, `AudioInputOptions.noise_cancellation` accepts a `FrameProcessor` or a per-participant selector, and `frame_size_ms` defaults to 50. — [PyPI livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)
- Open-source self-hosted alternatives named by the LiveKit community (covered by other researchers):
  - `aloware/livekit-plugins-dtln` — [GitHub](https://github.com/aloware/livekit-plugins-dtln)
  - `livekit-plugins-denoise` (MIT) — [PyPI](https://pypi.org/project/livekit-plugins-denoise/)
  - a proposed RNNoise plugin — [agents#5507](https://github.com/livekit/agents/issues/5507)
  - ai-coustics with your own key (search snippet) — [community.livekit.io/t/1227](https://community.livekit.io/t/noise-cancelling-features-with-self-hosted-agents/1227)

### Inferences
**Suggested evaluation plan**
1. Obtain a Krisp trial license. Test `krisp-viva-tel` (16 kHz, for PSTN/SIP callers), `krisp-viva-pro` (32 kHz, for WebRTC callers) and, if offered, inbound BVC-telephony. Route per participant with the `NoiseCancellationSelector`.
2. Measure WER with riva/Nemotron, VAD/barge-in false-trigger rate, and backchannel detection recall on the user's own TV and crosstalk recordings. Test suppression levels 75 and 100.
3. Watch for primary-speaker errors when the caller is far-field.
4. If the IP model is licensed, port `KrispVivaIPUserTurnStartStrategy` logic into LiveKit's interruption handling to separate backchannels from barge-ins.

**Privacy.** Audio processing is local. Whether the license check or metering is network-based must be confirmed in the Krisp contract, including any offline or air-gapped license option.

**Hardware.** Everything is CPU-only, so the GPU budget stays with ASR. Per-stream CPU cost must be measured.

### Gaps
- No hands-on test was possible: the `krisp_audio` wheel and `.kef` models are behind Krisp's portal.
- No confirmation of Linux aarch64 or specific Python versions for `krisp_audio`, of pricing, or of offline licensing.
