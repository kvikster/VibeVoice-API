# Krisp VIVA turn-taking and interruption models (Turn Prediction v1–v3, Interruption Prediction v1, VAD, TTS detection) and how they could be used in the LiveKit Agents 1.8.3 stack (state as of 2026-09-26)

**Source labels.**
- **[code]**: source I read myself. This covers Pipecat `main` at commit `2967e1c` (2026-09-26), the Pipecat docs repo at `64b83f3` (2026-09-25), Krisp's own Pipecat fork `krispai/pipecat-fork-sdk` (branches), `livekit/agents` `main` at `57b3227` (2026-09-25), the installed `livekit-agents==1.8.3` wheel, and this repo.
- **[wheel]**: my own inspection of PyPI wheels. That means the Python source plus `strings` on the native `.so`.
- **[snippet]**: WebSearch result text only. krisp.ai, sdk-docs.krisp.ai, docs.livekit.io, livekit.com, docs.pipecat.ai, deepgram.com, zylos.ai and huggingface.co were all blocked by the egress proxy (HTTP 403 / EGRESS_BLOCKED on 2026-09-26). Snippets can be out of context, so treat them as weaker than a page read.
- **[vendor]**: a claim by Krisp or LiveKit about its own product.
- **[inference]**: my reasoning, not a verified fact.

GitHub issue pages were read with WebFetch. The GitHub REST API was blocked for repositories outside this session.

## 1. Turn Prediction v1 / v2 / v3: what they are, inputs/outputs, latency, languages, thresholds, release dates, accuracy

### Takeaway
Krisp's turn models detect end-of-turn from audio alone. Turn Prediction v3 (`krisp-viva-tp-v3.kef`) is streaming:
- **Input:** the **user's audio only**, 10/15/20/30/32 ms frames, plus a **per-frame external VAD flag**.
- **Output:** **one end-of-turn probability per frame**. Pipecat fires at `prob ≥ 0.5`.
- **Size and languages:** about 9M parameters, 30 MB, CPU-only, "12+ languages" including English.

Versions: v1 is from mid-2025, v2 from November 2025, and v3 from April–May 2026 (Pipecat support 2026-04-17, public launch in VIVA 2.0 on 2026-05-06). All accuracy evidence is Krisp's own. Krisp says v3 beats SmartTurn and "LiveKit" on FPR vs. mean shift time. Krisp's own post also reportedly concedes that Deepgram Flux has a lower mean shift time and a marginally higher F1. There is no independent benchmark.

### Cited Findings
**Timeline**
- **v1 (2025).** Krisp blog "Audio-only, 6M weights Turn-Taking model for Voice AI Agents" [vendor][snippet]. A LiveKit feature request dated **2025-08-06** already cites "Krisp's new audio turn-taking model" as "6.1M params, 65MB, CPU-optimized". The issue was closed as not planned, with no staff comment visible. — [Krisp blog v1](https://krisp.ai/blog/turn-taking-for-voice-ai/); [livekit/agents#3094](https://github.com/livekit/agents/issues/3094)
- **v2 (`krisp-viva-tt-v2`), announced November 2025** [snippet]. It was "trained on a more diverse and better-structured dataset, with richer data augmentations". It delivers "up to a 6% improvement in F1 score under noisy conditions", and "when combined with Krisp's Voice Isolation … v2 achieves even greater accuracy and stability". — [Krisp blog Turn-Taking v2](https://krisp.ai/blog/krisp-turn-taking-v2-voice-ai-viva-sdk/); [sdk-docs turn-taking v2](https://sdk-docs.krisp.ai/docs/krisp-turn-taking-v2-blog)
- **v2 API as used by Pipecat (2026-01-09 to 2026-04-17)** [code]:
  - The call was `self._tt_session.process(frame.tolist())`, with no VAD flag.
  - The code comment says "Negative values indicate the model is not ready yet (working with 100ms data)", so the first ~100 ms produced no probability.
  - `KrispVivaTurn` itself first shipped in Pipecat **v0.0.99 (2026-01-13)**.
  - Sources: [pipecat commit 4c19f55 diff](https://github.com/pipecat-ai/pipecat/commit/4c19f5584cada7947d56f20de7a571b6cacbd7d5); [pipecat CHANGELOG 0.0.99](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md)
- **v3 support in Pipecat: commit "VIVA SDK TT v3 support (#4252)", 2026-04-17** [code]. It was authored by a Krisp engineer (Garegin Harutyunyan, later committing as `gharutyunyan@krisp.ai`) and first shipped in the Pipecat **v1.1.0** tag (2026-04-27). The CHANGELOG has no entry for it; I verified the release with `git describe --contains`. — [pipecat #4252 / 4c19f55](https://github.com/pipecat-ai/pipecat/commit/4c19f5584cada7947d56f20de7a571b6cacbd7d5)
- **Public launch: VIVA 2.0 on 2026-05-06** (Twilio Signal) [vendor][snippet]. Wording: "Turn Prediction v3 — multilingual model that predicts end-of-turn from audio alone, no transcription needed". — [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents); [Krisp blog VIVA 2.0](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/)

**v3 model facts**
- Model card data [vendor][snippet]: "Turn Prediction v3 (krisp-viva-tp-v3) has ~9M parameters and 30 MB size with support for 12+ languages and a recommended threshold of 0.5". It is "designed for low resource consumption on CPU with no GPU required". — [Krisp blog: turn-taking + interruption prediction](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/); [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)
- Output semantics [vendor][snippet]: v3 "listens to conversational audio and outputs a probability between 0 and 1 that the speaker has finished their turn, with the probability progressively refined during the silence period that follows speech". — [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)

**v3 API as used by Pipecat** [code]. Source: [`src/pipecat/audio/turn/krisp_viva_turn.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/krisp_viva_turn.py), lines 175–186, 246–341.
- **Session setup:** `krisp_audio.TtSessionConfig()` with `inputSampleRate`, `inputFrameDuration` and `modelInfo.path`, then `krisp_audio.TtFloat.create(cfg)`.
- **Per-frame call:** `prob = self._tt_session.process(frame, is_speech, False)`. The frame is a float32 array in [-1, 1]. `is_speech` is the external VAD flag for that buffer. The third argument is always `False` and is not documented.
- **Threshold and frame size:** `KrispTurnParams(threshold=0.5, frame_duration_ms=20)`.
- **Decision rule:** COMPLETE when `speech_triggered and prob >= threshold`. It measures `e2e_processing_time_ms` from the VAD speech→silence transition to the threshold crossing and emits `TurnMetricsData` (added in v0.0.104, 2026-03-02).
- **Environment variables:** `KRISP_VIVA_TURN_MODEL_PATH` for the model, `KRISP_VIVA_API_KEY` for the key.
- **Session state:** `clear()` resets only Python-side state. The Tt session object is never reset or re-created while the sample rate stays the same.
- Supported sample rates via Pipecat's mapping: 8, 16, 24, 32, 44.1 and 48 kHz. Frame durations: 10, 15, 20, 30 and 32 ms. — [`krisp_instance.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py) [code]
- Docs inconsistency: Pipecat's feature page names the v3 file `krisp-viva-tp-v3.kef`. The KrispVivaTurn reference page still shows `KRISP_VIVA_TURN_MODEL_PATH=/path/to/krisp-viva-tt-v2.kef`. — [pipecat docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx); [krisp-viva-turn.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/utilities/turn-detection/krisp-viva-turn.mdx) [code]
- Native internals (LiveKit's bundled Krisp SDK) [wheel]. `livekit-plugins-krisp-internal 0.2.0` (2026-07-22) contains source-file symbols `tt_session.cpp`, `tt3_processor.cpp`, `tt3_mel_extractor.cpp`, `tt3_preprocessor.cpp`, `tt3_postprocessor.cpp` and `tt3_config_reader.cpp`, and a `KRISP::TurnTakingV3` namespace with `tt3ModelName`, `tt3InferConfigName` and `fpConfigName`. This suggests TT v3 works on mel features with a frame-processor config embedded in the `.kef`. — [PyPI livekit-plugins-krisp-internal](https://pypi.org/project/livekit-plugins-krisp-internal/)

**Accuracy and latency claims (all vendor)**
- v3 vs v2 [snippet]: "pushes end-of-turn latency below 200ms". The share of fast responses (<200 ms) went "from 47% to 69%" relative to v2 "without increasing the risk of interrupting the user mid-sentence". — [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- v3 vs other models [snippet]:
  - "In comparisons of FPR vs Mean Shift Time, Krisp TT v3's curve sits below SmartTurn and LiveKit across the operating range".
  - "Turn Prediction v3 leads on Balanced Accuracy and AUC, while Deepgram Flux is marginally ahead on F1 Score (84.60 vs 84.44) and F1 Score Hold (92.60 vs 91.20)".
  - "Deepgram Flux achieves a lower mean shift time at the same FPR levels".
  - "threshold 0.5 recommended as the default operating point".
  - Source: [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)
- An earlier BusinessWire snippet says Krisp's curve "sat below LiveKit's built-in and Deepgram Flux's". That partially contradicts the blog snippet above, which has Flux ahead on mean shift time at equal FPR. — [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents) vs. [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)
- Krisp's own offline comparison tool (April 2026) runs Krisp TT against `smart-turn-v3` on a WAV [code].
  - It uses Pipecat's production VAD defaults (`confidence=0.7, start_secs=0.2, stop_secs=0.2, min_volume=0.6`), 20 ms TT frames, and threshold 0.5 (CLI `--threshold`).
  - It reports `detection_delay` (VAD silence → turn event). For SmartTurn it also reports `total_delay`, which adds `stop_secs`.
  - Source: [krispai/pipecat-fork-sdk `krisp-viva-demo` branch, `scripts/krisp/demo_turn_taking.py`, `demo_types.py`](https://github.com/krispai/pipecat-fork-sdk/tree/krisp-viva-demo/scripts/krisp)

### Inferences
- **Inputs.** "Audio-only" means no transcript. Krisp and Pipecat both show only the **user** stream plus a VAD flag going in. No agent/TTS channel is passed, unlike MaAI's two-channel `bc_det`.
- **Latency.** TP v3 is streaming. The earliest a decision can come is the frame at which the probability crosses 0.5 during silence. Krisp's "<200 ms for 69% of turn-ends" is measured from speech end. In LiveKit 1.8.3 the host only asks for a prediction after VAD end-of-speech, which needs at least 0.2 s of silence (LiveKit's floor; this repo uses 0.55 s). So LiveKit would cap the latency benefit unless the adapter reports the streaming decision as soon as it fires (see §6c).
- **Which LiveKit model was compared.** "LiveKit" in Krisp's chart is not identified. It may be LiveKit's older text EOU model or the 2026 audio `turn-detector-v1`/`v1-mini`. Do not assume it is `v1-mini`.

### Gaps
- The full Krisp blog post with plots, dataset description, languages list and per-language numbers could not be read (krisp.ai blocked).
- The meaning of the third `process()` argument, and whether Tt/Ip sessions have a reset API, are not documented in any readable source.
- There is no public model card (sdk-docs blocked). CPU cost per stream and real-time factor are not published anywhere I could reach.
- No independent (non-Krisp) evaluation of TP v1/v2/v3 was found.

## 2. Interruption Prediction v1: what it classifies, inputs, decision latency, output, thresholds, languages, metrics, release date

### Takeaway
IP v1 (`krisp-viva-ip-v1.kef`) is an **audio-only, English-only, streaming** classifier.
- **What it detects:** whether speech that starts while the agent is talking is a **genuine attempt to take the floor** or a **backchannel** ("yeah", "uh-huh", "mhm"). Per one snippet, it also covers noise.
- **Input:** user audio frames (float32, 10–32 ms) plus a per-frame VAD flag, fed continuously.
- **Output:** a per-frame **probability of genuine interruption**. There is no agent-audio input and no transcript input.
- **Size and threshold:** ~6M parameters, 24 MB. Krisp recommends threshold **0.4**, while Pipecat defaults to **0.5**.
- **Vendor metrics:** "<6% false positives" with "sub-second mean interruption time", against VAD firing on "almost two-thirds of backchannels".
- **Dates:** in the SDK and Pipecat since 2026-04-17; publicly launched 2026-05-06.

### Cited Findings
- **Definition** [vendor][snippet]: "Interrupt Prediction v1 — first-of-its-kind audio-only classifier that predicts when a user is intending to interrupt the agent, and distinguishes intent-to-take-the-floor from backchannel speech like 'yes' or 'mhm'". Elsewhere: "a brand-new model that distinguishes between backchannels … and genuine interruptions when the user wants to take the turn and interrupt the speaking AI agent". Another snippet adds that it "classifies whether overlapping speech is genuine interruption intent versus backchannel or noise". — [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents); [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)
- **Model card data** [vendor][snippet]: "Interruption Prediction v1 (krisp-viva-ip-v1) has ~6M parameters and 24 MB size for English with a recommended threshold of 0.4". Another snippet says it "operates on 40 ms frames". — [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/); [sdk-docs (search index)](https://sdk-docs.krisp.ai/)
- **Metrics** [vendor][snippet]:
  - "VAD-based interruption … fires on almost two-thirds of backchannels"
  - "Krisp Interruption Prediction v1 uses a learned model that separates the two with under 6% false positives at the recommended threshold"
  - "at the recommended threshold (0.4) achieves sub-second mean interruption time at under 6% false positive rate"
  - "It reacts in under a second"
  - "the probability progressively refined during the user's speech segment, distinguishing intent from acknowledgment without waiting for the user to complete a full sentence"
  - Source: [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)
- **API as used by Pipecat** [code]. Source: [`src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py), lines 144–165, 216–267.
  - **Session setup:** `krisp_audio.IpSessionConfig()` with `inputSampleRate`, `inputFrameDuration` and `modelInfo.path`, then `krisp_audio.IpFloat.create(cfg)`.
  - **Per-frame call:** `ip_prob = self._ip_session.process(ip_frame, self._speech_active)`, where the frame is float32 in [-1, 1] and the second argument is a VAD boolean.
  - **Continuous feed:** "Every frame is passed to the IP model regardless of speech state so that the model maintains continuous internal state (matching the standalone Krisp SDK behaviour)."
  - **Defaults:** `threshold=0.5`, `frame_duration_ms=20`.
  - **Environment variables:** `KRISP_VIVA_IP_MODEL_PATH` for the model, `KRISP_VIVA_API_KEY` for the key.
- **Decision rule in Pipecat** [code]:
  - The first frame with `speech_active and not decision_made and ip_prob >= threshold` triggers `trigger_user_turn_started()`. That is Pipecat's interruption when the bot is speaking. The strategy then returns `STOP`.
  - The decision is sticky: at most one trigger per VAD speech segment.
  - State resets on `VADUserStoppedSpeakingFrame` or `BotStoppedSpeakingFrame`.
  - The strategy does **not** check whether the bot is speaking; it runs on all user speech.
  - Source: [same file](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py), lines 193–283
- **Trailing-frame behaviour described by Krisp's engineers** [code]. Krisp's demo branch separates a raw per-frame VAD flag (passed to `process()`) from a debounced "speech active" gate (used for the threshold check), "because the IP model may output a high probability one frame *after* the raw VAD goes silent". Upstream `main` later merged both into `_speech_active` (#4335, 2026-04-27). — [krispai/pipecat-fork-sdk `krisp-viva-demo` strategy diff and `demo_interrupt_prediction.py`](https://github.com/krispai/pipecat-fork-sdk/blob/krisp-viva-demo/scripts/krisp/demo_interrupt_prediction.py); [pipecat #4335 / e594192](https://github.com/pipecat-ai/pipecat/commit/e5941926be79f16a515af2a4d356cefb56e8b34d)
- **Dates** [code]:
  - Strategy added in the "VIVA SDK TT v3 support (#4252)" commit on 2026-04-17, co-authored by Aram Poghosyan (`apoghosyan@krisp.ai`).
  - First release: Pipecat **v1.1.0** (tag 2026-04-27). The CHANGELOG has no "Added" entry. The first CHANGELOG mention is the SDK-1.11 nanobind fix in **v1.8.0 (2026-08-26)**.
  - Public launch: VIVA 2.0 on **2026-05-06** [snippet].
  - Sources: [pipecat git history](https://github.com/pipecat-ai/pipecat/commits/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- **Native internals** [wheel]. LiveKit's bundled Krisp SDK contains `krisp_audio_sdk_ip.cpp`, `ip_session.cpp`, `ip_processor.cpp`, `ip_config_reader.cpp`, `vocabulary_checker.cpp` and `audio_volume_calculator.cpp`, and a `KRISP::InterruptionPrediction` namespace with `ipModelName`, `ipInferConfigName`, `fpConfigName` and **`vadKefName`**. It also has `handleToIpFloatMap` and `handleToTtFloatMap`, which are C-API handle maps. This suggests the IP `.kef` is a bundle that carries its own VAD model and a volume gate. — [PyPI livekit-plugins-krisp-internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/)

### Inferences
- **What it classifies.** Per-frame "is this an intent to take the floor" during user speech, typically while the agent speaks. It is speaker-agnostic: it has no notion of *which* person is speaking. A TV or bystander saying a full sentence over the agent may well score as a "genuine interruption", unless Voice Isolation or Voice Focus removes them first. Krisp's recommended pipeline puts VI before everything else.
- **Decision latency.** "Sub-second mean" from speech onset at FPR < 6%. Because the output is a running probability, true barge-ins with strong acoustic cues (loud, fast, rising energy) plausibly cross earlier than 0.5 s. Short backchannels stay low and simply end. For comparison, LiveKit's Cloud model claims 100% recall by 500 ms of overlap (§5). The distribution was not published.
- **The 40 ms figure.** The snippet's "40 ms frames" vs. the SDK's 10–32 ms `inputFrameDuration` most likely means the model's internal hop is 40 ms and the SDK buffers input frames. This needs confirming. If true, the probability only changes every 40 ms, and the Pipecat default of 20 ms simply repeats values.

### Gaps
- No published precision/recall curve, per-condition breakdown (noise, telephony, accents), dataset, or decision-latency distribution could be read. Only "under 6% FP" and "sub-second" survive in snippets.
- Unknown: how the model reacts to the agent's own TTS echo leaking into the uplink. No agent-reference input exists.
- Unknown: whether IP is calibrated only for overlaps, or also for speech while the agent is silent (Pipecat runs it on both).
- No independent evaluation or community bug report about IP quality was found (GitHub search 2026-09-26).

## 3. Krisp VAD and the TTS-detection model

### Takeaway
- **Krisp VAD (`krisp-viva-vad-v2.kef`)** is a per-frame speech-probability model: `VadFloat.create(VadSessionConfig)`, then `process(frame)` returns a float. It covers 8–48 kHz, and Pipecat added it in v0.0.108 (2026-03-27). It could supply the per-frame VAD flag that TP v3 and IP v1 need.
- **The TTS detector** is a per-frame "synthetic speech" probability model: `TtsDetectorFloat.create(TtsDetectionSessionConfig)`, then `process(frame)` returns a float.
  - Pipecat uses it only as a **one-time gate at the start of a stream**. Voice isolation stays bypassed until synthetic speech has been detected and has then been absent for 0.5 s, or until 3 s pass with no synthetic speech.
  - The stated motive is phone call screening: the far end is first answered by a synthetic assistant (iPhone call screening). VI would otherwise lock onto that voice and then suppress the real human.
  - It is **not** a per-turn echo gate for the agent's own TTS. This corrects an inference in `Огляд рішень voice isolation/krisp.md` §1.

### Cited Findings
- **KrispVivaVadAnalyzer** [code]:
  - `krisp_audio.VadSessionConfig()` with `inputSampleRate`, `inputFrameDuration` and `modelInfo.path`, then `krisp_audio.VadFloat.create(cfg)`.
  - `voice_confidence()` returns `session.process(audio_float32)`.
  - Frame duration defaults to 10 ms. Accepted rates: 8, 16, 32, 44.1 and 48 kHz (24 kHz is rejected in `set_sample_rate`).
  - Environment variable: `KRISP_VIVA_VAD_MODEL_PATH`.
  - Pipecat's generic `VADParams` apply: `confidence=0.7, start_secs=0.2, stop_secs=0.2, min_volume=0.6`.
  - Sources: [`src/pipecat/audio/vad/krisp_viva_vad.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/vad/krisp_viva_vad.py) lines 94–205; [krisp-viva-vad-analyzer.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/vad/krisp-viva-vad-analyzer.mdx)
- **KrispVivaVadAnalyzer release history.** "Added `KrispVivaVadAnalyzer` …" in Pipecat **0.0.108 (2026-03-27)**. The SIGSEGV-on-teardown fix, which keeps the SDK initialized for the process lifetime, landed in **1.8.0 (2026-08-26)**. — [pipecat CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md) [code]
- Pipecat docs pitch Krisp VAD "for applications requiring support for higher sample rates". The VAD file named in the docs is `krisp-viva-vad-v2.kef`. — [speech-input.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/learn/speech-input.mdx); [krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) [code]
- **Native VAD internals** [wheel]: `vad_v2_processor.cpp`, `vad_v2_maincleaner.cpp`, `vad_v2_config_loader.cpp`, `krisp_dsp_energy_thresholding.cpp`, `krisp_dsp_mean_energy.cpp`. — [PyPI livekit-plugins-krisp-internal](https://pypi.org/project/livekit-plugins-krisp-internal/)
- **TTS detection in KrispVivaFilter** [code]. Source: [`src/pipecat/audio/filters/krisp_viva_filter.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py), lines 33–46, 171–256, 288–349.
  - The docstring says: "TTS detection (iPhone screening feature is standalone model) to delay voice isolation until bot speech playback has stopped, preventing later real human speech suppression artifacts".
  - Parameters: `tts_model_path` / `KRISP_VIVA_TTS_MODEL_PATH`, `tts_threshold=0.5`, `tts_detection_timeout=3.0`, and constant `_TTS_CLEARED_COOLDOWN = 0.5` s.
  - Logic:
    - `_tts_detection_active` is set only in `start()`.
    - While active, frames go through `TtsDetectorFloat.process()` and audio passes through **unfiltered**.
    - NC starts once TTS was seen and has been absent for ≥ 0.5 s, or once 3 s have passed with no TTS.
    - After that, detection never runs again for the session.
- **TTS detection history** [code]. Added in #4668 (merged 2026-06-30), first shipped in Pipecat **v1.5.0 (2026-07-04)**. The CHANGELOG has no entry. Branch `krisp-viva-tts-detect` in Krisp's fork also adds a file-based test script. — [pipecat commit 5085648](https://github.com/pipecat-ai/pipecat/commit/508564808); [krispai/pipecat-fork-sdk branches](https://github.com/krispai/pipecat-fork-sdk/branches)
- **Krisp's marketing of the TTS detector** [vendor][snippet]: "TTS Detector detects synthetic speech in real time", with "a use case where an outbound voice AI agent calls a number and recognizes when an inbound voice AI agent or IVR picks up". It is part of VIVA 2.0 "Signal Detectors", alongside gender and accent, "bundled into existing VIVA pricing at no additional charge". — [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462); [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)

### Inferences
- **For this stack.** Krisp VAD is interesting mainly as a cheap, frame-exact VAD flag source for TP v3 and IP v1, e.g. inside the bargein server. Replacing Silero or `AicVAD` in LiveKit would need an adapter like the repo's `AicVAD` (`local_voice_agent/aic.py`), which wraps a per-frame probability model in Silero's state machine.
- **Where the TTS detector matters.** It is relevant only for **outbound** calls (the agent calls an iPhone with screening, or an IVR/answering bot). For inbound English callers it is not needed. It is not a solution for the agent hearing its own TTS through the caller's speakerphone: Pipecat never re-arms it.
- **Echo as a signal.** Using the TTS detector as a per-overlap "is this our own echo?" signal is conceivable, but it is untested and not something Krisp documents.

### Gaps
- No readable spec for VAD v2 or the TTS detector: accuracy, latency, languages, frame hop, CPU cost.
- The TTS-detection model file name is not given in any readable source (only the environment variable).

## 4. Pipecat integration in depth (classes, `krisp_audio` calls, frame sizes, env vars, how decisions feed turn/interruption, defaults, version history)

### Takeaway
Pipecat, largely maintained by Krisp's own engineers, is the reference integration. Its four wrappers all share one process-wide `KrispVivaSDKManager` (`krisp_audio.globalInit` with the API key) and all use the `<Kind>SessionConfig` / `<Kind>Float.create()` / `process()` pattern.

| Wrapper | Session class | Default frame | Role in the pipeline |
|---|---|---|---|
| Filter | `NcInt16` | 10 ms | audio-in filter (voice isolation) |
| Turn | `TtFloat` | 20 ms | `TurnAnalyzerUserTurnStopStrategy` |
| IP | `IpFloat` | 20 ms | user-turn **start** strategy, i.e. barge-in gate |
| VAD | `VadFloat` | 10 ms | VAD analyzer |

The recommended configuration puts IP first in the start-strategy list with `TranscriptionUserTurnStartStrategy()` as a fallback. That fallback fires on **any** transcript, including "yeah", so in Pipecat's own example backchannel suppression depends on the STT not emitting a transcript first.

### Cited Findings
- **SDK manager** [code]. Source: [`src/pipecat/audio/krisp_instance.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)
  - `krisp_audio.globalInit("", key, license_callback, log_callback, LogLevel.Off)` runs once per process. The key comes from the argument or `KRISP_VIVA_API_KEY`, and only the first key is used.
  - `krisp_sdk_uses_nanobind_bindings()` checks `krisp_audio.getVersion() >= 1.11.0`.
  - Enum maps: `SamplingRate.Sr8000Hz…Sr48000Hz` and `FrameDuration.Fd10ms/15/20/30/32`.
  - Since v1.8.0 (2026-08-26) `release()` no longer calls `globalDestroy()`, which fixed a SIGSEGV.
- **Filter** [code]. `NcSessionConfig`, then `NcInt16.create`, then `process(frame_int16, noise_suppression_level)`. Level defaults to 100.0 (a float since the SDK 1.11 nanobind change) and frames to 10 ms. Runtime toggle via `FilterEnableFrame`. Optional TTS gate as described in §3. — [`krisp_viva_filter.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py)
- **How IP feeds the interruption path** [code]:
  - `UserTurnController.process_frame` runs the start strategies in order for every frame and stops at the first `STOP`.
  - `trigger_user_turn_started()` emits `on_user_turn_started` with `enable_interruptions`, which broadcasts the interruption while the bot speaks.
  - `TranscriptionUserTurnStartStrategy` triggers on every `InterimTranscriptionFrame` (when `use_interim=True`) or `TranscriptionFrame`, and returns `STOP`.
  - Sources: [`user_turn_controller.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_turn_controller.py) lines ~200–230; [`transcription_user_turn_start_strategy.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/transcription_user_turn_start_strategy.py); [`base_user_turn_start_strategy.py`](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/base_user_turn_start_strategy.py)
- **Reference example** [code]. `KrispVivaFilter()` on every transport, `start=[KrispVivaIPUserTurnStartStrategy(threshold=0.5), TranscriptionUserTurnStartStrategy()]`, `stop=[TurnAnalyzerUserTurnStopStrategy(turn_analyzer=KrispVivaTurn())]`, and `vad_analyzer=SileroVADAnalyzer()` ("or KrispVivaVadAnalyzer"). Environment variables: `KRISP_VIVA_FILTER_MODEL_PATH`, `KRISP_VIVA_TURN_MODEL_PATH`, `KRISP_VIVA_IP_MODEL_PATH`, `KRISP_VIVA_API_KEY`. — [`examples/voice/voice-krisp-viva.py`](https://github.com/pipecat-ai/pipecat/blob/main/examples/voice/voice-krisp-viva.py)
- **Docs.** IP is documented as a start strategy "designed to work alongside other start strategies (e.g., `TranscriptionUserTurnStartStrategy` as a fallback)". The interruptions guide lists it as the model-based alternative to `MinWordsUserTurnStartStrategy(min_words=3)`. — [user-turn-strategies.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/utilities/turn-management/user-turn-strategies.mdx); [interruptions.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/fundamentals/interruptions.mdx) [code]
- **Model files and setup** [code]:
  - Download from the Krisp developer portal (`sdk.krisp.ai`, "Server SDK Version" tab). The wheel example is `krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl`.
  - Model file names: `krisp-viva-vi-tel-v2.kef`, `krisp-viva-tp-v3.kef`, `krisp-viva-ip-v1.kef`, `krisp-viva-vad-v2.kef`.
  - Key requirement: "The `KRISP_VIVA_API_KEY` is required for Krisp SDK v1.6.1 and later".
  - Source: [pipecat docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- **Version history (Pipecat tags)** [code]. Sources: [CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md); `git describe --contains` on the commits.

  | Version (date) | Change |
  |---|---|
  | 0.0.48 (2024-11-10) | legacy `KrispFilter` |
  | 0.0.90 (2025-10-10) | `KrispVivaFilter` |
  | 0.0.94 (2025-11-10) | `KrispFilter` deprecated |
  | 0.0.99 (2026-01-13) | `KrispVivaTurn` (TT v2 API) and shared SDK manager |
  | 0.0.104 (2026-03-02) | `api_key` for SDK ≥ 1.6.1; `TurnMetricsData` |
  | 0.0.108 (2026-03-27) | `KrispVivaVadAnalyzer` |
  | 1.0.0 (2026-04-14) | `KrispFilter` and `krisp` extra removed |
  | 1.1.0 (2026-04-27) | TT v3 API (VAD flag) and `KrispVivaIPUserTurnStartStrategy` |
  | 1.5.0 (2026-07-04) | TTS detection in `KrispVivaFilter` |
  | 1.8.0 (2026-08-26) | SDK 1.11 nanobind compatibility; SDK kept alive for the process |

  The latest tag, v1.12.0 (2026-09-25), has no further Krisp changes.
- **Krisp's own fork, `krispai/pipecat-fork-sdk`** [code]. Its branches include:
  - `krisp-viva-demo` (2026-04-20): `scripts/krisp/demo_interrupt_prediction.py` (Krisp IP vs. VAD-only on a WAV, annotated WAVs plus HTML report) and `demo_turn_taking.py` (Krisp TT vs. SmartTurn v3).
  - `krisp-viva-tts-detect` (2026-06-30).
  - `feature/audio-test-viva` (2026-08-12): a release-eval scenario `krisp_viva_interruption_file.yaml` that plays a real noisy recorded barge-in ("Actually, never mind that — what's the capital of Japan?") during a long answer, because the IP model is "meant to be exercised against genuine noisy/real-mic audio, not synthesized speech".
  - Sources: [krispai/pipecat-fork-sdk](https://github.com/krispai/pipecat-fork-sdk); [demo_interrupt_prediction.py](https://github.com/krispai/pipecat-fork-sdk/blob/krisp-viva-demo/scripts/krisp/demo_interrupt_prediction.py)
- **IP demo settings** [code]. Pipecat's IP strategy, 20 ms frames, threshold 0.5 (CLI `--threshold`). VAD is Silero or Krisp with `VADParams(stop_secs=0.2)` and `confidence=0.7`. Input is **user audio only**, mono, resampled to 16 kHz. Each VAD speech segment is evaluated independently ("regression-test mode"). There is no agent timeline. — [same file](https://github.com/krispai/pipecat-fork-sdk/blob/krisp-viva-demo/scripts/krisp/demo_interrupt_prediction.py), lines 191–430

### Inferences
- **The fallback defeats backchannel suppression.** In Pipecat's shipped configuration IP mostly *speeds up* genuine barge-ins, since it fires before any transcript. A transcribed "yeah" still interrupts through the Transcription fallback, unless the STT drops it or the fallback is replaced by something like `MinWordsUserTurnStartStrategy(min_words≥2)` or a lexicon filter.
  - This repo's option 1 is already that kind of lexicon filter.
  - A faithful port should therefore pair IP with the repo's lexicon, not with a bare transcript trigger.
- **Continuous feed.** IP and TT keep state across the whole call, which Pipecat achieves by feeding every frame. Any LiveKit port must also feed continuously, e.g. a tap in `stt_node` or a FrameProcessor. The bargein-server path only sees overlap windows (§6a).

### Gaps
- No Pipecat GitHub issues reporting IP or TT quality problems were found. Search on 2026-09-26 returned only docs and release notes.
- The PR discussions for #4252 and #4335 could not be read through the API (the repository is not attached to this session).

## 5. LiveKit: what it offers (plugin, own models) and any issues/PRs about Krisp turn/IP

### Takeaway
As of 2026-09-26, LiveKit offers **no Krisp turn, IP or VAD integration**.
- **`livekit-plugins-krisp` 0.4.3** (2026-09-23) exposes only VIVA **voice isolation**. That holds in both the Cloud-auth and the `krisp_license` (OSS-server) modes.
- **The native `livekit-plugins-krisp-internal`** does link Krisp's IP, TT v3 and VAD v2 code, but its FFI exposes only NC sessions.
- **LiveKit's own equivalents:**
  - the **adaptive interruption** model, a Cloud-only barge-in vs. backchannel classifier behind `/bargein`;
  - the **audio turn detector** (`v1` in Cloud with a backchannel probability; `v1-mini` local without one).
- **Self-hosted requests:** agents#6033 (2026-06-09) asks for self-hosted adaptive interruption or Krisp VIVA turn/IP integration. It is open, with no staff reply.

### Cited Findings
- **`livekit-plugins-krisp`** [wheel]:
  - Releases run from 0.1.1 (2026-04-16) to 0.4.3 (2026-09-23), roughly weekly.
  - `__all__` = `KrispVivaFilterFrameProcessor`, `voice_isolation`, `voice_isolation_telephony`, `LiveKitCloudAuthProvider`, `KrispLicenseAuthProvider`, `auth`.
  - There is no turn, IP, VAD or TTS-detection symbol.
  - Modules: `_krisp.py`, `auth.py`, `viva_filter.py`, `log.py`, `version.py`.
  - The same holds on `livekit/agents` `main` at 2026-09-25 [code].
  - Sources: [PyPI JSON](https://pypi.org/pypi/livekit-plugins-krisp/json); [livekit/agents livekit-plugins-krisp](https://github.com/livekit/agents/tree/main/livekit-plugins/livekit-plugins-krisp)
- **`livekit-plugins-krisp-internal 0.2.0`** (manylinux x86_64, 110 MB `.so`) [wheel]:
  - The Rust FFI exposes an NC session (`krisp_nc::NcSession::new_from_blob`, `process_int16`).
  - The same binary contains `KRISP::InterruptionPrediction::*`, `KRISP::TurnTakingV3::*`, `handleToIpFloatMap`, `handleToTtFloatMap`, `handleToVadFloatMap`, and `ip_session.cpp` / `tt3_processor.cpp` / `vad_v2_processor.cpp`.
  - Source: [PyPI livekit-plugins-krisp-internal](https://pypi.org/project/livekit-plugins-krisp-internal/)
- **agents#6033** "Support Self-Hosted Adaptive Interruption / Krisp VIVA Integration for LiveKit Agents" [code]:
  - Opened 2026-06-09 and labelled enhancement.
  - Motivation: Hindi/Telugu backchannels ("haa", "avunu", "hmm") interrupting self-hosted SIP agents.
  - Asks for any of: a self-hostable adaptive-interruption model, an official Krisp VIVA turn/IP integration, a pluggable interruption-detector interface, or local inference.
  - Open, with no comments visible on 2026-09-26.
  - Source: [livekit/agents#6033](https://github.com/livekit/agents/issues/6033)
- **agents#3094** "Audio-Based Turn Detection Support" (2025-08-06), which cited Krisp's 6.1M/65 MB model, was closed as not planned. — [livekit/agents#3094](https://github.com/livekit/agents/issues/3094)
- **Krisp's GitHub org has a `livekit-agents-fork-sdk` repository** (updated 2026-08-28). Its only branch is `main`, identical to an upstream snapshot (last commit 1c472dd, 2026-08-28), with no Krisp turn/IP code. Its Pipecat fork, by contrast, carries Krisp feature branches. — [github.com/krispai](https://github.com/orgs/krispai/repositories); `git ls-remote` of both forks [code]
- **Krisp's marketing** [vendor][snippet]: VIVA "embedded in over 130 voice AI products, including LiveKit" and "VIVA models are available via … frameworks like LiveKit and Pipecat". That is true only for voice isolation on the LiveKit side (see above). — [Krisp VIVA page](https://krisp.ai/developers/viva/)
- **LiveKit adaptive interruption (its own model)** [vendor][snippet]:
  - Blog dated 2026-03-19.
  - "86% precision and 100% recall at 500 ms overlap speech"
  - "rejects 51% of VAD-based barge-ins"
  - "detects true barge-ins faster than VAD in 64% of cases"
  - "enabled by default in Python Agents v1.5.0+"
  - "deployed directly in LiveKit Cloud data centers"
  - Sources: [LiveKit blog](https://livekit.com/blog/adaptive-interruption-handling); [LiveKit docs](https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling/)
- **LiveKit 1.8.3 client for `/bargein`** [code: `livekit/agents/inference/interruption.py` in the installed 1.8.3 wheel]:
  - **Constants:** `SAMPLE_RATE=16000`, `MIN_INTERRUPTION_DURATION=0.05` (2 × 25 ms frames), `MAX_AUDIO_DURATION=3`, `DETECTION_INTERVAL=0.1`, `AUDIO_PREFIX_DURATION=1.0`, `REMOTE_INFERENCE_TIMEOUT=0.7`, `_FRAMES_PER_SECOND=40`.
  - **Docstring mismatch:** the docstrings say the prefix "defaults to 0.5s" and the timeout "defaults to 1 second". Both disagree with the constants.
  - **`session.create` settings:** only `sample_rate`, `num_channels`, `threshold`, `min_frames`, `encoding`. The server is **not** told the prefix length or interval.
  - **When audio is sent:** only while the agent speaks. On the first overlap the buffer is trimmed to `speech_duration + prefix`. After that the whole buffer (≤ 3 s) goes out every 0.1 s until the overlap ends.
  - **How the verdict is read:** the client takes it from the message type (`bargein_detected` vs. `inference_done`). The `probabilities` are used for `_estimate_probability`, the n-th largest value with n = `min_frames`, in events and metrics.
  - Source: [PyPI livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)
- **LiveKit 1.8.3 turn detector** [code: `inference/eot/*`, `voice/turn.py`]:
  - `inference.TurnDetector(version="v1-mini")` runs locally over ctypes. `v1` uses the Cloud gateway with a local fallback.
  - An inference request is sent only after VAD silence ≥ `MIN_SILENCE_DURATION_MS = 200`, over a 1.2 s audio buffer. The attached VAD's `min_silence_duration` must be ≥ (200 + 50) ms (`audio_recognition.py` line 894).
  - The English threshold for `v1-mini` is 0.36, and it covers 14 languages.
  - `TurnDetectionEvent.backchannel_probability` is "None when the detector does not produce one (e.g. the local mini model)".
  - **Plug points:** `TurnDetectionMode` accepts a runtime-checkable `_StreamingTurnDetector` protocol (`stream()` → `push_audio`, `predict() -> Future[TurnDetectionEvent]`, `unlikely_threshold`, `supports_language`, …) or the text `_TurnDetector` protocol (`predict_end_of_turn(chat_ctx)`).
  - Source: [PyPI livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)

### Inferences
- **What LiveKit could ship.** LiveKit has every technical ingredient for a Krisp IP/TT integration: the native code is in its internal wheel, and the plugin has a license mode for OSS servers. Nothing is exposed, and #6033 is unanswered. For planning, assume **no official LiveKit path in 2026**. Any use in this repo is a custom port from Pipecat's BSD-2 wrappers onto the public `krisp_audio` wheel.
- **Nearest official equivalents.** LiveKit's adaptive interruption (Cloud) and `turn-detector-v1` backchannel probability (Cloud) play the same role as Krisp IP. Both are unavailable locally, which is why the repo reimplements `/bargein`.

### Gaps
- LiveKit docs and blog pages could not be read in full, so any statement there about third-party interruption models is unknown.
- It is not known whether the internal wheel's IP/TT code is reachable through a hidden FFI entry point. I only checked symbol strings and the public `_ffi.py` function list.

## 6. Design for this repo (inference): Krisp IP v1 behind the local bargein server, as a PolicyRunner signal, Turn v3 vs. `turn-detector v1-mini`, and offline replay

### Takeaway
[inference, based on the code facts above and the repo code]
- **Most faithful integration:** run Krisp IP **continuously in the agent process** on the (optionally cleaned) caller audio, as Pipecat does and as the repo already does with MaAI. Feed its per-frame `p_interrupt` into both options:
  - Option 1: a `KrispReading` alongside `MaaiReading` in `decide_text` and `PolicyRunner`.
  - Option 2: the bargein server.
- **IP inside `bargein_server` alone:** workable within the 0.7 s budget, but the model then sees only LiveKit's overlap windows (1 s prefix + overlap, ≤ 3 s). Its continuous state and VAD flag have to be reconstructed.
- **Turn v3 in LiveKit:** it can replace `v1-mini` only through the private `_StreamingTurnDetector` protocol. Evaluate it in shadow first.
- **Offline replay:** add a `tools/krisp_ip_scores.py` (WAV → per-frame JSONL on `audio_pos_s`), mirroring `tools/maai_scores.py`, plus a `--krisp` input to `replay_policy`. Both stay deterministic and causal.

### Cited Findings
- **Bargein server** (repo facts) [code]:
  - It answers every binary window. Superseded windows get an immediate reply.
  - It reconstructs the new tail with `new_tail()`, which assumes a rolling window in 10 ms steps.
  - It starts a new overlap after a gap of more than 0.35 s between requests.
  - It returns a **constant** probability list, `[p] * max(2, n_samples // 400)`, i.e. one value per 25 ms.
  - Decisions never wait for ASR or MaAI.
  - Classifier thresholds: `min_overlap_s=0.25`, `single_word_s=0.6`, `maai_threshold=0.45`, `no_asr_min_s=0.6`, `long_overlap_s=2.0`.
  - Sources: `voice_agent/local_voice_agent/bargein_server/server.py` lines 190–281; `voice_agent/local_voice_agent/bargein_server/classifier.py` lines 42–201
- **MaAI** (repo facts) [code]:
  - `bc_det` is two-channel (user + agent from `tts_node`); `bc_det_mono` is used in the server.
  - Frames are 80 ms at 12.5 Hz. `reading(window_s)` returns the peak `p_bc` over a window.
  - `maai_scores` writes `{"kind":"maai","t","audio_pos_s","p_bc","mode"}` on the WAV clock.
  - `replay_policy` merges `agent`, `maai` and `stt` records by time, with agent < maai < stt at equal times, and never reads a clock.
  - Sources: `voice_agent/local_voice_agent/backchannel/maai_detector.py`; `voice_agent/local_voice_agent/tools/maai_scores.py`; `voice_agent/local_voice_agent/tools/replay_policy.py`; `voice_agent/local_voice_agent/policy_runner.py`
- **Text policy** (repo facts) [code]:
  - Backchannel and continuer lexicon ("do not stop" is a continuer).
  - Interrupt tokens ("stop", "wait", …) pass immediately.
  - Short interims are held for the final (`interim_min_words=3`).
  - A MaAI veto applies only to ≤ 2 content words at `p_bc ≥ 0.45`.
  - `awaiting_answer` exempts answers to the agent's question.
  - Source: `voice_agent/local_voice_agent/backchannel/policy.py`; `voice_agent/HANDOFF.md`
- **Agent config** (repo facts) [code]: `turn_detection = inference.TurnDetector(version="v1-mini")`. Adaptive mode uses `interruption={"mode": "adaptive", "resume_false_interruption": True}`; filters mode uses VAD mode with `min_words`. — `voice_agent/local_voice_agent/agent.py` lines 85–103
- **Continuous-state requirement.** Krisp's Pipecat code feeds IP "every frame … regardless of speech state so that the model maintains continuous internal state", and the model can peak "one frame after the raw VAD goes silent". — [pipecat IP strategy](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py); [Krisp demo branch](https://github.com/krispai/pipecat-fork-sdk/blob/krisp-viva-demo/scripts/krisp/demo_interrupt_prediction.py) [code]

### Inferences
All points in this section are [inference].

**(a) Krisp IP as the classifier behind `bargein_server`**
- **Session lifecycle.** Keep one `IpFloat` session per WebSocket session, created in `_on_create` after one process-wide `globalInit`. On each binary window, feed **only the new tail** (`new_tail()` already exists) to `IpFloat.process()` in 20 ms frames: 320 samples at 16 kHz, float32, `/32768`. Never re-feed audio the session has already seen, because it is a stateful streaming model.
- **First window of an overlap.** Real speech only begins after the prefix. The server is not told the prefix length (§5), so configure it on both sides.
  - Pass `audio_prefix_duration` explicitly on the agent side, if `AdaptiveInterruptionDetector` construction allows it, or keep LiveKit's 1.0 s default.
  - Mirror it in the server (e.g. `BARGEIN_PREFIX_S=1.0`).
  - Feed the first `prefix` seconds with `vad=False` and the rest with `vad=True`. A cleaner option is to compute the per-frame flag with a server-side VAD (Krisp VAD v2 or Silero) on the window, which also yields honest `False` frames during the trailing silence before LiveKit's VAD ends the overlap.
- **Between overlaps.** The server sees nothing between overlaps. Either (i) create a fresh `IpFloat` for each new overlap (after a gap of more than `new_overlap_gap_s`) and warm it with the 1 s prefix, or (ii) keep one session and accept a discontinuity. Session-creation cost is unknown, so pre-create a spare. Evaluate both variants offline (see d).
- **Mapping to the protocol:**
  - Compute Krisp per-frame probabilities (20 ms), then resample to the protocol's 25 ms grid by taking the max of the Krisp frames overlapping each 25 ms slot.
  - Emit `probabilities` covering the whole window, with `0.0` for prefix slots and real values for overlap slots, so that LiveKit's metrics estimate (n-th max, n = `min_frames` = 2) is meaningful.
  - Reply `bargein_detected` when any overlap frame so far crossed θ, where θ = the client-supplied `threshold` or the server default. Make the decision sticky per overlap, as Pipecat's `_decision_made` is. Otherwise reply `inference_done`.
  - Suggested default θ = **0.4** (Krisp's recommendation) and not Pipecat's 0.5. Tune it on the corpus.
- **Latency budget.** Each request adds only ~0.1 s of new audio (about 5 × 20 ms frames). The first request carries about 1.0–1.3 s (about 50–65 frames). A ~6M-parameter CPU model per frame should fit easily inside 0.7 s. Measure `prediction_duration` anyway, since per-frame cost is unpublished. Keep the existing "never wait for ASR" rule.
- **Combining with the existing rules.** Use IP as the **primary early signal** and keep the lexicon as an override when a transcript is available:
  - Transcript has an interrupt token → interrupt.
  - Transcript is only backchannel or continuer words → no, even if IP is high. This guards against IP false positives on emphatic "yeah!" and on "do not stop".
  - IP ≥ θ → interrupt.
  - IP < θ, but ≥ 2 content words or overlap ≥ `long_overlap_s` → interrupt. This is the safety net for IP misses, in the same role as Pipecat's Transcription fallback but backchannel-aware.
- **Background talkers.** Only the caller audio reaches `/bargein`, and IP is speaker-agnostic. In C-type audio (caller + background), IP will score background speech too. Put voice isolation before the room input: Krisp VI through `livekit-plugins-krisp` `krisp_license`, or ai-coustics `quail_vf_*`, both already options in the repo. Or require the Sortformer/primary-speaker check from ASR before honouring an IP-only interrupt on long overlaps.

**(b) Krisp IP as a signal in PolicyRunner / filters (like `MaaiReading`)**
- **Live.** Add a `KrispIpDetector` tapping user frames in `stt_node`, exactly where MaAI's `push_user` is. Feed the IP session **continuously** with a per-frame VAD flag, from the Krisp VAD session or LiveKit's VAD events. Keep a short history of `(t, p_int)`. Expose `reading(window_s)` returning `KrispReading(status, p_int_max, p_int_last, evaluated_at, window_s, clock)`.
  - This is the most faithful reproduction of Pipecat's usage: continuous state, and IP sees non-overlap speech too.
  - It also enables a **live shadow mode** for IP. The repo cannot do this for `/bargein`, because LiveKit trusts the server there.
- **Policy rules, in `decide_text` and `BargeinClassifier.decide`:**
  - `p_int_max ≥ θ` since overlap start → treat like an interrupt signal. In filters mode that lets a short interim pass instead of being held, cutting latency for real barge-ins.
  - `p_int_max < θ_low` over the utterance, and ≤ 2 content words → drop as backchannel. This is the same slot as `maai_backchannel` and covers ASR mis-hearings ("but high" for "uh-huh").
  - Keep `awaiting_answer` precedence: IP knows nothing about questions.
- **Why IP instead of or beside MaAI.** MaAI `bc_det` uses the **agent channel** too and is open (MIT code). Krisp IP is user-only, English-only, proprietary and licensed. Log both, as `signals.maai` and `signals.krisp_ip`, and compare them on the same events.

**(c) Krisp Turn v3 vs. LiveKit `turn-detector v1-mini`**

| | LiveKit `v1-mini` (in use) | Krisp TP v3 |
|---|---|---|
| Where it runs | local, ctypes | local, `krisp_audio` wheel with licence key |
| Input | 1.2 s audio window | streaming 20 ms frames + VAD flag |
| When it is queried | after VAD silence (≥ 0.2 s floor; 0.55 s here) | continuously; probability refined during the silence |
| English threshold | 0.36 | 0.5 recommended |
| Languages | 14 | "12+" |
| Size | ~108 MB of weights (repo README) | ~9M parameters, 30 MB |
| Backchannel output | none | none (that is IP's job) |

- **Adapter.** Implement `_StreamingTurnDetector` / `_StreamingTurnDetectorStream`:
  - `push_audio()` feeds `TtFloat` with a VAD flag.
  - `predict()` resolves immediately with `TurnDetectionEvent(end_of_turn_probability=latest or max-since-silence p, …)`.
  - `unlikely_threshold()` returns θ = 0.5.
  - `supports_language("en")` returns True.
- **Private-API risk.** This protocol is private, so the risk is the same as with `/bargein`: pin 1.8.3 and add a harness test.
- **Latency limit.** LiveKit asks only after VAD end-of-speech, so Krisp's advantage over `v1-mini` is limited to the probability's quality at that moment. Reclaiming the "<200 ms" claim would need a lower VAD `min_silence_duration`, bounded by LiveKit's 0.25 s requirement noted in HANDOFF, plus a shorter `min_endpointing_delay`.
- **Evaluation order.** Start with a shadow/log comparison: both detectors' probabilities at each VAD end on A/C, against labelled turn ends. Switch only if Krisp reduces premature EOT at equal latency.
- **Interaction with Riva endpointing.** `riva_server` has its own endpointing, which affects finals. Turn-detector changes interact with the NeMo `endpointing` config.

**(d) Offline replay and evaluation on the A/B/C corpus with `replay_policy`**
- **New tool `tools/krisp_ip_scores.py`,** modelled on `maai_scores.py`:
  - Read a 16 kHz WAV and run a VAD per 20 ms: Krisp VAD v2, or Silero through the same state machine as live.
  - Feed `IpFloat.process(frame, vad_flag)` for **every** frame, continuous as in Pipecat.
  - Write `{"kind":"krisp_ip","t":…,"audio_pos_s":…,"p_int":…,"vad":…}`.
  - Write `*.meta.json` with: SDK `getVersion()`, the `.kef` sha256, frame ms, VAD source and parameters, θ, and the WAV sha256.
  - Frames at `t` use only audio up to `t`, so the tool is causal by construction. Deterministic for fixed input, assuming single-threaded CPU inference; this is unverified, so re-run twice and diff as the repo already does.
- **Replay changes:**
  - Extend `replay_policy.merge` with `_ORDER = {"agent":0, "maai":1, "krisp_ip":2, "stt":3}` and a `--krisp` input.
  - Add `PolicyRunner.krisp(t, p)` storing a history like `maai()`, and a `_krisp_reading(t)` over a window.
  - Pass the reading into `decide_text` and `BargeinClassifier.decide`.
  - Add `signals.krisp_ip` to both decision records.
  - Truncating the log must not change earlier decisions (existing test pattern).
- **Second tool: `bargein_replay`.** It simulates what `/bargein` would see:
  - Using the agent timeline (`C_mix.agent.jsonl`) and a VAD on the caller WAV, build LiveKit-style windows (1 s prefix + overlap, a new window every 0.1 s, ≤ 3 s).
  - Use synthetic `created_at` = WAV position in ns.
  - Run the server's `_analyse` path with the Krisp classifier.
  - This isolates the "windowed / per-overlap session" variant from the "continuous tap" variant, on identical audio.
- **Metrics:**
  - Needs labels per user segment overlapping agent speech: `backchannel` / `barge_in` / `background` / `noise`.
  - Backchannel FPR (Krisp claims < 6%).
  - Barge-in recall and decision latency from onset (Krisp claims "sub-second mean"; LiveKit claims 100% recall by 500 ms).
  - False triggers on B (background only). This should be ~0 only if VI or Voice Focus runs first.
  - Compare against `text_filter`, `interruption_classifier` (ASR + lexicon), MaAI `bc_det` / `bc_det_mono`, and Krisp IP, alone and combined.
- **Krisp's own demo harness.** Krisp's `demo_interrupt_prediction.py` (IP vs. VAD on a WAV) can serve as a sanity cross-check that the port reproduces Krisp's reference behaviour on the same file.

**How Krisp IP compares with the repo's MaAI + lexicon approach**

| | Lexicon (option 1/2) | MaAI `bc_det` | Krisp IP v1 |
|---|---|---|---|
| Needs ASR text | yes: waits for interims/finals; 1-word interims held | no | no |
| Handles explicit semantics ("stop", "wait", "do not stop", answers after "?") | yes, deterministic | no | no |
| Latency | ASR-bound | 80 ms frames | 20–40 ms frames |
| Uses agent audio | n/a | yes (two-channel) | no |
| Languages | English lexicon | en/ja; repo uses en | English only |
| Licence and footprint | in repo | MIT code, weights licence to check, heavy torch/transformers stack | proprietary, licence key, ~6M parameters CPU |
| Validated here | tested | real model not yet run | none |

- MaAI directly predicts *backchannel-ness*. Krisp IP predicts *interruption intent*.
- Neither audio model solves background talkers.
- The best combination is likely **IP (or MaAI) for early, ASR-free decisions, with the lexicon as an override**. Pipecat's own default fallback (any transcript interrupts) is weaker than the repo's lexicon.

### Gaps
- Unknowns that block a firm design:
  - IpFloat/TtFloat cost per frame on Apple Silicon and x86.
  - Whether sessions can be reset or cheaply re-created.
  - Whether IP output is meaningful on a cold start from a 1 s prefix.
  - Whether `krisp_audio` wheels exist for Linux aarch64 and for the repo's Python (3.11 in the local venv; Pipecat's example wheel is cp312).
- Licensing and network behaviour of `globalInit` with a key (phone-home or metering) remains unverified, as in the previous note. That matters for "everything local".
- None of this was run: there is no Krisp wheel, model or key in this environment.

## 7. Quality evidence and community reports

### Takeaway
All quantitative evidence for Turn v3 and IP v1 is **Krisp's own**:
- IP: < 6% FP at θ = 0.4 with sub-second mean interruption time, against VAD firing on about 2/3 of backchannels.
- TP v3: 69% of responses under 200 ms, against 47% for v2; "leads on Balanced Accuracy and AUC", with Flux marginally ahead on F1 and mean shift time.
- LiveKit's comparable Cloud model has its own vendor numbers.

I found no independent benchmark, no GitHub bug reports and no community write-ups (as of 2026-09-26). The only community signal is demand: LiveKit issues asking for Krisp turn/IP support for self-hosting.

### Cited Findings
- **Krisp IP** [vendor][snippet]: "fires on almost two-thirds of backchannels" (VAD) vs. "under 6% false positives at the recommended threshold (0.4)", "sub-second mean interruption time". — [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)
- **Krisp TP v3** [vendor][snippet]: "<200 ms" responses "from 47% to 69%". Leads on "Balanced Accuracy and AUC". Flux "marginally ahead on F1 Score (84.60 vs 84.44) and F1 Score Hold (92.60 vs 91.20)" and has "lower mean shift time at the same FPR". — [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/); [voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)
- **Krisp platform claims** [vendor][snippet]: "Platforms using VIVA have reported a 3.5x improvement in turn-taking accuracy, 50% fewer dropped calls and 30% higher customer satisfaction". — [Krisp blog Turn-Taking v2 / VIVA pages (search summary)](https://krisp.ai/blog/krisp-turn-taking-v2-voice-ai-viva-sdk/)
- **LiveKit adaptive interruption** [vendor][snippet]: 86% precision and 100% recall at 500 ms overlap; rejects 51% of VAD barge-ins; faster than VAD in 64% of cases. — [LiveKit blog 2026-03-19](https://livekit.com/blog/adaptive-interruption-handling)
- **Community demand**: livekit/agents#6033 (2026-06-09, open, no replies) and #3094 (2025-08-06, closed as not planned). — [#6033](https://github.com/livekit/agents/issues/6033); [#3094](https://github.com/livekit/agents/issues/3094)
- **Krisp's internal evaluation practice** [code]:
  - An offline IP vs. VAD comparison per speech segment, with annotated WAVs.
  - An end-to-end release-eval scenario with a real noisy recorded barge-in.
  - Both live in Krisp's Pipecat fork.
  - Source: [krispai/pipecat-fork-sdk](https://github.com/krispai/pipecat-fork-sdk/tree/krisp-viva-demo/scripts/krisp)
- **Third-party articles found but not readable** (blocked or not fetched): Zylos Research "Turn-Taking and Barge-In Mechanics in Realtime Voice Agents" (2026-07-17), Hamming AI's interruption runbook, and a webrtc.ventures post (2026-09). Their content about Krisp is unknown. — [zylos.ai](https://zylos.ai/research/2026-07-17-turn-taking-barge-in-realtime-voice-agents/); [hamming.ai](https://hamming.ai/resources/voice-agent-interruption-handling-runbook); [webrtc.ventures](https://webrtc.ventures/2026/09/voice-ai-interruption-handling-state-machines-vs-streaming/)

### Inferences
- **Comparing the vendor numbers.** Krisp's "< 6% FP on backchannels" and LiveKit's "rejects 51% of VAD barge-ins, 86% precision" are measured on different datasets, with different definitions and operating points. They cannot be compared directly. Only a replay on the user's own A/B/C corpus (§6d) will tell.
- **Supporting evidence for the design choices.** Krisp's own emphasis on real noisy recordings and on running VI before turn and IP models supports two points: run evaluations on real caller audio, not TTS, and keep voice isolation in front of IP in this stack.

### Gaps
- No independent benchmark of Krisp TP v3 or IP v1 against LiveKit `v1`/`v1-mini`, Pipecat Smart Turn v3, Deepgram Flux, or MaAI.
- No field reports (positive or negative) on GitHub, Reddit or HN from Pipecat users of IP or TT were found in search on 2026-09-26.
- Krisp's full benchmark plots and data were not readable.
