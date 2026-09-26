# Krisp VIVA voice isolation in LiveKit Agents 1.8.3 (`livekit-plugins-krisp`), compared with Pipecat, and a design for this repo (as of 2026-09-26)

**Scope and method.** Everything below is dated by package version. There are three kinds of statement:
- **[code]** means I read the code directly.
- **[probe]** means I ran it myself in the scratch venv.
- **[vendor]** means README or docs text.
- **Inferences** are only in the "Inferences" subsections.

**Sources.** Unless another URL is given, file paths are relative to these scratch downloads:
- `KP/<ver>/` = the unpacked wheels of **all 37 released versions** of `livekit-plugins-krisp`, downloaded from PyPI into `/tmp/claude-0/-home-user-VibeVoice-API/e889273f-ddd7-5345-b39f-0e17440a49dd/scratchpad/kpv/x/<ver>/livekit/plugins/krisp/`.
- `KI/` = `livekit-plugins-krisp-internal` 0.2.0, manylinux x86_64 wheel (`…/scratchpad/kpv/ix/livekit/plugins/krisp_internal/`).
- `LK/` = the livekit-agents 1.8.3 / livekit (rtc) 1.1.18 scratch venv (`…/scratchpad/lkvenv/lib/python3.11/site-packages/livekit/`).
- `PC/` = a pipecat clone at `2967e1c` (v1.12.0+3, 2026-09-26).
- `LKA/` = a livekit/agents `main` clone at `57b3227` (2026-09-25) plus full history (`…/scratchpad/lk-history`).

**Test scripts.** I installed plugin 0.4.3 and internal 0.2.0 into the scratch venv (not the repo) and ran them against a **fake `krisp_audio`**: `…/scratchpad/kpv/t/fake_license.py`, `cloud_probe*.py`, `cloud_bench.py`.

**What was blocked.**
- The proxy blocked docs.livekit.io, docs.pipecat.ai and krisp.ai.
- Direct reads of GitHub issues and PRs for livekit/agents and pipecat-ai/pipecat were refused (the repos are not attached to this session). Issue text comes from the GitHub search API, which returns issue bodies.
- The real `krisp_audio` wheel, a `.kef` model and a Krisp key were not available. License mode was therefore exercised only with a fake SDK.

---

## 1. `livekit-plugins-krisp` internals across all released versions

### Takeaway
There are four code generations:
- **0.1.1–0.2.5:** license-only. Frame sizes had to match exactly, otherwise `ValueError`.
- **0.2.6:** adds the LiveKit-Cloud backend and adaptive buffering.
- **0.2.7:** adds `voice_isolation()` / `voice_isolation_telephony()` and makes the proprietary internal wheel a hard import.
- **0.2.8:** default level changes to 75.

0.2.8 through 0.4.3 are **code-identical**; the later releases only bump the minimum livekit-agents version in lockstep.

For a self-hosted server, the working path is `krisp.voice_isolation(auth_provider=krisp.auth.krisp_license(...))`:
- It needs no room token. The `_on_credentials_updated` and `_on_stream_info_updated` hooks are inherited no-ops.
- It runs `krisp_audio.NcInt16` synchronously on the calling thread.
- It re-chunks input into 10 ms blocks.
- On a per-chunk exception it passes raw audio through.

The processor has no VAD, turn or interruption-prediction components.

### Cited Findings

**Release history and dependencies** [code, PyPI metadata of every wheel]

| Versions (dates) | Code hash* | What changed | Requires |
|---|---|---|---|
| 0.1.1 (2026-04-16) … 0.2.5 (2026-07-09), incl. 0.1.17rc1, 0.2.0rc1/rc2 | identical | Original PR [#4370](https://github.com/livekit/agents/pull/4370) by realgarik, merged 2026-04-13. Modules `krisp_instance.py` and `viva_filter.py`. License-only. | `livekit-agents>=1.5.3` rising in lockstep to `>=1.6.5`; `livekit>=1.0.23,<2`; `numpy` |
| 0.2.6 (2026-07-18) | new | PR [#5914](https://github.com/livekit/agents/pull/5914) "Add LiveKit cloud auth to krisp viva plugin" (lukasIO, merged 2026-07-13). Adds `auth.py` and `_krisp.py` (adaptive buffering), a facade, and `tests/test_krisp_frame_buffer.py`. Deletes `krisp_instance.py` and its public exports (`KrispSDKManager`, `KRISP_SAMPLE_RATES`, …). | adds `livekit-plugins-krisp-internal>=0.1.0` |
| 0.2.7 (2026-07-25) | new | PR [#6510](https://github.com/livekit/agents/pull/6510) adds the telephony mode: `VivaMode`, `voice_isolation()`, `voice_isolation_telephony()`. `viva_filter.py` now imports `livekit.plugins.krisp_internal` **at module import**. | `krisp-internal==0.2.0` |
| 0.2.8 (2026-08-03) | new | PR [#6640](https://github.com/livekit/agents/pull/6640) changes the default `noise_suppression_level` from 100 to **75** (docs fix [#6651](https://github.com/livekit/agents/pull/6651)). | same |
| 0.2.9 … 0.4.3 (2026-09-23) | = 0.2.8 | Version bumps only. 0.4.3 requires `livekit-agents>=1.8.3`, the same minimum the user's 1.8.3 has. | same |

\*Hash of all `.py` files except `version.py`. Sources: [PyPI JSON](https://pypi.org/pypi/livekit-plugins-krisp/json); `git log` of `LKA` (`livekit-plugins/livekit-plugins-krisp`); `main` is byte-identical to 0.4.3 ([source](https://github.com/livekit/agents/tree/main/livekit-plugins/livekit-plugins-krisp)).

**`livekit-plugins-krisp-internal`** is proprietary (LiveKit ToS; README: "bundles the Krisp VIVA SDK").
- Wheels are cp310-abi3 for macOS x86_64/arm64, manylinux_2_28 x86_64/aarch64 and win_amd64. 0.2.0 was released 2026-07-22, ~58–71 MB compressed and **106 MB unpacked** on Linux x86_64.
- It contains Python uniffi bindings over `libplugins_krisp_uniffi.so`, a Rust layer over the Krisp C++ SDK and onnxruntime.
- Sources: [PyPI](https://pypi.org/pypi/livekit-plugins-krisp-internal/json); `KI/` file listing.

**Public API in 0.4.3** [code: `KP/0.4.3/__init__.py`, `viva_filter.py`, `auth.py`]
- Exports: `voice_isolation(*, auth_provider=None, noise_suppression_level=75)`, `voice_isolation_telephony(...)`, `KrispVivaFilterFrameProcessor(*, mode=VivaMode.VOICE_ISOLATION, auth_provider=None, model_path=None, noise_suppression_level=75, frame_duration_ms=None, sample_rate=None)`, `auth.livekit_cloud` / `auth.krisp_license` (aliases of `LiveKitCloudAuthProvider` / `KrispLicenseAuthProvider`).
- `model_path`, `frame_duration_ms` and `sample_rate` on the facade are deprecated and emit a `DeprecationWarning`. `frame_duration_ms` still reaches the license backend (default 10) — `viva_filter.py` L238-258.
- Runtime controls: `enabled` and `noise_suppression_level` setters. There are also back-compat shims: `process()`, `enable()`, `disable()`, `close()`, and context-manager use (`viva_filter.py` L284-334).

**How the auth mode is chosen** [code: `viva_filter.py` L76-120]
1. An explicit `auth_provider` is used as given.
2. Otherwise, if the legacy `model_path=` argument is passed, it builds `KrispLicenseAuthProvider(model_path=…)`.
3. Otherwise, if **both** `KRISP_VIVA_SDK_LICENSE_KEY` and `KRISP_VIVA_FILTER_MODEL_PATH` are set, license mode is chosen.
4. Otherwise the **LiveKit Cloud** backend is used.

[probe] With only the model-path environment variable set, `voice_isolation()` silently picks the Cloud backend (`fake_license.py` step 11).

**`KrispLicenseAuthProvider(license_key=None, model_path=None)`** [code: `auth.py` L59-79]
- It falls back to the two environment variables.
- It validates that `model_path` exists and ends in `.kef` (`ValueError` / `FileNotFoundError`).
- It **accepts an empty license key** (`""`) — confirmed in the probe.
- The key is a plain attribute and does not appear in `repr` (probe).

**How the license backend loads `krisp_audio`** [code: `_krisp.py` L50-96]
- Import name `krisp_audio`, imported lazily in `_KrispLicenseSDKManager.acquire()`.
- It is **not** a dependency, and there is no version pin. When missing: `RuntimeError("krisp-audio is not installed. Install Krisp's wheel (pip install krisp-audio) …")`.
- The README says it is "proprietary, not on public PyPI. Obtain and install it separately from Krisp" ([PyPI README 0.4.3](https://pypi.org/project/livekit-plugins-krisp/0.4.3/)). `pypi.org/pypi/krisp-audio/json` and `/simple/krisp-audio/` both return 404 (checked 2026-09-26).
- Initialization: `krisp_audio.globalInit("", license_key, licensing_error_cb, log_cb, krisp_audio.LogLevel.Off)`. The callbacks log at `livekit.plugins.krisp` (licensing errors at ERROR, SDK logs at DEBUG, but the SDK log level is Off).
- The SDK version is logged via `getVersion()`.
- It is a process-wide singleton with a **reference count**; the license key is taken from the **first** acquirer.
- `release()` calls **`krisp_audio.globalDestroy()` when the count reaches 0** (L98-115). Release happens only in `__del__` (L345-358), not in `_close()`.

**Model selection** [code: `viva_filter.py` L123-164]
- In license mode `mode` is **not passed** to the backend, so `voice_isolation()` and `voice_isolation_telephony()` behave identically. The `.kef` file decides the model.
- Session config: `NcSessionConfig{inputSampleRate, inputFrameDuration=Fd10ms by default, outputSampleRate=input, modelInfo.path=.kef}` → `krisp_audio.NcInt16.create(cfg)` (`_krisp.py` L211-247).
- Supported rates: 8/16/24/32/44.1/48 kHz. Supported chunk sizes: 10/15/20/30/32 ms.

**Sample rate, frames, buffering and latency** [code: `_krisp.py` L249-315]
- A **16 kHz session is pre-created in the constructor** (the model is loaded then). If a frame arrives at another rate, the session is **recreated inside `_process`** — the model is reloaded on the audio path — and the buffers are reset.
- There is no resampling.
- Input samples accumulate in `_in_buf` and are processed in whole 10 ms chunks. `chunk_out` must have exactly the chunk length, otherwise the chunk input is used.
- Each call emits `min(input_len, ready)` samples and never zero-pads.

[probe] Measured with the fake SDK:

| Input frames | Output per frame | Chunks per frame |
|---|---|---|
| 16 kHz / 20 ms | 320 (same as input) | 2 × 160 |
| 24 kHz / 50 ms | 1200 (same as input) | 5 × 240, but the first frame triggers `NcInt16.create(24000)` inside `_process` |
| 16 kHz / 25 ms | 320, then 400, 400, … | constant 5 ms extra lag |
| 5 ms first frame | a **0-sample frame** | — |

So with frame sizes that are multiples of 10 ms the buffering adds **zero** latency. Only the model's own algorithmic delay remains; see the Cloud-backend measurement below.

**Channels and rates** [code/probe]
- Non-mono frames are passed through with a one-time warning.
- An unsupported rate (e.g. 22050) raises `ValueError` **out of `_process`**. The fake-SDK probe confirmed this.

**Threading** [code]
- There is no thread, executor or queue. `_process` calls `session.process(chunk, level)` synchronously.
- In a room it runs inside `rtc.AudioStream._run()` on the asyncio loop (`LK/rtc/audio_stream.py` L294-316).
- The only lock is the SDK manager's `threading.Lock`.

**Per-stream lifecycle** [code]
- `_close()` drops the session and the buffers but keeps the SDK reference. A later frame recreates the session lazily (probe: `close()` then `_process` → `NcInt16.create`).
- In 1.8.3, RoomIO creates the stream with `auto_close_noise_cancellation=False` (`LK/agents/voice/room_io/_input.py` L389). A directly passed processor instance is therefore never closed by RoomIO. Its session and state persist across track changes and are freed only when the object is garbage-collected (`__del__` → `release()`).

**Error handling** [code/probe]
- An exception in `session.process` is logged at ERROR ("Error processing frame") and the **raw chunk** is used.
- Wrong output size → WARNING and raw chunk.
- `enabled=False` → the same frame object is returned.
- Exceptions escaping `_process` (unsupported rate, session create failure) are caught by `rtc.AudioStream`, which logs a warning "Frame processing failed, passing through original frame" with `exc_info` **on every frame** (`audio_stream.py` L302-309).
- Net result: every failure mode is **raw passthrough, never silence**. The output frame is new and carries **no `userdata`** (probe: `{}`).
- Level setter: `int(max(0, min(100, value)))` truncates, e.g. 55.7 → 55. The level is passed to `session.process` as a Python **int** (probe).

**Logging, metrics, network (license mode)** [code]
- Only the `livekit.plugins.krisp` logger. No metrics, no telemetry, and no network calls in the plugin's Python.
- Whether `krisp_audio.globalInit` validates the key online is not visible (see §3).

**Cloud backend (`krisp_internal` 0.2.0)** [code: `KI/plugin.py`]
- `_process` returns the input unchanged until `_on_credentials_updated(token, url)` has been called (L97-98).
- It then lazily builds a native `KrispVivaFilter(KrispVivaFilterSettings(mode, sample_rate, frame_duration_ms=10, noise_suppression_level, credentials))`. On `FilterError` it logs and passes through, and **retries on the next frame** (L111-128). The logger has a 5 s throttling filter (`KI/log.py`).
- It keeps `userdata` (L145).
- The docstring says the blocking "authorize HTTP call runs on the audio thread".
- Symbol names in the native library name the bundled models `KRISP_VIVA_PRO_V1` and `KRISP_VIVA_TEL_V2`, plus DRM strings: "Model use unauthorized", `ServerSettings.enhancedNoiseCancellation`, `featureUsage`, `KRISP_VIVA`. [code: `strings` on `KI/libplugins_krisp_uniffi.so`]

**Cloud backend network traffic** [probe, `cloud_probe2.py`]
- Pointed at a local stub, the backend sent `GET {room_url}/settings` with `Authorization: Bearer <room JWT>`.
- It then sent `POST {room_url}/report` with JSON `{"featureUsage":{"feature":"KRISP_VIVA","roomName":…,"participantIdentity":…,"trackId":…,"timeRanges":[…]}}`.
- So on a self-hosted server it would contact **the user's own server host**.
- In the ~4 s probe the audio was modified by the model whether `/settings` returned 404 or 200. I did not test whether or when an authorization failure later disables it.
- **This is not a licensed configuration for a self-hosted server.** The README says the Cloud path "authenticates through LiveKit Cloud" and the wheel is under the LiveKit ToS. Do not rely on it.

**Cloud backend compute cost** [probe, `cloud_bench.py`, 4-vCPU Xeon @ 2.1 GHz container; bundled models, not a licensed `.kef`]
- Steady state: **CPU real-time factor 0.087–0.101** per stream (≈9–10 % of one core), with CPU time ≈ wall time. It runs on the calling thread; one extra native thread appeared.
- First `_process` in a process: **290–470 ms** (SDK init, model load, authorization). Later new sessions: 15–30 ms.
- The first output frame starts with **14–27 ms of zeros**, depending on model and rate (PRO 16k ≈ 14 ms, TEL 24k ≈ 27 ms). This is a rough indicator of the model's algorithmic delay.
- `import livekit.plugins.krisp` takes **~1.25 s** because it loads the internal `.so`. Process maxrss is ~309 MB with both models loaded.

**No VAD, turn or interruption-prediction components** [code]
- Every version ships only the filter modules.
- PR #4370's description mentions "turn detection capability", but the released 0.1.1 contains only `krisp_instance.py` and `viva_filter.py` ([PR #4370](https://github.com/livekit/agents/pull/4370); `KP/0.1.1/`).

**0.1.x–0.2.5 behaviour, for reference** [code: `KP/0.1.1/viva_filter.py` L201-262]
- `_process` **raised `ValueError`** on a sample-rate mismatch or when `samples_per_channel != rate*frame_ms/1000`.
- The 0.1.x README therefore told users to set `AudioInputOptions(sample_rate=16000, frame_size_ms=10)`. With RoomIO defaults (24 kHz / 50 ms) every frame would have passed through raw with a warning.
- Default level was 100.

**Official standalone example** [vendor]
- `krisp_minimal_example.py` says: "Because this script runs outside an agent context, it cannot use the default LiveKitCloudAuthProvider (that path needs the framework to push the room's JWT into the FrameProcessor at runtime). It uses KrispLicenseAuthProvider". It then calls `processor.process(frame)` on hand-made frames.
- Source: [LKA examples](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-krisp/examples/krisp_minimal_example.py).
- LiveKit's `basic_agent.py` comment changed from `noise_cancellation.BVC()` to `krisp.KrispVivaFilterFrameProcessor()` in #5914 ([commit 69983cde](https://github.com/livekit/agents/commit/69983cde294cd6f4300ea8262317828c9feefce2)).

**LiveKit-side hooks** [code: `LK/rtc/frame_processor.py` L10-37; `LK/rtc/track.py` L52-103]
- `FrameProcessor` requires `enabled`, `_process` and `_close`.
- `_on_stream_info_updated`, `_on_stream_info_cleared`, `_on_credentials_updated` and `_on_credentials_cleared` are **no-op defaults**. The track pushes `room._token` and `room._server_url` into them on registration and on token refresh.
- The facade forwards only `_on_credentials_updated` and `_on_stream_info_updated`, so license mode needs neither.

**Plugin registration** [code]
- The plugin calls `Plugin.register_plugin(KrispPlugin())` at import.
- In 1.8.3 `register_plugin` raises `RuntimeError("Plugins must be registered on the main thread")` off the main thread (`LK/agents/plugin.py` L31-33).

### Inferences
- Use **0.4.3**, the exact lockstep with 1.8.3. Any version from 0.2.8 on has the same code; 0.1.x–0.2.5 should be avoided because of the strict frame-size failures.
- Always pass `auth_provider=krisp.auth.krisp_license(...)` explicitly, and make the repo check that the key is non-empty. Relying on the environment auto-selection can silently fall back to the Cloud backend: without credentials that is raw passthrough, and with self-hosted credentials it contacts `/settings` and `/report` on the server.
- Even in license mode the internal proprietary wheel (106 MB, LiveKit ToS) must be installed and is imported. That matters for licensing review and image size.
- Keep the input at 16 kHz and in multiples of 10 ms. The session is then pre-created off the audio path, and output length equals input length (no extra latency, no 0-sample frames).
- The per-stream CPU of a licensed `.kef` is probably similar to the bundled models, ~10 % of a core, on the asyncio loop. That is acceptable for one caller per job process, but it counts against event-loop latency budgets.

### Gaps
- The real `krisp_audio` path (licensed `.kef`, real `globalInit`) could not be run. Everything about it is from code plus the fake SDK.
- It is unverified whether nanobind builds of `krisp_audio` (≥1.11/1.12) accept the Python **int** level the plugin passes. nanobind usually converts int to float implicitly, but untested; Pipecat casts it explicitly.
- Algorithmic latency and CPU of the user's licensed VI-pro/VI-tel `.kef` models were not measured. The cloud-backend numbers above are the only real measurement.
- The behaviour of the Cloud backend against a real self-hosted livekit-server over time was not tested (and should not be relied on).

---

## 2. Pipecat `KrispVivaFilter` for comparison (pipecat `main` 2967e1c ≈ v1.12.0, 2026-09-26)

### Takeaway
Pipecat drives the same public `krisp_audio` API: `NcSessionConfig` → `NcInt16`, 10 ms chunks. The differences:
- Pipecat defaults to level **100.0**, sent as a float on nanobind SDKs.
- Its environment variable for the key is `KRISP_VIVA_API_KEY`.
- It **never calls `globalDestroy`**, a change made after a production SIGSEGV report.
- It has a **one-shot TTS-detection gate at session start**, meant for phone call screening. It is not a per-turn echo gate.

### Cited Findings

**Constructor and environment variables**
- `KrispVivaFilter(model_path=None, frame_duration=10, noise_suppression_level=100.0, api_key="", tts_model_path=None, tts_threshold=0.5, tts_detection_timeout=3.0)`.
- Model from `KRISP_VIVA_FILTER_MODEL_PATH`, falling back to the deprecated `KRISP_VIVA_MODEL_PATH`.
- Key from `KRISP_VIVA_API_KEY`. TTS model from `KRISP_VIVA_TTS_MODEL_PATH`.
- Validates `.kef` and file existence.
- Source: [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py).
- Other Krisp environment variables in the docs: `KRISP_VIVA_TURN_MODEL_PATH`, `KRISP_VIVA_IP_MODEL_PATH`, `KRISP_VIVA_VAD_MODEL_PATH`. Example model files: `krisp-viva-vi-tel-v2.kef`, `krisp-viva-tp-v3.kef`, `krisp-viva-ip-v1.kef`, `krisp-viva-vad-v2.kef` — [krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx).

**Session and frames**
- `start(sample_rate)` acquires the SDK and creates `NcInt16` at the transport's rate with `frame_duration` (10 ms).
- `filter(audio)` appends to a bytearray, processes whole frames only, and returns `b""` until a full frame is buffered. The output can therefore be shorter than the input, and the remainder stays buffered.
- On nanobind SDKs it copies samples to a writable array.
- On exception it logs and returns the original audio (raw passthrough).
- `FilterEnableFrame` toggles filtering.
- Source: same file.

**Level handling**
- `float(level)` if the SDK is ≥1.11.0 (nanobind), else `int(level)` — `krisp_sdk_uses_nanobind_bindings()` in [krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py).
- Changelog 1.8.0 (2026-08-26): "Fixed Krisp VIVA support against SDK 1.11.0 and newer, which switched its Python bindings from pybind11 to nanobind… `noise_suppression_level` is now a float" (PR #5302) — [CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md).

**TTS-detection gate** (source: `krisp_viva_filter.py`)
- Active only if `tts_model_path` is set.
- Builds `TtsDetectionSessionConfig` → `TtsDetectorFloat.create`, and feeds it float32 frames (int16/32768).
- While the gate is active the audio is passed through **unfiltered**.
- NC turns on once TTS was detected and then absent for `_TTS_CLEARED_COOLDOWN = 0.5` s, or after `tts_detection_timeout` (3 s) with no TTS. After that "noise cancellation activates for the remainder of the session".
- The docstring calls it an "iPhone screening feature" standalone model.

**SDK manager**
- `globalInit("", key, license_cb, log_cb, LogLevel.Off)`; on `TypeError` it falls back to the old 3-argument signature. Only the first caller's key is used.
- Since Pipecat 1.8.0 `release()` "no longer calls `krisp_audio.globalDestroy()`", keeping the SDK up for the life of the process (PR #5411).
- Sources: [krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py); [CHANGELOG 1.8.0](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md).

**Where the filter runs**
- The transport filter runs before VAD and STT, awaited inline in the audio task, with no executor (`PC/src/pipecat/transports/base_input.py` L128-138, L283+; earlier note `integration_and_evaluation.md` §2).

**Pipecat's other Krisp components** (not in LiveKit)
- `KrispVivaVadAnalyzer` (`VadFloat`, float32 in → probability).
- `KrispVivaTurn` (`TtFloat.process(frame, is_speech, False)`, 20 ms frames, threshold 0.5).
- `KrispVivaIPUserTurnStartStrategy` (`IpFloat.process(frame, speech_active)`, 20 ms, threshold 0.5).
- Sources: `PC/src/pipecat/audio/vad/krisp_viva_vad.py`, `audio/turn/krisp_viva_turn.py`, `turns/user_start/krisp_viva_ip_user_turn_start_strategy.py`.

### Inferences
- The earlier note (`Огляд рішень voice isolation/krisp.md` §2) treated the TTS gate as a barge-in or echo safeguard. The code shows it is a **start-of-call gate** for call-screening TTS. For a WebRTC or SIP caller agent it is mostly irrelevant, and LiveKit has no equivalent.
- The LiveKit and Pipecat defaults differ (75 vs 100), so any A/B test should pin the level explicitly.

### Gaps
- docs.pipecat.ai was blocked; the docs repository sources were used instead.
- There is no Pipecat-published latency or CPU data for `KrispVivaFilter`.

---

## 3. The `krisp_audio` wheel: availability, platforms, API

### Takeaway
`krisp_audio` is available **only from Krisp's developer portal** (`sdk.krisp.ai`, "Server SDK" tab). It is not on PyPI, and none of the LiveKit or Pipecat CI installs it; their tests mock it. Wheel tags seen publicly:
- `krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl`
- `1.12.0 (cp312-abi3)`

A key is required from SDK v1.6.1. The Python API is small: `globalInit`, `getVersion`, `globalDestroy`, `ModelInfo`, `*SessionConfig`, and `*Int16`/`*Float` `.create(cfg)` then `.process(...)`.

### Cited Findings
- PyPI: `krisp-audio` and `krisp_audio` → 404 (JSON and simple index, checked 2026-09-26).
- The LiveKit plugin README says "proprietary, not on public PyPI… from Krisp" — [PyPI 0.4.3](https://pypi.org/project/livekit-plugins-krisp/0.4.3/).
- Portal steps: "Log in to the Krisp developer portal (https://sdk.krisp.ai/)… download the Python SDK… install the Python wheel file that corresponds to your platform… `krisp-viva-uar-python-sdk-1.8.0/dist/krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl`". Also: "The `KRISP_VIVA_API_KEY` is required for Krisp SDK v1.6.1 and later" — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx).
- A user reports "krisp_audio 1.12.0 (cp312-abi3)", nanobind-based, which "reject[s] read-only NumPy arrays and plain Python lists, and raise[s] a TypeError" — [pipecat#5413](https://github.com/pipecat-ai/pipecat/issues/5413) (2026-08-24).
- **Conflict:** Pipecat's code and changelog place the nanobind switch at **1.11.0** (`_NANOBIND_SDK_VERSION = (1, 11, 0)`); issue #5413 says 1.12.0.
- The segfault trace in [pipecat#5408](https://github.com/pipecat-ai/pipecat/issues/5408) shows the native library `libkrisp-audio-sdk.so.9` on Linux x86_64 (GKE) and says it was "reproduced locally on macOS arm64".
- Krisp's public sample `python/krisp_audio_test.py` (requirements `krisp_audio>=1.0.0`) uses:
  - `globalInit("")` (the old no-key form), `getVersion()` (major/minor/patch/build), `ModelInfo().path`
  - `NcSessionConfig{inputSampleRate, inputFrameDuration, outputSampleRate, modelInfo}`
  - `NcFloat.create` / `NcInt16.create`, then `session.process(frame, suppression_level)`, then `globalDestroy()`
  - Source: [krispai/Krisp-SDK-Sample-Apps](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/main/python/krisp_audio_test.py) (commit 2bc86c7, 2026-08-28).
- The same repository's native C++ samples cover Linux x64/arm64, macOS x64/arm64 and Windows against "Krisp SDK Desktop/Server v9.9+". The licensing form is `globalInit(L"", "", licensingErrorCallback, logCallback, LogLevel::Off)` behind `-DENABLE_LICENSING` — [native-cpp/src/wav-cli/main.cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/main/native-cpp/src/wav-cli/main.cpp).

**API calls used across LiveKit and Pipecat** [code]

| Area | Calls |
|---|---|
| Enums | `SamplingRate.Sr{8000,16000,24000,32000,44100,48000}Hz`, `FrameDuration.Fd{10,15,20,30,32}ms`, `LogLevel.Off` |
| Noise cancellation | `NcSessionConfig` / `NcInt16.create` / `NcFloat.create`; `process(ndarray, level)` returns an ndarray of the same length |
| VAD | `VadSessionConfig` / `VadFloat.create`; `process(float32)` returns a probability |
| Turn | `TtSessionConfig` / `TtFloat.create`; `process(frame, is_speech, False)` |
| Interruption prediction | `IpSessionConfig` / `IpFloat.create`; `process(frame, speech_active)` |
| TTS detection | `TtsDetectionSessionConfig` / `TtsDetectorFloat.create`; `process(float32)` returns a probability |

The native library underneath is `libkrisp-audio-sdk` (v9); its log entry `globalDestroy` was already listed above.

### Inferences
- The wheel is **cp312-only** (1.8.0 cp312-cp312, 1.12.0 cp312-abi3), so a **Python ≥3.12 virtualenv** is needed. The repo declares `>=3.10`, and the earlier scratch venv was 3.11.
- macOS arm64 is covered for development. Linux x86_64 is covered. Linux aarch64 has not been confirmed for the public wheel.

### Gaps
- The exact platform and Python matrix of current `krisp_audio` releases, whether `globalInit` validates or meters the key online (phone-home), offline licensing, and pricing are all unknown. The portal and krisp.ai were not accessible.
- There is no public type stub or API reference for `krisp_audio`. The table above is reconstructed from callers.

---

## 4. Integration design for this repo (all inference unless marked; design only, no code changed)

### Takeaway
Mirror `aic.py`:
- Add a `krisp.py` that builds `krisp.voice_isolation(auth_provider=krisp.auth.krisp_license(...))`.
- Add `AUDIO_ENHANCEMENT=krisp` plus `KRISP_*` settings, with the key held as `repr=False`.
- Wire it into `AudioInputOptions(sample_rate=16000, frame_size_ms=20, noise_cancellation=…)`.
- Reuse `enhance(enhancer, frame) = enhancer._process(frame)` in both replay tools. This works outside a room in license mode.
- Keep the SDK alive for the whole process with a closed "pin" processor.
- Test against a fake `krisp_audio`.

For E2 (raw audio to STT, isolated audio to VAD), leave `noise_cancellation=None` and wrap the VAD so that only the VAD stream sees Krisp output.

### Cited Findings (facts the design relies on)
- The repo pattern: `aic.build_enhancer` returns a FrameProcessor with non-Cloud auth; `aic.enhance()` calls `_process`; `agent.py` passes it only when `AUDIO_ENHANCEMENT=aic`; the tools take `--enhance none|aic` — `/home/user/VibeVoice-API/voice_agent/local_voice_agent/{aic.py,agent.py,tools/replay_stt.py,tools/vad_scores.py}`.
- The STT stream runs at 16 kHz: `nvidia.STT(sample_rate=16000)` is the default, and the recognize stream uses `sample_rate=stt._opts.sample_rate` — `LK/plugins/nvidia/stt.py` L50, L142.
- RoomIO defaults are 24 kHz / 50 ms. `frame_size_ms` is user-settable in 1.8.3. 50 ms frames caused Silero latency spikes in [agents#3894](https://github.com/livekit/agents/issues/3894).
- AGC is off when NC is passed directly but **on** with a selector — `LK/agents/voice/room_io/room_io.py` L127-141 (earlier note).
- `AudioRecognition` pushes the **same frame** to STT, VAD, the turn detector and interruption. The VAD path calls `stream = vad.stream()` and then `stream.push_frame(frame)` — `LK/agents/voice/audio_recognition.py` L747-775, L1882-1924.
- `VADStream` exposes `_input_ch`, `_event_ch` and `_main_task` — `LK/agents/vad.py` L98-215.
- Console mode bypasses `noise_cancellation` (legacy console CLI with the WebRTC APM) — earlier note `integration_and_evaluation.md` §1.
- The Krisp processor works standalone in license mode (official minimal example; [probe] `_on_credentials_updated` is a no-op and `_process` processes without any room).
- Upstream raw-audio tap: PR [#7269](https://github.com/livekit/agents/pull/7269) "feat: preserve raw input audio in frame userdata" (open, 2026-09-14). It would "Expose aligned raw input through `lk.audio.raw` and label Krisp output with `lk.audio.processing` (`denoised` or `isolated`)", and carries the warning "should not be merged until backend can handle the new channel". It is not in 1.8.3.

### Inferences — concrete design

**1. Dependencies (`voice_agent/pyproject.toml`)**
- Add the optional extra `krisp = ["livekit-plugins-krisp==0.4.3"]`. This pulls `livekit-plugins-krisp-internal==0.2.0`, a proprietary 106 MB dependency.
- `krisp_audio` cannot go in pyproject. Document a manual step: `uv pip install /secure/path/krisp_audio-<v>-cp312-abi3-<platform>.whl` in a **Python 3.12** venv.
- Never vendor the wheel or `.kef` files. Add `*.kef` and `krisp_audio-*.whl` to `.gitignore` next to the existing `.env`.

**2. `local_voice_agent/krisp.py`** (analogous to `aic.py`)
```python
"""Krisp VIVA voice isolation (livekit-plugins-krisp, license mode: own Krisp key + .kef, no LiveKit Cloud).
Audio stays in-process; mode (voice_isolation vs _telephony) is decided by the .kef, not by the factory."""
def build_enhancer(settings) -> rtc.FrameProcessor:
    from livekit.plugins import krisp          # registers a Plugin: import on the main thread (prewarm/module import)
    return krisp.voice_isolation(
        auth_provider=krisp.auth.krisp_license(license_key=_require_key(settings), model_path=settings.krisp_model_path),
        noise_suppression_level=settings.krisp_level)          # never rely on env auto-selection (silent Cloud fallback)
def pin_sdk(settings):                           # call in prewarm; keep in proc.userdata for process lifetime
    p = build_enhancer(settings); p.close(); return p   # SDK ref held until __del__ → globalDestroy never runs mid-job
def enhance(enhancer, frame): return enhancer._process(frame)   # same hook RoomIO uses; raw passthrough on per-chunk errors
def enhancer_description(settings): {"backend": "livekit-plugins-krisp (license)", "model_file": basename + sha256 of .kef,
    "level": ..., "krisp_audio_version": krisp_audio.getVersion() (major.minor.patch), "plugin": metadata.version(...)}   # never the key
def _require_key(s): raise ValueError("set KRISP_VIVA_SDK_LICENSE_KEY …") if not s.krisp_license_key
```
- The pin works because `_close()` drops the session but keeps the SDK reference, and `release()` → `globalDestroy()` only fires when the count hits 0. This mirrors Pipecat's fix for SIGSEGV [#5408](https://github.com/pipecat-ai/pipecat/issues/5408). [probe: with a pin alive, deleting a per-job processor did not call `globalDestroy`]
- The pin also validates key and model at prewarm (fail fast) and pays the one-time SDK-init cost off the call path.
- Create the real processor **per job in `entrypoint`**, not in prewarm: it holds per-stream buffers and model state.
- If Krisp VAD, turn or IP models are added later using `krisp_audio` directly, they must share the same SDK lifetime. Never call `globalInit` or `globalDestroy` a second time in the process.

**3. `settings.py`**
- `AUDIO_ENHANCEMENT: none|aic|krisp`.
- `krisp_license_key` from `KRISP_VIVA_SDK_LICENSE_KEY` (the plugin's own name), `field(repr=False)`.
- `krisp_model_path` from `KRISP_VIVA_FILTER_MODEL_PATH` (validate `.kef` and existence).
- `krisp_level` from `KRISP_NOISE_SUPPRESSION_LEVEL`, default 75 (the LiveKit default; Pipecat uses 100).
- Optional `krisp_model_path_telephony` for a per-participant selector.
- `audio_input_sample_rate=16000` and `audio_input_frame_ms=20` (validate `frame_ms % 10 == 0` when Krisp is on).
- `enhancement_route: all|vad` (E2).
- Keep the rule `VAD_BACKEND=aic_enhancer ⇒ AUDIO_ENHANCEMENT=aic`; Krisp sets no VAD flag.
- `.env.example`: commented placeholders only, e.g. `# KRISP_VIVA_SDK_LICENSE_KEY=...  # from sdk.krisp.ai; never commit`.

**4. `agent.py` wiring**
```python
if settings.audio_enhancement == "krisp" and settings.enhancement_route == "all":
    room_options = room_io.RoomOptions(audio_input=room_io.AudioInputOptions(
        sample_rate=16000, frame_size_ms=20,          # 16 kHz = Nemotron/Silero/EOT rate, 16k session pre-created; 20 ms = 2×10 ms chunks
        noise_cancellation=krisp.build_enhancer(settings)))
```
- **SIP vs WebRTC:** use a `NoiseCancellationSelector` that returns a VI-tel processor for SIP participants and VI-pro otherwise. Pass `auto_gain_control=False` explicitly, because a selector turns AGC on. In license mode the factory's `telephony` flag is ignored, so the choice must be made by `.kef` file.

**5. Replay tools** (`--enhance none|aic|krisp`)
- Add a small `enhancement.py` dispatcher: `build_enhancer(settings)`, `enhance()` and `description()` for `aic` or `krisp`.
- Use it in `replay_stt.main()` and `vad_scores.score()`. `score()` currently builds only `aic`.
- `_process` works outside a room in license mode: no token and no `_on_credentials_updated` are needed. In Cloud mode it would silently pass audio through (probe), which is another reason to force license mode.
- Constraints:
  - The WAV rate must be one of 8/16/24/32/44.1/48 kHz, otherwise `ValueError` is raised from `_process`. In the tools, fail fast and suggest `ffmpeg -ar 16000`.
  - `--frame-ms` must be a multiple of 10 (defaults 20 and 10 are fine).
  - The tools' tail padding keeps frames constant.
- Record `krisp_audio.getVersion()`, the plugin versions and the `.kef` sha256 in `*.meta.json`. Extend `_aic_versions` with `livekit-plugins-krisp`, `livekit-plugins-krisp-internal` and `krisp-audio`.

**6. E2 — raw to STT, isolated to VAD**
- Set `noise_cancellation=None`, so STT, the turn detector and interruption get raw audio.
- Pass the VAD as `IsolatedVAD(inner=aic.build_vad(settings), make_enhancer=lambda: krisp.build_enhancer(settings))`, an `agents.vad.VAD` subclass. Its `stream()` builds the inner stream and one Krisp processor per stream, then overrides the instance's `push_frame` to call `push(enhance(enh, frame))`. The repo already patches instance methods this way in `replay_stt.py`.
- Delegate `capabilities`, `model` (`"<inner>+krisp"`), `provider` and `min_silence_duration`.
- Properties: output length equals input for multiples of 10 ms, so VAD timestamps stay aligned apart from Krisp's ~15–25 ms algorithmic delay (bundled-model estimate). The same CPU cost stays on the event loop. The turn detector keeps raw audio.
- The wrapper **also works in console mode**, because the VAD is still used there, unlike `noise_cancellation`.
- Alternatives:
  - isolated audio to everything, with an STT wrapper that opens a second raw `rtc.AudioStream` on the track (more plumbing);
  - wait for upstream PR #7269's `lk.audio.raw`.
  - Note that the license processor returns frames without `userdata`, so any userdata-based tap must be added at the RoomIO level, as the PR does.

**7. Tests** (`tests/test_krisp.py`, following the `test_aic.py` fake-SDK pattern)
- `pytest.importorskip("livekit.plugins.krisp")`, since it needs the internal wheel and imports in ~1.25 s.
- A fixture puts a fake `krisp_audio` module into `sys.modules`. The fake needs:
  - `SamplingRate` / `FrameDuration` / `LogLevel` namespaces
  - `globalInit` / `globalDestroy` / `getVersion`
  - `ModelInfo`, `NcSessionConfig`
  - `NcInt16.create` returning a session whose `process(arr, level)` records dtype, writability and level type, and halves amplitude
  - It must reset the private `_KrispLicenseSDKManager` counters between tests.
- Cases:
  1. license mode is always chosen, even with only the model env var (`type(enh._inner).__name__ == "_KrispLicenseFrameProcessor"`);
  2. a missing key raises with the environment-variable name, and the key is absent from `repr(Settings)`;
  3. 16 kHz / 20 ms in gives the same length out, with two 160-sample `process` calls;
  4. a session `TypeError` gives output == input (documents fail-open, cf. pipecat#5413);
  5. the pin prevents `globalDestroy` when a per-job processor is deleted;
  6. `replay_stt` and `vad_scores` with `--enhance krisp` through `fake_riva`;
  7. E2: with a fake enhancer that zeroes frames, the VAD reports no speech while the STT still receives the original audio.
- An opt-in smoke test (`KRISP_SMOKE=1`) with the real wheel, `.kef` and key checks that output ≠ input on noisy speech. It should also confirm the **int level** works with the installed nanobind SDK.
- LiveKit's own hermetic test builds the processor with `object.__new__` and an identity session — a useful pattern ([tests/test_krisp_frame_buffer.py](https://github.com/livekit/agents/blob/main/tests/test_krisp_frame_buffer.py)).

**8. Mac development**
- Python 3.12 venv, the macOS arm64 `krisp_audio` wheel from the portal, and `livekit-plugins-krisp-internal` (a macOS 11 arm64 wheel exists).
- `console` mode will **not** apply `noise_cancellation`. Test room-mode Krisp with `dev` against a local self-hosted `livekit-server --dev`; license mode needs no Cloud. Or use the replay tools on WAVs.
- E2's VAD wrapper does apply in console mode, but console also runs WebRTC APM noise suppression, so results are not comparable with room mode.
- Import `livekit.plugins.krisp` on the main thread (module import or prewarm), not lazily inside worker threads.

---

## 5. Known issues (GitHub, as of 2026-09-26)

### Takeaway
No GitHub issue reports errors, latency or CPU problems specifically for `livekit-plugins-krisp` (searched livekit/agents and livekit/python-sdks). The relevant risks come from Pipecat's Krisp integration:
- SDK teardown **SIGSEGV** caused by `globalDestroy`; LiveKit's plugin still calls it.
- nanobind SDKs **silently disabling NC** when given read-only arrays or lists; LiveKit's license path passes writable int16 arrays but an int level.

### Cited Findings

**livekit/agents**
- [#5448](https://github.com/livekit/agents/issues/5448) (2026-04-14, closed 04-20): "AudioInputOptions.noise_cancellation: FrameProcessor killed by premature _close() in _close_stream() — processes zero frames". Title only. 1.8.3 passes `auto_close_noise_cancellation=False` (`LK/agents/voice/room_io/_input.py` L389).
- [#6033](https://github.com/livekit/agents/issues/6033) (open, 2026-06-09): self-hosted deployments "eventually fall back to VAD-based interruption handling". It asks for "Official Krisp VIVA Turn Prediction / Interruption Prediction integration".
- [PR #7269](https://github.com/livekit/agents/pull/7269) (open): raw-input userdata tap (§4).
- [PR #6477](https://github.com/livekit/agents/pull/6477) (open, 2026-07-18): "Add livekit-plugins-rnnoise (OSS self-hosted noise cancellation)".
- [PR #5235](https://github.com/livekit/agents/pull/5235) (closed 2026-03-26): "Clarify that official noise cancellation filters require LiveKit Cloud". Title only.
- Earlier NC issues: [#3894](https://github.com/livekit/agents/issues/3894) (50 ms frames → Silero latency spikes) and [#4369](https://github.com/livekit/agents/issues/4369) (BVC "failed to initialize the audio filter").
- [livekit/python-sdks](https://github.com/livekit/python-sdks/issues): a search for FrameProcessor/Krisp found no matching issues.

**pipecat-ai/pipecat**
- [#5408](https://github.com/pipecat-ai/pipecat/issues/5408) (2026-08-23, closed 08-25): "SIGSEGV in libkrisp-audio-sdk on pipeline teardown". The report says it happened "10–15×/day, always within ~0.5 s of call teardown". The cause: `globalDestroy()` ran while native work was in flight. "The Krisp SDK contract expects one globalInit/globalDestroy per process, with all sessions destroyed and no process() in flight before destroy." The fix was PR #5411: never call `globalDestroy`.
- [#5413](https://github.com/pipecat-ai/pipecat/issues/5413) (2026-08-24, closed same day): with krisp_audio 1.12.0, `np.frombuffer` read-only arrays make `session.process` fail. The filter "catches the exception and returns the original audio. So noise cancellation is silently disabled — no crash, no warning". Turn and IP fail on `.tolist()` input.
- [#4994](https://github.com/pipecat-ai/pipecat/issues/4994) (2026-07-09, closed): on Pipecat Cloud the IP `.kef` was not provisioned; only the voice-isolation filter was. Title only.
- [#2507](https://github.com/pipecat-ai/pipecat/issues/2507) (2025-08-26, closed): "Krisp integration guide is not accurate". Title only.

**Code check against these issues** [code/probe]
- LiveKit 0.4.3 license path:
  - `np.concatenate` makes fresh buffers, so the chunks passed to `process` are **writable** `int16` arrays (probe: `flags.writeable=True`).
  - The level is passed as a Python `int` (probe).
  - `globalDestroy()` is still called when the last processor is garbage-collected (probe: refcount 0 → `globalDestroy`).
- Unlike Pipecat's VAD, LiveKit calls `process` synchronously on the loop thread, so there is no executor call left running during teardown.

### Inferences
- The SIGSEGV risk in LiveKit is lower than Pipecat's (no executor race), but it is not zero: `__del__` timing depends on GC, and other Krisp users might share the process. The prewarm pin in §4 removes it.
- A silently disabled filter (nanobind TypeError, any other per-chunk exception, Cloud fallback, unsupported rate) leaves the **raw** audio in place. It is hard to spot in A/B tests. The repo should log a counter of "processed vs passed-through" chunks, e.g. by wrapping the session, and assert output ≠ input in the smoke test.

### Gaps
- Direct reads of these GitHub issues and PRs were refused because the repositories are not attached to this session. Bodies for #5408, #5413, #6033 and #7269 came from the GitHub search API. #5448, #4994, #2507, #6477 and #5235 are known by title only.
- No reports from the community (forums, Slack) could be checked: community.livekit.io and docs were blocked.
