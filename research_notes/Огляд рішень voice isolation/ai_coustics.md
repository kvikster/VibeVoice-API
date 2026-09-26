# ai-coustics (Quail, Quail Voice Focus, Rook/Sparrow, VAD, Tyto) as a candidate for a self-hosted voice agent (as of 2026-09-26)

Research notes. Method and access limits: ai-coustics.com, docs.ai-coustics.com, developers.ai-coustics.com, artifacts.ai-coustics.io, livekit.io/docs.livekit.io, community.livekit.io, arxiv.org, huggingface.co and archive mirrors were all **blocked by the egress proxy** (HTTP 403). The ai-coustics blog, docs and pricing facts below therefore come from **WebSearch result snippets**, not full-page reads, and are marked "(snippet)". Facts marked "(verified)" come from primary artifacts I could read in full: the PyPI JSON API, raw GitHub files (`raw.githubusercontent.com`), and local inspection of the installed wheels `aic-sdk 3.2.0` and `livekit-plugins-ai-coustics 0.3.2` (scratchpad venv, read-only).

---

## 1. Model lineup (2025–2026): what each model is for, how Voice Focus picks the foreground speaker, and known failure modes

### Takeaway
As of September 2026, ai-coustics sells three enhancement product lines. **Quail Voice Focus** (`quail-vf-*`) isolates the primary speaker for ASR and voice agents. **Quail Multi Speaker** (`quail-ms-*`, which is "QUAIL_L" in LiveKit) enhances every speaker for ASR. **Rook Multi Speaker** (`rook-ms-*`, formerly "Sparrow", before that the original "Quail") is tuned for human listening. Alongside these are two VAD families, **VAD Multi Speaker** (`vad-ms-*`) and **VAD Voice Focus** (`vad-vf-*`), plus the **Tyto** audio-risk analyzer. Voice Focus needs no enrollment and picks the foreground speaker from acoustics alone (proximity, near-field cues). No speaker embedding is involved. Its main documented failure mode is suppressing quiet or uncertain foreground speech when the enhancement level is high. I found no "Lark" model.

### Cited Findings
**Naming history (verified from the SDK changelog)**
- Nov 2025 (aic-sdk 1.2.0): `QUAIL_STT` was added as "the new speech-to-text optimized model". Dec 2025 (1.3.0) added `QUAIL_STT_L8`, `QUAIL_STT_S16`, `QUAIL_STT_S8` and `QUAIL_VF_STT_L16`, the last described as a "Voice Focus STT model for isolating foreground speaker". — [aic-sdk-py CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- Jan 2026 (aic-sdk 2.0.0): "Quail-STT models are now called 'Quail' – These models are optimized for human-to-machine enhancement (e.g., Speech-to-Text applications). Quail models are now called 'Sparrow' – These models are optimized for human-to-human enhancement (e.g., voice calls, conferencing)." — [aic-sdk-py CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- Sparrow was later renamed Rook. The LiveKit plugin 0.3.2 warns `"sparrowS is deprecated, use rookS instead"` (verified, local inspection of the `livekit-plugins-ai-coustics` 0.3.2 wheel, `__init__.py`). The docs note "a recent renaming from Sparrow to Rook" — [ai-coustics Models docs (snippet)](https://docs.ai-coustics.com/guides/models). The July 2025 "Meet Quail…" launch post now lives at the URL "Meet Rook: the most advanced real-time speech enhancement model", so the 2025 "Quail" launch describes today's Rook — [ai-coustics blog (snippet)](https://ai-coustics.com/blog/meet-quail-the-most-advanced-real-time-speech-enhancement-model)
- Voice Focus generations. **VF 2.0** needed aic-sdk 2.1.0 (2026-02-27). **VF 2.1** needed 2.2.0 (2026-04-23), which also dropped VF 2.0. Both are verified in the [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md) and on [PyPI](https://pypi.org/pypi/aic-sdk/json). **VF 2.2** (`quail-vf-2.2-l-16khz`) was in use by mid-2026: Pipecat's changelog entry for its bump to aic-sdk ~=2.5.0 says the "ai-coustics voice examples now use the `quail-vf-2.2-l-16khz`" model — [Pipecat CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md). A search snippet dates a VF 2.2 demo to July 2026 (unverified).

**Current catalog (Sept 2026, from ai-coustics' own Agent Skills repo, verified)**
| Product | Family IDs | Purpose |
|---|---|---|
| Quail Voice Focus | `quail-vf-l-16khz`, `quail-vf-s-16khz`, `quail-vf-l-48khz` | "Isolate the primary speaker for Voice AI / STT. Suppresses interfering speakers as well as noise." |
| Quail Multi Speaker | `quail-ms-l-16khz`, `quail-ms-s-16khz`, `quail-ms-l-8khz` | "Enhance all speakers for Voice AI / STT (meetings, multi-party calls)." |
| Rook Multi Speaker | `rook-ms-l-16khz`, `rook-ms-s-16khz`, `rook-ms-l-48khz` | "Perceptual enhancement for human listeners (natural sound, 48 kHz builds)." |
| VAD Multi Speaker | `vad-ms-16khz` (e.g. `vad-ms-2.1-xxs-16khz`) | "Any audible speech, any speaker. Robust to noise, music, far-field." |
| VAD Voice Focus | `vad-vf-16khz` | "The primary speaker only; ignores interfering and background speech." |
| Tyto | `tyto-1.1-l-16khz` | Audio-risk analysis (see §3) |

Sources: [skills/ai-coustics-speech-enhancement/SKILL.md](https://github.com/ai-coustics/skills/blob/main/skills/ai-coustics-speech-enhancement/SKILL.md) and [skills/ai-coustics-voice-activity-detection/SKILL.md](https://github.com/ai-coustics/skills/blob/main/skills/ai-coustics-voice-activity-detection/SKILL.md). "l / s are model sizes (large is more accurate, small is faster)… Pre-rename ids (`quail-l-16khz`, `rook-l-48khz`, …) map onto the current products automatically." (same source)

**What the user's LiveKit enums actually load (verified, local inspection of the 0.3.2 binary `libplugins_ai_coustics_uniffi.so`, 80 MB, models embedded)**
- The binary contains these model IDs: `quail-l-16khz-…-v20`, `quail-vf-2.2-l-16khz-…-v14`, `quail-vf-2.2-s-16khz-…-v14`, `rook-s-48khz-…-v52`. The mapping is **QUAIL_L = Quail (Multi Speaker) 16 kHz, QUAIL_VF_L / QUAIL_VF_S = Voice Focus 2.2 L / S at 16 kHz, ROOK_S = Rook S at 48 kHz**. SPARROW_S is deprecated.
- The plugin README describes QUAIL_L as "default, best for voice enhancement" and QUAIL_VF_L as "higher quality, extra cost" (the extra cost applies under LiveKit Cloud billing). — [livekit-plugins-ai-coustics on PyPI](https://pypi.org/project/livekit-plugins-ai-coustics/)
- LiveKit's docs still describe the VF enums as "ai-coustics Voice Focus 2.1 (QUAIL_VF_S and QUAIL_VF_L)", which conflicts with the VF 2.2 IDs in the 0.3.2 binary. — [LiveKit noise cancellation docs (snippet)](https://docs.livekit.io/transport/media/noise-cancellation/)

**Machine vs human listening**
- "Quail is machine-targeted (optimised for ASR and VAD), while Rook is tuned for human listening." — [ai-coustics blog: human vs machine models (snippet)](https://ai-coustics.com/blog/audio-enhancement-voice-ai-asr-vad)
- Quail (Multi Speaker) "is designed for far-field and multi-speaker environments and does not suppress distant-sounding speech", so it suits speakerphones and meeting rooms. — [ai-coustics Models docs (snippet)](https://docs.ai-coustics.com/guides/models)

**How Voice Focus chooses the foreground speaker (vendor statements, partly contradictory)**
- It needs no enrollment. The public API takes only a mono audio block and an `EnhancementLevel` parameter, with no speaker-embedding or enrollment call (verified, [aic-sdk README/pyi on PyPI](https://pypi.org/project/aic-sdk/)).
- "Models like Quail Voice Focus reliably prioritize the speaker closest to the device, even in the presence of background speech or media playback." The model handles "spatial distance, room acoustics, device coloration, temporal overlap and echo behavior simultaneously." Once it finds the primary speaker it "locks onto the foreground speaker consistently regardless of input loudness." — [VF 2.0 deep-dive / VF 2.1 blog (snippets)](https://ai-coustics.com/blog/voice-focus-2.0-deepdive)
- **Contradiction:** the docs say Voice Focus "is signal-based rather than speaker-based, enhancing whichever speech signal is dominant in the foreground, allowing multiple near-field speakers to be enhanced without locking onto a single voice." — [Speech Enhancement for Voice AI Systems docs (snippet)](https://docs.ai-coustics.com/guides/speech-enhancement-for-asr). The blog's "lock-on" wording and the docs' "no locking onto a single voice" wording pull in opposite directions. The docs are the more technical source.
- VF 2.0 "is optimized for near-field, single-primary-speaker interactions and designed to suppress competing speech, media playback, and echo." — [VF 2.0 + LiveKit blog (snippet)](https://ai-coustics.com/blog/voice-focus-2.0-livekit-integration)
- VAD Voice Focus: "This targeting is dynamic, not fixed — the same speaker-switching behavior described for Quail Voice Focus applies here." With a single speaker, near or far, it triggers. When voices compete, only the primary one triggers. — [ai-coustics VAD docs (snippet)](https://docs.ai-coustics.com/models/voice-activity-detection/vad)

**Documented failure modes and tuning**
- `enhancement_level` sets how strict the model is under uncertainty. Lower values keep more ambiguous speech but let more background leak through. Higher values attenuate competing speech and echo more aggressively and "increas[e] the risk of suppressing low-energy foreground speech". "Total WER follows a characteristic U-shaped curve with a deployment-specific optimum." The docs recommend starting at the default 0.5 and moving toward 0.8 if competing speech or noise causes STT errors. — [docs: Speech Enhancement for Voice AI Systems (snippet)](https://docs.ai-coustics.com/guides/speech-enhancement-for-asr)
- The foreground speaker should arrive at about **−35 to −10 LUFS (integrated)** at the model input. A foreground speaker that is too quiet may be classified as background and suppressed. — same docs page (snippet)
- The vendor's own benchmark says the best English WER came at level **0.75, not 1.0** (see §2). — [ai-coustics benchmarks (snippet)](https://ai-coustics.com/benchmarks-quantitative)
- A search snippet says the Voice Focus VAD (2.0 generation) has a warm-up that "may cause under-firing on the first turn, so for first-turn-critical agents, the general QUAIL_VAD_2_0_XXS model is preferred". The exact page could not be confirmed. It surfaced with [ai-coustics/livekit-plugins-aic-vad](https://github.com/ai-coustics/livekit-plugins-aic-vad) and a third-party repo.
- Since aic-sdk 2.0.0, the SDK only accepts **mono** audio; multichannel input must be downmixed (3.0.0) (verified, [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)).

### Inferences
- For this use case (a near-field phone or web caller, with a TV or nearby people in the background), **Quail Voice Focus L (2.2)** for audio plus **VAD Voice Focus** for turn detection and barge-in is the combination ai-coustics designs for. QUAIL_L (Multi Speaker) deliberately keeps distant speech, so it will pass the TV and bystanders through. Rook and Sparrow are the wrong target, because they optimize perceptual quality rather than ASR.
- **Backchannels ("mm-hm", "yeah")** are short, often quiet, and uncertain. Two documented mechanisms put them at risk: quiet-foreground suppression at high enhancement levels, and VAD minimum-speech-duration or hold smoothing. No source addresses backchannels directly. Expect a trade-off: keep the enhancement level near 0.5–0.75 and validate backchannel recall on your own recordings.
- A loud background talker close to the mic (for example, someone standing next to the caller) can be "foreground" to a proximity- and dominance-based model. Voice Focus cannot tell the enrolled caller apart from a second near-field person, and the docs say it does not lock onto one voice. The Sortformer diarization plus `MultiSpeakerAdapter` stage remains the only identity-aware layer in the user's stack.

### Gaps
- No "Lark" (or other bird-named) product was found in any 2025–2026 source.
- No published statement explains exactly how Voice Focus switches speakers: its time constants, whether it re-acquires after long silences, or how it behaves when the caller moves away from the mic. The deep-dive pages were blocked.
- Exact VF 2.2 release date and changelog: not verified.

---

## 2. Published benchmarks and quality evidence (WER, background-speaker suppression, competitor comparisons)

### Takeaway
Almost all evidence comes from ai-coustics itself. It uses cloud STT APIs (AssemblyAI, Deepgram, Soniox, Speechmatics, Cartesia, Gladia, Mistral, ElevenLabs, Gradium) and ai-coustics-built datasets. The main foreground-isolation dataset, **Dawn Chorus** (450 real recordings), is open-sourced. The claimed gains are large on background-speech data: up to 43% (VF 2.0) and up to 84% (VF 2.2) relative WER reduction, driven mainly by fewer insertions. I found **no benchmarks on NVIDIA Nemotron, Parakeet or Riva, on Whisper, or against LiveKit BVC**, and no fully independent third-party evaluation.

### Cited Findings
**Voice Focus 2.0 on Dawn Chorus (vendor)**
- Dawn Chorus "contain[s] 450 challenging real-world recordings of foreground speakers and competing background speech as well as noise". Each example comes with the clean foreground audio and a transcript. — [VF 2.0 deep-dive (snippet)](https://ai-coustics.com/blog/voice-focus-2.0-deepdive). ai-coustics announced on X that it was open-sourcing the dataset ("dawn_chorus_en" on Hugging Face). — [ai-coustics on X](https://x.com/ai_coustics/status/2031748151095562725)
- Raw WER across the ASR providers was 21.9%–30.9%. Voice Focus pre-processing reduces it "up to 43%". "This improvement is mainly a result of heavily reduced insertions while substitutions and deletions remain relatively stable." Providers: AssemblyAI, Cartesia, Deepgram, Gladia, Mistral, Soniox, Speechmatics. — [VF 2.0 deep-dive (snippet)](https://ai-coustics.com/blog/voice-focus-2.0-deepdive)
- On Dawn Chorus, Voice Focus VAD raised balanced accuracy from 79% (Silero VAD on raw audio) to 90%. — same (snippet)

**Voice Focus 2.1 / 2.2 (vendor)**
- VF 2.1 WER: Speechmatics 65.8% → 12.5%, Cartesia 52.9% → 16.8%, AssemblyAI 48.3% → 15.1%. The dataset is not named in the snippet. The raw WERs are far above Dawn Chorus's 21.9–30.9%, so this is a harder set. — [VF 2.1 blog (snippet)](https://ai-coustics.com/blog/quail-voice-focus-2.1)
- "Across AssemblyAI, Deepgram, Soniox, Mistral, Cartesia, Gladia, Speechmatics and Gradium, Voice Focus 2.2 reduces WERs by up to 84%." — [ai-coustics benchmarks page (snippet)](https://ai-coustics.com/benchmarks-quantitative)

**Quail (STT / Multi Speaker) (vendor)**
- 10–25% relative WER reduction on English and German across Deepgram, Cartesia, Gladia, AssemblyAI and ElevenLabs, on an internal in-the-wild dataset ("several hours… diverse noises, rooms, speaker distances, recording devices, and transmission chains"). The post claims it outperforms Krisp "by several percentage points on challenging audio" and promises an open-source version of the dataset. — [Meet Quail: Improving transcription (snippet)](https://ai-coustics.com/blog/quail-stt-asr-transcription)
- Against NVIDIA Maxine BNR and Krisp NC, Quail Multi Speaker "was the only model that reduced Word Error Rate under background noise", with up to about 25% relative WER reduction on German. On English competing speech, Voice Focus cut WER by 4.23 pp at full intensity and by 6.96 pp at its optimal 0.75 setting. Maxine showed no reliable effect, and Krisp NC *raised* WER by over 10 pp. The page also compares against Krisp BVC and BVC-telephony on two datasets. — [ai-coustics benchmarks (snippets)](https://ai-coustics.com/benchmarks-quantitative)

**VAD (vendor)**
- VAD Voice Focus 2.0 primary-speaker detection accuracy: **92.4%**, versus 86.5% for VF enhancement followed by a standard VAD and 71.0% for a standard VAD alone. False-positive rates: **5.5% / 12% / 28.5%**. — [VAD Voice Focus 2.0 blog / VAD docs (snippet)](https://ai-coustics.com/blog/vad-voice-focus-2.0)
- VAD 2.1 against Silero on a drive-thru dataset: recall 0.48 → 0.83 and accuracy 0.67 → 0.82. The snippet wording is garbled, but the direction is that ai-coustics' model beats Silero. The Quail VAD reportedly "cuts false triggers by up to 80%" and was evaluated on MSDWild. — [ai-coustics VAD page / blog (snippets)](https://ai-coustics.com/vad). ai-coustics has published a Hugging Face dataset `ai-coustics/aic_drive_thru_intercom_en`. — [HF (listing snippet)](https://huggingface.co/datasets/ai-coustics/aic_drive_thru_intercom_en)

**Independent or third-party evidence**
- An independent review aggregator calls the WER reductions "vendor-reported" and says the "benchmarks are largely vendor-reported and need independent validation". — [aiquiks review (snippet)](https://aiquiks.com/ai-tools/ai-coustics)
- Recho Inc.'s arXiv paper "Foreground Voice Activity Detection" (2609.19856, Sept 2026) defines foreground as "sustained presence rather than instantaneous loudness". It claims its Mamba-FVAD "outperforms commercial VADs and enrollment-based speaker-aware systems in foreground selectivity… at 1–2 ms per-frame CPU latency" and introduces a BG-FAR metric. Whether ai-coustics' VAD Voice Focus is among the "commercial VADs" **could not be verified** (arXiv blocked). — [arXiv 2609.19856 (snippet)](https://arxiv.org/abs/2609.19856)
- Competitor context: Krisp launched VIVA 2.0 in May 2026 ("small, real-time models that improve WER, predict when users finish speaking, classify interruptions"). — [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)

### Inferences
- **Conflicts of interest.** The datasets are vendor-built and the enhancement levels are vendor-tuned (the English result is best at 0.75). The comparisons pit ai-coustics' ASR-tuned models against competitors' perceptual denoisers (Krisp NC, Maxine BNR), which are not designed for ASR. That flatters ai-coustics. The Krisp BVC comparisons, which are the fair head-to-head, were not retrievable in detail.
- The headline "up to 84%" is a best-case relative reduction on a background-speech-heavy set. The Dawn Chorus figure (≤43%, raw WER 22–31%) is the better prior for a realistic call mix.
- The gains come mostly from **fewer insertions** (background words being transcribed). That is exactly the TV and bystander problem. Deletions staying "relatively stable" is the vendor's claim, and backchannel deletions are where to test.
- Nemotron streaming ASR may react differently to enhanced audio than cloud APIs do; the docs themselves say different STT providers respond differently. Because Dawn Chorus is open, the user can run their own Nemotron evaluation on it. That is the cheapest independent check available.

### Gaps
- No benchmarks on NVIDIA Nemotron, Parakeet or Riva, on Whisper, or on any self-hosted ASR.
- No comparison against LiveKit's BVC or Krisp VIVA 2.0 in agent turn-taking or barge-in metrics.
- No PESQ, DNSMOS or SI-SDR numbers for Voice Focus were found in the snippets.
- The Dawn Chorus license terms and Hugging Face dataset card were unreadable (huggingface.co blocked).
- No Hacker News or Reddit threads with hands-on reports were found.

---

## 3. Latency, frame sizes, compute, model sizes, sample rates, platform support; the VAD family and Tyto

### Takeaway
All models run on CPU. The native library is a self-contained ~8.5 MB binary with no CUDA and no ONNX dependency, so there is **no GPU path**. The vendor quotes about 30 ms end-to-end latency for Voice Focus 2.1 S/L and Rook, at 8 or 16 kHz for Voice Focus (48 kHz builds exist too). Voice Focus 2.1 S is "10× smaller" than 2.0, and 2.1 L uses 25% less compute than 2.0. Parameter counts, MACs and real-time factors are not published. Wheels exist for macOS arm64 and Linux x86_64/aarch64.

### Cited Findings
**Latency and compute (vendor)**
- VF 2.1: "Both models run in real time on CPU with an end-to-end latency of 30ms, work at 8kHz as well as 16 kHz." VF 2.1 S "is 10x smaller than Voice Focus 2.0 and still outperforms it". VF 2.1 L gives the best quality "at 25% lower compute than 2.0". Both deliver "up to 10x more concurrent streams at 30% safety margin, tested across three major AWS instance types." — [VF 2.1 blog (snippet)](https://ai-coustics.com/blog/quail-voice-focus-2.1)
- Rook: "30ms latency, requires no GPU, and has no ONNX dependency", using "less than 1% of the processing power of flagship models". — [Rook page / blog (snippet)](https://ai-coustics.com/rook). The July 2025 Quail launch tweet (today's Rook) claimed "Latency as low as 20ms" and "<1% compute of cloud models". — [ai-coustics on X](https://x.com/ai_coustics/status/1940395134073327881)
- Pricing-tier text lists "real-time processing (<30 ms)" for all tiers. — [ai-coustics pricing (snippet)](https://ai-coustics.com/pricing)

**SDK mechanics (verified from the aic-sdk 3.2.0 README and CHANGELOG)**
- `Model.get_optimal_sample_rate()` and `get_optimal_block_size(sr)` are exposed. The README's illustrative config prints `ProcessorConfig(sample_rate=48000, block_size=480)`, i.e. a 10 ms block. `variable_block_size=True` allows shorter calls, and 2.5.0 "Reduced the necessary output delay… when using allow_variable_frames=True". The real delay can be queried with `ProcessorContext.get_audio_delay()`. — [aic-sdk on PyPI](https://pypi.org/project/aic-sdk/), [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- "The trailing rate is the model's native sample rate; the SDK resamples other input rates internally". Output is "mono at the input sample rate". — [skills SKILL.md](https://github.com/ai-coustics/skills/blob/main/skills/ai-coustics-speech-enhancement/SKILL.md)
- `ProcessorAsync` runs on a Rayon thread pool sized to the number of logical cores. `AIC_NUM_THREADS` caps it. The package ships a `benchmark.py` example "that tests how many concurrent processing sessions your CPU can support". — [aic-sdk README on PyPI](https://pypi.org/project/aic-sdk/)
- One `Model` can be shared by many `Processor`s, one per stream, sharing weights (2.0.0). — [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)

**Platforms and binary (verified)**
- The aic-sdk 3.2.0 wheels cover CPython 3.10–3.14 on macOS arm64 and x86_64, manylinux2014 x86_64 and aarch64, and Windows amd64 and arm64. — [PyPI JSON](https://pypi.org/pypi/aic-sdk/json)
- Local inspection: `aic_sdk.cpython-311-x86_64-linux-gnu.so` is 8.5 MB and links only libc, libm, libpthread and libdl. It contains no CUDA, ONNX Runtime, CoreML or Metal strings. Models are separate `.aicmodel` files from `artifacts.ai-coustics.io` (since 2.0.0: "the C library no longer includes any models").
- Other SDKs exist: C (`aic-sdk-c`), C++ (`aic-sdk-cpp`), Rust (`aic-sdk-rs`) and Node/npm (`@ai-coustics/aic-sdk`). — [search listing](https://github.com/ai-coustics/aic-sdk-cpp/releases), [npm](https://www.npmjs.com/package/@ai-coustics/aic-sdk)
- The official LiveKit plugin 0.3.2 does **not** use aic-sdk. It ships its own 80 MB Rust/uniffi library with the four models embedded (verified, local inspection). The `aic-sdk 3.2.0` the user installed is therefore a separate code path from the plugin.

**VAD family**
- Since aic-sdk 3.0.0 (2026-08-06), VAD is a standalone `Vad` class that requires dedicated VAD models such as `vad-2.1-xxs-16khz`. The old energy-based VAD derived from the enhancer output was removed ("an approximation… A dedicated VAD model is trained for the task and is considerably more accurate"). `Sensitivity` is always a 0–1 probability threshold. `get_prediction_delay()` reports the lag, which is not applied to the audio. ai-coustics recommends running the VAD **on the original input, not the enhanced output**, in parallel on the same block. — [CHANGELOG 3.0.0](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- Parameters: `SpeechHoldDuration`, whose maximum rose to 300× the model window in 2.2.1 and whose default semantics changed in 2.1.0; `MinimumSpeechDuration`, 0–1 s (1.3.0); `raw_vad_probability()` (2.5.0). — [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- The skills doc's illustrative output for `vad-ms-2.1-xxs-16khz` reads "15 ms blocks, prediction delay 30 ms". Defaults come from the model file, for example sensitivity 0.6 and hold 0.1 s in that example. The doc labels these values as illustrative. — [VAD SKILL.md](https://github.com/ai-coustics/skills/blob/main/skills/ai-coustics-voice-activity-detection/SKILL.md)
- The ai-coustics LiveKit plugin defaults to 50 ms minimum speech and a 250 ms speech hold, "chosen so LiveKit's streaming turn detector gets the minimum silence it needs". — [livekit-plugins-aic-vad README](https://github.com/ai-coustics/livekit-plugins-aic-vad)
- VAD model generations: Quail VAD 2.0 (`quail-vad-2.0-xxs-16khz`) and Quail VF VAD 2.0 (`quail-vf-vad-2.0-s-16khz`) were replaced by the `vad-2.1-*` generation: "the 2.1 generation is a different model, so re-validate". — same README. VAD Voice Focus 2.0 was announced on 2026-07-27 (snippet, [VAD VF 2.0 blog](https://ai-coustics.com/blog/vad-voice-focus-2.0)).
- The official LiveKit plugin's `VAD` "relies on the accompanying… audio_enhancement FrameProcessor instead of performing its own inference" (`update_interval=0.032`). No dedicated `vad-*` model ID appears in its binary (verified, local inspection).

**Tyto (audio-risk analyzer, added in 2.4.0 on 2026-06-11)**
- Tyto scores 5 s windows and "predict[s] the likelihood of failure of downstream models (speech-to-text, VAD, turn-taking, speech-to-speech)". Fields: `risk_score`, `speaker_reverb`, `speaker_loudness`, `interfering_speech`, `noise`, `codec_degradation`, `packet_loss`. Tyto 1.1 is required from 3.1.0. — [aic-sdk README/CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)

### Inferences
- Linux prod can run on CPU only; a GPU gives no benefit. Capacity has to be measured with the bundled `benchmark.py`, because no RTF or parameter counts are published.
- End-to-end latency is roughly the ~30 ms model delay plus LiveKit's 10 ms frames. Stacking the VAD on enhanced audio would add the enhancer delay to the VAD delay, which is why the parallel-on-raw design matters for barge-in.
- The official LiveKit plugin's VAD appears to be the **enhancer-output-derived VAD**, the approach aic-sdk 3.0 removed as inaccurate. That is inferred from the source and binary strings, not documented. For primary-speaker turn detection the user should not rely on it. They should run a dedicated `vad-vf-*` model through `aic_sdk.Vad` directly or through the ai-coustics-maintained plugin.
- Tyto's `interfering_speech` score could be logged per call to measure how often background speech actually occurs in production.

### Gaps
- Exact block size, algorithmic latency and model size for `quail-vf-2.2-l/s-16khz` and `vad-vf-*` were not found: the artifacts manifest and docs model table were blocked. The SDK can query these locally with `get_optimal_block_size`, `get_audio_delay` and `get_prediction_delay`, but that needs downloaded models and a license key.
- No CPU real-time factor or streams-per-core numbers beyond "10× more concurrent streams" (relative, undisclosed AWS instances).
- No Apple Silicon-specific performance data.

---

## 4. Pricing and licensing: plans, free tier, offline entitlements, telemetry, and behavior when the license server is unreachable

### Takeaway
Standard SDK licenses are self-serve, usage-metered subscriptions: roughly $149/month for 100k minutes, falling to about $0.0012–0.0015 per extra minute on higher tiers. They require online activation and continuous usage reporting. Processing **stops after about 10 s if activation fails and after about 5 minutes if telemetry cannot be sent**. **Offline or air-gapped licenses** exist only on request or the Enterprise tier, which one snippet prices from about $2,000/month. Audio never leaves the host, but metadata does: license key, model, OS, audio minutes, and since 3.2.0 error reports.

### Cited Findings
- Tiers (snippet, pricing page): **Startup $149/mo, 100,000 min, $0.0015 per extra min; Pro $399/mo, 300,000 min, $0.00135; Growth $599/mo, 500,000 min, $0.0012.** "Monthly minute subscriptions range from $149 to $599, including all models." — [ai-coustics pricing (snippet)](https://ai-coustics.com/pricing), [developer platform blog (snippet)](https://ai-coustics.com/blog/developer-platform-api-playground-sdk)
- A different snippet of the same page lists "Enterprise starting at $2,000/month with 500,000 minutes per month". It says all tiers include "real-time processing (<30 ms)… on-prem SDK deployment, and all core SDK models", and that "The Enterprise tier… includes offline or air-gapped license options, custom SLAs, dedicated engineering support". — [ai-coustics pricing (snippet)](https://ai-coustics.com/pricing). **This conflicts** with the $599 "Growth" tier at the same 500k minutes. The two snippets may be different snapshots or tiers; this could not be resolved without the page.
- An older cloud API (file processing) price of €0.04/min was reported in a 2025 third-party listing. — [toolsforhumans (snippet)](https://www.toolsforhumans.ai/ai-tools/ai-coustics)
- Free tier: none appeared in the snippets. License keys are self-generated at developers.ai-coustics.com. — [aic-sdk README](https://pypi.org/project/aic-sdk/)
- Telemetry (docs/changelog snippets): "The SDK requires a constant internet connection, and if the SDK cannot be activated online, enhancement will stop after 10 seconds." "If telemetry data cannot be sent, enhancement will stop after 5 minutes." "If you cannot provide a constant internet connection, you can contact ai-coustics to obtain a special offline license that does not require telemetry." The reported signals are "license key, SDK version and wrapper type, model identifier in use, operating system and CPU architecture, aggregate audio time processed, and whether VAD is enabled… No audio, recordings, transcripts, or model features are ever transmitted." — [ai-coustics SDK changelog (snippet)](https://docs.ai-coustics.com/sdk/changelog), [telemetry glossary (snippet)](https://ai-coustics.com/glossary/telemetry)
- aic-sdk 3.2.0 (2026-09-07) added SDK-internal error reporting to ai-coustics' error tracking for failed session activations, failed usage reports and rejected bearer-token refreshes. Each report contains "the error class and message, the SDK version and wrapper, the model ID, the operating system, the CPU architecture, and the account the license was issued to. It contains no audio, no license key and no bearer token." It can be disabled with `DO_NOT_TRACK=1`, and "Licenses with an offline entitlement never report." — [CHANGELOG 3.2.0 (verified)](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)
- Other licensing mechanics (verified, CHANGELOG):
  - JWT license keys with `update_bearer_token()` for rotation without interrupting audio (2.3.0).
  - "License keys previously generated… will no longer work. New license keys must be generated" (2.0.0).
  - Optional OpenTelemetry metrics export via `AIC_SDK_OTEL_ENABLE` / `OtelConfig`, experimental since 2.1.2. Where these metrics go by default is not documented in the README.
- Licenses: the Python wrapper is Apache-2.0, and "The core C SDK is distributed under the proprietary AIC-SDK license." — [aic-sdk README](https://pypi.org/project/aic-sdk/). The official LiveKit plugin is proprietary ("SEE LICENSE IN https://livekit.io/legal/terms-of-service"; source headers read "Proprietary and confidential"). — [PyPI metadata (verified)](https://pypi.org/project/livekit-plugins-ai-coustics/)
- LiveKit Cloud path: the official plugin defaults to `Auth.livekit_cloud()`, which is "Use LiveKit Cloud for ai-coustics authentication and billing (default)". `Auth.ai_coustics_api(license_key=…)` is "Use your own ai-coustics credentials directly, bypassing LiveKit Cloud" (verified, local `auth.py`). LiveKit docs: "Provided you use LiveKit Cloud for your media transport, you can use any of the Krisp or ai-coustics models, whether you host your agents on LiveKit Cloud or self-host them". Noise suppression is included across LiveKit Cloud plans. — [LiveKit docs (snippet)](https://docs.livekit.io/transport/media/noise-cancellation/)
- The ai-coustics-maintained plugin states that "use of this package is billed separately through ai-coustics" and that "LiveKit Cloud authentication is not carried over". — [ai-coustics/livekit-plugins README](https://github.com/ai-coustics/livekit-plugins/blob/main/python/README.md)

### Inferences
- The effective standard price is about **$0.0012–0.0015 per audio minute** ($0.07–0.09 per hour of caller audio). The license budget matters less than the **licensing posture**. A self-hosted server running on a standard key stops enhancing within 10 s (no activation) or 5 minutes (no reporting) if the ai-coustics backend or egress fails. For production this is a **hard runtime dependency on ai-coustics' SaaS** unless the user buys an offline entitlement, which likely means the Enterprise tier.
- The "no caller audio to third parties" requirement is met, since only metadata leaves. Operators should still know that per-account usage and error metadata are sent, and set `DO_NOT_TRACK=1` for error reports. Usage reports themselves cannot be disabled without an offline license.
- The model CDN (`artifacts.ai-coustics.io`) is only needed at provisioning. Pinned `.aicmodel` files can be baked into images. Model-file versions changed several times in 2026 (v3 → v4 → v7), so an SDK upgrade forces a model re-download.

### Gaps
- The price of the offline or air-gapped entitlement and its terms (term length, audits, minute caps) were not retrievable.
- Whether a free or trial tier exists in September 2026 is unconfirmed.
- The exact grace behavior (5 min / 10 s) was quoted from a docs changelog snippet of unknown date. It could not be verified whether 3.x still uses these numbers.
- LiveKit Cloud's per-minute price for QUAIL_VF_L ("extra cost") was not retrievable.

---

## 5. Integrations and 2025–2026 release history (LiveKit, Pipecat, SDK versions, breaking changes)

### Takeaway
There are now **two competing LiveKit integrations** that share the same import path. One is LiveKit's official, proprietary `livekit-plugins-ai-coustics` (0.3.2 is the latest, with fixed embedded models and LiveKit Cloud or ai-coustics auth). The other is ai-coustics' own Apache-2.0 `ai-coustics-livekit-plugin` (0.2.0, 2026-09-14), built on aic-sdk ≥3.2 with any model ID, a dedicated VAD model and Tyto. Both of the user's versions (aic-sdk 3.2.0, plugin 0.3.2) are the **latest published** as of 2026-09-26. aic-sdk had four breaking majors or minors in 2026.

### Cited Findings
**aic-sdk (PyPI) release history, verified from [PyPI JSON](https://pypi.org/pypi/aic-sdk/json) and the [CHANGELOG](https://github.com/ai-coustics/aic-sdk-py/blob/main/CHANGELOG.md)**
| Version | Date | Changes |
|---|---|---|
| 0.5.3 → 1.0.x | Jul–Aug 2025 | Early releases |
| 1.1.0 | 2025-11-11 | VAD added (energy-based, on processor) |
| 1.2.0 | 2025-11-20 | `QUAIL_STT` |
| 1.3.0 | 2025-12-12 | STT L8/S16/S8, `QUAIL_VF_STT_L16`, `SPEECH_HOLD_DURATION` |
| **2.0.0** | 2026-01-15 | PyO3 rewrite; module renamed `aic` → `aic_sdk`; models moved out of the binary to the CDN; **new license keys required**; Quail-STT → Quail, Quail → Sparrow |
| 2.1.0 | 2026-02-27 | VF 2.0, V2 model files; adjustable enhancement level on all models; `VoiceGain` deprecated |
| 2.2.0 | 2026-04-23 | VF 2.1; VF 2.0 dropped; model file v3 |
| 2.3.0 | 2026-05-29 | `OtelConfig`, JWT bearer tokens, probability sensitivity for dedicated VAD; model file v4 |
| 2.4.0 | 2026-06-11 | Tyto analysis |
| 2.5.0 | 2026-06-23 | `raw_vad_probability()` |
| **3.0.0** | 2026-08-06 | **Mono-only APIs; standalone `Vad` with dedicated VAD models; energy VAD removed**; renamed errors and delay getters |
| 3.1.0 | 2026-08-10 | Model file v7; Tyto 1.1 |
| 3.1.1 / 3.2.0 | 2026-09-07 | Manifest cache with 30 s timeout; SDK error reporting (`DO_NOT_TRACK`) |

**Official LiveKit plugin `livekit-plugins-ai-coustics` (verified, [PyPI JSON](https://pypi.org/pypi/livekit-plugins-ai-coustics/json))**
- 0.1.10 (2026-02-05) … 0.2.15 (2026-05-22), 0.3.0 (2026-06-15), 0.3.1 (2026-08-21), **0.3.2 (2026-09-02, latest)**. Requires `livekit>=1.0.25`, `livekit-agents>=1.4.2`. Repo: [livekit/plugins-ai-coustics-python](https://github.com/livekit/plugins-ai-coustics-python). A Node version also exists: [livekit/plugins-ai-coustics-node](https://github.com/livekit/plugins-ai-coustics-node).

**ai-coustics-maintained plugin `ai-coustics-livekit-plugin` (verified)**
- 0.1.0 (2026-08-12) and **0.2.0 (2026-09-14)**. Apache-2.0. Requires `aic-sdk>=3.2.0,<4`, `livekit-agents>=1.4.2,<2`, and `opentelemetry-api`. — [PyPI JSON](https://pypi.org/pypi/ai-coustics-livekit-plugin/json)
- It provides `Processor`, `VAD(model=…)` with `vad.processor`, `FrameProcessorChain(vad.processor, analyzer.collector, processor)` and `Analyzer`. "`vad.processor` must be installed in the `noise_cancellation` path… Put it first in the chain so it runs on original microphone audio before enhancement." "Do not install both packages because they provide the same `livekit.plugins.ai_coustics` import path." It "does not support `python -m livekit.agents download-files`". The official plugin "is the recommended integration path for most applications… stronger stability guarantees", while this one offers "early access… Some of those capabilities may be experimental". — [ai-coustics/livekit-plugins python/README](https://github.com/ai-coustics/livekit-plugins/blob/main/python/README.md)
- The standalone `livekit-plugins-aic-vad` (Quail VAD 2.0 / VF VAD 2.0, `aic-sdk>=2.5.0`, `livekit-agents>=1.6.5`) is **deprecated and archived** in favor of the plugin above. — [README](https://github.com/ai-coustics/livekit-plugins-aic-vad)

**Pipecat (verified)**
- `pipecat-ai` 1.12.0 (2026-09-26): the `aic` extra requires `aic-sdk~=3.1.0`. — [PyPI JSON](https://pypi.org/pypi/pipecat-ai/json)
- `AICFilter` (`license_key`, `model_id` or `model_path`, `enhancement_level`) with a shared `AICModelManager`. — [aic_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/aic_filter.py)
- `AICQuailVADAnalyzer` now defaults to `vad-2.1-xxs-16khz` ("the old default, `quail-vad-2.0-xxs-16khz`, does not work with aic-sdk 3.0"). `AICVADAnalyzer` / `create_vad_analyzer()` were removed. — [Pipecat CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md)

**Other integrations and assets**
- Official Agent Skills repo for coding agents: [ai-coustics/skills](https://github.com/ai-coustics/skills).
- Hugging Face demo space for VF 2.1: [ai-coustics/VoiceFocus (listing)](https://huggingface.co/spaces/ai-coustics/VoiceFocus).
- An Elgato VST3 plug-in partnership (Oct 2025): [ai-coustics (snippet)](https://ai-coustics.com/2025/10/16/elgato-and-ai-coustics-launch-new-vst3-plug-in/).
- A PolyAI production-agents case study: [ai-coustics blog (listing)](https://ai-coustics.com/blog/polyai-production-grade-voice-agents).

### Inferences
- The user's current stack (official plugin 0.3.2 with `Auth.ai_coustics_api`) works on self-hosted LiveKit without LiveKit Cloud, but it is limited to the four embedded models and appears to use an enhancer-derived VAD. To get **VAD Voice Focus** (primary-speaker VAD for barge-in), newer models and Tyto, switch to `ai-coustics-livekit-plugin` 0.2.0 or call `aic_sdk` directly. That plugin is young (two releases, marked "experimental"), so pin versions.
- API churn is high: 2.0 renamed the module and invalidated keys, 3.0 removed multichannel and the energy VAD, and model-file versions went v3 → v4 → v7 in about five months. Budget for re-validation at each SDK bump.

### Gaps
- The ai-coustics-livekit-plugin CHANGELOG and the official plugin's release notes (GitHub) were not retrievable. The GitHub API and HTML were blocked; only raw files worked.
- Whether the official LiveKit plugin will move to dedicated VAD models is not stated.

---

## 6. Community feedback, independent opinions, and company background

### Takeaway
Public hands-on feedback is thin. It consists mainly of LiveKit community support threads about authorization errors and self-hosting, plus review aggregators noting that the benchmarks are vendor-reported. I found no substantive Hacker News or Reddit discussion. The company is a small, VC-backed Berlin startup (about $7.5M raised), with close ties to LiveKit and several ASR vendors.

### Cited Findings
- LiveKit community: "Unable to use ai_coustics in agents". A paid-account user got "Unable to authorize model use: Model use unauthorized", which suggests a feature gate or auth issue. — [community.livekit.io thread 832 (snippet)](https://community.livekit.io/t/unable-to-use-ai-coustics-in-agents/832). There is also a thread "AI Coustics VAD and noise cancellation – Support needed – Self Hosting"; its content could not be retrieved. — [thread 1551](https://community.livekit.io/t/ai-coustics-vad-and-noise-cancellation-support-needed/1551)
- A third-party GitHub issue, "Probar AICFilter (ai-coustics, 8 kHz nativo) detrás del bench" ("test AICFilter, ai-coustics, native 8 kHz, behind the bench"), shows a builder evaluating the 8 kHz model in Pipecat. Its content was not retrievable. — [jferreiros/vortex#137 (listing)](https://github.com/jferreiros/vortex/issues/137)
- Reviews: "benchmarks are largely vendor-reported and need independent validation", and the product is a "good fit for engineering teams that need an SDK and runtime they can embed into apps, services, or on-prem pipelines". — [aiquiks (snippet)](https://aiquiks.com/ai-tools/ai-coustics). A review at juststeveking.com exists but was blocked. — [JustSteveKing](https://www.juststeveking.com/reviews/ai-coustics-in-review/)
- Open-source alternative that builders cite for fully self-hosted LiveKit NC: `livekit-plugins-dtln` by Aloware ("no cloud API, no per-minute fees"). — [aloware/livekit-plugins-dtln](https://github.com/aloware/livekit-plugins-dtln)
- Company:
  - Founded in 2021 out of TU Berlin by Corvin Jaedicke and Fabian Seipel. — [Partech / press](https://partechpartners.com/news/berlin-based-aicoustics-raises-5m-seed-round-bringing-studio-quality-sound-to-voice-ai)
  - €1.6M pre-seed, April 2024, led by Connect Ventures. — [ai-coustics blog](https://ai-coustics.com/blog/company-updates-aicoustics-raises-funding)
  - €5M seed led by Partech. — [Partech](https://partechpartners.com/news/berlin-based-aicoustics-raises-5m-seed-round-bringing-studio-quality-sound-to-voice-ai)
  - About $7.5M total raised. — [CB Insights (snippet)](https://www.cbinsights.com/company/aiicoustics)

### Inferences
- The absence of independent WER or turn-taking evaluations means the user's own A/B test is the deciding evidence. Useful comparisons: Nemotron WER, insertion rate from TV or bystanders, backchannel recall, and false barge-in rate, with raw audio vs. QUAIL_VF_L at 0.5/0.75/1.0 vs. competitors, on Dawn Chorus plus their own recordings.
- The vendor's small size and fast API churn are a longevity and stability risk. The online-licensing kill-switch amplifies it: if the vendor's backend has problems, standard-license deployments degrade within minutes.

### Gaps
- No Reddit or Hacker News threads with hands-on experience were found.
- No independent blog posts from voice-agent builders with measured results were found (the only candidate review was blocked).
- No 2026 funding round or acquisition news was found. Whether a Series A happened in 2025–2026 is unknown.
