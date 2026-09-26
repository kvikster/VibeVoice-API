# NVIDIA Maxine AFX Speaker Focus in a LiveKit Agents 1.8.3 voice agent: existing integrations, integration design, and quality/latency/failure-mode evidence (as of 2026-09-26)

Method and source-quality notes (read first):
- **Fetched in full (verified):**
  - GitHub repos cloned into the scratchpad (`…/scratchpad/sf/`):
    - NVIDIA-Maxine/AFX-SDK-Samples, commit `1998010` dated 2026-09-16. This is where the official Speaker Focus sample code lives.
    - NVIDIA-Maxine/Maxine-AFX-SDK, last release commit 2025-06-07.
    - NVIDIA-Maxine/nim-clients, 2026-07-15.
    - NVIDIA-Maxine/Maxine-Telepresence.
    - PINTO0309/Maxine-env.
    - About 10 community AFX wrappers.
  - The PyPI JSON API.
  - LiveKit code: the `livekit-agents 1.8.3` / `livekit 1.1.18` wheels already unpacked in the scratch venv `…/scratchpad/lkvenv/lib/python3.11/site-packages/` (abbreviated `SP/`). They were installed there earlier, never into the repo.
- **Blocked by the egress proxy (403):** docs.nvidia.com, forums.developer.nvidia.com, developer.nvidia.com, blogs.nvidia.com, www.amax.com, web.archive.org, archive.org.
  - Facts from those sites come from **search-engine snippets** and are marked "(snippet)". Snippets can lose context.
- Scratchpad path prefix: `/tmp/claude-0/-home-user-VibeVoice-API/e889273f-ddd7-5345-b39f-0e17440a49dd/scratchpad/`.
- Everything labelled "Inference" or "Design proposal" is my own reasoning, not a sourced fact.

---

## Q1. Existing wrappers and integrations that use (or could be reused for) Speaker Focus

### Takeaway
As of Sept 2026, only two public codebases use Speaker Focus:
- **NVIDIA's own C++ samples** (AFX-SDK-Samples 2.0.0 → 3.0.0, Linux and Windows).
- **One unverified hobby PipeWire project**.

Nothing else was found:
- No Python binding for AFX, official or community, on PyPI.
- No LiveKit or Pipecat plugin.
- No GStreamer, FFmpeg or Jitsi/Janus/mediasoup integration.
- No Triton, DeepStream or Riva integration.
- No Maxine NIM for Speaker Focus.

Plenty of community wrappers exist for the AFX **denoiser** (OBS, .NET, Rust, Java, PipeWire, LADSPA, VST3, and one ctypesgen Python binding). The C API is identical for every effect: Speaker Focus differs only in the effect selector string and the `.trtpkg` model file. So these wrappers, the official `effects_delayed_streams_demo`, the BNR NIM gRPC contract and AMAX's AEC-daemon pattern are the reusable pieces.

### Cited Findings

**Official NVIDIA code (verified by clone)**
- The **NVIDIA-Maxine/AFX-SDK-Samples** history is: "2.0.0 release" 2025-10-29, "Add 2.1.0" 2026-03-16, "3.0.0 release" 2026-09-10, "N1X driver version fix" 2026-09-16. It contains:
  - `linux/effects_demo`, `linux/effects_delayed_streams_demo`, `linux/container`, `windows/apps/effects_demo`
  - sample inputs `linux/input_files/speaker_focus/{16k,48k}`
  - chain inputs `chaining/speaker_focus_{16k,48k}_denoiser_{16k,48k}`
  - Source: [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- The Speaker Focus sample inputs are 12.61 s (int16) and 2.33 s (float32) mono WAVs at 16 kHz and 48 kHz (header parse of the cloned files). They are covered by "NVIDIA Sample Data License.pdf" in the same folder, and are usable as a smoke test once the SDK is available — [input_files](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/main/linux/input_files)
- The Linux samples create the effect as follows:
  - `#if EFFECT_SPEAKER_FOCUS … NvAFX_CreateEffect(NVAFX_EFFECT_SPEAKER_FOCUS, &handle)` — `effects_demo.cpp` L387-391 and `effects_delayed_streams_demo.cpp` L487-491.
  - Chained selectors `NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_16k_DENOISER_16k` and `…_48k_DENOISER_48k` — L468-471 and L560-563.
  - Sources: [effects_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/linux/effects_demo/effects_demo.cpp); [effects_delayed_streams_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/linux/effects_delayed_streams_demo/effects_delayed_streams_demo.cpp)
- The Windows sample (3.0.0) has two Speaker Focus specifics:
  - The chained SF+denoiser config logs "Capabilities of **Denoiser Version 1** Effect will be applied along with Speaker Focus Effect in Chain" (L776-784). The chain therefore uses Denoiser v1, not the ASR-tuned v2.
  - "**Speaker Focus models don't work with Cuda Graphs. Hence disabling them.**" The sample then sets `NVAFX_PARAM_DISABLE_CUDA_GRAPH` = {1,1} (L801-805).
  - Source: [windows effects_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/windows/apps/effects_demo/effects_demo.cpp)
- The Windows scripts README lists `speaker_focus - Input SR: 16k/48k - Output SR: 16k/48k` and chains "speaker_focus (16k->16k) + denoiser (16k->16k)" and "(48k->48k)". There is **no chain of superres 8k→16k with Speaker Focus**; superres 8k→16k chains exist only with denoiser/dereverb — [scripts/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/main/windows/apps/effects_demo/scripts/README.md)
- The Linux `run_effect.sh` (3.0.0) shows how the SDK expects to be run:
  - `["speaker_focus"]="16 48"` (L57).
  - GPU map (L35-48): a100/a30→sm_80; a2/a10/a16/a40→sm_86; t4→sm_75; v100→sm_70; l4/l40→sm_89; h100→sm_90; b100/b200→sm_100; rtx_pro_6000→sm_120.
  - GPU architecture is auto-detected from compute capability (L149).
  - Models load from `features/<effect>/models/sm_XX/<effect>_<sr>k.trtpkg` (per-architecture TensorRT packages).
  - `-f` frame size "10/20ms [default=10]" (L89).
  - `-b` batch size "[default=1, max=1024]" (L87).
  - Studio Voice "supports only 1 batch size" (L114). Speaker Focus is *not* listed there.
  - Source: [run_effect.sh](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/linux/effects_demo/run_effect.sh)
- The Linux `effects_demo` has a `real_time` config flag. It "simulated the input data rate of a mic" by sleeping to frame cadence, and prints "Processing time … secs processing time per sec of audio" (L51, L316, L882-897). This is a ready-made RTF probe for Speaker Focus at batch N on the target GPU — [effects_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/linux/effects_demo/effects_demo.cpp)
- The Linux sample container `linux/container/Dockerfile` is `FROM ubuntu:20.04`. It "will use the driver installed on the host system (via Nvidia Container Toolkit)", and the SDK sits at `/opt/nvidia/Audio_Effects_SDK` — [container README](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/main/linux/container/README.md)
- The public API repo **NVIDIA-Maxine/Maxine-AFX-SDK** (last commit "1.3.0-release", 2025-06-07) contains `nvAudioEffects.h` with:
  - Effect selectors (L222-237): **only** denoiser, dereverb, dereverb_denoiser, aec, superres and the superres chains. There is no Speaker Focus selector; the Speaker Focus headers ship only inside the NGC SDK packages.
  - Parameters (L242-271): `NVAFX_PARAM_NUM_STREAMS`, `USE_DEFAULT_GPU`, `USER_CUDA_CONTEXT`, `DISABLE_CUDA_GRAPH`, `ENABLE_VAD`, `INTENSITY_RATIO`.
  - `NvAFX_Run(effect, const float** input, float** output, unsigned num_input_samples, unsigned num_input_channels)`, which expects float32 in [-1, 1] (L180-206).
  - Its README lists five effects: denoise, dereverb, dereverb+denoise, AEC, superres.
  - Source: [Maxine-AFX-SDK](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK)
- **Maxine NIMs** (nim-clients, last commit 2026-07-15; "BNR - Update to v2.0.0" 2026-05-28): grep finds **no "speaker focus"** anywhere.
  - The BNR NIM gRPC contract is `service BNR { rpc EnhanceAudio(stream EnhanceAudioRequest) returns (stream EnhanceAudioResponse) }`. It carries raw float32 bytes plus an `EnhanceAudioConfig{intensity_ratio}`.
  - The Python client's streaming mode sends "10ms" chunks and prints "Average latency per request" (`bnr/scripts/bnr.py` L79-102, L305-308).
  - Source: [nim-clients/bnr](https://github.com/NVIDIA-Maxine/nim-clients/tree/main/bnr)
- NVIDIA-Maxine/Maxine-Telepresence embeds AFX for acoustic echo cancellation (`src/Modules/AudioModule/AcousticEchoCanceller.cpp`); it has no Speaker Focus — [Maxine-Telepresence](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- Early Access download (snippet): Early Access features must be named explicitly, e.g. `./download_features.sh --effects …,speaker_focus-16k,speaker_focus-48k` — [AFX Install (Linux)](https://docs.nvidia.com/maxine/afx/latest/LinuxAFXSDK/InstallTheAFXSDK.html); [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- Linux SDK access gate (third-party doc, 2026-06-29/30): "If the page shows 'Subscribe to get access' or redirects to 'Contact an NVIDIA AI Enterprise Sales Representative', you do not currently have SDK download access" to the NGC Linux Audio Effects SDK collection — [tsuchim/nvafx-audio-cli docs/linux.md](https://github.com/tsuchim/nvafx-audio-cli/blob/main/docs/linux.md)

**Code search results (GitHub, run 2026-09-26)**
- `NVAFX_EFFECT_SPEAKER_FOCUS` → 6 files in total: the AFX-SDK-Samples (Linux + Windows) and Darudas/maxine-pipewire.
- `"speaker_focus" trtpkg` → only the AFX-SDK-Samples scripts.
- `maxine livekit` (Python) → 0; `maxine pipecat` (Python) → 0; `"nvAudioEffects" pybind11 OR ctypes OR cffi` → 0; GStreamer/nvafx → 0.
- Source: GitHub code search via API, no stable URL; reproduce at [github.com/search?type=code&q=NVAFX_EFFECT_SPEAKER_FOCUS](https://github.com/search?type=code&q=NVAFX_EFFECT_SPEAKER_FOCUS)
- `NvAFX_CreateEffect` → 153 hits, all denoiser/dereverb/AEC uses:
  - OBS Studio `plugins/nv-filters/nvidia-audiofx-filter.c` and its many forks
  - .NET: NightVsKnight/NvMaxineSdkDotNet (updated 2026-09-04), roman-miniailov/NvidiaMaxineNet, trackdubllc/Trackdub
  - Rust: loganintech/nvafx_rs, UMCEKO/hush, Haor/Echoless, RinLogs/nv-maxine-vst3 (VST3, 2026-08), lxe/iqhub
  - Java: USS-Shenzhou/Channel
  - C/C++ Linux: theCarlG/pw-nvidia-denoiser, londospark/broadcast (LADSPA, 2026-09-10), arzvaak/linux-broadcast (2026-08-23), ymmyk/nv-broadcast-linux, mexicantexan/studiocast, aethersdr/AetherSDR, tsuchim/nvafx-audio-cli
  - A grep of 7 of these cloned repos found **no Speaker Focus** references. Examples: [OBS nv-filters](https://github.com/obsproject/obs-studio/tree/master/plugins/nv-filters); [NvMaxineSdkDotNet](https://github.com/NightVsKnight/NvMaxineSdkDotNet)
- **The only Python AFX binding found:** MTJOBHUNTING/AutoKirinukiVideo (May 2023). It is a ctypesgen-generated `nvAudioEffects.py` plus an `NvAFX` class that calls `NvAFX_CreateEffect(NVAFX_EFFECT_DENOISER, byref(handle))` with 160 samples per frame at 16 kHz, for offline Windows denoising — [nvafx.py](https://github.com/MTJOBHUNTING/AutoKirinukiVideo/blob/main/src-pywebview/autoedit/nvafx.py)
- **PyPI** (checked 2026-09-26): `nvafx`, `pynvafx`, `py-nvafx`, `nvidia-afx`, `nvidia-maxine`, `maxine-afx`, `nv-afx`, `pymaxine`, `nvaudioeffects`, `nvidia-audio-effects`, `livekit-plugins-maxine` and `pipecat-maxine` all return 404. `maxine` exists but is an unrelated LLM-agent package ("Multifunctional Agent with eXceptional Intelligence…", 0.1.1) — [PyPI JSON API](https://pypi.org/pypi/maxine/json)

**Community project that claims Speaker Focus (low reliability)**
- **Darudas/maxine-pipewire** ("NVIDIA Broadcast for Linux via Maxine SDK + PipeWire") was created 2026-03-21. All 4 commits are dated 2026-03-22, and it has 0 stars. Its `doc/EFFECTS.md` claims Speaker Focus has "Latency ~10 ms", "GPU Load Low–Medium (~3–7%)" and an intensity 0.0–1.0 control.
- The project contradicts itself:
  - Its own registry sets `.has_intensity = false` for speaker-focus (`src/maxine_effect_registry.c` L133-150).
  - Its hand-written header defines the chain as `NVAFX_CHAINED_EFFECT_DENOISER_16k_SPEAKER_FOCUS_16k "denoiser16k_speaker_focus16k"`, the opposite order to NVIDIA's `NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_16k_DENOISER_16k`.
  - Source: [maxine-pipewire](https://github.com/Darudas/maxine-pipewire)
- Treat its numbers as unverified; they look unmeasured.

**Useful non-Speaker-Focus integration precedents**
- **PINTO0309/Maxine-env** (2024): runs the *Linux* AFX SDK in `nvcr.io/nvidia/tensorrt:22.11-py3` (CUDA 11.8, TensorRT 8.5.1) on a **GeForce RTX 3070**, by adding `["rtx3070"]="sm_86"` to `run_effect.sh`'s gpu_map — [Maxine-env README](https://github.com/PINTO0309/Maxine-env)
- **arzvaak/linux-broadcast** (2026-08) maps GeForce generations to the datacenter model directories: RTX 20→sm_75 (T4), RTX 30→sm_86 (A10), RTX 40→sm_89 (L40), RTX 50→sm_120 (RTX PRO 6000). It warns this does "not imply official GeForce support from NVIDIA"; the RTX 40 bundle was hardware-probed on an RTX 4080 — [linux-broadcast README](https://github.com/arzvaak/linux-broadcast)
- **aethersdr/AetherSDR** `docs/nvidia-bnr.md` (current 2026-09) runs the AFX denoiser in-process on Linux and Windows.
  - It **removed** an earlier "Service (NIM)" gRPC backend in favour of the local path.
  - Linux runtime packaging: CUDA libs come from NVIDIA's PyPI wheels; the AFX libs, TensorRT and the per-architecture model form "~335 MB for sm_89"; the total one-time download is "~1.2 GB".
  - Licensing as the authors describe it: SDK under the "NVIDIA Software License Agreement + Product-Specific Terms for NVIDIA AI Products"; model under the "NVIDIA Community Model License"; "licensed for use on NVIDIA RTX / GeForce RTX GPUs on a single-user PC/workstation".
  - Source: [AetherSDR nvidia-bnr.md](https://github.com/aethersdr/AetherSDR/blob/main/docs/nvidia-bnr.md)
- **AMAX Engineering** (blog series, ~Mar 2026; snippets):
  - Maxine runs as "a proxy-style architecture that sits between audio capture clients and the Riva ASR service".
  - A Windows Python client streams "paired 10 ms frames" over gRPC to a Linux C++ "Maxine AEC Daemon".
  - The daemon "processes AEC on every 10ms frame, then accumulates cleaned audio into ~200ms chunks before sending them to Riva". The ingest loop "never blocks on ASR I/O"; a separate Riva send thread handles output. Both sides run at 16 kHz.
  - Sources: [AMAX part 1](https://www.amax.com/maxine-sdk-part1/); [AMAX part 2: Building an AEC daemon on Linux](https://www.amax.com/maxine-sdk-part2/)
- **LiveKit**: the `livekit-plugins-nvidia` 1.8.3 wheel contains only `stt.py` and `tts.py` (Riva). A grep for maxine/bnr/denoise/noise finds nothing (`SP/livekit/plugins/nvidia/`, [PyPI](https://pypi.org/project/livekit-plugins-nvidia/1.8.3/)). An issue search in livekit/agents for "Maxine noise removal plugin" returned no relevant issue — [livekit/agents issues](https://github.com/livekit/agents/issues?q=maxine)
- **Pipecat**: the issue search returned only "Add DeepFilterNet as noise cancellation library" (#3266, Dec 2025, closed) — [pipecat#3266](https://github.com/pipecat-ai/pipecat/issues/3266). The built-in filters in 1.12.0 are AIC, Koala, KrispViva and RNNoise; none is Maxine (see the earlier note `Огляд рішень voice isolation/integration_and_evaluation.md` §2).

### Inferences
- **Nothing ready-made exists for LiveKit + Speaker Focus.** A Python binding is small: about 15 C functions, strings for selectors and params, and float32 buffers. Build it with plain `ctypes` against `libnv_audiofx.so`, or regenerate with ctypesgen from the NGC SDK header (as AutoKirinukiVideo did).
- **Reuse map:**
  1. `effects_delayed_streams_demo.cpp`: the reference for multi-stream batching with `NUM_STREAMS`, `ACTIVE_STREAMS` and per-stream `NvAFX_Reset`.
  2. The BNR NIM proto: a ready gRPC contract (bidi stream of float32 chunks plus a config message) to copy for a self-hosted Speaker Focus sidecar.
  3. AMAX: the threading pattern (10 ms processing loop decoupled from ASR sends; ~200 ms chunks to Riva).
  4. AetherSDR / linux-broadcast: runtime packaging and GPU-arch model selection.
  5. OBS nv-filters: a mature C integration with dynamic loading (`nvafx-load.h`).
- **Early Access status after ~4 years** (announced Sept 2022, still EA in 3.0.0 in Sept 2026) and the lack of any third-party user suggest thin real-world validation. Budget for being the first to find its failure modes.

### Gaps
- The Speaker Focus section of the AFX 3.0.0 header (the exact `NVAFX_EFFECT_SPEAKER_FOCUS` string and any SF-specific parameters, e.g. whether `INTENSITY_RATIO` applies) could not be read: it ships only in the NGC package, and docs.nvidia.com was blocked.
- Triton, DeepStream and Holoscan: found no Speaker Focus integration. The Holoscan-for-Media NIMs are Studio Voice and BNR (earlier note). GitHub code search found no Jitsi/Janus/mediasoup/FreeSWITCH/Asterisk AFX integration; this search is not exhaustive.
- NVIDIA forum threads could not be read. Search surfaced only the title "Need help downloading NVIDIA Maxine Audio Effects SDK for real-time speech processing project" ([forum #363349](https://forums.developer.nvidia.com/t/need-help-downloading-nvidia-maxine-audio-effects-sdk-for-real-time-speech-processing-project/363349)).

---

## Q2. Integration design for LiveKit Agents 1.8.3 (FrameProcessor vs async input vs shared GPU sidecar)

### Takeaway
The code facts constrain the design:
- LiveKit 1.8.3 calls `FrameProcessor._process()` **synchronously on the asyncio loop**, with an unbounded frame queue. It fails open on exceptions.
- AFX needs float32 16 kHz frames of a fixed size (10 ms / 160 samples by default; 20 ms is a supported sample option).
- AFX batches many streams per `NvAFX_Run` via `NUM_STREAMS` + `ACTIVE_STREAMS` (Linux "delayed streams").

Recommended architecture (design proposal):
- A **shared Speaker Focus sidecar process on each GPU host**, next to riva_server, that batches all calls every 10 ms.
- A thin agent-side client exposed in two forms:
  - an `rtc.FrameProcessor` (drop-in for `AudioInputOptions(noise_cancellation=…)` and the existing replay tools);
  - optionally an async `io.AudioInput` wrapper that never blocks the loop.
- `AudioInputOptions(sample_rate=16000, frame_size_ms=20)` (or 10).
- On Mac: bypass or remote-sidecar mode.

### Cited Findings (code facts: LiveKit 1.8.3 / rtc 1.1.18 wheels, `SP/`)
- `rtc.FrameProcessor[T]` is an ABC with abstract `enabled` (property + setter), `_process(frame) -> frame` and `_close()`, plus optional stream-info and credential hooks. `_process` is **synchronous**; there is no async variant — `SP/livekit/rtc/frame_processor.py` ([livekit 1.1.18 on PyPI](https://pypi.org/project/livekit/1.1.18/)).
- `AudioStream._run()` does `frame = self._processor._process(frame)` inline in an `async` loop; on exception it logs "Frame processing failed, passing through original frame". Frames then go into `RingQueue(capacity)`, where `capacity` defaults to `0` = **unbounded**. A slow processor therefore grows latency instead of dropping frames — `SP/livekit/rtc/audio_stream.py` L63, L78, L115, L293-313.
- `AudioInputOptions` defaults: `sample_rate=24000`, `num_channels=1`, `frame_size_ms=50`, `noise_cancellation: NoiseCancellationOptions | NoiseCancellationSelector | FrameProcessor | None`. The `auto_gain_control` docstring: "disabled when noise cancellation is configured directly. Set explicitly when using a noise cancellation selector" — `SP/livekit/agents/voice/room_io/types.py` L57-75 ([livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)).
- `frame_size_ms` is passed to the Rust FFI (`new_audio_stream.frame_size_ms` / `audio_stream_from_participant.frame_size_ms`), and the FFI also resamples to `sample_rate` — `SP/livekit/rtc/audio_stream.py` L261-283.
- `io.AudioInput(label=…, source=…)` is chainable with `async def __anext__()`, which delegates to `source` — `SP/livekit/agents/voice/io.py` L42-73.
- `AgentInput.audio` setter detaches the old stream and attaches the new one — io.py L645-660.
- LiveKit itself wraps the input this way:
  - `self.input.audio = self._recorder_io.record_input(self.input.audio)` — `agent_session.py` L1078
  - RoomIO sets `self._agent_session.input.audio = self.audio_input` — `room_io/room_io.py` L198
- Behaviour already documented in the earlier note (`integration_and_evaluation.md` §1), repeated for completeness:
  - The same post-processor frame goes to STT, VAD, AMD, the interruption detector and the turn detector (`audio_recognition.py` L747-775).
  - A processor passed directly is reused across tracks and never closed. A selector-returned processor is owned per track, and selectors turn AGC **on** by default.
- **AFX multi-stream API** (Linux `effects_delayed_streams_demo.cpp`, 3.0.0):
  - Setup (L611-664): `NvAFX_SetU32(handle, NVAFX_PARAM_NUM_STREAMS, num_streams)`, then query `NVAFX_PARAM_SUPPORTED_NUM_SAMPLES_PER_FRAME` (defaulting to the first supported value), then set `NVAFX_PARAM_NUM_SAMPLES_PER_INPUT_FRAME`, then `NvAFX_Load`.
  - Per tick (L290-322):
    - `NvAFX_SetBoolList(handle, NVAFX_PARAM_ACTIVE_STREAMS, activity_map, n)`
    - `NvAFX_Reset(handle, reset_map, n)` when any stream needs resetting. The Linux API resets **per stream**, unlike the 1-argument Windows `NvAFX_Reset(handle)` in the public header.
    - one `NvAFX_Run(handle, input, output, samples_per_frame, channels)`, where stream *i* occupies `input[i*frame … (i+1)*frame)` (L262-267).
  - Source: [effects_delayed_streams_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/1998010fdbc656d13b3ed53c495c9a8f20a929a0/linux/effects_delayed_streams_demo/effects_delayed_streams_demo.cpp)
- NVIDIA docs (snippet):
  - "The Linux SDK supports cases where some streams do not arrive at the expected time, such as when the audio is being processed in real-time… referred to as delayed streams".
  - Applications set `NVAFX_PARAM_ACTIVE_STREAMS`. For delayed streams, "set them as active and set the on-time audio streams as inactive… followed by one or more NvAFX_Run() calls… After the delayed audio streams are processed, the on-time audio streams are set to active, and NvAFX_Run() is executed once".
  - Sources: [effects_delayed_streams_demo (2.0.0 docs)](https://docs.nvidia.com/maxine/afx/2.0.0/LinuxAFXSDK/SampleApplicationsLinux/EffectsDelayedStreamsDemoApplication.html); [Use the AFX SDK in Applications (3.0.0)](https://docs.nvidia.com/maxine/afx/3.0.0/UseAFXInApps/UseTheAFXSDKInApplications.html)
- The AFX built-in VAD (`NVAFX_PARAM_ENABLE_VAD`) is enabled in the sample only for `{"denoiser", "dereverb_denoiser"}`, **not Speaker Focus** — `effects_delayed_streams_demo.cpp` L507-516.
- GPU selection: `NVAFX_PARAM_USE_DEFAULT_GPU`, or `NVAFX_PARAM_USER_CUDA_CONTEXT` for an app-managed context (mutually exclusive), per the public header L242-252. `run_effect.sh` says: "If using a multi-GPU device, use CUDA_VISIBLE_DEVICES".
- NVIDIA release-readiness gate (snippet; the Denoiser v2 reference workload, not Speaker Focus):
  - Reference: "10 ms frames (160 samples) at 16 kHz"; p95 `NvAFX_Run` must stay below the 10 ms frame budget, and p05 throughput above 1.0× real time.
  - "report effect creation and model-load time separately from NvAFX_Run".
  - Measured with "SDK version 3.0.0.25, an NVIDIA RTX 3500 Ada Generation Laptop GPU".
  - Sources: [AFX Windows Performance and Deployment Guide](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ReleaseReadiness.html); [3.0.0 version](https://docs.nvidia.com/maxine/afx/3.0.0/WindowsAFXSDK/ReleaseReadiness.html)
- There is no macOS SDK: the samples repo has only `linux/` and `windows/`, and the Windows README requires "NVIDIA GPUs with Tensor Cores" — [AFX-SDK-Samples windows/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/main/windows/README.md)
- The AMAX precedent (snippet): a Linux daemon runs a Maxine effect on 10 ms frames and forwards to Riva in ~200 ms chunks from a separate thread — [AMAX part 2](https://www.amax.com/maxine-sdk-part2/)

### Inferences — design proposals (mine, not sourced)

**D1. Topology (recommended for prod): a `sf-sidecar` per GPU host**
- **Service shape:**
  - One process, one CUDA context, one Speaker Focus handle with `NUM_STREAMS = N_max` (e.g. 32–128; size it by measurement), `DISABLE_CUDA_GRAPH=1` (per NVIDIA's Speaker Focus note), and `NUM_SAMPLES_PER_INPUT_FRAME=160` at 16 kHz.
  - Transport: a gRPC bidi stream per call, copying the BNR NIM proto (`bytes float32 audio_stream_data`, plus a config message carrying session id, intensity and reset). A Unix-domain socket or shared memory also works if the agents run on the same host.
  - A **10 ms tick loop**: collect one 160-sample frame from every stream that has data, set `ACTIVE_STREAMS` for those slots, call `NvAFX_Run` once, then scatter the outputs.
  - Streams that miss the tick are left inactive and caught up with extra Runs, exactly the "delayed streams" recipe.
  - On `StreamStart`, call `NvAFX_Reset` for that slot only. Never reset mid-call.
- **Why:**
  - Agent workers stay CPU-only and identical on Mac and Linux.
  - One model copy per GPU instead of one per worker process. LiveKit agent jobs usually run in separate processes, so in-process AFX would create one CUDA context and model load per job.
  - Batching amortises GPU launches.
  - It co-locates with riva_server, whose TensorRT engines share the GPU by time-slicing; MIG is only on A30/A100 per the earlier note.
  - It mirrors AMAX's AEC-daemon split.
- **Cost:** one extra localhost hop, sub-millisecond (inference), plus up to one tick (≤10 ms) of alignment wait.

**D2. Agent-side client, form A: `rtc.FrameProcessor` (drop-in; works with `replay_stt` / `vad_scores`, which call `_process`)**
- **Settings:** `AudioInputOptions(sample_rate=16000, frame_size_ms=20, noise_cancellation=SFProcessor(...), auto_gain_control=False)`. At 16 kHz, LiveKit's FFI delivers 320-sample frames. The processor splits each into 2×160 and sends them.
- **Two modes:**
  - **blocking** (replay tools and low-load prod): send both sub-frames and wait on the reply with a hard timeout (e.g. 8 ms). On timeout or error, return the raw frame, which is also LiveKit's own fail-open behaviour. This blocks the event loop for the round trip. With a GPU sidecar the wait is mostly I/O, so other asyncio tasks stall only briefly, but they do stall.
  - **pipelined** (live, non-blocking): push frame *k* to a background thread or socket and return the processed frame *k−1* if it is ready, else raw *k−1*. The loop never waits. The cost is exactly **+1 LiveKit frame** of latency (20 ms at `frame_size_ms=20`; 10 ms at 10) plus Speaker Focus's own look-ahead, which is unknown.
- **In-process variant** (no sidecar): call `NvAFX_Run` through `ctypes` on a **dedicated single worker thread** per handle, so the CUDA context stays on one thread and GIL/loop contention is avoided. `ctypes` foreign calls on `CDLL` release the GIL (Python ctypes docs; not re-fetched here). In the pipelined mode the loop then never waits on the GPU.
- **Selector vs. direct instance:**
  - Pass a **selector** returning a fresh processor per track, so each track gets its own sidecar stream and reset.
  - Set `auto_gain_control` explicitly (False), because selectors enable AGC by default.
  - Note that AGC runs *after* the processor in RoomIO.
- **Alternative form B: async `io.AudioInput` wrapper:**

  ```python
  class SFAudioInput(io.AudioInput):
      def __init__(self, source): super().__init__(label="speaker_focus", source=source)
      async def __anext__(self):
          frame = await self.source.__anext__()
          return await self._client.process(frame)  # awaits sidecar/executor; never blocks the loop
  # after session.start(...): session.input.audio = SFAudioInput(session.input.audio)
  ```

  This keeps the loop free without the +1-frame pipelining penalty; latency is only the actual round trip. It must be re-applied if RoomIO re-sets `input.audio` (for example when RecorderIO wraps it at start, `agent_session.py` L1078), so test the ordering. Keep form A for the replay tools.

**D3. Frame size and sample rate choice**
- `sample_rate=16000`: this matches the Speaker Focus 16k model, Nemotron/riva_server (16 kHz) and LiveKit's audio EOT model, which runs on 16 kHz PCM (earlier note). It avoids the extra 24k→16k resampling hop that the current default of 24 kHz implies.
- `frame_size_ms=20` is a good compromise: half the per-frame Python overhead of 10 ms, and a 30 ms smaller pipeline delay than the default 50 ms.
- If the Speaker Focus model reports 320 samples in `SUPPORTED_NUM_SAMPLES_PER_FRAME`, run 20 ms natively; otherwise split into 2×160.
- 48 kHz Speaker Focus is only worth it if the same processed audio is also recorded or played back at full band; the ASR and VAD path is 16 kHz.

**D4. Latency budget** (to measure; everything except the frame sizes is unknown)

| Component | Estimate |
|---|---|
| LiveKit frame accumulation | = `frame_size_ms` (20 ms; already present today at 50 ms) |
| Pipelined-mode penalty | +1 frame (20 ms), or 0 in async/blocking form |
| Sidecar tick alignment | 0–10 ms |
| `NvAFX_Run` compute | p95 < 10 ms by NVIDIA's generic gate; likely ≪10 ms at small batch (unverified) |
| **Speaker Focus algorithmic look-ahead** | **unknown — measure by cross-correlating input/output on clean speech** |

- Target: keep the total added delay ≤ 30–40 ms over raw.

**D5. Fallback and robustness**
- If the sidecar is unreachable, the handle fails to load, the GPU is missing, or there are N consecutive timeouts:
  - trip a circuit breaker to **pass-through** (raw audio), log a metric and emit a per-call flag;
  - optionally fall back to the existing ai-coustics Quail Voice Focus processor (CPU, same interface).
- Never fail closed: returning silence would kill barge-in.
- Warm up at worker start by running ~50 frames of silence through the path, since NVIDIA says model load and creation are separate costs.
- Keep one `NvAFX_Reset` per new track.
- Validate that output frames keep the **same sample count** as input frames (query `NUM_SAMPLES_PER_OUTPUT_FRAME`).

**D6. Mac development**
- Options:
  1. A `SF_MODE=bypass` flag (default on darwin).
  2. `SF_MODE=remote`: point the agent at the Linux GPU sidecar over a VPN or SSH tunnel. Audio stays on your own infrastructure, which respects the no-third-party-cloud rule.
  3. `SF_MODE=aic`: use ai-coustics as a stand-in.
- Record which mode produced every metric; front-end mismatch changes ASR, turn and barge-in behaviour.
- The replay tools can run against the remote sidecar from the Mac through form A's blocking mode.

**D7. Which consumers get Speaker Focus audio** (per the earlier ASR-vs-VAD analysis)
- **E1 (all consumers):** the plain `noise_cancellation=` wiring.
- **E2 (VAD, turn and interruption only):** leave `noise_cancellation=None` and wrap the VAD (and turn detector) so they consume the Speaker Focus output while STT receives raw audio. The alternative is to apply Speaker Focus **inside an ASR proxy**, i.e. the AMAX pattern, if you want the opposite split.
- **E3:** Speaker Focus on the ASR path only, via a proxy in front of riva_server.
- For a speaker-isolation model (as opposed to a denoiser), E1 may win when background *words* dominate errors. A/B all three.

**D8. Chaining**
- NVIDIA's SF+denoiser chain applies **Denoiser v1**, not the ASR-oriented v2.
- If a denoiser is wanted, create two separate handles, SF then Denoiser v2 (or v2 then SF), and measure both orders.
- The AFX VAD flag is not available on Speaker Focus.

### Gaps
- Speaker Focus-specific supported frame sizes, **algorithmic latency (look-ahead)**, per-stream GPU memory and maximum streams per GPU: not published in reachable sources.
- Speaker Focus support for `NUM_STREAMS > 1` / `ACTIVE_STREAMS` is **unverified**. The demo code path is generic, and only Studio Voice is flagged as batch-1 (`run_effect.sh` L114), which hints, but does not prove, that Speaker Focus batches.
- Thread-affinity rules for AFX handles (must `NvAFX_Run` be called from the creating thread?) were not found. Assume single-thread ownership.
- Whether `NVAFX_PARAM_INTENSITY_RATIO` works on Speaker Focus (a wet/dry knob) is unknown; the community project contradicts itself.
- The CPU and GPU cost of `DISABLE_CUDA_GRAPH=1`, which Speaker Focus requires, is unmeasured.

---

## Q3. Evidence on Speaker Focus quality, latency, GPU cost, comparisons, and production use

### Takeaway
There is **no published quantitative evidence** of any kind for Speaker Focus: no NVIDIA SI-SDR, DNSMOS or WER figures, no third-party test, no latency or GPU figure, no forum reports, and no comparison against Krisp BVC, ai-coustics Voice Focus or NVIDIA Broadcast. All that exists is NVIDIA's one-paragraph description (unchanged from 2.0.0 to 3.0.0), a 2022 GTC announcement, and an unverified hobby project's figures.

No voice-agent, contact-center or CPaaS company was found publicly using Speaker Focus. Historic Maxine adopters (Avaya Spaces 2020, Pexip 2021) used noise removal in conferencing.

### Cited Findings
- **NVIDIA's description** (snippets; identical wording across the 2.0.0, 2.1.0, 3.0.0 and latest docs):
  - "identifies and isolates the primary speaker from all other speakers and removes the speech of all other speakers from the input audio… significantly improves the intelligibility of the speech of the primary speaker".
  - "32-bit float audio with a sampling rate of 16 kHz or 48 kHz… mono-channel input and output… supports audio with up to four speakers".
  - "robust against various types of background noises including AC noise, clapping, fan noise, keyboard, mouse clicks, PC noise, sounds of a vacuum cleaner, and tapping".
  - "currently available under the Early Access program".
  - Sources: [AFX latest: Speaker Focus](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html); [2.0.0](https://docs.nvidia.com/maxine/afx/2.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html); [2.1.0](https://docs.nvidia.com/maxine/afx/2.1.0/AboutTheEffects/AboutSpeakerFocusEffect.html); [3.0.0](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- **History** (snippet): at GTC Sept 2022, NVIDIA announced cloud-native Maxine and said "Speaker Focus, available in early access, is a new feature that separates the audio tracks of foreground and background speakers, making each voice more intelligible" (blog dated 2022-09-20) — [NVIDIA blog: Maxine cloud-native](https://blogs.nvidia.com/blog/2022/09/20/maxine-cloud-native)
  - One search summary instead attributed the announcement to CES 2023. That source is unverified and conflicts with the dated blog; prefer Sept 2022.
- **Still Early Access in AFX 3.0.0** (samples released 2026-09-10). The 3.0.0 guide says Speaker Focus 16k/48k are Early Access and "must be explicitly named when downloading" (snippet, earlier note) — [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf)
- **No Speaker Focus metrics:** searches for Speaker Focus latency, known issues, limitations, reviews or demos returned only the description pages (searches run 2026-09-26; e.g. [AFX 3.0.0 index](https://docs.nvidia.com/maxine/afx/3.0.0/index.html)).
  - The only NVIDIA accuracy claim in the AFX line is for **BNR v2**: "offers improved accuracy for automated speech recognition" / "improves the speech recognition accuracies of ASR systems" (snippet), with no numbers — [AFX noise removal](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutNoiseRemovalBackgroundNoiseSuppression.html)
- **Latency context from sibling effects** (snippet, earlier note): Studio Voice Low Latency has **80 ms** algorithmic latency. AFX effects can therefore carry large look-ahead, so Speaker Focus look-ahead cannot be assumed to be ~10 ms — [AFX docs index](https://docs.nvidia.com/maxine/afx/latest/index.html)
- **Compute gate** (generic, Denoiser v2 reference): p95 `NvAFX_Run` < 10 ms per 10 ms frame (snippet) — [Performance and Deployment Guide](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ReleaseReadiness.html)
- **Community figures (unverified):** maxine-pipewire claims Speaker Focus "Latency ~10 ms", "GPU Load Low–Medium (~3–7%)". The same project is internally inconsistent (see Q1) — [EFFECTS.md](https://github.com/Darudas/maxine-pipewire/blob/master/doc/EFFECTS.md)
- **Forums:** the only reachable-by-search thread title is a download/access question ([#363349](https://forums.developer.nvidia.com/t/need-help-downloading-nvidia-maxine-audio-effects-sdk-for-real-time-speech-processing-project/363349)). No Speaker Focus artifact, crash or latency thread surfaced (forum blocked; search only).
- **Video:** "Improving End-to-End Conversation Quality with NVIDIA Maxine" exists on YouTube (content not verified; unclear whether it demos Speaker Focus) — [YouTube WO4KB5VjT2E](https://www.youtube.com/watch?v=WO4KB5VjT2E)
- **NVIDIA Broadcast (consumer):** the FAQ and app pages list Noise Removal and Room Echo Removal. No "Speaker Focus" feature surfaced in snippets. Search summaries said Broadcast noise removal handles background noise "including voices", which is marketing wording, not a background-voice-cancellation (BVC) claim — [NVIDIA Broadcast FAQ](https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/faq/)
- **Production adopters of Maxine (not Speaker Focus, not voice agents):**
  - Avaya integrated NVIDIA Maxine into Avaya Spaces, including background noise removal (Oct 2020) — [ExecutiveBiz](https://executivebiz.com/2020/10/avaya-integrates-nvidia-ai-to-advance-avaya-spaces-app-anthony-bartolo-ian-buck-quoted/)
  - Pexip began collaborating with NVIDIA on noise cancellation (Apr 2021), and its partner page cites Maxine and Riva for captioning, translation and AV quality — [Pexip blog](https://www.pexip.com/blog/pexip-seeks-to-reimagine-virtual-meetings-using-nvidia); [Pexip + NVIDIA](https://www.pexip.com/technology-partners/nvidia)
  - AMAX (a systems integrator) reports AEC + BNR + Riva "produced noticeably cleaner transcripts compared to ASR alone" in hybrid meetings. This is qualitative, with no WER table in the snippets — [AMAX part 1](https://www.amax.com/maxine-sdk-part1/)
- **Comparisons:** searches for Krisp BVC vs Maxine returned only consumer RTX Voice/Broadcast vs Krisp *noise* reviews, e.g. [Picovoice: RTX Voice vs Krisp](https://picovoice.ai/blog/nvidia-rtx-voice-krisp/) and [Krisp blog](https://krisp.ai/blog/nvidia-rtx-voice-krisp/). None tests competing-talker removal or Speaker Focus.
- **Context: the competitors' published numbers are vendor claims** (see the earlier note §3):
  - Krisp BVC before VAD: "3.5x" fewer false VAD triggers.
  - ai-coustics Quail VF 2.x: "up to 84%" WER reduction on foreground+background-speaker sets.
  - ai-coustics' single-sample comparison: Krisp BVC 23.5% vs ai-coustics 7.1% WER.
  - Sources: [Krisp blog](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/); [ai-coustics VF 2.1](https://ai-coustics.com/blog/quail-voice-focus-2.1); [ai-coustics vs Krisp](https://ai-coustics.com/2025/11/10/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you/)
  - Nothing comparable exists for Speaker Focus.

### Inferences
- Speaker Focus must be treated as **unbenchmarked**. The user's A/B/C corpus plus the replay tools will be the first real evidence. Run Speaker Focus through the same harness as ai-coustics Quail VF (already integrated) and, if a Cloud project is available, Krisp BVC via `livekit-examples/noise-canceller`.
- A four-year Early Access period, no NIM, no Pipecat/LiveKit plugin, and no named voice-AI customer together suggest NVIDIA has not productised Speaker Focus for agents. NVIDIA's voice-agent focus appears to be ASR-side: Nemotron, Sortformer diarization and noise-augmented training.
- "Up to four speakers" implies the model was trained on mixtures of ≤4 talkers. Crowd/babble (TV audience, call-center floor) is outside the stated envelope.

### Gaps
- No SI-SDR, DNSMOS, PESQ, WER or listening-test numbers for Speaker Focus from any source.
- Could not read the AFX 3.0.0 PDF or the release notes (known issues, performance tables); docs.nvidia.com was blocked.
- Could not verify GTC 2023–2026 session content on Speaker Focus; no such session surfaced in searches.
- No public comparison of Speaker Focus against Krisp BVC, ai-coustics VF, Sanas VI or Hecttor.

---

## Q4. Failure modes relevant to voice agents (backchannels, first-word clipping, silent caller + TV, speaker switching, 8 kHz telephony, TTS echo/AEC)

### Takeaway
NVIDIA documents **none** of these behaviours. The only design facts are:
- "prominent/primary speaker" selection without enrollment;
- ≤4 speakers;
- 16/48 kHz only;
- no VAD output;
- CUDA graphs disabled;
- NVIDIA's own AEC effect is **deprecated in AFX 3.0.0**.

Every agent-relevant failure mode is therefore a hypothesis to test with the replay harness.

### Cited Findings
- Primary-speaker heuristic, no enrollment input: the effect "identifies and isolates the **prominent** speaker"; the documented inputs are mono audio only, with no reference or embedding parameter (snippet) — [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- Sample rates: 16 kHz / 48 kHz only, and no 8 kHz → Speaker Focus chain (the superres 8k→16k chains pair only with denoiser/dereverb) — [scripts/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/main/windows/apps/effects_demo/scripts/README.md)
- AEC: "The Acoustic Echo Cancellation (AEC) effect and Voice Font effect have been depreciated" in AFX 3.0.0 (snippet). NGC lists "(Depreciated) Acoustic Echo Cancellation Effect" — [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf); [NGC AEC collection](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/collections/maxine_afx_aec/-)
- LiveKit 1.8.3's AEC warm-up and uninterruptible speech: STT receives a *silence* frame while "VAD, AMD and the interruption detector keep receiving the real frame". The processed caller audio can therefore still carry TTS echo into VAD and barge-in — `SP/livekit/agents/voice/agent_activity.py` L1651-1683 (earlier note).
- Analogous field reports for other BVC products:
  - LiveKit BVCTelephony "can be overly aggressive and occasionally cancels out quiet callers" (snippet) — [LiveKit community](https://community.livekit.io/t/audio-gain-before-bvctelephony/300)
  - Pipecat's Krisp VIVA filter has TTS-detection options to "delay voice isolation until bot speech playback has stopped, preventing later real human speech suppression artifacts" — `krisp_viva_filter.py` in pipecat-ai 1.12.0 (earlier note)
  - Deepgram: "Aggressive AEC suppression makes barge-in harder" (snippet) — [Deepgram audio preprocessing & barge-in](https://developers.deepgram.com/guides/deep-dives/audio-preprocessing-barge-in)

### Inferences (hypotheses and how to test each with replay_stt / vad_scores)
- **Backchannel suppression.** Short, quiet "mm-hm"/"yeah" while the *agent* talks may be judged non-prominent, especially if the TTS echo is louder than the backchannel.
  - Test: A-set short-utterance recall (VAD start plus STT final) raw vs Speaker Focus, stratified by level (−10 to −30 dBFS).
- **First-word clipping / lock-on delay.** A primary-speaker tracker needs context to decide who is "primary", so onsets after long silence, or the first utterance of a call, may be attenuated.
  - Test: VAD onset latency and first-word WER on A; the energy envelope of the first 300 ms, input vs output.
  - Do **not** `NvAFX_Reset` between turns; reset only per new track.
- **Caller silent, TV talking.** With only one voice present, the "prominent" voice *is* the TV. Expect Speaker Focus to **pass TV speech**. This is the most dangerous case for false barge-ins and phantom turns.
  - Test: B-set (background only) leakage words/min, VAD triggers/min, false barge-ins/min.
  - Mitigation: keep the Sortformer speaker-ID gate (lock on the caller's ID) as a second line of defence.
- **Speaker switching.** If the TV is louder than the caller for a stretch, Speaker Focus may switch its "primary" and later suppress the real caller.
  - Test: C-mixes at SIR −5/0/+5/+10 dB, measuring caller-word deletions per SIR bin and hysteresis after TV bursts.
- **Legitimate second caller** (speakerphone family member answering): Speaker Focus would suppress them by design. This is acceptable or not depending on the product; Sortformer-level gating is more controllable.
- **Telephony 8 kHz (SIP).**
  - Let LiveKit's FFI resample 8→16 kHz (`sample_rate=16000`) and feed the Speaker Focus 16k model. The band above 4 kHz will be empty, a distribution shift for a wideband-trained model (unknown effect).
  - Alternatively, cascade two handles, superres 8k→16k then Speaker Focus 16k. This adds the superres latency and may hallucinate high band.
  - Test both on narrowband recordings.
- **TTS echo** (speakerphone, laptop speakers, SIP handsets with poor AEC).
  - Speaker Focus is not an AEC. The agent's own voice may be kept (if louder or "prominent") or removed (if treated as a background talker). Either way it is not a reliable substitute for AEC.
  - Keep AEC upstream: browser/WebRTC client AEC, handset or carrier AEC. For SIP, consider a WebRTC-APM AEC stage with the TTS reference before Speaker Focus. NVIDIA's own AEC is deprecated in 3.0.
  - Test: agent-speaking segments with echo, measuring false barge-ins and TTS words leaking into STT.
- **Over-suppression artifacts on the ASR path** (a known SE-hurts-ASR effect). Speaker Focus is a masking or separation model with unknown artifacts. Measure A-set WER raw vs Speaker Focus for Nemotron before putting it on the STT path (see Q5).

### Gaps
- No NVIDIA or third-party statement on backchannels, onset behaviour, single-talker-TV behaviour, speaker-switch hysteresis, narrowband input, or echo handling for Speaker Focus.
- Unknown whether Speaker Focus handles non-speech vocal sounds (laughs, "uh") or singing/music (TV) differently from speech.

---

## Q5. Effect on ASR: NVIDIA guidance on Maxine before Riva/NeMo, and WER evidence

### Takeaway
There is **no NVIDIA guidance and no WER data for Speaker Focus → ASR**. The evidence that exists:
- NVIDIA claims BNR v2 is "ASR-tuned" (no numbers).
- NVIDIA's Riva material pushes noise-robust acoustic models (noise-augmentation fine-tuning) rather than front-end enhancement.
- A systems integrator (AMAX) ran Maxine AEC/BNR as a proxy before Riva, with qualitative gains only.

Academic evidence (earlier note) shows SE front-ends often raise WER for modern robust ASR, NVIDIA Parakeet included. For a *speaker-isolation* model, however, removing background words can reduce insertions. The deciding measurement is the user's own E1/E2/E3 A-B test on Nemotron + Sortformer.

### Cited Findings
- BNR v2: "offers improved accuracy for automated speech recognition" and "integrates seamlessly in pipelines where audio cleaning is required before being used in other subsystems" (snippet; no WER numbers) — [AFX noise removal](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutNoiseRemovalBackgroundNoiseSuppression.html)
- Riva guidance favours robust training: "How to Improve the Accuracy on Noisy Speech by Fine-Tuning the Acoustic Model (Conformer-CTC) in the Riva ASR Pipeline" (title/snippet) — [Riva tutorial](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tutorials/asr-noise-augmentation.html); [nvidia-riva/tutorials asr-noise-augmentation.ipynb](https://github.com/nvidia-riva/tutorials/blob/main/asr-noise-augmentation.ipynb)
- The Maxine-before-Riva proxy pattern: 10 ms AEC frames accumulated to ~200 ms Riva chunks; "cleaner transcripts" qualitatively (snippets) — [AMAX part 1](https://www.amax.com/maxine-sdk-part1/); [AMAX part 2](https://www.amax.com/maxine-sdk-part2/)
- SE can hurt NVIDIA ASR: "When De-noising Hurts" (arXiv 2512.17562, Dec 2025) reports noisy audio beat MetricGAN+-enhanced audio in all 40 configurations, with **Parakeet** among the degraded models (snippet via earlier note) — [arXiv 2512.17562](https://arxiv.org/abs/2512.17562)
- ASR vendors (Deepgram, AssemblyAI) recommend raw audio to STT and NC for VAD/turn-taking (snippets via earlier note) — [AssemblyAI](https://www.assemblyai.com/blog/noise-cancellation-stt-pros-cons); [Deepgram](https://deepgram.com/learn/the-noise-reduction-paradox-why-it-may-hurt-speech-to-text-accuracy)
- NVIDIA's own speaker-aware stack is ASR-side: Streaming Sortformer diarization, positioned for "meetings, calls, and voice apps" in real time (title/snippet) — [NVIDIA blog: Streaming Sortformer](https://developer.nvidia.com/blog/identify-speakers-in-meetings-calls-and-voice-apps-in-real-time-with-nvidia-streaming-sortformer/)

### Inferences
- **Evaluation plan specific to Speaker Focus** (extends §5 of the earlier note):
  - Conditions: R0 raw; E1 SF→all; E2 SF→VAD/turn/interruption only; E3 SF→ASR only (proxy in front of riva_server); plus an SF+BNRv2 two-handle variant.
  - Metrics on Nemotron:
    - caller-word errors vs **background insertions**, split, on C mixes by SIR;
    - A-set WER delta;
    - short-utterance recall;
    - B-set leakage.
  - Metrics on Sortformer: DER and the number of speaker IDs. With Speaker Focus on, expect fewer speaker IDs; check that Sortformer does not split the caller into two IDs because of artifacts.
- **Where to apply it:**
  - If E1 wins on C but loses on A, prefer E2 plus Sortformer-ID gating of ASR text. This matches the ASR-vendor guidance and keeps raw audio to Nemotron.
  - If Speaker Focus artifacts are mild and TV insertions dominate, E1 or E3 is justified.
- **Mechanics:** running Speaker Focus in a proxy directly in front of riva_server (the AMAX pattern) means the ASR sees Speaker Focus audio while LiveKit's VAD sees raw audio, i.e. the inverse of E2. With the sidecar design (Q2 D1), both E2 and E3 are just routing choices.

### Gaps
- No NVIDIA statement on whether Speaker Focus output is suitable ASR input, and no Speaker Focus/Nemotron/Parakeet/Riva WER numbers anywhere.
- No evidence on Speaker Focus × Sortformer DER.
- The AMAX WER numbers (if any) could not be read; www.amax.com was blocked.
