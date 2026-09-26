# Commercial / proprietary voice isolation and noise suppression other than Krisp and ai-coustics: candidates for a self-hosted LiveKit + NeMo voice agent (as of Sept 2026)

Scope: the stack is LiveKit Agents 1.8.3 (Python), NeMo-Speech.cpp riva_server (Nemotron streaming ASR + Sortformer streaming diarization), Mac dev, and Linux prod on CPU or NVIDIA GPU. Caller audio must not leave the environment. The goal is to remove competing human speech (TV, bystanders, crosstalk) and noise before ASR, turn detection and barge-in, while keeping the caller's backchannels. Krisp and ai-coustics appear only for comparison.

Method note: this environment's egress proxy blocked direct fetches of docs.nvidia.com, forums.developer.nvidia.com, picovoice.ai, elevenlabs.io, sanas.ai, developer.sanas.ai, docs.retellai.com, vapi.ai, hecttor.ai, yobeinc.com, techcommunity.microsoft.com, speechmatics.com and assemblyai.com. For those vendors, the facts below come from **search-engine snippets of the cited page** and are marked "(snippet)". Facts marked "(fetched)" come from full pages that loaded: github.com, raw.githubusercontent.com and pypi.org (speechmatics-voice). Snippets can lose context, so treat them as less reliable than fetched pages.

---

## Q1. What each product does: plain noise suppression, background-voice / primary-speaker isolation, or enrollment-based personalized isolation

### Takeaway
Among the non-Krisp, non-ai-coustics options, verifiable real-time **primary-speaker isolation that removes competing voices** exists in five places:
- **NVIDIA Maxine/AFX "Speaker Focus"**: Early Access, GPU only.
- **Sanas SDK** voice-isolation models for agents.
- **Agora AI Noise Suppression v2.0.2**: "background voice removal", but only inside Agora RTC.
- **Cisco Webex "Optimize for my voice"**: inside Webex only.
- **Hecttor Orpheus SDK**: a 2025-26 newcomer; the claims are unverified.

**Microsoft Teams voice isolation** is enrollment-based and not licensable. **Apple Voice Isolation** is a user-selected OS mic mode. Picovoice Koala, NVIDIA BNR, ElevenLabs, Adobe, Auphonic, Dolby, Zoom, Google Meet and Tencent are noise suppression or offline enhancement, with no documented removal of competing talkers. Speechmatics and AssemblyAI offer *ASR-side* speaker focus, not audio isolation.

### Capability map (dense summary; details and sources below)

| Vendor / product | Class | Real-time streaming? | Deployment | Removes competing voices? |
|---|---|---|---|---|
| NVIDIA AFX SDK: BNR (Denoiser v1/v2), dereverb, AEC, SuperRes | Noise suppression / enhancement | Yes (10 ms frames) | On-prem SDK, Linux + Windows, NVIDIA GPU | No |
| NVIDIA AFX **Speaker Focus** (Early Access) | Primary-speaker isolation (no enrollment) | Yes | On-prem SDK, Linux + Windows, NVIDIA GPU | **Yes**, "removes all background speakers", up to 4 speakers |
| NVIDIA Maxine NIMs (BNR, Studio Voice) | Noise suppression / studio enhancement | Streaming + transactional modes | Self-hosted container (GPU) or NVIDIA-hosted API | No (no Speaker Focus NIM found) |
| NVIDIA Broadcast | Consumer app | Yes | Windows desktop + RTX only | No |
| Picovoice Koala | Noise suppression | Yes (frame-based) | On-device SDK: Linux, macOS arm64, Windows, mobile, web | Not claimed |
| Sanas SDK (agentic) | Noise cancellation + **voice isolation** mode | Yes ("server-side") | Server-side SDK; on-prem status unverified | **Yes** (vendor claim, AGENTIC_VI_G_NC) |
| Sanas agent desktop app | NC + voice isolation + accent translation | Yes | Windows agent desktop app | Yes (vendor claim) |
| Dolby.io / OptiView Media APIs (Enhance) | Offline enhancement | No (job-based) | Cloud, "legacy" | No |
| ElevenLabs Voice Isolator | Offline/near-line enhancement | Upload-then-stream-back endpoint | Cloud only | Removes "background noise" (not documented for competing talkers) |
| Adobe Podcast Enhance, Auphonic | Offline enhancement | No | Cloud / web | No |
| Apple Voice Isolation mic mode | OS mic mode | Yes, on-device | macOS/iOS capture only; user-selected | Attenuates "other signals"; not a server API |
| Microsoft Teams voice isolation | **Enrollment-based personalized** isolation | Yes | Teams clients only | Yes, needs a voice profile |
| Azure Communication Services audio effects | Noise suppression + AEC (DeepVQE) | Yes | Client SDK (Web: Chrome/Edge) | Claims to suppress "distant conversations" |
| Cisco Webex (BabbleLabs) "Optimize for my voice" | Primary (closest) speaker focus | Yes | Webex clients / Webex Calling | Yes (inside Webex) |
| Agora AI Noise Suppression v2.0.2 | NS + background voice removal | Yes (~40 ms web low-latency mode) | Agora RTC SDK extension | Yes (v2.0.2), but only within Agora |
| Zoom Video SDK | Noise suppression levels | Yes | Zoom SDK sessions | Not documented |
| Google Meet noise cancellation | Noise suppression | Yes | Meet only | Not an SDK |
| Tencent TRTC AI noise suppression | Noise suppression | Yes | TRTC SDK | Not documented |
| Twilio | Resells/integrates **Krisp** | Yes | Client plugin / Programmable Voice | (Krisp) |
| Vapi | Krisp "Smart Denoising" + experimental "Fourier Denoising" | Yes | Vapi cloud | Krisp BVC-style; Fourier is experimental |
| Retell | Denoising modes ($0.005/min) | Yes | Retell cloud | Has a mode aimed at background speech (vendor docs) |
| Speechmatics Voice SDK "Speaker Focus" | **Transcript-level** diarization filter | Yes | Cloud SDK (on-prem not documented) | Filters words, not audio |
| AssemblyAI Universal-3.5 Pro Realtime `voice_focus` | ASR-side speaker focus | Yes | Cloud | Claimed (details not verified) |
| Hecttor Orpheus SDK (newcomer) | Speaker isolation + turn-taking + VAD | Claimed real time | Claimed on-prem: Linux, macOS, Windows, browser | Claimed |
| Yobe (VISPR) | Voice identification / separation | Claimed | SDK | Claimed ("Identification Listening" for known speakers) |

### Cited Findings

**NVIDIA Maxine / Audio Effects (AFX) SDK**
- The AFX SDK offers noise removal and room echo removal for narrowband, wideband and ultra-wideband audio on Windows and Linux. "A second version of this effect [Background Noise Removal] offers improved accuracy for automated speech recognition" (snippet). Sources: [NVIDIA AFX docs, noise removal effect](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutNoiseRemovalBackgroundNoiseSuppression.html); [AFX 2.0.0 index](https://docs.nvidia.com/maxine/afx/2.0.0/index.html)
- The public GitHub repo lists five effects: Background Noise Suppression (denoising), Room Echo Cancellation (dereverb), dereverb + denoise, Acoustic Echo Cancellation, and Audio Super Resolution. Requirements: 64-bit Windows 10/11, NVIDIA Tensor Core GPU, driver ≥ 520.46. The repo carries MIT-licensed API source and samples; the "installer with DLLs and models" is hosted on the Maxine developer page (fetched). [GitHub NVIDIA-Maxine/Maxine-AFX-SDK](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK)
- **Speaker Focus** "identifies and isolates the prominent speaker by removing all background speakers from the input audio, improving the intelligibility of the primary speaker." It takes 32-bit float mono audio at 16 kHz or 48 kHz, "supports audio with up to four speakers and various types of background noises", is **Early Access** in both the Linux and Windows SDKs, and can be chained with Background Noise Removal at 16 kHz and 48 kHz (snippet). Sources: [AFX latest: About the Speaker Focus Effect](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 2.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/2.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- In AFX 3.0.0, Speaker Focus (16k and 48k versions) is still an Early Access feature that "must be explicitly named when downloading". Linux users get the Speaker Focus models from the SDK models directory via helper scripts that take a GPU argument (snippet). [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf); [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- The product has been renamed from "NVIDIA **Maxine** Audio Effects SDK" (2.0.0 docs) to "NVIDIA Audio Effects (AFX) SDK" (2.1.0 / 3.0.0 / latest docs titles) (snippet, from page titles). [AFX 2.0.0](https://docs.nvidia.com/maxine/afx/2.0.0/index.html) vs [AFX latest](https://docs.nvidia.com/maxine/afx/latest/index.html)
- **Maxine NIMs**: the NIM client repo lists Active Speaker Detection, Background Noise Removal (BNR), Eye Contact, LipSync, Relighting, Studio Voice, Synthetic Video Detector and Audio2Face-2D, plus ST 2110 variants. **No Speaker Focus NIM** is listed (fetched). [GitHub NVIDIA-Maxine/nim-clients](https://github.com/NVIDIA-Maxine/nim-clients)
- The BNR NIM (v1.0.0, released June 10, 2025) "removes a variety of background noises", "retains emotive tones", and has a **streaming mode** (real-time) and a **transactional mode** (whole-file) (snippet). [NGC: BNR NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/maxine-bnr/-?_lr=1); [build.nvidia.com BNR](https://build.nvidia.com/nvidia/bnr)
- The Studio Voice NIM has three modes: Quality 48 kHz, Quality 16 kHz and Low-Latency 48 kHz. On Holoscan-for-Media it processes audio in 10 ms frames; "the 10 ms window setting the practical floor for end-to-end latency" (snippet). [NVIDIA NIM Studio Voice H4M docs](https://docs.nvidia.com/nim/maxine/studio-voice-h4m/latest/limitations.html); [NGC Studio Voice](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/maxine-studio-voice/-)
- **NVIDIA Broadcast** (consumer app) is Windows-only and needs a GeForce RTX 2060 / Quadro RTX 3000 / TITAN RTX or better with Windows 10 64-bit (snippet). [NVIDIA Broadcast FAQ](https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/faq/)

**Picovoice Koala**
- Koala is "an on-device noise suppression engine" built on deep learning. Platforms: Linux x86_64; macOS x86_64 and arm64; Windows x86_64 and arm64; Android; iOS; Chrome/Safari/Firefox/Edge; Raspberry Pi 3/4/5. SDKs: Python, Java (Android), Swift, C, JS/TS (fetched). [GitHub Picovoice/koala](https://github.com/Picovoice/koala)
- Picovoice's 2026 "Voice Isolator Guide" describes voice isolation as suppressing "background noise, music, or other speakers" and recommends Koala. It says modern voice isolators handle non-stationary babble noise such as café chatter (snippet, vendor marketing). [Picovoice blog: Voice Isolator Guide 2026](https://picovoice.ai/blog/voice-isolator/)

**Sanas**
- Sanas runs a real-time speech-to-speech platform for contact centers: accent neutralization and background-noise removal (snippet). [Sanas noise cancellation page](https://www.sanas.ai/noise-cancellation?wGjRTY=lv1kykC)
- "Voice Isolation Mode … isolates and preserves only the foreground speaker while suppressing other voices" (snippet). [Sanas noise cancellation page](https://www.sanas.ai/noise-cancellation?wGjRTY=lv1kykC)
- The **Sanas SDK** is "a server-side audio enhancement toolkit that reduces WER … by cleaning and normalizing voice input before ASR". Developers pick **AGENTIC_VI_G_NC** (default; "full voice isolation") or **AGENTIC_ST_NC** ("preserve background speech in multi-speaker environments") (snippet). [Sanas Developer Hub: Welcome](https://developer.sanas.ai/Overview/Welcome-to-Sanas)
- The quickstart configures AGENTIC_VI_G_NC at 16000 Hz (snippet). [Sanas SDK Quickstart](https://developer.sanas.ai/SDK/Get-Started/Quickstart-Guide)
- Sanas also markets "Omni-directional" noise cancellation that cleans both the agent and the far-end customer (snippet). [Sanas blog: Omni-directional NC](https://www.sanas.ai/blog/introducing-noise-cancellation-with-omni-directional-capabilities-a-new-standard-in-voice-communication)

**Dolby**
- Dolby.io is now branded **Dolby OptiView**, organized around Real-time Streaming (formerly Millicast), Live Streaming (formerly THEOlive) and Playback (formerly THEOplayer). A third-party API profile marks Media APIs as "Legacy … migrating to the OptiView platform" and Communications APIs as "generally superseded by the OptiView product line". The Media API "Enhance" noise reduction is job-based cloud processing, not a real-time SDK (fetched; third-party profile, not Dolby). [GitHub api-evangelist/dolby-io](https://github.com/api-evangelist/dolby-io); [Dolby OptiView docs](https://optiview.dolby.com/docs/)

**ElevenLabs, Adobe, Auphonic**
- The ElevenLabs Voice Isolator "removes background noise from audio". The `/v1/audio-isolation/stream` endpoint "accepts an audio file" and streams the result back. With `pcm_s16le_16` input (16-bit, 16 kHz, mono) "latency will be lower than with passing an encoded waveform" (snippet). [ElevenLabs API: Audio isolation stream](https://elevenlabs.io/docs/api-reference/audio-isolation/stream)
- Adobe Podcast Enhance Speech v2 is a web tool; the free tier is "one file at a time, and limited to 30 minutes per file" (snippet, third-party). [Cleanvoice on Adobe Enhance](https://cleanvoice.ai/blog/adobe-podcast-enhance-speech/); [Adobe Enhance Speech v2](https://podcast.adobe.com/en/enhancespeech)
- Auphonic is presented as a post-production tool (leveling, loudness, noise reduction) to run after Adobe Enhance (snippet, third-party). [MixingGPT 2026 comparison](https://mixinggpt.com/blog/best-ai-audio-cleanup-tools-2026)

**Apple**
- `AVCaptureDevice.MicrophoneMode.voiceIsolation` "processes microphone audio to isolate the voice and attenuate other signals" (snippet). [Apple docs: MicrophoneMode.voiceIsolation](https://developer.apple.com/documentation/avfoundation/avcapturedevice/microphonemode/voiceisolation)
- `preferredMicrophoneMode` is **read-only**: only the user sets it in Control Center. Apps can only open the picker with `AVCaptureDevice.showSystemUserInterface(.microphoneModes)` (snippet). [Apple docs: preferredMicrophoneMode](https://developer.apple.com/documentation/avfoundation/avcapturedevice/preferredmicrophonemode); [WWDC21 "What's new in camera capture"](https://developer.apple.com/videos/play/wwdc2021/10047/); [Apple docs: SystemUserInterface.microphoneModes](https://developer.apple.com/documentation/avfoundation/avcapturedevice/systemuserinterface/microphonemodes)
- `kAudioUnitSubType_VoiceProcessingIO` and `AVAudioIONode.setVoiceProcessingEnabled(_:)` provide VoIP voice processing (echo cancellation, AGC and related). WWDC23 "What's new in voice processing" covers muted-talker detection and ducking (snippet). [Apple docs: VoiceProcessingIO](https://developer.apple.com/documentation/audiotoolbox/kaudiounitsubtype_voiceprocessingio); [setVoiceProcessingEnabled](https://developer.apple.com/documentation/avfaudio/avaudioionode/setvoiceprocessingenabled(_:)?changes=_8%2C_8); [WWDC23 10235](https://developer.apple.com/videos/play/wwdc2023/10235)
- WWDC25 "Enhance your app's audio recording capabilities" adds spatial-audio recording and editing that can "isolate speech and ambient background sounds" through AudioToolbox, AVFoundation and Cinematic frameworks (snippet). [WWDC25 session 251](https://developer.apple.com/videos/play/wwdc2025/251/)
- An Apple Developer Forums thread asks how to *read* the device's Voice Isolation status via Core Audio, which suggests limited programmatic control (title only). [Apple forums thread 757948](https://developer.apple.com/forums/thread/757948)

**Microsoft**
- Teams "voice isolation" ensures "only your voice is transmitted, suppressing unwanted background speech". It relies on an **enrollment voice profile**: the user reads a paragraph in one of 25 languages, and the profile is stored on the local device. It uses "a personalized deep voice quality enhancement AI model" (snippet). [Microsoft Tech Community: Teams voice isolation (2024)](https://techcommunity.microsoft.com/blog/microsoftteamsblog/voice-isolation-in-microsoft-teams-enables-personalized-noise-suppression-for-ca/4096077); [Microsoft Learn: manage voice isolation](https://learn.microsoft.com/en-us/microsoftteams/voice-isolation); [Teams support blog, June 2026](https://techcommunity.microsoft.com/blog/microsoftteamssupport/teams-meetings-voice-isolation-help-your-voice-stand-out/4524496)
- The Azure Communication Services Calling SDK uses a **DeepVQE** model for echo cancellation and noise suppression. Noise suppression targets "typing sounds, fan hums, distant conversations, or street noise". WebJS audio effects need Calling SDK ≥ 1.28.4 and Effects SDK ≥ 1.1.2, and run only on desktop Chrome and Edge. "Deep noise suppression" was in public preview (snippet). [Microsoft Learn: ACS AI](https://learn.microsoft.com/en-us/azure/communication-services/concepts/ai); [MicrosoftDocs azure-docs: audio quality enhancements (web)](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/communication-services/tutorials/audio-quality-enhancements/includes/web.md); [ACS manage audio filters](https://learn.microsoft.com/en-us/azure/communication-services/how-tos/calling-sdk/manage-audio-filters)

**Cisco Webex, Agora, Zoom, Google, Tencent, Twilio**
- Cisco Webex "Optimize for my voice" "focuses on the speaker closest to the microphone and suppresses distracting background conversations". Webex Calling can also remove background noise from external (non-Webex) callers. Cisco acquired BabbleLabs (2020) for this tech. Browser SDK noise reduction has been available since webex-js-sdk@2.19.1 (2022) (snippet). [Cisco: Audio Intelligence in Webex Calling](https://www.cisco.com/c/en/us/products/collateral/unified-communications/webex-calling/audio-intelligence-webex-calling-aag.html); [Webex Developers blog](https://developer.webex.com/blog/background-noise-reduction-added-to-webex-browser-sdk)
- Agora AI Noise Suppression: "v2.0.2 adds background voice removal, which further isolates the target voice in noisy or multi-speaker scenarios". Modes are Balance (0), Aggressive (1) and Ultra-low-latency (2). It runs "in the pre-processing stage" of the Agora SDK. The web low-latency mode is "approximately 40 ms" with "slightly reduced" denoising (fetched). [GitHub AgoraIO/docs-portal ai-noise-suppression.mdx](https://github.com/AgoraIO/docs-portal/blob/main/content/docs/en/realtime-media/voice/build/enhance-the-audio-experience/ai-noise-suppression.mdx)
- Agora's product page lists Web, iOS, Android, Mac, Windows, Unity, React Native, Flutter, **Linux** and Electron, and claims removal of 100+ noise types including "background conversations" (snippet). [Agora AI Noise Suppression product](https://www.agora.io/en/products/ai-noise-suppression/)
- Zoom Video SDK exposes `setSuppressBackgroundNoiseLevel`. "Original sound" disables suppression (snippet). [Zoom Video SDK core audio features](https://developers.zoom.us/docs/video-sdk/windows/audio/)
- Google Meet noise cancellation is a user-facing Meet feature (snippet). [Google Meet Help: Filter out noise](https://support.google.com/meet/answer/9919960?hl=en&co=GENIE.Platform%3DDesktop)
- Tencent TRTC AI noise suppression comes from Tencent Tianlai Labs and is built into the TRTC SDK (on by default in TUIRoomKit) (snippet). [Tencent RTC docs: AI Noise Suppression](https://trtc.io/document/66040); [TUIRoomKit AI noise reduction](https://www.tencentcloud.com/document/product/647/60485)
- Twilio's noise cancellation is **Krisp**: a client-side Krisp Audio Plugin for Twilio Video, and a Krisp plugin for Twilio Programmable Voice that removes "unwanted background noise and voices" (snippet). [Twilio: Noise Cancellation](https://www.twilio.com/docs/video/noise-cancellation); [Krisp blog: Twilio Voice](https://krisp.ai/blog/krisp-delivers-leading-ai-noise-cancellation-to-twilio-voice-customers/)

**Voice-agent platforms**
- Vapi "Smart Denoising uses Krisp's AI-powered technology". "Fourier Denoising" is a "highly experimental" frequency-domain filter that detects persistent noise patterns and switches to aggressive filtering "within seconds". Vapi also blogged "How We Built Adaptive Background Speech Filtering" (snippet). [Vapi docs: Background speech denoising](https://docs.vapi.ai/documentation/assistants/conversation-behavior/background-speech-denoising); [Vapi blog](https://vapi.ai/blog/how-we-built-adaptive-background-speech-filtering-at-vapi)
- Retell's denoising modes are meant "to combat background speech and noise before the transcription is generated". "Remove noise" is the recommended default; denoising costs **$0.005/min** (snippet). [Retell docs: Handle background speech & noise](https://docs.retellai.com/build/handle-background-noise)
- Ada: background noise cancellation is on by default for all Voice AI agents (dated 2026-03-31) (snippet). [Ada docs](https://docs.ada.cx/2026-03-31-background-noise-cancellation)
- Speechmatics Voice SDK (`speechmatics-voice`, v0.2.8, 2026-01-26) has `SpeakerFocusConfig` with `focus_speakers`, `ignore_speakers`, `focus_mode` (RETAIN / IGNORE) and `prefer_current_speaker`. It works on diarized speaker IDs (S1, S2 …) or enrolled "known speakers". It **filters at transcript/segment level**, not audio (fetched). [PyPI speechmatics-voice](https://pypi.org/project/speechmatics-voice/); [Speechmatics blog: Speaker Focus](https://www.speechmatics.com/company/articles-and-news/speaker-lock-fixing-voice-ai-for-the-real-world)
- AssemblyAI "Universal-3.5 Pro Realtime (released June 23, 2026) includes voice_focus for isolating a speaker's voice in noisy rooms" (snippet; cloud ASR). [AssemblyAI blog: LiveKit + Voice Agent API](https://www.assemblyai.com/blog/build-a-voice-agent-with-livekit-voice-agent-api)
- Deepgram released Flux Multilingual (April 29, 2026): conversational STT with built-in end-of-turn detection. No isolation feature was found (search-summary snippet; the exact source page among the results is uncertain). [Deepgram 2026 roundup (probable source)](https://deepgram.com/learn/best-text-to-speech-apis-2026)
- For comparison, LiveKit supports two enhanced noise-cancellation providers, Krisp and ai-coustics (snippet). [LiveKit docs: Noise & echo cancellation](https://docs.livekit.io/transport/media/noise-cancellation/). ai-coustics ships "Quail Voice Focus 2.0" with native LiveKit integration (snippet). [ai-coustics blog](https://ai-coustics.com/blog/voice-focus-2.0-livekit-integration)

**Newcomers (2025–2026)**
- **Hecttor** (hecttor.ai) offers the "Orpheus SDK", which combines "speaker isolation, turn-taking, and voice activity detection". It claims to separate "the main speaker from other voices". Bindings: C++, Python, Node.js, C#. Deployment: Windows, macOS, Linux and browser. It states "no call audio, recordings, or transcripts leave your environment" and SOC 2 Type II certification (snippet; vendor claims). [Hecttor voice isolation](https://hecttor.ai/voice-isolation); [Hecttor Orpheus SDK](https://hecttor.ai/hecttor-orpheus-sdk); [Hecttor explore SDK](https://hecttor.ai/explore-sdk)
- **Yobe** (Boston, MIT spin-out): "VISPR" identifies, tracks and separates voices. Its SDK variants include "Identification Listening", which outputs speaker-specific signals for crosstalk or known-speaker scenarios (snippet; the pages look older and are undated). [Yobe documentation](https://yobeinc.com/documentation/); [Yobe article](https://yobeinc.com/yobe-uses-ai-and-microphones-to-isolate-voices-in-a-crowd/)
- The search phrase "background voice cancellation" in 2026 mostly returns Krisp material and roundup blogs such as BuiltWithAgents and Brilo. No additional licensable on-prem BVC vendor surfaced beyond those listed here. [BuiltWithAgents roundup](https://www.builtwithagents.ai/blog/best-ai-voice-agents-background-noise-cancellation); [Brilo roundup](https://www.brilo.ai/resources/best-ai-phone-call-agent-with-background-noise-cancellation)

### Inferences
- NVIDIA Speaker Focus, Sanas VI, Agora v2.0.2, Webex and Hecttor all implement a "prominent/foreground speaker" heuristic without enrollment (similar in spirit to Krisp BVC and ai-coustics Voice Focus). When the TV is louder than the caller, or the caller is quiet, these heuristics can lock onto the wrong talker. Only Teams and Speechmatics' known-speakers mode (and Yobe's "Identification Listening") use enrollment.
- The **Speechmatics** approach, filtering by diarized speaker ID at the transcript level, can be reproduced in this stack with the **Sortformer** speaker IDs already in hand: lock onto the first or dominant caller speaker and gate turn detection, barge-in and ASR text by speaker ID. This needs no third-party isolation model and complements any audio-level isolation.
- ElevenLabs, Adobe, Auphonic and Dolby Media APIs are cloud, file-oriented tools, so the no-third-party-cloud rule and real-time latency needs rule them out for this pipeline.
- Twilio and Vapi reuse Krisp, so they add nothing beyond the Krisp evaluation. Retell, Ada and AssemblyAI are cloud-only and do not disclose their underlying models.

### Gaps
- NVIDIA Riva: found **no** Riva speech-enhancement or denoise model. Riva appears to rely on noise-robust ASR rather than a front-end enhancer (unverified; docs.nvidia.com blocked).
- Whether NVIDIA Speaker Focus keeps short backchannels ("mm-hm", "yeah") from the primary speaker is undocumented, and so is how it handles a TV voice louder than the caller.
- Sanas: could not fetch developer.sanas.ai to confirm the SDK language, OS, CPU/GPU needs, on-prem/air-gapped availability, or frame size/latency.
- Retell and Vapi underlying tech for the "background speech" modes (beyond Vapi's Krisp) is not disclosed in reachable sources.
- Hecttor and Yobe: no independent evidence, no latency figures, no pricing, no public repos or PyPI packages found.
- Vonage: no information found on its noise suppression.
- Dolby Voice (enterprise conferencing) was not researched further; no evidence of a licensable server SDK in 2026.
- Cartesia: found no isolation or denoising feature.
- Deepgram: no isolation feature found.

---

## Q2. Which can run fully on-prem on Linux (and macOS for dev) in real time with ≤ ~40 ms algorithmic latency?

### Takeaway
Two options are *verified* to run fully on-prem on Linux in real time:
- **NVIDIA AFX SDK** (BNR + Speaker Focus): GPU-only, Linux + Windows, **no macOS**, 10 ms frames, but no published algorithmic latency for Speaker Focus.
- **Picovoice Koala**: CPU, Linux x86_64 + macOS arm64, but noise-only, and its **AccessKey is validated online**.

Sanas SDK and Hecttor Orpheus *claim* server-side / on-prem use, but details could not be verified. Agora runs locally only inside Agora's RTC SDK. Apple Voice Isolation runs only on the Mac or iPhone that captures the audio, never on a Linux server.

### Cited Findings
- **NVIDIA AFX (Linux)**: "designed and optimized for server-side (datacenter or cloud) deployments" (snippet). [NGC: Linux Audio Effects SDK](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)
- AFX 2.1 Linux GPU options: t4, a100, a10, a2, a16, a30, a40, l4, l40, h100, b100, b200, rtx_pro_6000. MIG is supported only on A30 and A100 (snippet). [AFX 2.1.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/GetStartedOnLinux.html)
- AFX release readiness: the reference workload is Denoiser v2 with **10 ms frames (160 samples) at 16 kHz**. Acceptance thresholds: p95 `NvAFX_Run` below the 10 ms frame budget, and p05 throughput above 1.0× real time (snippet). [AFX Windows Performance and Deployment Guide](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ReleaseReadiness.html)
- Studio Voice Low Latency (48 kHz) has an **80 ms** algorithmic latency, above the 40 ms budget (snippet, AFX docs). [AFX docs index](https://docs.nvidia.com/maxine/afx/latest/index.html)
- AFX 3.0 docs mention only GPU architectures (e.g., Turing, Ampere), with no CPU execution path for Speaker Focus (snippet). [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf)
- **Picovoice Koala**: processes audio on-device. Platforms include Linux x86_64 and macOS arm64. Python 3.9+ via `pip3 install pvkoala`. "You would need internet connectivity to validate your AccessKey", and usage is tracked against account limits (fetched). [GitHub Picovoice/koala](https://github.com/Picovoice/koala); [Koala Python README](https://raw.githubusercontent.com/Picovoice/koala/main/binding/python/README.md)
- Koala works on mono 16-bit **16 kHz** audio in fixed frames (`koala.frame_length`). It reports its latency as `koala.delay_sample` ("number of samples of latency between input and output") (snippet). [PyPI pvkoala](https://pypi.org/project/pvkoala/); [Picovoice blog: Suppress noise in 3 lines of Python](https://picovoice.ai/blog/suppress-noise-in-3-lines-of-python/)
- Koala v3.0.0 (Dec 9, 2025) adds "improved engine performance" and GPU/multi-core support (fetched). [GitHub Picovoice/koala](https://github.com/Picovoice/koala)
- Koala real-time factor is ~0.01 on an AMD Ryzen 7 5900X under Ubuntu 22.04, about the same as RNNoise (fetched). [GitHub Picovoice/noise-suppression-benchmark](https://github.com/Picovoice/noise-suppression-benchmark)
- **Sanas SDK** is described as "server-side" with 16 kHz models (snippet). Whether it is on-prem or cloud could not be verified. [Sanas Developer Hub](https://developer.sanas.ai/Overview/Welcome-to-Sanas); [Sanas SDK Quickstart](https://developer.sanas.ai/SDK/Get-Started/Quickstart-Guide)
- The Sanas agent desktop app needs **URL whitelisting** and uses auto-activation tied to the domain and logged-in user, implying online activation. Sanas says it does not "monitor, record or store any call data" (snippet). [Sanas help: Noise Cancellation app](https://help.sanas.ai/v1/docs/sanas-noise-cancellation-app)
- **Hecttor Orpheus** claims Linux, macOS, Windows and browser deployment, with no audio leaving the environment (snippet). [Hecttor Orpheus SDK](https://hecttor.ai/hecttor-orpheus-sdk)
- **Agora**: processing is local "pre-processing" inside the Agora SDK; web low-latency mode is ~40 ms (fetched). [AgoraIO docs-portal](https://github.com/AgoraIO/docs-portal/blob/main/content/docs/en/realtime-media/voice/build/enhance-the-audio-experience/ai-noise-suppression.mdx)
- **Apple**: the Voice Isolation mic mode is user-controlled and read-only to apps (snippet). [Apple docs: preferredMicrophoneMode](https://developer.apple.com/documentation/avfoundation/avcapturedevice/preferredmicrophonemode)
- **LiveKit comparison**: "Server-side processing of inbound audio with access to LiveKit Cloud's enhanced models is the recommended default". A LiveKit community thread discusses noise-cancelling features with **self-hosted** agents (snippet; details are covered by the Krisp/ai-coustics researchers). [LiveKit docs](https://docs.livekit.io/transport/media/noise-cancellation/); [LiveKit community thread](https://community.livekit.io/t/noise-cancelling-features-with-self-hosted-agents/1227)

### Inferences
- **For Linux GPU prod**, NVIDIA AFX (BNR v2 → Speaker Focus chain at 16 kHz) is the only big-vendor, documented on-prem SDK that removes competing speakers. Integration effort:
  - A C API (`NvAFX_CreateEffect` / `NvAFX_Load` / `NvAFX_Run`) called from Python via ctypes/cffi or a small C++ extension.
  - float32 conversion.
  - Resampling from LiveKit's 48 kHz or 16 kHz frames to exactly 160-sample (10 ms) chunks.

  The model's look-ahead is unpublished, so the "≤ 40 ms" goal must be measured. The 10 ms frame and the p95 < 10 ms compute budget mean compute alone fits easily.
- The same GPU host already runs the Nemotron/Sortformer riva_server, so AFX would share the GPU. The MIG restriction (A30/A100 only) matters if GPU partitioning is planned.
- **Mac dev cannot run AFX.** On a Mac you would bypass isolation, use a Linux GPU box for dev tests, or stand in with Koala or Krisp/ai-coustics. Any dev/prod difference in front-end processing will change ASR, turn and barge-in behaviour.
- Apple Voice Isolation can make a developer's *own* mic cleaner during Mac testing (the user toggles it in Control Center for the browser or native LiveKit client). It cannot process remote callers' audio on a server, and it would hide the very conditions the agent must handle. For realistic tests, turn it **off** on dev machines.
- Koala runs on-device but checks its licence online. Caller audio stays local, but this is a runtime network dependency and an availability risk for an air-gapped deployment. Confirm offline or enterprise licence terms with Picovoice.

### Gaps
- Speaker Focus algorithmic latency (look-ahead), per-stream GPU memory, and streams per GPU (e.g., on L4/T4) are not verified.
- Koala's actual `frame_length` and `delay_sample` values were not verifiable (picovoice.ai blocked; the README does not list them). Measure them with `pvkoala` locally.
- Whether an **offline / air-gapped Koala licence** exists could not be confirmed.
- Sanas and Hecttor: OS, CPU/GPU needs, latency and offline operation are unverified.
- Whether the Agora extension can run *outside* an Agora channel (e.g., on raw PCM in a LiveKit agent) is undocumented. It appears tied to the Agora RTC engine.

---

## Q3. Licensing and pricing (where published)

### Takeaway
Few vendors publish prices.
- **NVIDIA AFX Linux SDK** comes with an **NVIDIA AI Enterprise (NVAIE)** licence (the price was not verifiable here).
- **Picovoice Koala** has a free tier of 100 min/month; paid plans are opaque.
- **ElevenLabs Voice Isolator** costs **$0.12/min** (cloud).
- **Retell denoising** costs **$0.005/min** (cloud).
- **Sanas, Hecttor, Yobe, Agora and Dolby** are sales-led or unpublished.

### Cited Findings
- NVIDIA: "The Linux SDKs are included with NVAIE license (NVIDIA AI Enterprise)" (snippet). [NGC: Linux Audio Effects SDK](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)
- NVIDIA AFX GitHub repo: the samples and API source are **MIT**-licensed; the runtime DLLs and models come separately from the NVIDIA developer page (fetched). [GitHub Maxine-AFX-SDK](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK)
- NVIDIA Maxine NIMs (BNR, Studio Voice) are on NGC and build.nvidia.com (snippet). [NGC BNR NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/maxine-bnr/-?_lr=1); [build.nvidia.com/nvidia/bnr](https://build.nvidia.com/nvidia/bnr)
- Picovoice: the free tier includes Koala at **100 minutes/month**; paid plans are "Starter" and "Enterprise"; Koala usage is metered in one-second increments (snippet). [Picovoice pricing](https://picovoice.ai/pricing/)
- Third-party aggregators disagree on Picovoice's price: "lowest paid plan starts at $6000 per month" versus "$899/Flat Rate/Monthly". Treat both as **unreliable** (snippet). [SoftwareSuggest](https://www.softwaresuggest.com/picovoice/pricing); [SaaSworthy](https://www.saasworthy.com/product/picovoice-ai/pricing)
- ElevenLabs Voice Isolator costs **$0.12 per minute** via API, or 1,000 credits per minute of audio (snippet). [ElevenLabs help: Voice Isolator cost](https://help.elevenlabs.io/hc/en-us/articles/26446706351377-How-much-does-Voice-Isolator-cost); [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- Retell denoising costs **$0.005/min** (snippet). [Retell docs](https://docs.retellai.com/build/handle-background-noise)
- One third-party source says Adobe Podcast API pricing is "approx $0.02 per minute". This is unverified and conflicts with other sources saying there is no API access (snippet). [AI Tools DevPro (third-party)](https://aitoolsdevpro.com/ai-tools/adobe-podcast-guide/); [Cleanvoice](https://cleanvoice.ai/blog/adobe-podcast-enhance-speech/)
- Speechmatics' Flow voice-agent API is quoted at $0.0537/min in a 2026 comparison (third-party snippet; cloud). [Coval STT 2026](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/)

### Inferences
- NVAIE is usually sold per GPU per year. For a single-tenant self-hosted agent, the AFX licence cost could exceed per-minute alternatives at low volume. Get a quote before investing engineering time.
- Sanas and Hecttor will almost certainly need an enterprise contract. Ask specifically for an air-gapped Linux licence with no call-home, and for a macOS arm64 dev build.

### Gaps
- The NVAIE price for AFX use and whether a dev/eval licence is free were not verified (the NVIDIA pages were blocked).
- No published pricing for Sanas SDK, Hecttor, Yobe, Agora AI NS (per-minute extension pricing not found), Tencent TRTC AI NS, or Dolby OptiView.
- Picovoice's actual Starter or Enterprise price for Koala is not verified.

---

## Q4. Quality evidence (benchmarks, WER impact, independent reviews)

### Takeaway
No independent, third-party benchmark was found for competing-talker removal by any non-Krisp, non-ai-coustics vendor. The available evidence is:
- Picovoice's own open benchmark (noise only, STOI).
- Sanas' vendor WER claims (5–30% relative WER reduction; comparison against an unnamed "generic BVC").
- NVIDIA's claim that Denoiser v2 is ASR-tuned.

Several sources warn that conventional denoising can **raise** ASR WER, so any front end must be A/B-tested against Nemotron WER on in-domain audio.

### Cited Findings
- Picovoice benchmark on the synthetic no-reverb test set of the Microsoft DNS Challenge (Interspeech 2020; 150 files). STOI: original 0.915, RNNoise 0.925, **Koala 0.959**. RTF about 0.01 for both engines. PESQ not reported (fetched). [GitHub Picovoice/noise-suppression-benchmark](https://github.com/Picovoice/noise-suppression-benchmark)
- Picovoice summarizes this as Koala cutting STOI distance to clean speech to 0.0415 versus 0.0748 for RNNoise, and calls Koala "four times more effective than RNNoise" (vendor marketing; snippet). [Picovoice Koala benchmark](https://picovoice.ai/docs/benchmark/noise-suppression-picovoice-koala/); [Picovoice voice-isolator blog](https://picovoice.ai/blog/voice-isolator/)
- Sanas: "AI Voice Agent models reduce Word Error Rate (WER) by 5-30% in noisy environments" (vendor claim; snippet). [Sanas Developer Hub](https://developer.sanas.ai/Overview/Welcome-to-Sanas)
- Sanas compared its ASR-optimized NC against "a generic background voice cancellation (BVC) tool" on **Deepgram Nova-3 streaming** ASR. The reported results are qualitative: "significantly better relative to the source and moderately better relative to the generic solution". Sanas also checked LibriSpeech test-clean to confirm there is no degradation on clean input (snippet). [Sanas science: ASR-optimized NC for agentic AI](https://www.sanas.ai/science/inside-sanas-asr-optimized-noise-cancellation-for-agentic-ai)
- Sanas cites Deepgram's "Noise Reduction Paradox": "conventional noise cancellation can actually reduce ASR accuracy, even when the audio sounds clearer to people" (snippet). [Sanas blog](https://www.sanas.ai/blog/inside-sanas-asr-optimized-noise-cancellation-for-agentic-ai); [Deepgram: noise-robust ASR techniques](https://deepgram.com/learn/noise-robust-speech-recognition-techniques)
- NVIDIA: Denoiser v2 "offers improved accuracy for automated speech recognition". No WER numbers were found in reachable snippets. [NVIDIA AFX noise removal effect](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutNoiseRemovalBackgroundNoiseSuppression.html)
- Microsoft Teams voice isolation is described only in Microsoft's own blog and support pages; no independent metrics were found (snippet). [Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/voice-isolation)
- Sanas reports "89% reduction in communication stress and 12% lower turnover" from one contact-center deployment. This is a business metric, not an acoustic one (vendor claim; search-summary snippet, and the exact Sanas page could not be confirmed). [Sanas blog (probable source)](https://www.sanas.ai/blog/why-sanas-is-the-better-choice-for-contact-centers-and-enterprises)

### Inferences
- The Picovoice benchmark uses DNS-2020 noise clips at mixed SNRs, and neither it nor Picovoice's claims test **competing-talker interference**. It says nothing about TV or bystander speech. Expect Koala to pass TV speech through as "speech".
- The Sanas "generic BVC" comparison is probably a veiled Krisp comparison, but the vendor does not name it, so this is inference only.
- For this stack, the key metrics are:
  - Nemotron streaming WER on (a) clean, (b) noisy and (c) competing-talker/TV mixtures.
  - Sortformer DER.
  - Backchannel recall: short "mm-hm" or "yeah" must survive.
  - False barge-in rate from TV speech.
  - Added latency.

  Run the NVIDIA Speaker Focus chain and any Sanas or Hecttor eval builds through the same harness as Krisp and ai-coustics.

### Gaps
- No independent tests of NVIDIA Speaker Focus quality were found: no WER, DER, SI-SDR or listening test.
- Sanas WER numbers per dataset are not public in reachable sources.
- No independent reviews of Hecttor or Yobe.
- Agora v2.0.2 background-voice removal: no metrics.

---

## Q5. Fit for this stack (LiveKit Agents 1.8.3 + NeMo riva_server, Mac dev / Linux prod, no third-party cloud)

### Takeaway
Excluding Krisp and ai-coustics, **NVIDIA AFX (BNR v2 + Speaker Focus)** is the only verified, licensable, fully on-prem primary-speaker isolator. Its drawbacks: NVIDIA GPU only, Early Access, NVAIE licence, no macOS, C API only. **Sanas SDK** (AGENTIC_VI_G_NC) and **Hecttor Orpheus** are the two commercial candidates worth an evaluation request, but their on-prem terms are unverified. **Picovoice Koala** is an easy CPU, Mac + Linux *noise* suppressor, not a background-voice remover. Everything else is disqualified by cloud-only delivery or by being locked to one platform (Teams, Webex, Agora, Zoom, Meet, Tencent, Apple).

### Cited Findings
- NVIDIA AFX: Linux server-oriented; the Speaker Focus effect removes background speakers; 16 kHz supported; NVAIE licence; GPUs T4/L4/A10/etc. [NGC Linux AFX](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-); [AFX Speaker Focus](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 2.1 Linux GPUs](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/GetStartedOnLinux.html)
- Sanas SDK: server-side; AGENTIC_VI_G_NC gives full voice isolation and AGENTIC_ST_NC preserves background speech; 16 kHz (snippet). [Sanas Developer Hub](https://developer.sanas.ai/Overview/Welcome-to-Sanas); [Quickstart](https://developer.sanas.ai/SDK/Get-Started/Quickstart-Guide)
- Hecttor: SDK with speaker isolation + turn-taking + VAD, Python binding, Linux/macOS, audio stays local (snippet; claims). [Hecttor Orpheus SDK](https://hecttor.ai/hecttor-orpheus-sdk)
- Koala: Python, Linux x86_64 + macOS arm64, on-device, AccessKey validated online (fetched). [GitHub Picovoice/koala](https://github.com/Picovoice/koala)
- Speechmatics Voice SDK speaker focus works at transcript level on diarization IDs or known speakers (fetched). [PyPI speechmatics-voice](https://pypi.org/project/speechmatics-voice/)
- Agora background voice removal lives inside the Agora RTC SDK pre-processing (fetched). [AgoraIO docs-portal](https://github.com/AgoraIO/docs-portal/blob/main/content/docs/en/realtime-media/voice/build/enhance-the-audio-experience/ai-noise-suppression.mdx)
- Teams voice isolation needs a per-user enrollment profile stored on the client (snippet). [Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/voice-isolation)

### Inferences
Suggested ranking for evaluation beyond Krisp and ai-coustics:
1. **NVIDIA AFX Speaker Focus (+ BNR v2)**, if prod has NVIDIA GPUs and an NVAIE licence is acceptable. Integrate as a custom per-participant audio processor before the STT/VAD stream in the LiveKit agent: wrap `rtc.AudioStream` frames, resample to 16 kHz float32, and feed 10 ms chunks. Dev on Mac would need a remote Linux GPU box or a bypass flag.
2. **Sanas SDK (AGENTIC_VI_G_NC)**. Request an eval and confirm Linux on-prem, offline licensing, CPU vs GPU, latency, backchannel handling, and a macOS build. Its ASR-optimized design suits Nemotron, but that needs verification.
3. **Hecttor Orpheus**. Its claims fit the need exactly (isolation + turn-taking + VAD, local processing). It is unproven, so treat it as a speculative eval only.
4. **Picovoice Koala**: a CPU noise-only fallback that works identically on Mac and Linux. It will not remove TV or bystander speech, and its online AccessKey validation is a dependency.

Two further points:
- **No-model complement: use Sortformer speaker IDs.** Pattern this on Speechmatics Speaker Focus: lock onto the caller's speaker ID, ignore ASR segments and VAD/barge-in events attributed to other speakers, and keep backchannels from the locked speaker. This covers residual leakage from any isolator and never deletes the caller's own backchannels at the audio level.
- **Do not use:** ElevenLabs, Adobe, Auphonic or Dolby (cloud/offline); Maxine NIM BNR / Studio Voice for this goal (noise only, and Studio Voice LL has 80 ms latency); NVIDIA Broadcast (Windows desktop); Apple Voice Isolation (client-side only, user-toggled); Teams, Webex, Zoom, Meet, Tencent or Agora (platform-locked); Twilio or Vapi (Krisp underneath); Retell, Ada or AssemblyAI `voice_focus` (cloud).

### Gaps
- How any of these isolators treat short, quiet backchannels from the primary speaker is undocumented for every vendor here. It must be tested empirically.
- Whether NVIDIA AFX runs on Jetson/ARM64 servers or on Grace-based systems was not checked.
- No LiveKit plugin exists for NVIDIA AFX, Sanas, Hecttor or Koala; integration effort was not verified against LiveKit Agents 1.8.3 APIs. No LiveKit plugin was found in the searches; only Krisp and ai-coustics are listed as LiveKit providers ([LiveKit docs](https://docs.livekit.io/transport/media/noise-cancellation/)).
