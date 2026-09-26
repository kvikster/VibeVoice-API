# Voice isolation / noise cancellation: integration layer (LiveKit Agents 1.8.3, Pipecat) and cross-vendor evidence, as of Sept 2026

Scope note: this covers the integration layer and cross-vendor evidence. Other notes cover each vendor's product details.

Source caveats:
- `/home/user/VibeVoice-API/voice_agent/.venv` and `/home/user/VibeVoice-API/voice_agent/livekit_harness/.livekit-agents` do **not exist** in this research container.
- Code facts were therefore verified against an equivalent scratch venv installed from PyPI: livekit-agents 1.8.3, livekit (rtc) 1.1.18, livekit-plugins-ai-coustics 0.3.2, aic_sdk 3.2.0, livekit-plugins-silero 1.8.3, livekit-local-inference 0.2.7. It lives at `/tmp/claude-0/-home-user-VibeVoice-API/e889273f-ddd7-5345-b39f-0e17440a49dd/scratchpad/lkvenv/lib/python3.11/site-packages/`, shortened below to `SP/`.
- The installed wheels are the sources for the code facts. Line numbers are for these versions.
- Extra wheels were inspected (not installed into the repo):
  - `livekit-plugins-noise-cancellation` 0.3.2 (`…/scratchpad/nc/x/`)
  - `pipecat-ai` 1.12.0 (released 2026-09-25; `…/scratchpad/integ/pc/`)
  - `torchmetrics` 1.9.0
- Blocked by the egress proxy, so not fetched directly: arxiv.org, docs.livekit.io, livekit.com, community.livekit.io, docs.pipecat.ai, developers.deepgram.com, assemblyai.com, krisp.ai, ai-coustics.com, semanticscholar.
- For those sites, claims below come from search-engine snippets (marked "snippet"), GitHub (raw.githubusercontent.com works), or PyPI.

---

## 1. LiveKit Agents 1.8.3 integration mechanics

### Takeaway
`RoomOptions(audio_input=AudioInputOptions(noise_cancellation=...))` accepts three kinds of value:
- an `rtc.NoiseCancellationOptions`: a native Rust audio-filter module such as Krisp NC/BVC. It is authenticated against LiveKit Cloud and fails on self-hosted servers.
- an `rtc.FrameProcessor[rtc.AudioFrame]`: a Python object. This is what ai-coustics is, and what any custom DeepFilterNet/RNNoise/DTLN/TSE model would be.
- a per-track selector callable.

The processor runs inside `rtc.AudioStream` on the linked participant's microphone track, **before** everything else. Every downstream consumer gets the same processed frame: STT, VAD, AMD, the adaptive-interruption detector and the audio EOT turn detector. There is no built-in "raw to STT, enhanced to VAD" split. The `console` mode does not use RoomIO at all. It uses the WebRTC APM (AEC+NS+HPF+AGC) instead, which is why the enhancer is not applied there.

### Cited Findings

**Types and options**

- `AudioInputOptions.noise_cancellation: rtc.NoiseCancellationOptions | NoiseCancellationSelector | rtc.FrameProcessor[rtc.AudioFrame] | None`. Other defaults: `sample_rate=24000`, `num_channels=1`, `frame_size_ms=50`, `auto_gain_control: NotGivenOr[bool]`. The docstring says AGC is "disabled when noise cancellation is configured directly. Set explicitly when using a noise cancellation selector." — `SP/livekit/agents/voice/room_io/types.py` L57-75. (The deprecated `RoomInputOptions` keeps `noise_cancellation: NoiseCancellationOptions | FrameProcessor` at L253.)
- `NoiseCancellationSelector = Callable[[NoiseCancellationParams], NoiseCancellationOptions | FrameProcessor | None]`, where `NoiseCancellationParams(participant, track)` — `SP/livekit/agents/voice/room_io/types.py` L34-43.
  - The selector is called per new track in `_ParticipantAudioInputStream._create_stream()`.
  - This makes per-participant model choice possible, e.g. a telephony model for SIP participants — `SP/livekit/agents/voice/room_io/_input.py` L373-390.
- `rtc.NoiseCancellationOptions` is just `@dataclass(module_id: str, options: dict)`. It is passed to the Rust FFI as `audio_filter_module_id` / `audio_filter_options` (JSON), and the native module runs inside the FFI — `SP/livekit/rtc/audio_stream.py` L46-50, L117-127, L264-289.
- `rtc.FrameProcessor[T]` is a small ABC:
  - abstract: `enabled` (property + setter), `_process(frame) -> frame`, `_close()`
  - optional hooks: `_on_stream_info_updated(room_name, participant_identity, publication_sid)`, `_on_stream_info_cleared()`, `_on_credentials_updated(token, url)`, `_on_credentials_cleared()`
  - Source: `SP/livekit/rtc/frame_processor.py` (whole file, ~35 lines).

**Where the processor runs**

- In `AudioStream._run()`, each received frame goes through `if self._processor is not None and self._processor.enabled: frame = self._processor._process(frame)`. It runs **synchronously on the asyncio loop**. On exception it logs "Frame processing failed, passing through original frame" and forwards the original frame — `SP/livekit/rtc/audio_stream.py` L293-313.
- The room token/URL and stream info are pushed into the processor when the stream registers with a track and on token refresh (`_push_processor_metadata_to_stream`, `_on_room_token_refreshed`) — `SP/livekit/rtc/track.py` L60-110. Cloud-billed processors (ai-coustics in LiveKitCloud mode) authenticate this way.
- RoomIO creates the stream with `rtc.AudioStream.from_track(track, sample_rate, num_channels, frame_size_ms, noise_cancellation=..., auto_close_noise_cancellation=False)` — `SP/livekit/agents/voice/room_io/_input.py` L373-390.
  - The processor sees frames already resampled by the FFI to the `AudioInputOptions.sample_rate` (default 24 kHz), in 50 ms chunks (default).
- After the processor, `_ParticipantAudioInputStream._process_frame` applies the APM AGC when enabled, i.e. AGC runs **after** NC — `_input.py` L366-371, L186.
- AGC default: `auto_gain_control = NC is None or callable(NC)`. Consequences:
  - direct NC → AGC off
  - selector → AGC on
  - Source: `SP/livekit/agents/voice/room_io/room_io.py` L127-141.
- Ownership: a directly passed FrameProcessor instance is not closed when a track ends, so it is reused across tracks and keeps its internal state. A selector-returned processor is owned and closed when replaced (`_update_processor`) — `_input.py` L228-236, L337-352.
- Per participant: `_ParticipantAudioInputStream` only accepts `TrackSource.SOURCE_MICROPHONE` of the **linked** participant (`set_participant`; `RoomOptions.participant_identity` or first participant). NC is therefore applied to that one track, not to the whole room — `_input.py` L25-75, L113-120, L337-347.
- For custom multi-participant pipelines, `rtc.AudioStream(...)`, `.from_track(...)` and `.from_participant(...)` all accept `noise_cancellation=` — `SP/livekit/rtc/audio_stream.py` L60-90, L150-230.

**Fan-out to downstream consumers**

- `AudioRecognition._push_audio(frame, stt_frame=None)` is documented as "Forward an audio frame to STT, VAD, AMD and the interruption detector". The same frame goes to:
  - `_stt_pipeline.audio_ch`
  - `_vad_ch`
  - `session.amd`
  - `_interruption_ch`
  - `_turn_detector_stream.push_audio`
  - Source: `SP/livekit/agents/voice/audio_recognition.py` L747-775.
- The only path divergence: during AEC warm-up or uninterruptible speech, STT (and a realtime model) get a *silence* frame, while "VAD, AMD and the interruption detector keep receiving the real frame" — `SP/livekit/agents/voice/agent_activity.py` L1651-1683.
- Consequence: in LiveKit there is no hook that sends raw audio to STT and enhanced audio to VAD. A split has to be built by hand, e.g.:
  - do enhancement inside a VAD wrapper and leave `noise_cancellation=None`; or
  - wrap the STT so it taps pre-NC audio from a second `AudioStream`.
  (This is an inference from the code.)

**Adaptive interruption and turn detection**

- The adaptive interruption detector (`inference.AdaptiveInterruptionDetector`) is a **remote** model. It uses `LIVEKIT_INFERENCE_URL` plus `LIVEKIT_INFERENCE_API_KEY/SECRET` (falling back to `LIVEKIT_API_KEY/SECRET`) — `SP/livekit/agents/inference/interruption.py` L265-330.
  - A June 2026 issue says self-hosted deployments "eventually fall back to VAD-based interruption handling" and asks for a self-hostable model or a Krisp VIVA interruption-prediction integration — [livekit/agents#6033](https://github.com/livekit/agents/issues/6033).
- 1.8.3 ships an **audio** end-of-turn detector, `inference.TurnDetector` ("Audio end-of-turn detector with cloud → local fallback"):
  - `turn-detector-v1` runs over a cloud WebSocket.
  - `turn-detector-v1-mini` runs in-process via `livekit-local-inference` (`EOT.predict()` on ≤1.2 s of 16 kHz int16 PCM, model ~108 MB).
  - Its stream receives the post-NC frames through `_turn_detector_stream.push_audio`.
  - Source: `SP/livekit/agents/inference/eot/detector.py` L1-45, `transports.py` L1, L384-385; `SP/livekit/local_inference/_native.pyi` L1-60.

**Console mode**

- `python agent.py console` in 1.8.3 goes through the legacy rich CLI (`cli.run_app` → `_legacy.run_app`, "being phased out in favor of … `lk agent …`") — `SP/livekit/agents/cli/cli.py` L471-480.
- That CLI builds its own `ConsoleAudioInput` and processes mic audio with `rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True, high_pass_filter=True, auto_gain_control=True)`. It assigns `sess.input.audio = audio_input` directly, with no RoomIO and no `noise_cancellation` hook — `SP/livekit/agents/cli/_legacy.py` L123, L350-355, L552-560, L749-782.
- This explains why the user's ai-coustics enhancer applies in room mode but not in `console`. Console also adds WebRTC NS/AGC that room mode does not have, so console and room results are not directly comparable. (The last point is an inference.)

**ai-coustics plugin (livekit-plugins-ai-coustics 0.3.2) — works self-hosted**

- `AICousticsAudioEnhancer(rtc.FrameProcessor[rtc.AudioFrame])` in `SP/livekit/plugins/ai_coustics/plugin.py`:
  - Auth defaults to `Auth.livekit_cloud()`.
  - With `Auth.ai_coustics_api(license_key=...)` ("Use your own ai-coustics credentials directly, bypassing LiveKit Cloud"), `_auth_mode_requires_credentials()` and `_auth_mode_requires_stream_info()` return False. It therefore processes without any room token, so it works with a self-hosted LiveKit server (`SP/livekit/plugins/ai_coustics/auth.py`).
  - The enhancer is lazily (re)created when sample rate, channels or **samples_per_channel** change.
  - It converts int16 to float32 and calls `process_with_vad()`. The VAD flag is stored in `frame.userdata["lk.aic-vad"]`.
  - On a native init error it disables itself for the rest of the stream and returns the original frames.
- `ai_coustics.VAD` performs no inference of its own. It "relies on the accompanying … audio_enhancement FrameProcessor" and reads `frame.userdata['lk.aic-vad']` (`update_interval=0.032`) — `SP/livekit/plugins/ai_coustics/vad.py` L16-80.
  - Inference: it only works when the enhancer runs in the same stream, i.e. room mode, not console.

**Krisp NC/BVC plugin (livekit-plugins-noise-cancellation 0.3.2) — requires LiveKit Cloud**

- PyPI METADATA says "Requires [LiveKit Cloud](https://cloud.livekit.io)".
- `NC()`, `BVC()` and `BVCTelephony()` return `rtc.NoiseCancellationOptions(module_id, {"modelPath": ...})`. They point at bundled Krisp `.kef` models (`c8.f.s.026300-1.0.0_3.1.kef` 6.6 MB; `hs.c6.f.m.75df8f.kef` 29 MB; `inb.bvc.hs.c6.w.s.23cdb3.kef` 28 MB) and a 41 MB `liblivekit_nc_plugin.so` that is registered through `rtc.AudioFilter(...)` — `…/scratchpad/nc/x/livekit/plugins/noise_cancellation/{__init__,plugin}.py`, `…dist-info/METADATA`.
- `strings` on the `.so` show a token-based entitlement check plus usage reporting:
  - `"initialization options are missing a token"`
  - `"noise cancellation is not enabled for this project"`
  - `"noise cancellation is not authorized for this connection"`
  - `audio_filter_update_token`
  - `feature_usage … KRISP_NOISE_CANCELLATION / KRISP_BACKGROUND_VOICE_CANCELLATION`
  - Source: binary inspection of `…/resources/liblivekit_nc_plugin.so` (0.3.2).
- On a self-hosted server the FFI logs `"audio filter cannot be enabled: LiveKit Cloud is required"`. A user asking to plug in their own model was told nothing public and the issue was closed — [livekit/agents#3073](https://github.com/livekit/agents/issues/3073) (Aug 2025).
- Even on Cloud, a silent `"failed to initialize the audio filter. it will not be enabled for this session"` has been reported (K8s) — [livekit/agents#4369](https://github.com/livekit/agents/issues/4369).
- An April 2026 issue quotes the LiveKit docs: "Krisp BVC usage will incur an additional cost beginning May 1, 2026" — [livekit/agents#5507](https://github.com/livekit/agents/issues/5507).
- The same issue says the only open-source self-hosted NC option for LiveKit then was third-party [aloware/livekit-plugins-dtln](https://github.com/aloware/livekit-plugins-dtln), and proposes a `livekit-plugins-rnnoise` FrameProcessor (48 kHz/10 ms). Status: proposal, open.
- `livekit-examples/noise-canceller` is a "Utility for applying LiveKit Cloud enhanced noise cancellation to individual audio files". It needs a Cloud project, but could process the A/B/C corpus offline — [GitHub](https://github.com/livekit-examples/noise-canceller).

**Custom and third-party FrameProcessors**

- DTLN plugin example of a custom FrameProcessor:
  - `noise_cancellation=dtln.noise_suppression()` in `RoomOptions`, or `rtc.AudioStream.from_track(..., noise_cancellation=...)`
  - ONNX in-process, ~8 ms block shift, ~4 MB weights
  - `strength` wet/dry blend (default 0.5)
  - Its notes: "Create one instance per session" (stateful LSTM); "Do not chain it with another noise cancellation model"; `mask_mean < 0.3` indicates over-suppression.
  - Source: [aloware/livekit-plugins-dtln README](https://github.com/aloware/livekit-plugins-dtln) (raw README fetched).
  - Its table claims Krisp/ai-coustics are "Cloud API required / audio sent to third party". This is **contradicted** for ai-coustics by the plugin code above (local native inference with its own license key) and is only partly true for Krisp (local inference, Cloud-gated auth).
- Frame size history: [livekit/agents#3894](https://github.com/livekit/agents/issues/3894) reported that RoomIO hard-coded 50 ms frames with BVC, "causing Silero VAD latency spikes". In 1.8.3 `frame_size_ms` is exposed in `AudioInputOptions` (default still 50) — `types.py` L60-61.

### Inferences

**How to write a custom FrameProcessor** (DeepFilterNet, RNNoise, DTLN, a TSE model):
- Subclass `rtc.FrameProcessor[rtc.AudioFrame]`.
- Implement `enabled` (property + setter), `_process` and `_close`.
- Buffer internally to the model's hop, e.g. 10 ms/480 samples for RNNoise at 48 kHz, or 10 ms hop at 48 kHz for DeepFilterNet3. Return a frame of the **same length** as the input, so there is no buffering jitter; this means carrying a fixed algorithmic delay.
- Set `AudioInputOptions.sample_rate` to the model's native rate (e.g. 48000 for RNNoise/DFN, 16000 for DTLN, 16000 to match Nemotron). This avoids a second resampling hop.
- Keep `_process` cheap, because it runs on the event loop. A PyTorch DFN3 per 50 ms frame on CPU may be acceptable, but GPU/TSE models should run in a thread or process with a bounded queue.
- Remember that the processor fails open: exceptions pass the raw frame through.
- For TSE (target-speaker extraction), the processor needs an enrollment embedding. The selector gets `participant` and can fetch one per caller.

**Console mode**: `AiCousticsApi` auth needs no room context, so the enhancer could in principle be applied in console mode.
- Wrap `ConsoleAudioInput` in a custom `io.AudioInput` that calls `enhancer._process(frame)`.
- Or disable the legacy APM NS for parity.
- Not tested.

**Raw ASR plus enhanced VAD/turn** (inference): the lowest-friction pattern in 1.8.3 is to leave `noise_cancellation=None` and put the enhancer inside a custom VAD (or `ai_coustics` VAD driven by a private enhancer instance), plus inside the interruption/turn path. STT then receives raw audio. This duplicates nothing if the enhancer is only instantiated for the VAD path.

### Gaps
- The livekit/agents GitHub clone path given in the brief was absent, so `main` could not be diffed against 1.8.3.
- LiveKit docs pages (docs.livekit.io) could not be fetched. Official wording on per-participant selectors and on "don't apply NC twice (frontend and backend)" is known only from search snippets: "apply noise cancellation within your agent, and avoid using two enhanced models on the same audio pathway" (snippet of [LiveKit NC docs](https://docs.livekit.io/transport/media/noise-cancellation/)).
- The exact BVC price and whether Cloud-gating also applies to agents connecting to self-hosted servers but authenticated with a Cloud project key were not verified. The binary evidence suggests the entitlement is tied to the room's token/URL, so this would be unlikely to work.

---

## 2. Pipecat audio filters as a reference catalog (pipecat-ai 1.12.0, 2026-09-25)

### Takeaway
Pipecat 1.12.0 ships four built-in `BaseAudioFilter`s: `AICFilter`, `KoalaFilter`, `KrispVivaFilter` and `RNNoiseFilter`. `NoisereduceFilter` and the old `KrispFilter` were removed in 1.0.0 (2026-04-14). Community filters listed in the Pipecat docs are `ArctanAudioFilter` and `HecttorFilter`/`HecttorAudioProcessor`. Like LiveKit, the transport filter runs **before VAD and before STT**, so all consumers see filtered audio. Two Pipecat-side documents explicitly discuss the VAD/STT mismatch; there is no general "how to choose" guide.

### Cited Findings

**Placement**
- `BaseAudioFilter` docstring: "If an audio filter is provided to the input transport it will be used to process audio before VAD and before pushing it downstream" — `pipecat/audio/filters/base_audio_filter.py` (pipecat-ai 1.12.0 wheel).
- `_audio_task_handler` applies `frame.audio = await audio_in_filter.filter(frame.audio)` and then pushes downstream. Frames that are empty because the filter is still buffering are skipped — `pipecat/transports/base_input.py` L269-300.

**Built-in filters** (constructors from the 1.12.0 wheel)
- `AICFilter(license_key, model_id|model_path, model_download_dir, enhancement_level)`, extra `aic` → `aic-sdk~=3.1.0`. Model IDs in the docs: `quail-vf-2.0-l-16khz`, `quail-vf-l-16khz`, `quail-s-16khz`, `quail-l-8khz` — `aic_filter.py`; [docs source](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/aic-filter.mdx).
- `KoalaFilter(access_key)` (Picovoice), extra `koala` → `pvkoala~=2.0.3` — `koala_filter.py`.
- `KrispVivaFilter(model_path(.kef), frame_duration=10, noise_suppression_level=100.0, api_key, tts_model_path, tts_threshold, tts_detection_timeout)`. Optional TTS detection "delay[s] voice isolation until bot speech playback has stopped, preventing later real human speech suppression artifacts" — `krisp_viva_filter.py`.
- `RNNoiseFilter(resampler_quality="QQ")`, extra `rnnoise` → `pyrnnoise~=0.4.3`. It runs at 48 kHz in 480-sample chunks; docs say it "requires no API keys or external services" — `rnnoise_filter.py`; [docs](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/rnnoise-filter.mdx).

**Changelog history** ([pipecat CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md))
- `RNNoiseFilter` added in 0.0.99 (2026-01-13).
- 0.0.97 (2025-12-05): "Updated `AICFilter` to use Quail STT as the default model … optimized for human-to-machine interaction".
- 1.0.0 (2026-04-14): "⚠️ Removed `NoisereduceFilter`. Use system-level noise reduction or a service-based alternative" and "⚠️ Removed `KrispFilter`. The `krisp` extra has been removed".
- 1.4.0 (2026-06-16): added `AICQuailVADAnalyzer`, which "works independently of `AICFilter`, so it can sit before or after enhancement".
- 1.8.0 (2026-08-26): removed `AICVADAnalyzer`/`AICFilter.create_vad_analyzer()`, because "`aic-sdk` 3.0 removed the energy-based VAD".

**Related VAD, turn and interruption components** (1.12.0)
- `pipecat/audio/vad/aic_quail_vad.py`, `krisp_viva_vad.py` (8–48 kHz), `silero.py`
- `pipecat/audio/turn/krisp_viva_turn.py`. Krisp turn v3 "accepts an external VAD flag alongside audio frames".
- The Krisp VIVA feature page lists four capabilities: voice isolation, turn detection, **interruption prediction** ("Distinguish genuine user interruptions from backchannels") and VAD — [pipecat docs source krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx).

**Choosing guidance (vendor docs)**
- The AIC docs say "The recommended approach is to use `AICFilter` for enhancement and `AICQuailVADAnalyzer` for voice activity detection" — [aic-filter.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/aic-filter.mdx).
- The `AICQuailVADAnalyzer` docstring caveat is the key integration point: "When `AICFilter` is installed as the transport's `audio_in_filter`, that audio has already been enhanced, while the AIC SDK expects a VAD to run on the original signal. Detection still works, but the model is judging audio it was not trained on and the filter's own delay is added to the VAD's prediction delay. Pipecat offers no hook for tapping pre-enhancement audio further down the pipeline" — `pipecat/audio/vad/aic_quail_vad.py` (1.12.0).

**Community filters** (listed in Pipecat docs as "CommunityMaintained")
- `ArctanAudioFilter` (`arctan-vi[pipecat]`): "tuned for ASR/STT accuracy"; license key; "agent process must be able to reach Arctan's servers to validate the license key" — [arctan.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/arctan.mdx).
- `HecttorFilter` (`pipecat-hecttor`; SDK wheel "not published to PyPI"; network key validation; `enhancer_weight` wet/dry blend) and `HecttorAudioProcessor`. The latter produces **two blends from one input**, `asr_weight` for STT and `vad_tt_weight` for VAD/turn-taking. The pipeline order is transport.input → hecttor → stt → `hecttor.vad_tt_stage()` → user_aggregator (VAD + turn) — [hecttor.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/hecttor.mdx).
- Vendor claim from the Hecttor docs: "STT usually wants fully enhanced audio, while VAD and turn-taking models can perform better with some of the original signal blended back in". This is the **opposite** of the Deepgram and AssemblyAI guidance in §4.

### Inferences
- Hecttor's two-stage design is a reusable pattern for LiveKit: run one enhancer and emit two outputs (full-wet for one consumer, a blend for the other).
- A LiveKit port needs a custom STT wrapper or VAD wrapper, because `_push_audio` sends one frame to all consumers.
- DeepFilterNet has no Pipecat built-in (checked the 1.12.0 filter directory). NVIDIA Maxine is not in the Pipecat filter list either.

### Gaps
- docs.pipecat.ai was blocked. The docs GitHub repo was used; no Pipecat-authored comparison or selection matrix across filters was found.
- Latency and CPU numbers per filter are not published in the Pipecat docs.

---

## 3. Independent comparisons and practitioner reports

### Takeaway
Truly independent, quantitative cross-vendor comparisons for **voice agents** (background-voice suppression, false barge-ins, WER with modern ASR) are essentially absent in public sources as of Sept 2026. Most numbers are vendor-authored:
- Krisp: VAD false-trigger reductions.
- ai-coustics: large WER reductions under competing speakers.
- Picovoice: STOI.

The credible independent evidence is academic and ASR-vendor guidance, and it cautions against feeding enhanced audio to ASR. Practitioner reports (GitHub, LiveKit community) mention:
- plain NC letting background speech through
- BVCTelephony over-suppressing quiet callers
- frame-size latency effects on VAD

### Cited Findings

**Vendor-authored (Krisp)**
- BVC placed before VAD reduced false-positive VAD triggers "by 3.5x on average" and gave a "71% decrease in AI cutting off users unnecessarily" — [Krisp blog: Improving turn-taking…](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/) (snippet; page blocked).
- Krisp VIVA claims ">2x improvement in WER on AMI" (individual headset mics, overlapping speech) with its BVC-VAD pipeline (snippet, same source family).
- A dev-agency guide (ForaSoft, not an NC vendor) says LiveKit Cloud's licensed Krisp models "lift STT accuracy 10–20% on noisy channels and cut false interruptions sharply" — [ForaSoft LiveKit playbook 2026](https://www.forasoft.com/blog/article/voice-ai-agents-livekit-guide) (snippet). No methodology or data; treat it as marketing-grade.

**Vendor-authored (ai-coustics)**
- "Comparing Krisp and ai-coustics real-time audio enhancement" (2025-11-10) reportedly shows Krisp BVC at 23.5% WER vs ai-coustics at 7.1% on **a specific audio sample** — [ai-coustics blog](https://ai-coustics.com/2025/11/10/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you/) (snippet; single sample, vendor).
- Quail Voice Focus 2.x claims:
  - "reduces WERs by up to 84%" across AssemblyAI, Deepgram, Soniox, Mistral, Cartesia, Gladia, Speechmatics and Gradium
  - e.g. Speechmatics 65.8%→12.5%, AssemblyAI 48.3%→15.1%
  - measured on an internal in-the-wild set with "a foreground speaker and one or several background speakers or media devices"
  - Sources: [VF 2.1 blog](https://ai-coustics.com/blog/quail-voice-focus-2.1), [VF 2.0 deep dive](https://ai-coustics.com/blog/voice-focus-2.0-deepdive) (snippets).

**Vendor-authored (Picovoice, maker of Koala)**
- "Across all noise levels tested, RNNoise reduces STOI distance by a small fraction, while Koala cuts it in half or more" — [Picovoice noise-suppression guide](https://picovoice.ai/blog/complete-guide-to-noise-suppression/) / [Top noise suppression software](https://picovoice.ai/blog/top-noise-suppression-software-free-paid/) (snippets).

**Non-vendor, low-evidence (agency blog)**
- ForaSoft states:
  - RNNoise "adds about 10 ms"
  - DeepFilterNet "adds around 40 ms and needs more compute"
  - Krisp "lands in between"
  - "a Krisp- or DeepFilterNet-class front-end delivers a 20–40% relative WER improvement in genuinely loud conditions"
  - No data or methodology is shown — [ForaSoft: Krisp, RNNoise and DeepFilterNet](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/real-time-noise-suppression-krisp-rnnoise-deepfilternet) (snippet).
  - The latency figures are roughly consistent with the published algorithmic delays of RNNoise (10 ms frame) and DeepFilterNet (≈40 ms incl. lookahead), but this is unverified here.

**ASR vendors (independent of NC vendors, but interested parties)**
- Deepgram: "For pure transcription use cases, … skip noise suppression entirely and send unaltered audio". "Many customers who A/B test find that removing noise suppression improves transcription accuracy".
- Deepgram also says preprocessing "can improve conversational flow for voice agents". It recommends Flux `StartOfTurn` over an external VAD for barge-in ("every StartOfTurn is guaranteed to contain a non-empty transcript"), and warns "Aggressive AEC suppression makes barge-in harder".
- Deepgram sources: [Audio Preprocessing & Barge-In](https://developers.deepgram.com/guides/deep-dives/audio-preprocessing-barge-in); [The Noise Reduction Paradox](https://deepgram.com/learn/the-noise-reduction-paradox-why-it-may-hurt-speech-to-text-accuracy) (snippets).
- AssemblyAI: "In most cases, noise cancellation actually makes accuracy worse". NC "is more effective when applied to VAD and turn-taking logic rather than to the STT input itself". It recommends a noise-robust STT first, then "NC surgically — VAD-only, environment-matched, benchmarked" — [AssemblyAI: Noise cancellation with STT — pros and cons](https://www.assemblyai.com/blog/noise-cancellation-stt-pros-cons) (snippet). Its "up to 3.5x" figure is Krisp's number.

**Practitioner reports**
- A developer PR notes that a test call "picked up other people talking near the caller and treated them as caller turns, because the room input applied the plugin's plain NC model, which attenuates stationary noise but lets background speech through". The fix was `BVCTelephony` for narrowband SIP — [vimalvijayakumar1983/Voice-Ai-Agent PR #52](https://github.com/vimalvijayakumar1983/Voice-Ai-Agent/pull/52) (snippet).
- LiveKit community threads report:
  - ["Unexpected audio degradation after enabling BVC"](https://community.livekit.io/t/unexpected-audio-degradation-after-enabling-bvc-noise-cancellation-in-livekit-voice-agent/745)
  - ["Audio gain before BVCTelephony()"](https://community.livekit.io/t/audio-gain-before-bvctelephony/300): BVCTelephony "can be overly aggressive and occasionally cancels out quiet callers"
  - Both are snippets only; the threads were blocked.
- Silero in noise: VAD "can flip `user_state` to `speaking` on background noise even when STT emits no transcript". The requested fix is to decouple the user-state source from VAD — [livekit/agents#5580](https://github.com/livekit/agents/issues/5580) (Apr 2026, open).
- Self-hosted interruption gap: see [#6033](https://github.com/livekit/agents/issues/6033) (backchannels trigger false interruptions when adaptive interruption falls back to VAD).
- The RNNoise vs DTLN comparison table in [#5507](https://github.com/livekit/agents/issues/5507) cites DTLN at "PESQ 3.04 / STOI 94.76% on DNS-Challenge". That figure comes from the DTLN paper, not a voice-agent test.

### Inferences
- Vendor "WER reduction" numbers in background-talker conditions mostly measure **suppression of background-speaker words** (insertions against a foreground-only reference), not better recognition of the caller.
  - The ai-coustics test set description (foreground plus background speakers/media) is consistent with this.
  - This does not conflict with academic findings that SE hurts WER on single-talker noisy speech. The user should measure the two effects separately (see §5).
- No public source reports head-to-head, same-corpus results for Krisp BVC vs ai-coustics Voice Focus vs DeepFilterNet vs NVIDIA Maxine vs RNNoise with a modern streaming ASR plus turn-taking metrics. The user's A/B/C corpus would itself be the most relevant evidence.

### Gaps
- No independent benchmark repo was found that covers false barge-ins across NC vendors.
- Nothing was found on HN/Reddit with substantive comparative data; searches returned vendor pages.
- NVIDIA Maxine (BNR/AFX) had no voice-agent practitioner comparisons in the results.
- The Krisp and ai-coustics blog methodologies could not be read in full (egress blocked). Numbers above are snippet-level.

---

## 4. Effect of enhancement on ASR, VAD, turn detection, barge-in, diarization

### Takeaway
There is consistent 2022–2026 evidence that single-channel SE front-ends often **increase** WER for modern noise-robust ASR (Whisper, Parakeet, Gemini, etc.). The main cause is processing artifacts and over-suppression, and it can be partly mitigated by blending the raw signal back in (observation adding) or by weaker magnitude masks. ASR vendors therefore recommend raw (or lightly blended) audio to STT and enhanced audio for VAD/turn-taking/barge-in; Hecttor dissents. Competing-talker suppression is a different problem: removing background *words* can reduce insertion errors that no ASR can avoid. No direct evidence was found on SE × Sortformer.

### Cited Findings

**Academic evidence on SE and ASR**
- **"When De-noising Hurts"** (Dec 2025, arXiv 2512.17562):
  - MetricGAN+ (VoiceBank) denoising before Whisper, NVIDIA Parakeet, Gemini Flash 2.0 and Parrotlet-a; 500 medical recordings × 9 noise conditions.
  - "original noisy audio achiev[ed] lower semWER than enhanced audio in all 40 tested configurations". Degradations ranged from 1.1% to 46.6% absolute semWER.
  - Whisper degraded most, then Parakeet.
  - Code: [eka-care/when-denoising-hurts](https://github.com/eka-care/when-denoising-hurts).
  - Sources: [arXiv abs](https://arxiv.org/abs/2512.17562) (snippet; arXiv blocked).
  - Caveat: one older, non-causal enhancer and the medical domain.
- **Iwamoto et al., "How Bad Are Artifacts?"** (Interspeech 2022):
  - Decomposes SE error into noise versus **artifact** components and finds the artifact component "the main cause of performance degradation".
  - **Observation adding** (adding scaled raw signal to enhanced) "can monotonically increase the signal-to-artifact ratio" and improved ASR on simulated and real recordings — [ISCA PDF](https://www.isca-archive.org/interspeech_2022/iwamoto22_interspeech.pdf); [arXiv 2201.06685](https://arxiv.org/abs/2201.06685) (snippet).
  - Follow-up: "Rethinking Processing Distortions…", IEEE/ACM TASLP 2024 — [ACM DL](https://dl.acm.org/doi/10.1109/TASLP.2024.3426924).
- **"Where Speech Enhancement Hurts Recognition: An Inference Time Polar Projection Diagnosis"** (Huo et al., UIUC/Wuhan, Jul 2026, arXiv 2607.11157):
  - For STFT-mask SE, "magnitude strength is the operative axis, while estimated phase correction provides no recognition benefit".
  - "waveform-input wav2vec 2.0 favors strong correction, whereas log-Mel-input, noise-robust Whisper prefers weaker correction".
  - It gives a training-free knob that is "directly useful for voice assistants and agents" — [arXiv abs](https://arxiv.org/abs/2607.11157) (snippet).
- **"Too Good to Be True"** (De Oliveira et al., May 2026, arXiv 2605.12107):
  - Modern ASR with large noisy training and embedded LMs correlates better with human WER, with a transducer the most reliable.
  - But their "robustness to noise and use of context can be uninformative to an acoustics-focused evaluation of enhancement" — [arXiv abs](https://arxiv.org/abs/2605.12107) (snippet).
- Title-level only (content not read):
  - "Training-Free Intelligibility-Guided Observation Addition for Noisy ASR" (arXiv 2602.20967)
  - "When Audio Separation Hurts Zero-Shot ASR: Evaluating SAM-Audio with Whisper…" (arXiv 2603.04710)
  - Source: search results.

**ASR-vendor guidance: raw audio to STT, NC for VAD and turn-taking**
- Deepgram and AssemblyAI (§3) both recommend unprocessed audio for transcription and NC for VAD/turn-taking/barge-in.
- The contrary vendor view is Hecttor: STT wants fully enhanced audio, VAD/TT a blend ([hecttor.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/hecttor.mdx)).
- ai-coustics positions "Quail STT" as an ASR-targeted enhancement model ([Pipecat CHANGELOG 0.0.97](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md); [ai-coustics Quail blog](https://ai-coustics.com/blog/quail-stt-asr-transcription), snippet). This is the "ASR-targeted model" option, but it is vendor-claimed.

**VAD and turn detection**
- The ai-coustics SDK "expects a VAD to run on the original signal". Running it on enhanced audio adds the filter delay to VAD delay (`pipecat/audio/vad/aic_quail_vad.py`, 1.12.0).
- In LiveKit 1.8.3, `ai_coustics.VAD` consumes the flag the enhancer computes during `process_with_vad` rather than enhanced audio (`SP/livekit/plugins/ai_coustics/{plugin,vad}.py`).
- Silero VAD false triggers on noise are a known pain point ([#5580](https://github.com/livekit/agents/issues/5580)).
- The older bundled Silero checkpoint missed short clear utterances: max probability 0.213 for "yes" vs 0.970 with Silero 6.2.1 ([#6815](https://github.com/livekit/agents/issues/6815), Aug 2026).
- The livekit-plugins-silero **1.8.3** wheel bundles `silero_vad.onnx` with SHA256 `1a153a22…88e3`. This equals the 6.2.1 checkpoint hash quoted in #6815, so the short-utterance regression is fixed in the user's version (verified by hashing `SP/livekit/plugins/silero/resources/silero_vad.onnx`).
- LiveKit 1.8.3's audio EOT turn detector (`turn-detector-v1(-mini)`) and adaptive interruption both take post-NC audio (§1). Enhancement artifacts or delay therefore affect EOT timing directly, not only via transcripts (code fact; the effect size is unmeasured).

**Diarization**
- General diarization literature (snippet-level): denoising can reduce missed speech and improve DER, but SE "tends to introduce distortions which deteriorate the performance of subsequent processing modules" — [Multi-Stage Speaker Diarization for Noisy Classrooms, arXiv 2505.10879](https://arxiv.org/html/2505.10879v1) (snippet).

### Inferences

**Recommended default for this stack** (Nemotron streaming ASR is a transducer trained on large noisy data, like Parakeet):
- STT gets raw or lightly blended audio (enhancement_level around 0.3–0.6, or wet/dry blending).
- VAD, barge-in and turn detection get enhanced or voice-focused audio.
- Validate on A/B/C.
- If background *talkers* (not stationary noise) are the dominant failure, a speaker-isolation model on the STT path may still reduce total errors, because the insertions it removes outweigh the artifacts it adds. Measure both terms separately.

**Diarization (Sortformer) after voice isolation**
- Removing background voices makes most frames single-speaker, so diarization contributes less for the "ignore bystanders" goal.
- It still helps as a second line of defence: residual leaked background speech tends to get a different speaker ID, which `MultiSpeakerAdapter` can drop.
- It also covers legitimately multi-party calls (speakerphone family members), where a primary-speaker isolator may suppress a second legitimate caller.
- A generative or "reconstructing" enhancer can alter timbre and confuse speaker embeddings. Run Sortformer on the same signal the ASR uses, and test DER/JER with and without enhancement.
- The four points above are hypotheses, not verified.

**Barge-in**
- Enhancement lowers false barge-ins from background talk/TV.
- But its algorithmic delay (plus the 50 ms RoomIO frame) postpones true barge-in onset.
- Over-suppression of short utterances ("yes", "no", "uh-huh") can drop genuine interruptions and backchannels. This is the risk flagged for BVCTelephony with quiet callers.

### Gaps
- No study was found that measures SE effects on **NVIDIA Nemotron streaming ASR** or on **Sortformer streaming diarization** specifically.
- No study was found of SE effects on LiveKit's audio EOT model or on Silero false-alarm/miss rates under Krisp vs ai-coustics.
- The full texts of the 2025–2026 arXiv papers could not be read (arXiv blocked). Numbers are from abstracts and snippets.

---

## 5. Evaluation methodology for the A/B/C corpus

### Takeaway
Evaluate each enhancer configuration against at least three baselines:
- raw audio
- enhancer on all paths
- enhancer on VAD/turn only with raw audio to STT, plus optional blend levels

Score each on:
1. caller-speech fidelity on A (WER/CER, short-utterance recall)
2. background leakage on B and C (words, VAD triggers, barge-ins, extra speaker IDs)
3. timing (VAD onset/offset delay, EOT latency, algorithmic latency, compute cost)

Where C is a digital mix of A and B, also use intrusive quality metrics against A (PESQ/STOI/SI-SDR), and use non-intrusive DNSMOS/NISQA elsewhere.

### Cited Findings (tools)
- **jiwer**: "simple and fast python package to evaluate an automatic speech recognition system", with WER, MER and WIL (and CER) — [jitsi/jiwer README](https://github.com/jitsi/jiwer).
- **DNSMOS**: Microsoft's non-intrusive MOS for noise suppressors, "high correlation to human ratings in stack ranking noise suppression methods". DNSMOS P.835 gives SIG/BAK/OVRL (ICASSP 2022) — [microsoft/DNS-Challenge DNSMOS README](https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS).
- **NISQA v2.0**: non-intrusive overall quality plus *Noisiness, Coloration, Discontinuity, Loudness* dimensions — [gabrielmittag/NISQA](https://github.com/gabrielmittag/NISQA).
  - The Coloration and Discontinuity scores are useful for spotting enhancer artifacts.
- **torchmetrics 1.9.0** (PyPI) includes `DeepNoiseSuppressionMeanOpinionScore`, `NonIntrusiveSpeechQualityAssessment`, `PerceptualEvaluationSpeechQuality`, `ShortTimeObjectiveIntelligibility` and `ScaleInvariantSignalDistortionRatio` (verified in `torchmetrics/audio/{dnsmos,nisqa,pesq,stoi,sdr}.py` of the 1.9.0 wheel).
- **VERSA**: "over 90 evaluation/profiling metrics" (v1.0, Dec 2024), integrated with ESPnet — [wavlab-speech/versa](https://github.com/wavlab-speech/versa).
- **pyannote.metrics**: DER/JER for diarization, and detection error rate / precision / recall for VAD timelines — [pyannote/pyannote-metrics](https://github.com/pyannote/pyannote-metrics). (README not fetched; the metric names are from general knowledge of the library.)
- **Observation adding** (raw+enhanced blend) as the variable to sweep: Iwamoto 2022 ([ISCA](https://www.isca-archive.org/interspeech_2022/iwamoto22_interspeech.pdf)). DTLN `strength` and Hecttor `enhancer_weight`/`asr_weight`/`vad_tt_weight` expose the same knob.
- **Evaluator choice matters**: modern robust ASR may be insensitive to SE quality differences ([arXiv 2605.12107](https://arxiv.org/abs/2605.12107), snippet). Use the deployed Nemotron ASR as the primary judge.
- **An offline Krisp arm**: the [livekit-examples/noise-canceller](https://github.com/livekit-examples/noise-canceller) utility can run LiveKit Cloud NC/BVC on files, which fits A/B/C replay if a Cloud project is available.

### Inferences (proposed protocol; not taken from a single source)

**Conditions**
- R0: raw
- E1: enhancer → all consumers (current `noise_cancellation` wiring)
- E2: enhancer → VAD/turn/interruption only, raw → STT (custom wrapper)
- E3: E1 with blend or `enhancement_level` ∈ {0.3, 0.5, 0.7, 1.0}
- Optionally one model per vendor/open-source: ai-coustics Quail vs Quail-VF, DTLN, RNNoise, DeepFilterNet3, Krisp BVC via noise-canceller.
- Replay identical audio through RoomIO (room mode), not console, because of the APM difference (§1).

**Metrics on A (caller alone)**
- WER and CER against the reference, normalised (e.g. Whisper English normalizer), for the conditions above. Also report per-utterance paired deltas with bootstrap 95% CIs.
- **Short-utterance and backchannel recall**: the fraction of ≤1 s utterances ("yes", "no", "mm-hm", digits) that
  - (a) trigger VAD start and
  - (b) appear in STT finals.
  This is the over-suppression metric.
- VAD timeline versus an oracle derived from A:
  - pyannote detection error rate (missed and false-alarm seconds)
  - onset latency (VAD start minus true onset)
  - offset latency
- DNSMOS SIG/BAK/OVRL and NISQA Coloration/Discontinuity on the enhanced A, to detect enhancer artifacts on clean speech.

**Metrics on B (background only; the ideal output is silence and no events)**
- **Leakage words per minute**: count of STT final words, plus the fraction of B's reference words recovered (jiwer alignment of hypothesis against B's transcript).
- VAD false-trigger rate (starts per minute and false-alarm seconds).
- **False barge-in rate**: interruptions per minute while the agent is speaking and only B is playing.
- Spurious user turns (EOU commits) per minute.
- Number of Sortformer speaker IDs emitted.

**Metrics on C (mix; reference = A's transcript)**
- Split jiwer alignment errors into:
  - caller-word errors (substitutions and deletions of A words)
  - **background insertions**: inserted hypothesis words that align to B's transcript
  Report both, not just WER.
- False barge-in and false-EOU rates, compared with B.
- Barge-in latency for true interruptions (A onsets during agent speech).
- DER/JER of Sortformer against the A+B oracle speaker timeline.
- If C = A + B mixed digitally at known SNR/SIR: PESQ, STOI and SI-SDR of enhanced(C) against A (torchmetrics). Also stratify all metrics by SIR (e.g. −5, 0, 5, 10 dB), because background-voice suppressors typically degrade sharply at low SIR.

**Latency and compute**
- Algorithmic delay: cross-correlate enhancer input and output on A.
- Per-frame `_process` wall time (p50/p99) on the Mac dev box and the Linux prod servers, as RTF.
- Event-loop lag while processing, because the processor runs on the asyncio loop.
- End-to-end user-stop to agent-speak latency distribution.

**Decision rule**: prefer the configuration that
- minimises false barge-ins and leakage on B/C, and
- keeps A-WER within a pre-set tolerance of raw (e.g. ≤0.5 pp absolute) and short-utterance recall ≥ raw.

Expect E2 or a moderate blend to win for Nemotron. If background insertions on C dominate total errors, full-wet voice isolation on the STT path may still win.

### Gaps
- No published standard exists for "false barge-in rate" or "background-word leakage rate". The definitions above are proposals.
- DNSMOS and NISQA are trained on human-perception labels and do not predict ASR or VAD impact. Use them only as artifact detectors.
- It is not known whether the user's C recordings are acoustic (re-recorded) or digital mixes. Intrusive metrics (PESQ/STOI/SI-SDR) are only valid for digital mixes with a time-aligned A.
