# Target-speaker extraction (TSE), personalized speech enhancement (PSE), personal VAD and enrollment-free primary-speaker isolation for a real-time voice agent (state as of September 2026)

Scope: research and open-source ways to isolate *the caller* in a self-hosted LiveKit Agents 1.8.3 stack (NeMo-Speech.cpp `riva_server` with Nemotron streaming ASR + Sortformer diarization, LiveKit `MultiSpeakerAdapter`). Commercial BVC (Krisp, ai-coustics) is out of scope and covered elsewhere.

How this was verified: arxiv.org, huggingface.co, isca-archive.org, semanticscholar, researchgate, github.io pages and Google blogs were **blocked by the egress proxy**. Facts from those sites come from **search-engine snippets of the named page** and are marked "(snippet)". GitHub repos (raw README/LICENSE files), the microsoft.com DNS page, and local clones of `livekit/agents` (v1.8.3, commit 2026-09-25) and `NVIDIA/NeMo-Speech.cpp` (commit 2026-09-24) were read directly and are marked "(verified)".

---

## Key Question 1: Which approaches have streaming implementations with ≤ ~100 ms added latency and open weights that allow commercial use?

### Takeaway
Almost no *ready-to-run, commercially licensed, streaming* TSE/PSE checkpoint exists for 16 kHz English telephony in September 2026. The research leaders (VoiceFilter-Lite, pVAD 2.0, TEA-PSE, Microsoft's PSE line, TargetVoice, FVAD) meet the latency budget but released **no weights**. The usable open pieces are:
1. Causal BSRNN TSE checkpoints from the REAL-TSE (SLT 2026) baseline repo. They are research-grade and their checkpoint license is not stated.
2. Speaker-embedding models with permissive licenses (WeSpeaker/VoxCeleb models under CC-BY-4.0, NVIDIA TitaNet-Large under CC-BY-4.0, 3D-Speaker and sherpa-onnx under Apache-2.0 code). These can drive an embedding gate.
3. NVIDIA's diarization-conditioned streaming multitalker Parakeet in NeMo (Python). It needs no enrollment, but it is a different ASR model from the one `riva_server` runs today.

### Cited Findings

**A. Enrollment-based PSE/TSE (front-end that outputs cleaned audio or features)**
- **Google VoiceFilter-Lite (Interspeech 2020).** Single-channel, streaming, on-device model that "preserves only the speech signals from a target user", placed in front of a streaming ASR. It uses an asymmetric loss and adaptive runtime suppression strength (snippet) — [arXiv 2009.04323](https://arxiv.org/abs/2009.04323). A 2.2 MB model gives a 25.1% WER improvement on overlapping speech (snippet) — [Google Research blog](https://research.google/blog/improving-on-device-speech-recognition-with-voicefilter-lite/). The filterbank-based model outputs enhanced ASR features rather than audio (snippet) — [arXiv 2009.04323v1](https://arxiv.org/html/2009.04323v1). Follow-ups add multi-user support — [Multi-user VoiceFilter-Lite, arXiv 2107.01201](https://arxiv.org/pdf/2107.01201) and [Closing the gap single/multi-user, arXiv 2202.12169](https://arxiv.org/pdf/2202.12169). I found no official code or weights.
- **Google Personal VAD (Odyssey 2020) and Personal VAD 2.0 (2022).** A frame-level classifier with three outputs: non-speech, target-speaker speech, non-target speech. It is conditioned on a speaker embedding or a speaker-verification score (snippet) — [arXiv 1908.04284](https://arxiv.org/abs/1908.04284), [arXiv 2204.03793](https://arxiv.org/abs/2204.03793).
  - pVAD 2.0 targets streaming ASR gating in both enrolled and enrollment-less modes, under tight latency and CPU/memory budgets. It uses FiLM-style speaker modulation (snippet) — [arXiv 2204.03793](https://arxiv.org/abs/2204.03793).
  - Conformer backbone and 8-bit quantization cut model size by about 75% (secondary snippet) — [Lacuna summary](https://lacuna.tiptreesystems.com/work/personal-vad-2-0-optimizing-personal-voice-activity-detection-for-on-device/wrk_deb0a095e91442833d446e2d27854c42).
  - No official weights. The only open implementation found is the unofficial [pirxus/personalVAD](https://github.com/pirxus/personalVAD), a BUT bachelor thesis from 2021 under **GPL-3.0** (LICENSE verified). A related paper is [Enrollment-less training for personalized VAD, arXiv 2106.12132](https://arxiv.org/pdf/2106.12132).
- **Microsoft PSE / personalized DNS (ICASSP 2022–2023).**
  - Eskimez et al. proposed real-time PSE networks for video conferencing that beat VoiceFilter. They introduced the **TSOS (target-speaker over-suppression)** metric and showed that multi-task training with an ASR back-end reduces TSOS (snippet) — [arXiv 2110.09625](https://arxiv.org/abs/2110.09625), [MSR page](https://www.microsoft.com/en-us/research/publication/personalized-speech-enhancement-new-models-and-comprehensive-evaluation/).
  - pDCCRN "outperformed causal VoiceFilter and highlighted TSOS" (snippet, same line of work) — [arXiv 2110.09625](https://arxiv.org/abs/2110.09625).
  - Related Microsoft real-time PSE work: [E3Net, arXiv 2204.00771](https://arxiv.org/pdf/2204.00771), [joint PSE+AEC, Interspeech 2023](https://www.isca-archive.org/interspeech_2023/eskimez23_interspeech.pdf), [cross-task KD, arXiv 2211.02944](https://arxiv.org/pdf/2211.02944).
  - I found no public weights for any of these.
- **ICASSP 2023 DNS Challenge** (verified) — [MS DNS 2023 page](https://www.microsoft.com/en-us/research/academic-program/deep-noise-suppression-challenge-icassp-2023/):
  - Two tracks: headset and speakerphone.
  - Each test clip comes with a **30 s enrollment clip** of the primary talker, which may be noisy or reverberant.
  - Metrics: P.835 SIG/BAK/OVRL, DNSMOS P.835, and word accuracy (WAcc) from Azure ASR. Final score = ((OVRL−1)/4 + WAcc)/2.
  - Blind test set: 600 clips per track.
- **ICASSP 2022 DNS personalized track.** Personalized DNS models were trained to suppress neighbouring talkers and background noise and keep only the primary talker (snippet) — [arXiv 2202.13288](https://arxiv.org/html/2202.13288v1).
- **TEA-PSE family (Tencent Ethereal Audio Lab).**
  - TEA-PSE ranked 1st in the ICASSP 2022 DNS challenge. TEA-PSE 2.0 is a sub-band version with +0.102 personalized-DNSMOS OVRL at 21.9% of the MACs (snippet) — [arXiv 2303.07704](https://arxiv.org/pdf/2303.07704).
  - TEA-PSE 3.0 ranked **1st in both ICASSP 2023 DNS tracks**. It has 22.24 M parameters, 19.66 G MAC/s and a per-frame RTF of 0.46 on an Intel Xeon CPU (snippet) — [arXiv 2303.07704](https://arxiv.org/pdf/2303.07704).
  - The only public repo, [jvyvkai/TEAPSE2](https://github.com/jvyvkai/TEAPSE2), contains **demo clips only** (README verified). No code or weights.
  - NPU-Elevoc tied 1st on the headset track and placed 2nd on speakerphone (snippet) — [arXiv 2303.06811](https://arxiv.org/pdf/2303.06811).
- **Personalized DeepFilterNet2 (pDeepFilterNet2, Int. J. Speech Technology 2024).** Adds frame-wise speaker adaptation, causal multi-head self-attention, a multi-domain loss and ECAPA-TDNN embeddings, with "minimal computational overhead" over real-time DeepFilterNet2 (snippet) — [Springer](https://link.springer.com/article/10.1007/s10772-024-10101-z). Also see the [dual-stage DFN2 PSE, arXiv 2404.08022](https://arxiv.org/pdf/2404.08022) and the [audio samples page](https://pdeepfilternet2.github.io/). I found no code or weights.
- **Personalized PercepNet (Amazon, 2021).** "Real-time, low-complexity target voice separation and enhancement" — [arXiv 2106.04129](https://arxiv.org/pdf/2106.04129). I found no weights.
- **PSE without a separate speaker-embedding model** (Pärnamaa, Interspeech 2024). Uses the PSE network's own internal representation as the enrollment embedding. It performs equal to or better than a pretrained speaker embedder and has 2.7× fewer over-suppressed frames by TSOS (snippet) — [arXiv 2406.09928](https://arxiv.org/html/2406.09928).
- **TargetVoice (Interspeech 2025).** Single-channel TSE with **10 ms latency** and 8–10 dB SI-SDR improvement at SIR from −10 to 0 dB. The speaker-embedding module is 10 MB; the paper positions it for "voice bots" (snippet) — [ISCA PDF](https://www.isca-archive.org/interspeech_2025/pallala25_interspeech.pdf). I found no code or weights.
- **SpeakerBeam** (BUT, Interspeech 2021 tutorial code). Built on Asteroid with a Libri2Mix **8 kHz** recipe. The README lists training and eval steps only, with no pretrained model (verified) — [BUTSpeechFIT/speakerbeam](https://github.com/BUTSpeechFIT/speakerbeam).
- **WeSep (WeNet community).**
  - The README (updated 2026-09-21) says: "WeSep v0.1 is a research preview … production deployment is not yet supported". Local CLI inference and official pretrained models are "coming soon". ONNX/TorchScript/C++ support is "to be updated", and the legacy C++ runtime "is not supported by the current v0.1 model interface" (verified).
  - Recipes: BSRNN, SpEx+, DPCCN, TF-GridNet with speaker cues. Code is Apache-2.0 (verified) — [wenet-e2e/wesep](https://github.com/wenet-e2e/wesep).
  - Papers: [WeSep framework, arXiv 2607.27436](https://arxiv.org/abs/2607.27436) and the original [Interspeech 2024 paper](https://www.isca-archive.org/interspeech_2024/wang24fa_interspeech.html).
- **REAL-TSE Challenge (IEEE SLT 2026)** — the most relevant recent benchmark.
  - Task: real conversational recordings plus enrollment. It has an **Online (streaming) track** and an Offline track (snippet) — [arXiv 2607.15198](https://arxiv.org/abs/2607.15198).
  - "Nearly all online systems were compact, causal discriminative extractors (mainly BSRNN and TF-GridNet variants) adapted with causal normalization, unidirectional recurrence, and controlled look-ahead." The top entries were BSRNN-style, close to the baseline; their gains came from data simulation, real-data adaptation, pseudo-label filtering and post-processing (snippet) — [arXiv 2607.15198](https://arxiv.org/html/2607.15198v1).
  - **Baseline repo** [REAL-TSE/wesep-real-tse](https://github.com/REAL-TSE/wesep-real-tse) (verified):
    - Ships checkpoints on Google Drive: `spk_emb_100`, `spk_emb_causal_100`, `tfmap_context_100`, `tfmap_context_causal_100`.
    - BSRNN separator in causal and non-causal variants, with cues from WeSpeaker embeddings, USEF, TF-map or contextual embeddings.
    - Inference: `evaluate.py --mixture mix.wav --enroll enroll.wav`.
    - **No license is stated for the checkpoints** in the README.
  - **SonicAGI** ranked 2nd in Track 1 (online) with "SwiftNet-Lookahead": a single bounded look-ahead module in front of a strictly causal separator, **96 ms total system latency** (snippet) — [arXiv 2607.11083](https://arxiv.org/abs/2607.11083).
- **Causal BSRNN latency.** One claim: "by converting both the separator and speaker feature extractors into causal mode, a BSRNN-based TSE system achieves a theoretical latency of 32 ms". This is a search snippet from the 2026 TSE results. The exact source page is uncertain: [arXiv 2607.27436](https://arxiv.org/pdf/2607.27436) or [arXiv 2607.15198](https://arxiv.org/pdf/2607.15198).
- **StarTSE (Apr 2026).** Streaming TSE with an autoregressive language model, using chunk-wise interleaved splicing. On Libri2Mix, AR baselines degrade at low latency while StarTSE "maintains 100% stability" (snippet) — [arXiv 2604.19635](https://arxiv.org/abs/2604.19635). This is a generative LM approach and likely too heavy for CPU real time (inference).
- **Other TSE work.**
  - X-TF-GridNet: T-F complex spectral mapping with adaptive speaker-embedding fusion — [Information Fusion 2024](https://www.sciencedirect.com/science/article/abs/pii/S1566253524003282).
  - Dual-mode training for real-time TSE — [APSIPA 2025](https://www.apsipa.org/proceedings/2025/papers/APSIPA2025_P184.pdf).
  - TF-MLPNet, tiny real-time separation — [Clarity 2025](https://www.isca-archive.org/clarity_2025/itani25_clarity.pdf).
- **ClearerVoice-Studio (Alibaba/ModelScope).** Code is Apache-2.0 (LICENSE verified).
  - Audio-only TSE conditioned on reference speech is a **training recipe at 8 kHz**: SpEx+ (**non-causal**) on WSJ0-2mix, with a checkpoint at 17.1 dB SI-SDRi.
  - The packaged `clearvoice` inference only exposes **AV_MossFormer2_TSE_16K**, which is face/lip-conditioned.
  - Causal variants are listed only for AV-ConvTasNet and the EEG model (verified) — [TSE training README](https://github.com/modelscope/ClearerVoice-Studio/blob/main/train/target_speaker_extraction/README.md), [clearvoice README](https://github.com/modelscope/ClearerVoice-Studio/blob/main/clearvoice/README.md).

**B. Target-speaker / speaker-conditioned ASR and VAD (NVIDIA and others)**
- **NeMo streaming multitalker Parakeet** (`nvidia/multitalker-parakeet-streaming-0.6b-v1`) (verified from the NeMo tutorial notebook):
  - "Self-speaker adaptation": learnable **speaker kernels** derived from streaming Sortformer activity are injected into the Fast-Conformer encoder.
  - **No enrollment is needed.** One model instance runs per speaker on the same audio, so it handles overlap.
  - Cache-aware streaming with chunk sizes of 0.08 s, 0.16 s, 0.56 s or 1.12 s (attention context [70,0] … [70,13]).
  - Sources: [NeMo tutorial](https://github.com/NVIDIA-NeMo/Speech/blob/main/tutorials/asr/Streaming_Multitalker_ASR.ipynb), paper [arXiv 2506.22646](https://arxiv.org/pdf/2506.22646), model card [HF](https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1) (card not readable here).
  - A NeMo PR titled "Adding the multispeaker support for nemotron 3.5 ASR" exists (title from search) — [NVIDIA-NeMo/Speech PR #16277](https://github.com/NVIDIA-NeMo/Speech/pull/16277).
- **NVIDIA's architecture study (Sep 2026)** compares four streaming multi-speaker ASR designs: cascaded, masked input, word-level SOT, and diarization-conditioned multi-instance (SSA). SSA gets the lowest cpWER, 23.36 on average with predicted diarization, versus 42.27 for cascaded. The study also reports single-speaker accuracy degradation and memory footprint (snippet) — [arXiv 2609.10265](https://arxiv.org/abs/2609.10265).
- **NeMo-Speech.cpp `riva_server`** (the user's server) (verified):
  - `RecognitionConfig.diarization_config.enable_speaker_diarization` "adds a 1-based speaker tag to each final word". Two diarizers are supported: Sortformer V2 (4 speakers, 80 ms output frame) and Nemotron 3 Diarization (V3, 8 speakers, 10 ms output frame) — [docs/asr/customization.md](https://github.com/NVIDIA/NeMo-Speech.cpp/blob/main/docs/asr/customization.md), [docs/asr/models.md](https://github.com/NVIDIA/NeMo-Speech.cpp/blob/main/docs/asr/models.md).
  - The repo has **no speaker-embedding (TitaNet/ECAPA) model** (grep of the local clone).
- **Nemotron 3 Diarization (released around 2026-09-23).**
  - 100 M parameters, 31-layer Transformer, 10 ms output resolution, arrival-order speaker cache (AOSC) plus FIFO. Latency profiles run from an 80 ms buffer to 30.4 s offline (snippet) — [HF blog](https://huggingface.co/blog/nvidia/nemotron-diarization), [MarkTechPost](https://www.marktechpost.com/2026/09/23/nvidia-releases-nemotron-3-diarization/).
  - One secondary outlet says "its preview is evaluation-only" — [RuntimeWire](https://runtimewire.com/article/nvidia-nemotron-diarization-eight-speakers-open-weights). **License not verified**; check before production.
- **Streaming Sortformer 4spk-v2** is CC-BY-4.0 with configurable latency from 0.32 s to 30.4 s (snippet) — [HF model card](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2).
- **DiCoW (BUT).** Whisper conditioned on frame-level diarization masks (Silence/Target/Non-target/Overlap).
  - Code is Apache-2.0 and weights are CC-BY-4.0. The bundled DiariZen diarizer is **CC BY-NC 4.0** (verified) — [BUTSpeechFIT/DiCoW](https://github.com/BUTSpeechFIT/DiCoW).
  - The README cites a "SE-DiCoW: Self-Enrolled" variant (verified).
  - It is long-form and Whisper-based, so not streaming (inference).

**C. Enrollment-free "primary / foreground speaker" methods**
- **Foreground VAD (FVAD), Sep 2026.**
  - Definition: an enrollment-free, frame-synchronous task where only the dominant speaker is positive. Dominance is "defined by sustained presence rather than instantaneous loudness".
  - Selectivity comes mainly from supervision: foreground-only labels plus competing-speaker mixing augmentation.
  - The streaming **Mamba-FVAD** runs at **1–2 ms per frame on CPU** and "outperforms commercial VADs and enrollment-based speaker-aware systems in foreground selectivity".
  - New metric BG-FAR (background false-alarm rate) and a Mix-Interference benchmark plus adapted VOiCES (snippet) — [arXiv 2609.19856](https://arxiv.org/abs/2609.19856).
  - Code and weights availability unknown.
- **EEND-SAA (Sep 2025).** Enrollment-less, streaming-compatible (causal masking) main-speaker VAD. The main speaker is the one who "talks more steadily and clearly (continuity and volume)". On LibriSpeech mixtures, main-speaker DER drops from 6.63% to **3.61%** and F1 rises from 0.9667 to 0.9818 versus SA-EEND (snippet) — [arXiv 2509.11957](https://arxiv.org/abs/2509.11957).
- **Other enrollment-free cues.**
  - Text-cued TSE can target "the near-field speaker" (snippet) — [arXiv 2310.07284](https://arxiv.org/html/2310.07284).
  - Negative-enrollment TSE compares noisy positive and negative enrollments — [arXiv 2502.16611](https://arxiv.org/html/2502.16611v1).
  - Enrollment augmentation — [arXiv 2409.09589](https://arxiv.org/pdf/2409.09589).
- **LiveKit's own heuristic** (verified, v1.8.3 source, [multi_speaker_adapter.py](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/stt/multi_speaker_adapter.py)):
  - The primary speaker is chosen **only on FINAL transcripts**, by the median frame RMS over each word-span.
  - The first speaker seen becomes primary. A switch requires 1.3× the primary's smoothed RMS, and that threshold decays toward 0.5× while the primary is silent.
  - `suppress_background_speaker=True` drops non-primary finals.
  - Events with `speaker_id=None` (for example interims, since riva tags only finals) pass through untouched.
  - `is_primary_speaker` is not read anywhere under `livekit/agents/voice/` (grep).

**D. Speaker-embedding models usable as a gate (all offline/segment-level, run on ~1–3 s windows)**
- **WeSpeaker.** Code is Apache-2.0. VoxCeleb-trained checkpoints "follow the license of the dataset", CC-BY-4.0. ONNX runtime models are provided for ResNet34, CAM++, ECAPA512/1024, ResNet152/221/293 and others, and the runtime supports MNN (verified) — [wespeaker pretrained.md](https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md), [wespeaker](https://github.com/wenet-e2e/wespeaker).
- **3D-Speaker (Alibaba).** LICENSE is Apache-2.0 (verified).
  - VoxCeleb EER: CAM++ 7.2 M params 0.65%; ERes2NetV2 17.8 M 0.61%; ERes2Net-large 22.46 M 0.52%. ONNX runtime available since 2024-04 (verified) — [modelscope/3D-Speaker](https://github.com/modelscope/3D-Speaker).
  - The 200k-speaker checkpoints are zh-cn trained; for English, use the VoxCeleb variants (for example via WeSpeaker).
- **NVIDIA TitaNet-Large**: about 23 M parameters, **CC-BY-4.0** with commercial use allowed and attribution required (verified via mirror of the HF card) — [mirror README](https://github.com/chemcoder-2020/speakerverification_en_titanet_large), [HF](https://huggingface.co/nvidia/speakerverification_en_titanet_large).
- **sherpa-onnx** (Apache-2.0, LICENSE verified) ships speaker identification, verification and diarization in C++/Python across platforms (verified README) — [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).

### Inferences
Summary of candidates against the ≤100 ms / open-weights / commercial criteria:

| Candidate | Streaming ≤100 ms? | Open weights? | Commercial license? | Fit for this stack |
|---|---|---|---|---|
| Speaker-embedding gate on Sortformer-tagged finals (WeSpeaker/TitaNet/CAM++) | Adds 0 ms to audio. Decisions arrive at final-transcript time, plus ~5–30 ms of embedding compute per segment (my estimate, not measured). | Yes | CC-BY-4.0 / Apache-2.0 | Best low-code option |
| NeMo multitalker Parakeet (SSA) | Yes (80–160 ms chunks) | Yes (HF) | License unverified | Needs the NeMo Python runtime and replaces the Nemotron ASR |
| REAL-TSE causal BSRNN baseline | Probably (causal; the ~32 ms figure is uncertain) | Yes (Google Drive) | **Unstated** | Research prototype; needs profiling and legal check |
| pVAD 2.0 / VoiceFilter-Lite / TEA-PSE / TargetVoice / pDFN2 / FVAD | Yes, per papers | **No** | n/a | Only by re-implementing and training |
| pirxus/personalVAD | Yes | Train it yourself | GPL-3.0 | Poor fit |
| ClearerVoice audio-only TSE | No (non-causal, 8 kHz, WSJ0-trained) | Yes | Code Apache-2.0; WSJ0 training data is LDC-licensed (my concern) | Poor fit |
| DiCoW | No (offline Whisper) | Yes | Weights CC-BY-4.0, DiariZen NC | Poor fit |

- "Open + streaming + commercial + ≤100 ms + pretrained" is essentially satisfied only by the embedding-gate route. The multitalker-Parakeet route qualifies too if its license checks out.
- Everything else either needs your own training (WeSep/REAL-TSE recipes, pVAD re-implementations) or has no weights.
- The REAL-TSE results suggest a causal BSRNN trained with good data simulation and real-data adaptation is the current recipe for streaming TSE. Training one on VoxCeleb/LibriMix online mixing with the Apache-2.0 WeSep code is feasible, but it is a project of weeks, not a plug-in.

### Gaps
- Could not read the REAL-TSE results paper: exact online-track latency cap, per-team SI-SDR/TER/DNSMOS numbers, and whether top-team code or weights are released. The REAL-TSE site (github.io) and arXiv were blocked.
- License of the REAL-TSE baseline checkpoints, of `multitalker-parakeet-streaming-0.6b-v1`, and of Nemotron 3 Diarization (the "evaluation-only preview" claim) could not be verified. HF was blocked.
- Whether FVAD (arXiv 2609.19856), EEND-SAA or TargetVoice release code or weights: not found.
- Measured CPU/Apple-Silicon RTF for causal BSRNN TSE at 16 kHz: not found.
- No NVIDIA *enrollment-based* TSE model or recipe was found in NeMo. Its target-speaker path is diarization-conditioned ASR.
- No Apple or Meta open TSE/PSE for real-time use was found in this search.

---

## Key Question 2: What quality is reported — SI-SDR/DNSMOS gains, target-speaker WER, false rejection of the target (TSOS/over-suppression), especially on short utterances like backchannels?

### Takeaway
Reported gains are large on simulated two-speaker mixtures: 8–17 dB SI-SDRi, and 25–60% relative WER reduction on overlapped speech for VoiceFilter-Lite. But every PSE/TSE paper also documents the **cost**:
- Degraded WER on clean, target-only audio.
- Over-suppression of the target, worst for same-gender interferers and noisy enrollment.
- Leakage when the target is silent.

Speaker embeddings degrade sharply below about 1–3 s of speech. **No paper found reports backchannel-level (≤0.5 s) target false-rejection numbers**, so that risk has to be measured in-house.

### Cited Findings
- **VoiceFilter-Lite WER.**
  - Baseline ASR WER is 8.6% on the LibriSpeech test set (5.2% on test-clean).
  - The filterbank model gives a 47.3% absolute (60.7% relative) WER improvement under additive *speech* noise without hurting clean WER.
  - Some variants "hurt the WER in the clean condition", which asymmetric L2 loss or a fixed suppression strength mitigate at the cost of noisy-condition gains (snippet) — [arXiv 2009.04323v1](https://arxiv.org/html/2009.04323v1).
  - The 2.2 MB model gives a 25.1% WER improvement on overlapped speech (snippet) — [Google Research blog](https://research.google/blog/improving-on-device-speech-recognition-with-voicefilter-lite/).
- **TSOS as a first-class metric.** Microsoft's PSE work introduced TSOS because target over-suppression was "critical" for deployment and "not sufficiently investigated". Multi-task ASR training "alleviates the TSOS issue" (snippet) — [arXiv 2110.09625](https://arxiv.org/abs/2110.09625).
- Using the PSE's internal embedding cut over-suppressed frames 2.7× versus a two-stage (external embedder) model, with equal or better background-speech removal (snippet) — [arXiv 2406.09928](https://arxiv.org/html/2406.09928).
- **Known PSE failure modes** (snippets from the PSE literature search) — [arXiv 2211.12097](https://arxiv.org/pdf/2211.12097), [arXiv 2302.09953](https://arxiv.org/pdf/2302.09953), [arXiv 2303.06811](https://arxiv.org/pdf/2303.06811):
  - Causal PSE over-suppression "is worse for same-gender mixtures".
  - Mismatch between clean enrollment and noisy test audio misleads the voiceprint.
  - PSE "often fail[s] to remove interfering speakers when the target speaker is not present … for a sustained period". This is exactly the "caller silent, TV talking" case.
- **DNS 2023 personalized scoring** puts ASR word accuracy on par with P.835 OVRL. TEA-PSE 3.0 had the best BAK/OVRL on the blind set and ranked 1st in both tracks (verified page; TEA-PSE snippet) — [MS DNS 2023](https://www.microsoft.com/en-us/research/academic-program/deep-noise-suppression-challenge-icassp-2023/), [arXiv 2303.07704](https://arxiv.org/pdf/2303.07704).
- **SI-SDR numbers.**
  - TargetVoice: 8–10 dB SI-SDRi at SIR −10…0 dB with 10 ms latency (snippet) — [ISCA 2025](https://www.isca-archive.org/interspeech_2025/pallala25_interspeech.pdf).
  - SpEx+ (offline, 8 kHz WSJ0-2mix): 17.1 dB SI-SDRi (verified) — [ClearerVoice TSE README](https://github.com/modelscope/ClearerVoice-Studio/blob/main/train/target_speaker_extraction/README.md).
- **REAL-TSE metrics** go beyond SI-SDR: TER (transcription error rate), speaker similarity, DNSMOS and **target-speaker activity F1**, on real conversational data (snippet) — [arXiv 2607.11083](https://arxiv.org/abs/2607.11083), [arXiv 2607.15198](https://arxiv.org/abs/2607.15198).
- **Personal/foreground VAD.**
  - EEND-SAA main-speaker DER is 3.61% and F1 0.9818 (snippet) — [arXiv 2509.11957](https://arxiv.org/abs/2509.11957).
  - FVAD reports better BG-FAR than commercial VADs and enrollment-based systems while staying competitive as a normal VAD (snippet, no numbers retrieved) — [arXiv 2609.19856](https://arxiv.org/abs/2609.19856).
- **Short-utterance speaker verification.**
  - SOTA SV "severely degrades on short utterances" (snippet) — [MFA-TDNN, arXiv 2202.01624](https://arxiv.org/pdf/2202.01624).
  - One snippet reports "VAM-ECAPA" at **8.334% EER on 1-s test segments**, 54.8% relative better than its baseline. The source page is probably [arXiv 2609.25007](https://arxiv.org/html/2609.25007), but that is not certain.
  - MR-RawNet: 20.2% relative EER reduction on 1-s utterances versus RawNet3 (snippet) — [arXiv 2406.07103](https://arxiv.org/pdf/2406.07103).
  - Hybrid enrollment with neural re-scoring stabilizes SV for utterances under 3 s (snippet) — [arXiv 2606.16115](https://arxiv.org/abs/2606.16115).
  - Compare full-length VoxCeleb EERs of 0.5–0.65% (verified) — [3D-Speaker](https://github.com/modelscope/3D-Speaker).
- **Streaming target-speaker ID pipeline (Aug 2026).**
  - Built from Diart streaming diarization plus pyannote verification against a registered target, both open pretrained.
  - Across 17 episodes: median accuracy >0.90 and **specificity 0.95–0.98** at cosine-distance thresholds of 0.7–0.75 (snippet) — [arXiv 2608.17972](https://arxiv.org/abs/2608.17972).
- **Diarization-conditioned ASR (NVIDIA).** SSA has the best cpWER (23.36) among streaming designs. The study explicitly measures "single-speaker accuracy degradation", a cost that also applies to a single-caller agent (snippet) — [arXiv 2609.10265](https://arxiv.org/abs/2609.10265).
- **Diarizer quality ceiling.** Nemotron 3 Diarization has 14.72% DER on Voice Arena Diarization-Bench, ranked 1st (snippet) — [MarkTechPost](https://www.marktechpost.com/2026/09/23/nvidia-releases-nemotron-3-diarization/).

### Inferences
- A 1-s embedding at about 8% EER means roughly 1 in 12 genuine short caller turns would be misjudged at the equal-error point. Backchannels ("yeah", "mm-hm", 0.2–0.6 s) are far below that. So **per-segment embedding decisions are unreliable for backchannels**. They must inherit identity from the diarizer's speaker slot (Sortformer ID continuity), not be scored alone.
- PSE front-ends put the risk on the **target**: any over-suppression deletes caller words before ASR, and the error is unrecoverable downstream. Embedding gating on diarized finals puts the risk on **dropping a whole segment**. That is auditable and reversible, because you can log dropped text and fall back.
- Because the caller is usually near-field and the TV or bystander far-field, the enrollment-free cues in FVAD and EEND-SAA (sustained presence, continuity, level) align well with this use case. LiveKit's RMS-only, finals-only heuristic is a crude version of the same idea.

### Gaps
- No published TSOS or false-rejection numbers split by utterance length, and no backchannel-specific evaluation for any PSE/TSE/pVAD system.
- No SI-SDR or WER numbers for the REAL-TSE online-track winners or the causal baseline (paper not accessible).
- pVAD 2.0's numeric results (EER, WER, latency) could not be retrieved (arXiv blocked).
- No evidence on 8 kHz telephony (PSTN/SIP) versus 16/48 kHz WebRTC for any of these models.

---

## Key Question 3: What is the most practical, lowest-code path for this stack, and what are the risks?

### Takeaway
The lowest-code path is a **speaker-embedding gate layered on Sortformer's per-word speaker tags**:
- Auto-enroll the caller from the first clean single-speaker final (about 2–3 s or more of speech).
- Map each Sortformer speaker ID to caller or non-caller by cosine similarity.
- Replace or augment `MultiSpeakerAdapter`'s RMS rule with that mapping.
- Add an audio-level gate for barge-in and turn detection. The adapter only filters final text, and LiveKit's VAD-driven interruption never consults `is_primary_speaker`.

A PSE/TSE front-end (causal BSRNN) is a second-phase option, justified only if crosstalk *overlapping* the caller hurts ASR, and only after profiling and a license check.

### Cited Findings
- **What the current stack does.**
  - riva_server tags speakers **only on final words** — [NeMo-Speech.cpp customization.md](https://github.com/NVIDIA/NeMo-Speech.cpp/blob/main/docs/asr/customization.md).
  - LiveKit's adapter updates the primary speaker only on `FINAL_TRANSCRIPT` and passes through any event with `speaker_id=None`.
  - The first speaker heard becomes primary. Another speaker takes over if 1.3× louder, falling to 0.5× after the primary has been silent for a while.
  - (All verified) — [multi_speaker_adapter.py](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/stt/multi_speaker_adapter.py).
- **Interruption in LiveKit 1.8.3** is configured through `TurnHandlingOptions.interruption`: `mode` ("adaptive" or "vad"), `min_duration` (default 0.5 s), `min_words` (default 0, "STT only"), `resume_false_interruption` (default True), `false_interruption_timeout` (default 2.0 s) and `backchannel_boundary` (verified) — [voice/turn.py](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py). `is_primary_speaker` is defined in `stt/stt.py` but not consumed by the voice pipeline (grep of v1.8.3).
- **Embedding models for the gate** (licenses verified above): WeSpeaker ONNX CAM++/ResNet34 (CC-BY-4.0 weights) — [pretrained.md](https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md); TitaNet-Large (CC-BY-4.0) — [mirror](https://github.com/chemcoder-2020/speakerverification_en_titanet_large); sherpa-onnx speaker ID/verification runtime (Apache-2.0) — [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).
- **Prior art for "diarize, then verify against the enrolled target" in streaming:** accuracy >0.90 and specificity 0.95–0.98 with off-the-shelf pretrained models (snippet) — [arXiv 2608.17972](https://arxiv.org/abs/2608.17972).
- **Streaming Sortformer's AOSC** keeps speaker identities over time within a stream (verified, NeMo tutorial) — [Streaming_Multitalker_ASR.ipynb](https://github.com/NVIDIA-NeMo/Speech/blob/main/tutorials/asr/Streaming_Multitalker_ASR.ipynb). That is the basis for trusting a slot's identity on short segments.
- **Enrollment-less / self-enrollment is established in the literature:** pVAD 2.0's enrollment-less mode — [arXiv 2204.03793](https://arxiv.org/abs/2204.03793); SE-DiCoW "Self-Enrolled" — [DiCoW README](https://github.com/BUTSpeechFIT/DiCoW); PSE using its own internal representation as enrollment — [arXiv 2406.09928](https://arxiv.org/html/2406.09928).
- **Enrollment quality matters.** DNS 2023 gave 30 s of (possibly noisy) enrollment — [MS DNS 2023](https://www.microsoft.com/en-us/research/academic-program/deep-noise-suppression-challenge-icassp-2023/). Enrollment/test acoustic mismatch degrades PSE (snippet) — [arXiv 2211.12097](https://arxiv.org/pdf/2211.12097). Hybrid, multi-utterance enrollment stabilizes short-duration SV (snippet) — [arXiv 2606.16115](https://arxiv.org/abs/2606.16115).
- **Heavier alternative.** NeMo multitalker Parakeet transcribes each diarized speaker separately without enrollment; one instance per speaker; 80 ms minimum chunk (verified) — [NeMo tutorial](https://github.com/NVIDIA-NeMo/Speech/blob/main/tutorials/asr/Streaming_Multitalker_ASR.ipynb).

### Inferences
Proposed wiring, ordered from lowest to highest effort. All of this is my design, not published recipes.

1. **Embedding gate on finals (lowest code; roughly a few hundred lines of Python).**
   - Keep a 30–60 s ring buffer of 16 kHz PCM in a custom STT wrapper, alongside or replacing `MultiSpeakerAdapter`.
   - On each final, group words by `speaker_id` and slice the audio by word timestamps.
   - **Enrollment:** the first final (or first N finals) where only one speaker ID is present, total speech ≥2–3 s, and no overlap. Compute an embedding with WeSpeaker CAM++/ResNet34 ONNX or TitaNet and store it as the caller centroid, plus the Sortformer slot ID it came from.
   - **Decisions per speaker ID:**
     - Segment ≥1–1.5 s: score cosine against the centroid.
     - Shorter segments (backchannels): inherit the slot's last decision.
     - A slot is marked non-caller only after cumulative evidence (for example two segments or ≥3 s total) falls below the threshold. This hysteresis avoids flip-flopping.
   - **Updating:** EMA-update the centroid only with segments of high similarity and long duration.
   - Log every dropped final with its similarity score so thresholds can be tuned on real calls.
   - Thresholds are model-specific; the 0.7–0.75 cosine *distance* in arXiv 2608.17972 is for pyannote embeddings.
2. **Gate barge-in and end-of-turn on the same decision.**
   - Set `interruption.min_words ≥ 1–2` so barge-in requires STT words.
   - Filter *interim* transcripts from non-caller slots. This is hard, because riva only tags finals.
   - Alternative: run a separate streaming Sortformer (or FVAD, if weights appear) to get frame-level speaker activity as a personal-VAD signal for the caller's slot.
   - Without this step, TV speech still triggers VAD barge-in and end-of-turn even when its text is dropped.
3. **Optional PSE/TSE front-end (phase 2).**
   - Prototype the REAL-TSE `spk_emb_causal_100` BSRNN checkpoint offline on recorded calls. Enroll it with the same auto-enrollment audio.
   - Measure caller WER on clean audio, caller TSOS on short turns, and CPU RTF on Mac and Linux.
   - Adopt only if it clearly beats gating on overlapped segments. The checkpoint license must also be clarified or the model retrained with Apache-2.0 WeSep code on licensable data.
4. **Alternative ASR path.** Multitalker Parakeet (SSA) via NeMo Python gives per-speaker transcripts for free. Costs: replacing the C++ riva_server ASR, per-speaker instances, and a possible single-speaker accuracy regression (arXiv 2609.10265 measures this).

**Enrollment failure modes and mitigations:**
- **The wrong person speaks first** (IVR prompt, bystander, TV at call start). Require ≥2–3 s of single-speaker speech. Prefer the speaker who answers the agent's first question. Allow re-enrollment when a "non-caller" slot dominates for a long time and keeps answering the agent.
- **The caller changes device or channel mid-call** (handset to speaker, Bluetooth switch). The channel shift lowers cosine similarity. Keep slot-continuity as the primary signal, use embeddings as secondary, and allow the centroid to adapt.
- **Similar voices** (same gender and family, or a TV host with a similar voice). Embeddings alone may not separate them. Combine with the level and proximity cue (the RMS rule already in LiveKit, or an FVAD-like foreground cue).
- **Short utterances and backchannels.** Never gate these by their own embedding; use the diarizer's slot.
- **Sortformer slot errors** (speaker confusion, slot reuse after long silence, the 4-speaker cap on V2). The embedding check can catch a slot that silently switches identity. Periodic re-scoring of long segments is the safeguard.
- **Privacy and legal.** Storing a caller voiceprint is biometric data in some jurisdictions. Keep it per-call and in-memory only.

**Risk ranking.** Gating risks dropping real caller turns (false rejection) and letting a bystander through (false accept), both measurable from logs. A PSE front-end adds irreversible audio distortion (TSOS), extra latency and CPU, unclear weight licenses, and domain mismatch (training on LibriMix/VoxCeleb versus 8 kHz or Opus call audio).

### Gaps
- No published open-source implementation of "Sortformer tags + embedding gate" for LiveKit or Pipecat was found. The closest is the Diart + pyannote pipeline in arXiv 2608.17972.
- Embedding latency and cost per 1–3 s segment on Apple Silicon and on a Linux CPU for CAM++/ResNet34/TitaNet were not measured or found. The 5–30 ms figure above is an estimate.
- Whether NeMo-Speech.cpp can expose frame-level Sortformer speaker probabilities, or tags on interim results, over the Riva gRPC API is not documented. The docs only state final-word tags.
- No evidence was found on how well Sortformer keeps slot identity for a TV voice versus the caller over long calls (for example 10+ minutes), or on channel-change robustness.
