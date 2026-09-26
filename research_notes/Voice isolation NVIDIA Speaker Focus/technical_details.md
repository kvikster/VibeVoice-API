# NVIDIA Audio Effects (AFX) SDK "Speaker Focus": technical details (as of 26 Sept 2026)

Scope: the NVIDIA AFX SDK's Speaker Focus effect (SF). It is judged as a front end for a self-hosted LiveKit Agents 1.8.3 + NeMo riva_server (Nemotron streaming ASR + Sortformer) voice agent: Mac dev, Linux GPU prod, no caller audio to third-party clouds.

**Method and evidence levels.**

The egress proxy returned HTTP 403 for every NVIDIA web host: docs.nvidia.com (all versions, HTML and PDF), catalog.ngc.nvidia.com, api.ngc.nvidia.com, developer.nvidia.com, forums.developer.nvidia.com, blogs.nvidia.com, research.nvidia.com and build.nvidia.com. It also blocked the cloudfront PDF mirror (d29g4g2dyqv443.cloudfront.net), web.archive.org / archive.org, archive.ph, r.jina.ai and Google cache/translate.

Evidence therefore comes from three sources:

- **(code)**: facts read directly from NVIDIA's official sample repositories, cloned with git. These are the strongest evidence here:
  - `NVIDIA-Maxine/AFX-SDK-Samples`: branches `2.0.0`, `2.1.0`, `3.0.0`.
  - `NVIDIA-Maxine/Maxine-AFX-SDK`: the old v1.3.0 repo.
  - `NVIDIA-Maxine/nim-clients`.
- **(snippet)**: text the search engine returned for a docs.nvidia.com or NVIDIA page. It is often paraphrased by the search tool, so it is weaker.
- **(third-party)**: a community repo, reported for completeness and marked unreliable.

The SDK binaries, the real `nvAudioEffects.h` for 2.x/3.x, and the models are *not* public, so selector string values that do not appear in the sample code are inferred.

---

## 1. Version history: when Speaker Focus appeared, what changed through 2.0 → 2.1 → 3.0, Early Access status, deprecations

### Takeaway
- **Announced:** Speaker Focus was announced at NVIDIA GTC in September 2022 as a new Maxine SDK feature.
- **Where it first appears in shipped code:** the public sample code for **AFX SDK 2.0.0** (published Oct 2025), for both **Windows and Linux**. It was not in the old public v1.3.0 Windows repo.
- **2.x changes:** from 2.0.0 through 2.1.0 (Mar 2026), the Speaker Focus code paths did not change.
- **3.0.0 (samples published 10 Sept 2026):**
  - Speaker Focus is still **Early Access**.
  - The Windows sample stopped disabling CUDA graphs for standalone Speaker Focus, but still disables them for the Speaker Focus + BNR chain.
  - The SDK samples dropped **AEC** and **Voice Font** entirely.
- **Status:** no evidence of GA status or of any new Speaker Focus model version as of Sept 2026.

### Cited Findings

**Announcement (2022)**
- At GTC (blog dated 2022-09-20), NVIDIA announced a cloud-native re-architecture of Maxine, an early-access Audio Effects microservice, and "new Maxine SDK features including Speaker Focus and Face Expression Estimation". Speaker Focus was described as "a new feature that separates the audio tracks of foreground and background speakers, making each voice more intelligible" (snippet). Sources: [NVIDIA blog, 2022-09-20: Maxine cloud-native](https://blogs.nvidia.com/blog/2022/09/20/maxine-cloud-native); [NVIDIA Technical Blog: New Maxine microservices](https://developer.nvidia.com/blog/new-maxine-microservices-enhance-real-time-audio-and-video-effects-for-video-conferences-at-scale/)

**Pre-2.x releases**
- The old public Windows repo `NVIDIA-Maxine/Maxine-AFX-SDK` has a single tag, `v1.3.0`. Its `nvAudioEffects.h` defines only these selectors (code):
  - `denoiser`, `dereverb`, `dereverb_denoiser`, `aec`, `superres`
  - six chained Superres selectors, e.g. `superres8kto16k_denoiser16k`

  There is **no Speaker Focus selector**. The README lists five effects: BNR, dereverb, dereverb+denoiser, AEC and SR. [Maxine-AFX-SDK nvAudioEffects.h (v1.3.0)](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK/blob/main/nvafx/include/nvAudioEffects.h); [README](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK)
- An unversioned docs URL, titled "About the Speaker Focus Effect — NVIDIA **Maxine** Audio Effects (AFX) SDK User Guide", is indexed alongside the 2.0.0 / 2.1.0 / 3.0.0 / latest pages (snippet: title only). [docs.nvidia.com/maxine/afx/AboutTheEffects/AboutSpeakerFocusEffect.html](https://docs.nvidia.com/maxine/afx/AboutTheEffects/AboutSpeakerFocusEffect.html)
- "Maxine R14 Release Notes and Highlights" (December 2024) is a forum post. Its content could not be fetched. The search summary mixed a Speaker Focus description with R14 highlights, such as "Audio Super Resolution latency has been reduced by over 50%". Whether Speaker Focus shipped in R14 is **unverified** (snippet). [NVIDIA forums: Maxine R14 release notes](https://forums.developer.nvidia.com/t/maxine-r14-release-notes-and-highlights/318615)

**Sample-repo release timeline (AFX-SDK-Samples)**

| Date | Commit | Event |
|---|---|---|
| 2025-10-29 | `e205600` | "2.0.0 release" |
| 2026-03-16 | `73cbdb8` | "Add 2.1.0" |
| 2026-09-10 | `1707ee0` | "3.0.0 release" |
| 2026-09-16 | `1998010` | "N1X driver version fix" |

The default branch is `3.0.0` (code). [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples); [3.0.0 release commit](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/commit/1707ee0)

**AFX 2.0.0 (Oct 2025)**
- **Windows effect list** (8 effects): BNR v1 & v2, Room Echo Cancellation, REC+BNR, AEC, SR, **Speaker Focus (SF)**, Studio Voice HQ/LL, Voice Font HQ/LL (code). [windows/README.md @2.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/2.0.0/windows/README.md)
- **Linux sample:**
  - `run_effect.sh` lists `["speaker_focus"]="16 48"`.
  - The Linux demo creates `NVAFX_EFFECT_SPEAKER_FOCUS`.
  - It also creates the chains `NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_16k_DENOISER_16k` and `..._48k_DENOISER_48k`.

  So Speaker Focus shipped on **both Linux and Windows** in 2.0.0 (code). [linux/effects_demo/effects_demo.cpp @2.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/2.0.0/linux/effects_demo/effects_demo.cpp)
- **Windows 2.0.0 and 2.1.0 CUDA graphs:** both register standalone Speaker Focus as `EffectConfig(NVAFX_EFFECT_SPEAKER_FOCUS, true)`, where `true` means "disable CUDA graph". The chain code carries the comment "Speaker Focus models don't work with Cuda Graphs. Hence disabling them." (code). [windows effects_demo.cpp @2.1.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/2.1.0/windows/apps/effects_demo/effects_demo.cpp)
- **Early Access download:** Early Access features must be named explicitly when running the model-download script:
  - Linux: `./download_models.sh --gpu <gpu> --effects speaker_focus-16k,speaker_focus-48k`
  - Windows: `powershell -ExecutionPolicy Bypass -File ./download_models.ps1 --gpu_architecture <gpu> --effects speaker_focus-16k,speaker_focus-48k`

  (snippet) Sources: [AFX 2.0.0 Windows Install](https://docs.nvidia.com/maxine/afx/2.0.0/WindowsAFXSDK/InstallTheAFXSDK.html); [AFX 3.0.0 Linux Install](https://docs.nvidia.com/maxine/afx/3.0.0/LinuxAFXSDK/InstallTheAFXSDK.html)
- "The Speaker Focus effect is currently available under the Early Access program" (snippet, 2.0.0 docs). [AFX 2.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/2.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)

**AFX 2.1.0 (Mar 2026)**
- The Speaker Focus code is identical to 2.0.0 in both samples (same line numbers and content). `git diff 2.0.0 2.1.0` shows no change to `linux/effects_demo/run_effect.sh` (code). [AFX-SDK-Samples @2.1.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/2.1.0)
- **Rebrand:** the product dropped the "Maxine" name. Docs titles went from "NVIDIA Maxine Audio Effects (AFX) SDK" (2.0.0) to "NVIDIA Audio Effects (AFX) SDK" (2.1.0 / 3.0.0 / latest) (snippet: titles). In the samples repo, the 3.0.0 README says "NVIDIA AudioEffects SDK" where the 2.0.0 README said "NVIDIA Maxine AudioEffects SDK" (code). [AFX 2.1.0 index](https://docs.nvidia.com/maxine/afx/2.1.0/index.html); [README diff](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/README.md)

**AFX 3.0.0 (Sept 2026)**
- **Still Early Access:** Speaker Focus (16k and 48k versions) is still an Early Access feature that "must be explicitly named when downloading" (snippet, 3.0.0 user guide PDF / 3.0.0 Speaker Focus page). [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf); [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- **Windows effect list is now 6 items:** BNR v1/v2, REC, REC+BNR, SR, **Speaker Focus**, and Studio Voice HQ/LL + Mic Profiles. The six Studio Voice LL mic profiles are Full, Bright, Warm, Flat, Thin and Vibrant. **AEC and Voice Font were removed** (code). [windows/README.md @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/README.md)
- **Linux run script:** the 3.0.0 `run_effect.sh` removed the `aec`, `voice_font_high_quality` and `voice_font_low_latency` entries. `git diff --stat 2.1.0 3.0.0` shows all AEC and Voice Font sample WAVs deleted. Speaker Focus stays at `"16 48"` (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **CUDA-graph workaround narrowed:** the Windows 3.0.0 sample registers standalone Speaker Focus as `EffectConfig(NVAFX_EFFECT_SPEAKER_FOCUS)`, with no CUDA-graph disable (line 963). The chained Speaker Focus + denoiser entries still pass `true` and call `NvAFX_SetU32List(chained_handle, NVAFX_PARAM_DISABLE_CUDA_GRAPH, {1,1}, 2)` with the same "don't work with Cuda Graphs" comment (lines 776–804) (code). [windows effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **Windows on ARM:** 3.0.0 adds Windows ARM64 (NVIDIA **N1X**), which needs driver ≥ 616.41; x86/x64 needs ≥ 520.46. The Windows sample now uses `-g blackwell` in its examples. Architectures are turing / ampere / ada / blackwell, and N1X/ARM64 auto-selects blackwell (code). [windows/README.md @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/README.md); [run_effects_demo.bat @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat)

**API renames visible across versions**
- The samples try the new parameter name first and fall back to the old one ("Try previous version") (code). [linux effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp)

  | Old name | New name |
  |---|---|
  | `NVAFX_PARAM_SAMPLE_RATE` | `NVAFX_PARAM_INPUT_SAMPLE_RATE` |
  | `NVAFX_PARAM_NUM_SAMPLES_PER_FRAME` | `NVAFX_PARAM_NUM_SAMPLES_PER_INPUT_FRAME` |
  | `NVAFX_PARAM_NUM_CHANNELS` | `NVAFX_PARAM_NUM_INPUT_CHANNELS` |

- In v1.3.0, `NVAFX_PARAM_DENOISER_MODEL_PATH` was already `#pragma deprecated` in favour of `NVAFX_PARAM_MODEL_PATH` (code). [nvAudioEffects.h v1.3.0](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK/blob/main/nvafx/include/nvAudioEffects.h)

### Inferences
- **Status by Sept 2026:** four years after the GTC 2022 announcement, Speaker Focus is still Early Access and absent from NIMs and NVIDIA Broadcast (see Q6). NVIDIA has kept it in the SDK but has not promoted it. Plan for Early Access terms: no stability promise, and possibly a separate access request.
- **CUDA-graph change in 3.0.0:** dropping the workaround for standalone Speaker Focus suggests the model/runtime was fixed to tolerate CUDA graphs on Windows, but not yet in the chain.
- **AEC and Voice Font:** their removal in 3.0.0 shows NVIDIA does prune effects between major versions. Speaker Focus survived the 3.0 pruning, but its Early Access status means it could be pruned later.
- **First shipped version:** the unversioned "Maxine … User Guide" Speaker Focus page, plus Maxine R14 (Dec 2024), suggest Speaker Focus may have been documented in a 1.x/2.0 build before the Oct 2025 samples repo existed. The exact first SDK version could not be pinned down.

### Gaps
- Could not fetch any AFX release-notes page (2.0.0/2.1.0/3.0.0), so the exact wording of Speaker Focus changes and known issues per release is unknown. It is also unknown whether Speaker Focus models were retrained between 2.0 and 3.0; the model file names are unchanged, `speaker_focus_{16,48}k.trtpkg`.
- The first SDK version containing Speaker Focus (for example a 1.x Windows EA or 2.0 Dec 2024), and whether Windows and Linux got it simultaneously, are unconfirmed.
- Whether the 3.0 docs formally deprecate AEC and Voice Font, as opposed to only dropping them from samples, is unconfirmed.

---

## 2. API: selectors, chains, models, parameters, formats, frames, multi-stream, CUDA, Run/Reset semantics

### Takeaway
Speaker Focus uses the standard AFX C API:

- `NvAFX_CreateEffect(NVAFX_EFFECT_SPEAKER_FOCUS)`, or `NvAFX_CreateChainedEffect(NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_{16k,48k}_DENOISER_{16k,48k})`.
- One model per rate: `features/speaker_focus/models/<sm_xx>/speaker_focus_{16k,48k}.trtpkg`.
- Audio is **float32 mono**, in and out, at the **same rate (16→16 or 48→48 only)**.
- The default frame is 10 ms: 160 samples at 16k, 480 at 48k.

On Linux, one handle serves N streams (`NVAFX_PARAM_NUM_STREAMS`) through a single `NvAFX_Run` on a stream-major buffer. `NVAFX_PARAM_ACTIVE_STREAMS` lets a call process only a subset of streams, and a per-stream `NvAFX_Reset(handle, bitmap, n)` clears state.

In the official samples, Speaker Focus has **no enrollment input, no VAD output and no intensity control**. It chains only with BNR (the v1 denoiser model), with Speaker Focus first.

### Cited Findings

**Effect selectors and creation**
- Effect ID string `"speaker_focus"` maps to `NVAFX_EFFECT_SPEAKER_FOCUS`. The Linux sample calls `NvAFX_CreateEffect(NVAFX_EFFECT_SPEAKER_FOCUS, &handle)` behind `#if EFFECT_SPEAKER_FOCUS`, which is generated when the feature package is installed (code). [linux effects_demo.cpp @3.0.0 L387–391](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L387-L391)
- The docs describe `NvAFX_CreateEffect()` as creating "a handle to the audio effect instance for use in additional API calls", and list `NVAFX_EFFECT_SPEAKER_FOCUS` among the type definitions for 2.0.0, 2.1.0 and 3.0.0 (snippet). [AFX Create an Audio Effect](https://docs.nvidia.com/maxine/afx/latest/UseAFXInApps/CreateAudioEffect.html); [AFX 3.0.0 Type Definitions](https://docs.nvidia.com/maxine/afx/3.0.0/APIReference/AFXTypeDefinitions.html)
- A third-party reconstructed header (Darudas/maxine-pipewire, Mar 2026) defines `NVAFX_EFFECT_SPEAKER_FOCUS "speaker_focus"`, consistent with the sample's effect key (third-party). [maxine-pipewire include/nvafx_types.h](https://github.com/Darudas/maxine-pipewire)

**Chained effects**
- Only two Speaker Focus chains exist, and Speaker Focus is always **first**, BNR second (code). [linux effects_demo.cpp @3.0.0 L468–471](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L458-L471)

  | Chain tuple (effect1, effect2, rate1, rate2) | Selector |
  |---|---|
  | `("speaker_focus","denoiser",16000,16000)` | `NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_16k_DENOISER_16k` |
  | `("speaker_focus","denoiser",48000,48000)` | `NVAFX_CHAINED_EFFECT_SPEAKER_FOCUS_48k_DENOISER_48k` |

- The Windows sample keys these chains as `"speaker_focus16k_denoiser16k"` and `"speaker_focus48k_denoiser48k"`, and logs "Capabilities of Denoiser Version 1 Effect will be applied along with Speaker Focus Effect in Chain" (code). [windows effects_demo.cpp @3.0.0 L776–784](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp#L776-L784)
- The chained scripts load the second model as `denoiser_{16,48}k.trtpkg`, i.e. the **v1** denoiser, not `denoiser_v2_16k.trtpkg` (code). [run_effect_chained.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect_chained.sh); [run_effects_demo.bat @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat)
- Docs: "Chaining effects only support combinations of Superres+Denoiser/Dereverb/Combined Denoiser+Dereverb effect and Denoiser + Speaker Focus. Other effect chains are not supported." (snippet). [AFX Create a Chained Audio Effect](https://docs.nvidia.com/maxine/afx/latest/UseAFXInApps/CreateChainedAudioEffect.html); [Chain Multiple Effects (Windows)](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ChainMultipleEffects.html)
- The Windows batch script's list of supported chains shows `speaker_focus (16k->16k) + denoiser (16k->16k)` and `speaker_focus (48k->48k) + denoiser (48k->48k)` only. There is **no** superres8k→16k + Speaker Focus chain and no dereverb + Speaker Focus chain (code). [run_effects_demo.bat @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat)
- A chained handle takes list-valued parameters, one entry per effect (code). [windows effects_demo.cpp @3.0.0 L798–888](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp#L798-L888)
  - `NvAFX_SetStringList(NVAFX_PARAM_MODEL_PATH, {sf_model, bnr_model}, 2)`
  - `NvAFX_SetU32List(NVAFX_PARAM_INPUT_SAMPLE_RATE / OUTPUT_SAMPLE_RATE, …, 2)`
  - `NvAFX_SetFloatList(NVAFX_PARAM_INTENSITY_RATIO, …, 2)`
  - Getters use `NvAFX_GetU32List` for channels and samples per frame.
  - The sample errors out if effect 1's output rate ≠ effect 2's input rate.
- On Linux multi-GPU systems, `NVAFX_PARAM_CHAINED_EFFECT_GPU_LIST` (a U32 list) places each chained effect on its own GPU (code + snippet). [linux effects_demo.cpp @3.0.0 L501](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L501); [AFX Use Multiple GPUs](https://docs.nvidia.com/maxine/afx/latest/UseAFXInApps/UseMultipleGPUs.html)
- The third-party maxine-pipewire header defines chain strings `"denoiser16k_speaker_focus16k"` / `"denoiser48k_speaker_focus48k"`, i.e. **reversed order**. This **contradicts** NVIDIA's official sample naming, so treat that repo as unreliable (third-party). [maxine-pipewire](https://github.com/Darudas/maxine-pipewire)

**Model files and packaging**
- **Linux model path** (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
  - `../../features/speaker_focus/models/${arch}/speaker_focus_${sample_rate}k.trtpkg` → `speaker_focus_16k.trtpkg` or `speaker_focus_48k.trtpkg`, where `arch` is `sm_XX`.
  - Each feature's `lib/` directory is added to the RPATH. [AudioEffectsLibraryCommon.cmake @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/AudioEffectsLibraryCommon.cmake)
- **Linux GPU → arch map** in the 3.0.0 sample (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)

  | Arch | GPUs |
  |---|---|
  | sm_70 | v100 |
  | sm_75 | t4 |
  | sm_80 | a100, a30 |
  | sm_86 | a2, a10, a16, a40 |
  | sm_89 | l4, l40 |
  | sm_90 | h100 |
  | sm_100 | b100, b200 |
  | sm_120 | rtx_pro_6000 |

  - If no GPU is given, the compute capability is auto-detected.
  - The earlier survey recorded MIG support only on A30/A100 in the 2.1 docs. [AFX 2.1.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/GetStartedOnLinux.html)
- **Windows packaging:** features install as `%AFX_SDK_ROOT%\features\nvafx<name>\` (for example `nvafxspeakerfocus`, giving the macro `EFFECT_NVAFXSPEAKERFOCUS`) with a `bin` folder. CMake reads each feature header's `NVAFX_<FEATURE>_VERSION_STRING`. A feature is enabled only if its major.minor matches the SDK's and its release number is ≥ the SDK's, so feature packs are versioned with the core SDK (code). [FindAFXSDKFeatures.cmake @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/cmake/FindAFXSDKFeatures.cmake); [VersionCheck.cmake](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/cmake/VersionCheck.cmake); [run_effects_demo.bat](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat)
- **Linux linking:** link the core library `libnv_audiofx.so` at build time, or `dlopen`/`dlsym` it. Dependent CUDA libraries ship in the SDK (`external/cuda/lib`). Older drivers can use CUDA forward-compat user-mode libraries (`libcuda.so.*`, `libnvidia-ptxjitcompiler.so.*`) (snippet). [AFX 3.0.0 Build Applications](https://docs.nvidia.com/maxine/afx/3.0.0/UseAFXInApps/BuildApplicationsWithTheSDK.html); [AFX 3.0.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/3.0.0/LinuxAFXSDK/GetStartedOnLinux.html)
- **CUDA runtime check:** `NvAFX_CreateEffect` / `NvAFX_CreateChainedEffect` can return `NVAFX_UNSUPPORTED_RUNTIME` if the CUDA runtime/driver is too old. The sample prints "requires >= CUDA_SUPPORTED_RUNTIME" and suggests forward-compat (FCU) libraries (code). [linux effects_demo.cpp @3.0.0 L396–403](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L396-L403)
- **Container:** the sample Dockerfile is `FROM ubuntu:20.04` + cmake/make/g++, with the SDK copied to `/opt/nvidia/Audio_Effects_SDK`. It needs Docker ≥ 20.10.21 with the NVIDIA Container Toolkit, and the host driver is used. The `config.sh` tag still reads `2.1.0` in the 3.0.0 branch (code). [linux/container @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/3.0.0/linux/container)

**Audio format and sample rates**
- "Supported input/output format is 32-bit float audio with a sampling rate of 16 kHz or 48 kHz… supports mono-channel input and output" (snippet). [AFX latest Speaker Focus](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 2.1.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/2.1.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- The Windows script lists `speaker_focus - Input SR: 16k/48k - Output SR: 16k/48k`. It only accepts 16k→16k or 48k→48k (`validate_sample_rates`), so Speaker Focus does **no internal resampling** (code). [run_effects_demo.bat @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat)
- After `NvAFX_Load`, the Windows sample reads back `NVAFX_PARAM_INPUT_SAMPLE_RATE` / `OUTPUT_SAMPLE_RATE` and fails if they differ from what was requested ("do not match the loaded model"). The rate is therefore baked into the `.trtpkg` (code). [windows effects_demo.cpp @3.0.0 L1112–1120](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)

**Frame size (samples per frame)**
- Linux scripts: `-f, --frame_size: frame size to be used 10/20ms [default=10]`.
  - The demo converts milliseconds to samples as `input_sample_rate*frame_size/1000`: 160 or 320 samples at 16k, 480 or 960 at 48k.
  - It validates that value against `NVAFX_PARAM_SUPPORTED_NUM_SAMPLES_PER_FRAME`, a U32 list queried with the two-call pattern where the first call returns `NVAFX_STATUS_OUTPUT_BUFFER_TOO_SMALL`.
  - It then sets `NVAFX_PARAM_NUM_SAMPLES_PER_INPUT_FRAME` before `NvAFX_Load`.
  - If no frame size is configured, it uses `supported_list[0]`.

  (code) [linux effects_demo.cpp @3.0.0 L507–585](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L507-L585)
- Unlike Studio Voice, **no frame-size override exists for Speaker Focus**. The scripts force Studio Voice LL to 10 ms ("online, supports smaller frame sizes") and Studio Voice HQ to 6000 ms ("offline, supports only a larger frame size"). Speaker Focus keeps the generic 10/20 ms path (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- Docs: "frame size can be specified as either 10 or 20 milliseconds, with a default value of 10… each frame is passed in every 10ms, like how audio is received from a physical microphone" (snippet). [AFX 3.0.0 effects_demo Application](https://docs.nvidia.com/maxine/afx/3.0.0/LinuxAFXSDK/SampleApplicationsLinux/EffectsDemoApplication.html)

**Parameters Speaker Focus does *not* use in the official samples**
- **VAD:** "VAD is supported only for denoiser and dereverb_denoiser effect". `NVAFX_PARAM_ENABLE_VAD` is set, and `NvAFX_GetBoolList(NVAFX_PARAM_VAD_RESULT)` is read, only for those two effects. VAD is also "not supported for chaining" (code). [windows effects_demo.cpp @3.0.0 L673–686, L1052–1055](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp); [linux effects_demo.cpp @3.0.0 L409–412](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L409-L412)
- **Intensity ratio:** the Linux sample sets `NVAFX_PARAM_INTENSITY_RATIO` only when the effect list contains denoiser, dereverb or dereverb_denoiser (`kIntensityRatioSupportedEffects`). It also tolerates `NVAFX_STATUS_INVALID_PARAM`. The Windows sample calls `NvAFX_SetFloat(INTENSITY_RATIO)` for every effect but with non-fatal `CHECK_STATUS` (code). [linux effects_demo.cpp @3.0.0 ~L624–644](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp); [windows effects_demo.cpp @3.0.0 L1049](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- Search summary of the API docs: the intensity ratio "is currently supported only for setting per-stream intensity ratio for the Background Noise Removal effect" (snippet, paraphrased by the search tool, so medium confidence). [AFX 3.0.0 Functions](https://docs.nvidia.com/maxine/afx/3.0.0/APIReference/AFXFunctions.html); [AFX Set Parameters](https://docs.nvidia.com/maxine/afx/latest/UseAFXInApps/SetParametersOfAnEffect.html)
- **Effect version:** `NVAFX_PARAM_EFFECT_VERSION` (1/2) applies only to `denoiser` (code). [windows effects_demo.cpp @3.0.0 L1036–1046](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **No enrollment or reference input:**
  - Speaker Focus setup passes only model path, rates, stream count and frame size.
  - The removed Voice Font effect needed a separate reference model and reference WAV (`voice_font_reference.trtpkg` plus `input_farend`/`reference` lists in 2.x scripts).
  - The third-party header shows a `NVAFX_PARAM_REFERENCE_AUDIO` parameter, apparently for Voice Font.
  - Nothing like it is used for Speaker Focus.

  (code / third-party) [run_effect.sh diff 2.1.0→3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/2.1.0/linux/effects_demo/run_effect.sh); [maxine-pipewire](https://github.com/Darudas/maxine-pipewire)

**Multi-stream batching, active streams, reset (Linux)**
- **Stream count:** `NvAFX_SetU32(handle, NVAFX_PARAM_NUM_STREAMS, num_streams)` is set before `NvAFX_Load`; the demo uses one stream per input WAV. The scripts allow `-b, --batch_size … [default=1, max=1024]` for Speaker Focus. Only Studio Voice is restricted to batch 1 ("studio_voice low_latency and high latency supports only 1 batch size") (code). [linux effects_demo.cpp @3.0.0 L532](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L532); [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **Buffer layout:** stream-major, contiguous per stream. `input_frame[i*num_input_samples_per_frame …]` for stream *i*, size `num_channels*samples_per_frame*num_streams`. A **single** `NvAFX_Run(handle, input, output, num_input_samples_per_frame, num_input_channels)` processes all streams (code). [linux effects_demo.cpp @3.0.0 L775–853](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L775-L853)
- **Per-stream reset:** `NvAFX_Reset(handle, NvAFX_Bool* bitmap, n)` resets only the flagged streams. The demo uses it when a stream slot moves on to a new file (`-r` → `reset 2 3 5`, which needs batch ≥ 5 for non-Studio-Voice effects, including Speaker Focus) (code). [linux effects_demo.cpp @3.0.0 L837](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L837); [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **Windows reset:** the Windows 3.0.0 sample calls single-argument `NvAFX_Reset(handle_)`. The old v1.3.0 header also declares `NvAFX_Reset(NvAFX_Handle effect)` (code). [windows effects_demo.cpp @3.0.0 L569](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp); [nvAudioEffects.h v1.3.0](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK/blob/main/nvafx/include/nvAudioEffects.h)
- **Active streams (asynchronous arrival):** `NvAFX_SetBoolList(handle, NVAFX_PARAM_ACTIVE_STREAMS, activity_map, n)` marks which streams hold valid data for the next `NvAFX_Run`. The `effects_delayed_streams_demo` runs "one-step/two-step delayed" streams in extra Run calls. It **explicitly supports `speaker_focus`** and its chains (code). [effects_delayed_streams_demo.cpp @3.0.0 L289–323, L487–491](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_delayed_streams_demo/effects_delayed_streams_demo.cpp)
- **Older batching guidance:** in older (1.x-style) docs, the model "gives the best throughput performance when the number of audio streams is set to 64 or a multiple of 256". The example `denoiser_48k_1152.trtpkg` serves 1–1152 streams (snippet; this reflects older per-batch model naming, and 2.x/3.x models are named without batch size). [AFX Set Parameters (2.0.0)](https://docs.nvidia.com/maxine/afx/2.0.0/UseAFXInApps/SetParametersOfAnEffect.html)

**GPU / CUDA settings**
- **Device selection:**
  - `NVAFX_PARAM_USE_DEFAULT_GPU` (U32) lets the SDK pick the GPU.
  - `NvAFX_GetSupportedDevices(handle,&num,nullptr)` returns `NVAFX_STATUS_OUTPUT_BUFFER_TOO_SMALL` plus a count, then the device list sorted by priority.
  - On multi-GPU hosts, the sample advises `CUDA_VISIBLE_DEVICES`.

  (code) [linux effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp); [windows effects_demo.cpp @3.0.0 L1060–1080](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **User CUDA context:** v1.3.0 also has `NVAFX_PARAM_USER_CUDA_CONTEXT`, which "cannot be used at the same time" as `USE_DEFAULT_GPU` (code, 1.3.0). [nvAudioEffects.h v1.3.0](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK/blob/main/nvafx/include/nvAudioEffects.h)
- **CUDA graphs:**
  - "By default, graphs are enabled in the Windows SDK". Disable them with `NvAFX_SetU32(effect, NVAFX_PARAM_DISABLE_CUDA_GRAPH, 1)` before loading.
  - "CUDA graph enable/disable is available on Windows only".
  - Graphs can conflict with other applications that use CUDA graphs.

  (snippet) [AFX Chain Multiple Effects / Windows docs](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ChainMultipleEffects.html)
- **Windows ARM64 (N1X):** the sample sets `NVAFX_MODEL_CACHE_MODE` and `NVAFX_MODEL_CACHE_DIRECTORY` (code). [windows effects_demo.cpp @3.0.0 L1002–1008](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **Logging:** `NvAFX_InitializeLogger(severity, target, file, cb, userdata)` / `NvAFX_UninitializeLogger()` (code). [linux effects_demo.cpp @3.0.0 L321](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp)

**Lifecycle**
- The typical call order is below (code). [windows effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
  1. `CreateEffect`
  2. Set `MODEL_PATH`, `INPUT_SAMPLE_RATE`, `OUTPUT_SAMPLE_RATE`, `NUM_STREAMS`, and optionally `NUM_SAMPLES_PER_INPUT_FRAME`
  3. `Load`
  4. Get `NUM_INPUT_CHANNELS`, `NUM_OUTPUT_CHANNELS`, `NUM_SAMPLES_PER_INPUT_FRAME` and `NUM_SAMPLES_PER_OUTPUT_FRAME`
  5. Loop `Run`
  6. `Reset`
  7. `DestroyEffect`
- For effects other than Superres, output samples per frame equal input samples per frame. The Linux demo reads `NUM_SAMPLES_PER_OUTPUT_FRAME` because "Superres has more number of output samples" (code). [linux effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp)

**Sample data**
- The official Speaker Focus inputs are named as follows (code; format read from the WAV headers). [linux/input_files/speaker_focus @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/3.0.0/linux/input_files/speaker_focus); [windows chaining inputs](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/3.0.0/windows/apps/effects_demo/input_files/chaining)
  - `speaker_focus_16k_1.wav`: 16-bit PCM mono 16 kHz, 403,826 B ≈ 12.6 s.
  - `speaker_focus_16k_short.wav`: 32-bit float mono 16 kHz, ≈ 2.3 s, used for reset tests.
  - Matching 48k files.
  - The Windows chain inputs are named `speaker_focus_keyboard_{16,48}k.wav`, the same size as the Linux `_1` files, i.e. multi-talker speech plus keyboard noise.

### Inferences
- **Selector string values.** The chained selector strings are probably `"speaker_focus16k_denoiser16k"` / `"speaker_focus48k_denoiser48k"`, by analogy with the v1.3.0 pattern (e.g. `"superres8kto16k_denoiser16k"`) and the Windows sample keys. The real 2.x/3.x header was not visible, so use the macros, not literals.
- **A BNR v2 chain is not official.** To get BNR v2 (the ASR-tuned denoiser) with Speaker Focus you must run **two separate handles**: `speaker_focus` → `denoiser` with `EFFECT_VERSION=2`. This is outside the supported chain and adds a second model pass.
- **Mapping to LiveKit.** One Linux handle with `NUM_STREAMS = max concurrent calls` fits the agent: pre-allocate slots, mark them in `ACTIVE_STREAMS`, and call `NvAFX_Reset(bitmap)` when a slot is reassigned to a new call. `NUM_STREAMS` is fixed at load, so resizing means reloading. The alternative is one handle per call, which is simpler but costs more GPU memory and CUDA contexts.
- **Frame size.** 10 ms at 16 kHz means 160 float32 samples per call, which matches LiveKit's 10 ms frames and Nemotron's 16 kHz input. Resample LiveKit 48 kHz to 16 kHz first, or run the 48k model and resample after it.
- **No SDK-side controls.** Speaker Focus exposes no intensity, VAD or enrollment knob in the samples. The only control points are chaining BNR and reset/state handling, so any "aggressiveness" tuning must happen outside the SDK, for example by mixing dry and wet signal.

### Gaps
- The actual `nvAudioEffects.h` for 2.x/3.x (and any Speaker Focus-specific parameter such as a speaker-selection or mode flag) could not be read. The headers ship only inside the SDK download.
- Whether Speaker Focus actually supports 20 ms frames: query `NVAFX_PARAM_SUPPORTED_NUM_SAMPLES_PER_FRAME` at runtime. Also unknown is whether `NVAFX_PARAM_INTENSITY_RATIO` is silently ignored or returns `INVALID_PARAM` for Speaker Focus.
- Maximum `NUM_STREAMS` for Speaker Focus models (the script max of 1024 is generic), and whether multi-stream is supported by the Speaker Focus model on every GPU arch.
- Which GPU architectures actually have Speaker Focus `.trtpkg` models published. The download script takes `--gpu`, but the per-arch availability list was not visible.

---

## 3. Algorithmic latency / look-ahead

### Takeaway
**No latency or look-ahead figure for Speaker Focus (or its BNR chain) was found in any reachable NVIDIA source.**

What is documented:

- Speaker Focus runs as a streaming ("online") effect on 10 ms (optionally 20 ms) frames with 1:1 in/out frames.
- The SDK's release-readiness criterion is compute-only: p95 `NvAFX_Run` < 10 ms, throughput > 1.0× real time.
- Other effects publish latencies well above one frame: Studio Voice LL 80 ms algorithmic, and Studio Voice "extra latency up to 110 ms".

So "10 ms frame" must not be read as "10 ms latency". Speaker Focus look-ahead must be measured.

### Cited Findings
- **Streaming path:** the Speaker Focus scripts use the generic frame path (`frame_size` 10/20 ms, default 10). Studio Voice HQ, by contrast, is "offline" with 6000 ms frames, and Studio Voice LL is "online" at 10 ms (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **Release readiness:**
  - The reference workload is Denoiser v2, 10 ms frames (160 samples) at 16 kHz.
  - Acceptance is "a p95 NvAFX_Run time below the 10-ms frame budget and p05 processing throughput above 1.0x real time" for "both reference workloads".
  - GPU utilisation and memory are sampled from nvidia-smi.

  (snippet) [AFX 3.0.0 Windows Performance and Deployment Guide](https://docs.nvidia.com/maxine/afx/3.0.0/WindowsAFXSDK/ReleaseReadiness.html); [latest](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ReleaseReadiness.html)
- **Studio Voice latency:**
  - Studio Voice Low Latency (48 kHz) has **80 ms** algorithmic latency (snippet, from the earlier survey). [AFX docs index](https://docs.nvidia.com/maxine/afx/latest/index.html)
  - The Studio Voice page says outputs "might have extra latency (up to 110 ms) and might not be generated in real time on lower-end GPUs" (snippet). [AFX 3.0.0 Studio Voice](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutStudioVoiceEffect.html); [AFX 2.0.0 Studio Voice](https://docs.nvidia.com/maxine/afx/2.0.0/AboutTheEffects/AboutStudioVoiceEffect.html)
- **Studio Voice NIM:** "the 10 ms window setting the practical floor for end-to-end latency" (snippet, from the earlier survey). [NIM Studio Voice H4M limitations](https://docs.nvidia.com/nim/maxine/studio-voice-h4m/latest/limitations.html)
- **Search dead end:** a targeted search for Speaker Focus look-ahead or algorithmic latency returned only frame-size text: "specific details about the Speaker Focus effect's algorithmic latency and lookahead… were not explicitly detailed" (snippet). [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf)
- **Third-party claim:** maxine-pipewire claims "Latency ~10 ms" for Speaker Focus and ~10 ms for nearly every effect, including Studio Voice LL. That contradicts NVIDIA's 80 ms Studio Voice LL figure, so these look like frame-size placeholders, **not measurements** (third-party; unreliable). [maxine-pipewire doc/EFFECTS.md](https://github.com/Darudas/maxine-pipewire)
- **Marketing claim:** a third-party marketing blog claims AFX adds "only 10–20 ms of latency instead of 80–150 ms" for a CPU pipeline. It is unsourced marketing (snippet). [VoxBooster blog](https://voxbooster.com/blog/voice-changer-nvidia-maxine/)

### Inferences
- **Minimum delay.** End-to-end added delay is at least one frame (10 ms) of buffering plus `NvAFX_Run` time (p95 < 10 ms by NVIDIA's gate for BNR; unknown for Speaker Focus), plus any internal model look-ahead (STFT window overlap / future context).
- **Plausible range.** Separation and extraction models typically need 20–40+ ms of STFT context. A realistic guess for Speaker Focus is 20–60 ms total, but it is **unverified**.
- **Chain adds more.** The Speaker Focus → BNR chain adds BNR's own look-ahead, which is also undocumented.
- **How to measure.** Pass a click or chirp embedded in speech through `NvAFX_Run` and cross-correlate input and output, or compare speech-onset timestamps. Run both 16k and 48k, and both standalone and chain. Count leading output frames that are silent or "warm-up" after `NvAFX_Reset`.
- **No low-latency mode.** Unlike Studio Voice (HQ vs LL), there is no evidence of a separate low-latency Speaker Focus variant; only `speaker_focus_{16,48}k` exist.

### Gaps
- Speaker Focus algorithmic latency, look-ahead, warm-up/convergence time after reset or at stream start, and the chain's combined latency are all undocumented in reachable sources.
- BNR v1/v2, dereverb and AEC algorithmic latencies were not found either, so there is no in-family anchor for inference beyond Studio Voice.

---

## 4. Performance: streams per GPU, GPU memory, throughput

### Takeaway
**No published Speaker Focus performance table was found:** no streams per GPU, per-stream memory or throughput for T4/L4/A10/A100/H100/L40S/RTX.

What is known:
- **Supported hardware:** Speaker Focus runs through TensorRT `.trtpkg` models built per SM architecture, from sm_70/75 up to sm_120.
- **Batching:** it supports multi-stream batching up to the samples' generic cap of 1024.
- **CUDA graphs:** on Windows it historically could not use CUDA graphs, and the chain still cannot. That implies higher per-call CPU overhead than BNR.
- **Performance gate:** NVIDIA's generic gate is p95 `NvAFX_Run` < 10 ms, measured for BNR/Studio Voice, not Speaker Focus.

### Cited Findings
- **Deployment targets:** the Linux SDK is "designed and optimized for server-side (datacenter or cloud) deployments"; the Windows SDK is "optimized for client-side application integration". The Linux SDK needs "a minimum of 10 GB RAM and NVIDIA GPUs with Tensor Cores" (snippet). [NGC Linux AFX](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-); [AFX 2.0.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/2.0.0/LinuxAFXSDK/GetStartedOnLinux.html)
- **GPU list:** T4 (sm_75), V100 (sm_70), A100/A30 (sm_80), A2/A10/A16/A40 (sm_86), L4/L40 (sm_89), H100 (sm_90), B100/B200 (sm_100) and RTX PRO 6000 (sm_120) (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **Sample configs:** the only per-GPU configs shipped are `{t4,a10,a100,v100}_denoise{16,48}k_1_cfg.txt`, all for the denoiser. There are none for Speaker Focus (code). [linux/effects_demo @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/tree/3.0.0/linux/effects_demo)
- **Batch size:** `-b, --batch_size … [default=1, max=1024]` is generic across effects; only Studio Voice is capped at 1 (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **What the demo times:** the Windows 3.0.0 demo reports per-frame `NvAFX_Run` latency with an `ApiTimer` ("effects_demo.exe reports NvAFX_Run latency per frame"). No numbers are published in the repo (code). [windows effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **Older throughput guidance:** best throughput at 64 streams or multiples of 256 (1.x-era denoiser guidance) (snippet). [AFX Set Parameters 2.0.0](https://docs.nvidia.com/maxine/afx/2.0.0/UseAFXInApps/SetParametersOfAnEffect.html)
- **Search dead end:** searches for a per-GPU performance table returned no Speaker Focus numbers ("the actual table data wasn't captured") (snippet). [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf)
- **Third-party estimates:** maxine-pipewire gives Speaker Focus ≈ 250 MB VRAM and 3–7 % of an RTX 3060, with no methodology (third-party; unreliable). [maxine-pipewire](https://github.com/Darudas/maxine-pipewire)
- **Other effects, for comparison:** AFX 2.0 and later hosts per-effect Maxine NIMs (BNR, Studio Voice) with their own performance pages. There is none for Speaker Focus (see Q6).

### Inferences
- **Memory.** Speaker Focus probably costs more than BNR per stream (a separation model versus a mask-based denoiser), and GPU memory is dominated by the TensorRT engine plus per-stream state.
- **Sizing is guesswork.** For a single-digit to low-hundreds concurrent-call agent, an L4 or T4 is likely sufficient compute-wise, but this is a guess. It must be benchmarked with `effects_demo -b N` on the target GPU, alongside Nemotron and Sortformer on the same GPU.
- **CPU overhead on Windows.** With CUDA graphs disabled (Windows chain), per-`NvAFX_Run` CPU launch overhead rises. On Linux, CUDA-graph control is unavailable (Windows-only), so graph behaviour on Linux is unknown.

### Gaps
- No NVIDIA figures for Speaker Focus: streams/GPU, memory per stream, p50/p95 `NvAFX_Run`, or MIG behaviour, for any GPU.
- No independent benchmarks (forum reports and blogs) of Speaker Focus performance were found. forums.developer.nvidia.com was unreachable, and search showed no Speaker Focus threads.

---

## 5. Behaviour: how the "prominent" speaker is chosen, silence and TV leakage, switching, backchannels, overlap, far-field, 8 kHz, music, reverberation; underlying model

### Takeaway
NVIDIA documents only the outcome:

- It "identifies and isolates the primary/prominent speaker… removes the speech of all other speakers", handles "up to four speakers" and "various types of background noises".
- The GTC wording is "separates the audio tracks of **foreground** and **background** speakers".

It is **enrollment-free**: the samples expose no reference or enrollment input. **Nothing is documented** about:

- the selection criterion (loudness, proximity or first talker)
- what happens when the primary speaker is silent
- switching between speakers
- short utterances or backchannels
- overlapped speech
- far-field or speakerphone input
- 8 kHz input
- music
- reverberation

No NVIDIA paper describing the model was found.

### Cited Findings
- **What it does:** "identifies and isolates the primary speaker from all other speakers and removes the speech of all other speakers from the input audio, which significantly improves the intelligibility of the speech of the primary speaker". Alternate phrasing: "identifies and isolates the prominent speaker by removing all background speakers" (snippet). [AFX latest Speaker Focus](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 2.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/2.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- **Coverage:** "supports audio with up to four speakers and the noises listed earlier". The noise list itself was not retrievable, and the search tool only guessed "babble, music" (snippet). [AFX 2.1.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/2.1.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- **GTC 2022 wording:** "separates the audio tracks of foreground and background speakers, making each voice more intelligible" (snippet). [NVIDIA blog 2022-09-20](https://blogs.nvidia.com/blog/2022/09/20/maxine-cloud-native)
- **No enrollment in code:** the Speaker Focus API use in all official samples is model path, rate, streams, frame size and Run. There is no reference audio, speaker embedding, "target speaker" parameter or intensity control (code). [linux effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp); [windows effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp)
- **Stateful streaming:** Speaker Focus has per-stream state that must be cleared with `NvAFX_Reset(bitmap)` when a stream slot switches to a new audio source. The demos reset exactly when a new file starts in a slot (code). [linux effects_demo.cpp @3.0.0 L783–841](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/effects_demo.cpp#L783-L841)
- **Rates:** only 16 kHz and 48 kHz are accepted, with no 8 kHz model. The only official 8 kHz path in AFX is Superres 8k→16k, which chains only with denoiser, dereverb and dereverb_denoiser, **not** with Speaker Focus (code + snippet). [run_effects_demo.bat @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/scripts/run_effects_demo.bat); [AFX Create a Chained Audio Effect](https://docs.nvidia.com/maxine/afx/latest/UseAFXInApps/CreateChainedAudioEffect.html)
- **Selection rule, third-party only:** maxine-pipewire describes Speaker Focus as isolating "the primary (loudest/nearest) speaker". No NVIDIA source was found for "loudest/nearest" (third-party; unverified). [maxine-pipewire doc/EFFECTS.md](https://github.com/Darudas/maxine-pipewire)
- **No research found:** searches for an NVIDIA paper or GTC talk on the Speaker Focus model (primary-speaker extraction without enrollment) found none. Results were only adjacent NVIDIA work (TitaNet speaker embeddings; Streaming Sortformer diarization; the Maxine Active Speaker Detection NIM, which is video-based) (snippet). [NVIDIA Streaming Sortformer blog](https://developer.nvidia.com/blog/identify-speakers-in-meetings-calls-and-voice-apps-in-real-time-with-nvidia-streaming-sortformer/); [NVIDIA Conv-AI speaker-recognition publications](https://research.nvidia.com/labs/conv-ai/publications/category/speaker-recognition/); [NIM Active Speaker Detection](https://docs.nvidia.com/nim/maxine/active-speaker-detection/latest/overview.html)
- **No user reports:** no forum threads or user reports on Speaker Focus behaviour were found. Search for forums.developer.nvidia.com "speaker focus" returned only docs and NGC pages (snippet). [NGC Linux AFX](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)

### Inferences
- **How it probably picks the speaker.** "Prominent / foreground / primary" with no enrollment implies a **level- or proximity-dominance heuristic learned by the model**: near-field, higher direct-to-reverberant ratio, louder speech is kept. This is the same class as Krisp BVC and ai-coustics Voice Focus.
- **Risk: TV louder than the caller.** If a TV or bystander is louder or closer than the caller (speakerphone, far-field caller, loud TV), Speaker Focus may keep the wrong voice or flip between voices. Nothing in the docs suggests a "lock on the first talker" mechanism.
- **Risk: primary speaker silent.** When the caller is silent and only the TV talks, the TV voice may become "prominent" and leak through. This is plausible for dominance-based models and unverified for Speaker Focus. It matters directly for false barge-in and VAD triggering in the agent.
- **Risk: backchannels.** Short, quiet backchannels ("mm-hm", "yeah") from the caller under simultaneous TV speech are at risk of attenuation. Speaker Focus is trained to keep one talker's speech, so isolated backchannels with no competing speech *should* pass, but overlapped quiet backchannels are the hardest case.
- **8 kHz telephony.** Inputs (SIP/PSTN via LiveKit) must be upsampled to 16 kHz first. Use a plain resampler, or a separate Superres 8k→16k handle (not an official chain), and test both. Band-limited 8 kHz content upsampled to 16 kHz is out-of-distribution if Speaker Focus was trained on wideband speech, which is plausible but not documented.
- **Stack mitigation.** Sortformer speaker IDs in the NeMo stack provide an independent check: gate barge-in and turn-taking by the locked caller ID. This catches Speaker Focus failures (leakage or wrong-talker lock) and is safer for backchannels than audio-level suppression alone.

### Gaps
- Selection criterion, adaptation or lock-in behaviour, and behaviour with the primary speaker silent, overlapping speech, speaker switches, backchannels, far-field/speakerphone, music (including TV music beds), reverberant rooms and non-English speech: **all undocumented**. They must be measured on in-domain audio.
- The documented "noises listed" for Speaker Focus (noise categories) could not be retrieved.
- Model architecture, training data, and whether the 16k and 48k models differ beyond rate are all unknown.

---

## 6. Relationship to other NVIDIA audio features (BNR, Studio Voice, Room Echo Removal, AEC, Superres, Broadcast, NIMs, Riva)

### Takeaway
Speaker Focus lives only in the **AFX SDK**: Windows client, Linux server, and Windows ARM64 in 3.0. It is the only AFX effect that removes competing talkers, and its only official chain partner is **BNR (v1 model)**.

- **No Speaker Focus NIM:** the NIM clients repo (as of July 2026) has none. NIMs exist for BNR, Studio Voice, Active Speaker Detection and others.
- **No Speaker Focus in NVIDIA Broadcast:** the consumer app offers Noise Removal, Room Echo Removal and Studio Voice-style enhancement, not Speaker Focus.
- **No Riva front-end enhancer.** No Speaker Focus-like feature was found in Riva.
- **Other effects:** Studio Voice is an enhancement/restoration effect with much higher latency. AEC and Voice Font were dropped in AFX 3.0.

### Cited Findings
- **AFX 3.0.0 Windows effect set:** BNR v1/v2, Room Echo Cancellation (REC), REC+BNR, Audio Super Resolution, Speaker Focus, and Studio Voice HQ/LL with mic profiles (code). [windows/README.md @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/README.md)
- **AFX 2.x effect set:** the above plus AEC and Voice Font HQ/LL (code). [windows/README.md @2.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/2.0.0/windows/README.md)
- **Linux 3.0.0 effect set:** denoiser, dereverb, dereverb_denoiser, superres, speaker_focus, studio_voice_low_latency (48 kHz only) and studio_voice_high_quality (16/48 kHz) (code). [run_effect.sh @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/linux/effects_demo/run_effect.sh)
- **BNR v2 is ASR-tuned:** "A second version of this effect offers improved accuracy for automated speech recognition" (snippet). [AFX BNR effect](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutNoiseRemovalBackgroundNoiseSuppression.html)
- **The official chain uses BNR v1:** "Capabilities of Denoiser Version 1 Effect will be applied along with Speaker Focus Effect in Chain" (code). [windows effects_demo.cpp @3.0.0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples/blob/3.0.0/windows/apps/effects_demo/effects_demo.cpp#L776-L784)
- **NIM list:** the `NVIDIA-Maxine/nim-clients` repo (HEAD `7ada346`, 2026-07-15 "Lipsync v1.3.0") contains `active-speaker-detection`, `audio2face-2d`, `bnr`, `eye-contact`, `lipsync`, `relighting`, `st2110`, `studio-voice` and `synthetic-video-detector`. A full-text grep for "speaker focus / speaker_focus" found **no matches** (code). [nim-clients](https://github.com/NVIDIA-Maxine/nim-clients)
- **BNR NIM:** has streaming and transactional modes (snippet, from the earlier survey). [NGC BNR NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/maxine-bnr/-?_lr=1)
- **Studio Voice NIM:** "Streaming mode provides lower latency than transactional mode because it processes audio chunk-by-chunk without file I/O overhead" (code/README). [nim-clients studio-voice README](https://github.com/NVIDIA-Maxine/nim-clients/tree/main/studio-voice)
- **2022 Audio Effects microservice:** announced alongside Speaker Focus, it contained BNR, Room Echo Removal and Audio Super Resolution ("four state-of-the-art audio features"). Speaker Focus was announced as an SDK feature, not as part of the microservice (snippet). [NVIDIA Technical Blog: New Maxine microservices](https://developer.nvidia.com/blog/new-maxine-microservices-enhance-real-time-audio-and-video-effects-for-video-conferences-at-scale/)
- **NVIDIA Broadcast:** no "speaker focus" or background-voice removal feature was found. Its features are noise removal (mic and speaker side), room echo removal and a 2025 upgrade that replaces both with a "cleaner, more polished vocal track", i.e. Studio Voice-like. It is Windows + RTX only (snippet). [NVIDIA Broadcast app](https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/); [Broadcast FAQ](https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/faq/); [Interactive & Immersive HQ: Broadcast 2.0 (2025)](https://interactiveimmersive.io/blog/outputs/nvidia-broadcast-update/)
- **Riva:** no Riva speech-enhancement or "speaker focus" component was found. NVIDIA's multi-speaker tooling in the speech stack is diarization (Streaming Sortformer / "Nemotron 3 Diarization"), not audio isolation (snippet; earlier survey found the same). [NVIDIA Streaming Sortformer blog](https://developer.nvidia.com/blog/identify-speakers-in-meetings-calls-and-voice-apps-in-real-time-with-nvidia-streaming-sortformer/)
- **Licensing:** the Linux SDKs are included with an NVIDIA AI Enterprise (NVAIE) licence (snippet, from the earlier survey). [NGC Linux AFX](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)

### Inferences
- **Recommended pipeline shape.** For the agent, the NVIDIA-native front end is `resample→16 kHz float32 → [SF 16k → BNR v1 16k] (official chain)`, or `SF 16k → BNR v2 16k` (two handles, unofficial). Evaluate "BNR v2 only" as a baseline too, since Speaker Focus may hurt Nemotron WER or backchannels.
- **No container path.** There is no NVIDIA-supported container for Speaker Focus, because there is no NIM. Deploy it by embedding the Linux SDK (for example via the sample Ubuntu 20.04 container) in a sidecar service or a Python extension next to the LiveKit agent worker.
- **Mac dev.** Development on Apple Silicon cannot run any of this, since AFX is NVIDIA-GPU only (Windows and Linux).

### Gaps
- Whether NVIDIA plans a Speaker Focus NIM or GA is unknown; no roadmap statement was found.
- Whether Speaker Focus shares an architecture with BNR/Studio Voice, or with Broadcast's models, is unknown.
- Early Access licence terms (production use allowed? separate EA sign-up?) could not be read because the NGC and developer pages were blocked.
