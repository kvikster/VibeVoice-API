# NVIDIA Audio Effects (AFX, formerly Maxine) Speaker Focus: how to obtain, license, deploy and run it on your own Linux servers (as of 26 Sept 2026)

Context: a self-hosted English voice agent on LiveKit Agents 1.8.3 (Python) with a NeMo-Speech.cpp `riva_server` (Nemotron streaming ASR + Sortformer; ggml, optional CUDA). Development is on an Apple Silicon Mac; production runs on the user's own Linux servers, GPU model not yet chosen. Caller audio must not go to third-party clouds. These notes build on `research_notes/Огляд рішень voice isolation/other_commercial.md`.

**Method and source reliability.** The egress proxy blocked every NVIDIA web host: docs.nvidia.com, developer.nvidia.com, catalog.ngc.nvidia.com, api.ngc.nvidia.com, nvcr.io, build.nvidia.com, forums.developer.nvidia.com, enterprise-support.nvidia.com, blogs.nvidia.com, www.nvidia.com and developer.download.nvidia.com. It also blocked web.archive.org, aws.amazon.com, azuremarketplace, theregister.com, pi3g.com, page.adn.de, docs.rafay.co and codeberg.org. Evidence therefore comes in three grades:
- **(primary, git)**: files read from GitHub via `git clone`. These are NVIDIA's own repos, including licence PDFs NVIDIA ships in them, plus a few third-party integrator repos.
- **(snippet)**: search-engine snippets or summaries of the cited page. They can lose context, and the version a snippet came from is sometimes unclear.
- **(third-party)**: hobby or integrator repos. Useful as practitioner evidence, not authoritative.

NVIDIA's performance tables, the full "Get Started on Linux" page for 3.0.0, the NGC page bodies and the June 2026 pricing update could **not** be read in full. See the Gaps sections.

---

## Q1. Distribution: where the Linux and Windows AFX SDKs come from, what entitlement each needs, evaluation paths, and how Speaker Focus models are delivered

### Takeaway
- **Linux AFX SDK**: an NGC resource/collection gated behind an **NVIDIA AI Enterprise (NVAIE)** entitlement. A free NGC or Developer Program account sees "Subscribe to get access" or a redirect to NVAIE sales (reported June 2026).
- **Windows AFX SDK**: free to download for RTX developers. NVIDIA forum users describe it as "free on Windows, but not on Linux" (June 2026).
- **Speaker Focus** is **not** a separate product. It is an **Early Access feature package** inside the normal SDK (`speaker_focus-16k`, `speaker_focus-48k`), downloaded per GPU architecture with the SDK's `download_features.sh` or from NGC. It must be named explicitly in the download command.
- The separate **"AI for Media Early Access Program"** is by application only: limited admission, mutual NDA, corporate e-mail domain. It carries a non-production evaluation licence. It is for EA microservices and pre-release builds, not the route to production.

### Cited Findings
**Linux SDK on NGC (entitlement-gated)**
- The NGC resource "Linux Audio Effects SDK" (`orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk`) states: "The Linux SDKs are included with NVAIE license (NVIDIA AI Enterprise)". The SDK is "designed and optimized for server-side (datacenter or cloud) deployments" (snippet, undated page, seen in 2026 searches). [NGC: Linux Audio Effects SDK](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)
- The collection page is `maxine_linux_audio_effects_sdk_collection`. Older "GA" resource IDs also exist: `maxine_linux_audio_effects_sdk_ga` and `maxine_linux_audio_effects_sdk_guide` (snippet). [NGC collection](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/collections/maxine_linux_audio_effects_sdk_collection/-); [NGC GA resource](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/maxine/resources/maxine_linux_audio_effects_sdk_ga); [NGC programming guide resource](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/maxine/resources/maxine_linux_audio_effects_sdk_guide)
- The NGC CLI path used by a community installer (2026-03-22) is `ngc registry resource download-version "nvidia/maxine/maxine_linux_audio_effects_sdk:latest"`. The same installer uses `nvidia/maxine/maxine_linux_video_effects_sdk` for the VFX SDK (primary, git; third-party). [Darudas/maxine-pipewire scripts/setup-sdk.sh](https://github.com/Darudas/maxine-pipewire)
- **Access gate, reported 2026-06-29/30 by a third-party integrator**: "External Linux real processing requires existing access to the NVIDIA NGC Linux Audio Effects SDK collection. If NGC shows 'Subscribe to get access' or redirects to 'Contact an NVIDIA AI Enterprise Sales Representative', the external technical install cannot proceed." The documented entry path is "NVIDIA AI for Media → Audio Effects → View on NGC (Linux) → Linux Audio Effects SDK collection". Only after the "Artifacts" tab is visible can you download the base SDK archive and then models for the target GPU, via the in-SDK download script or the NGC UI (primary, git; third-party). [tsuchim/nvafx-audio-cli README + docs/linux.md](https://github.com/tsuchim/nvafx-audio-cli)
- **Conflicting third-party claim**: the maxine-pipewire hobby project (single-day project, 2026-03-22) says the SDK "is freely available but requires an NVIDIA NGC account". This conflicts with the NGC page text, the integrator report above and the forum thread below, so treat it as **unreliable**. [Darudas/maxine-pipewire README](https://github.com/Darudas/maxine-pipewire)
- A second integrator (arzvaak/linux-broadcast, last commit 2026-08-23) also writes "With NVIDIA AI Enterprise access, install the 48 kHz feature packages …" and uses an NGC personal key with "catalog access required by the AFX resources in your organization" (primary, git; third-party). [arzvaak/linux-broadcast README](https://github.com/arzvaak/linux-broadcast)
- An NVIDIA Developer Forums thread titled **"Why is the Maxine Audio Effects SDK Free on windows, but not on Linux?"** (category "AI for Media"). A search summary dates it to June 2026. The page body and any NVIDIA reply could not be read (snippet, title only). [NVIDIA forums thread 372446](https://forums.developer.nvidia.com/t/why-is-the-maxine-audio-effects-sdk-free-on-windows-but-not-on-linux/372446)
- NVIDIA developer page wording (snippet; the exact page version is uncertain): "The latest Maxine production release is included exclusively with NVIDIA AI Enterprise … if you're interested in early access, with non-production access to production and soon-to-be-released features, see the Maxine Early Access program." [NVIDIA AI For Media developer page](https://developer.nvidia.com/maxine)

**SDK structure and Speaker Focus model delivery**
- The SDK has two parts (snippet, AFX docs):
  - a **core SDK package**: base library, headers, dependent libraries, and scripts that download feature packages and samples;
  - **feature packages**: the model library plus GPU-specific model files per effect, downloaded from NGC or with the feature download script.

  Both the base SDK and at least one feature package must be installed. [AFX latest: Install the AFX SDK (Linux)](https://docs.nvidia.com/maxine/afx/latest/LinuxAFXSDK/InstallTheAFXSDK.html)
- The Early Access features are named explicitly in the download script. Example documented command (snippet, 2.1.0/3.0.0 docs; `aec` and `voice_font` belong to pre-3.0 lists): `./download_features.sh --effects …,denoiser-16k,denoiser-48k,…,speaker_focus-16k,speaker_focus-48k,…`. In AFX 3.0.0, Speaker Focus (16k and 48k) "must be explicitly named when downloading" (snippet). [AFX 2.1.0 Install (Linux)](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/InstallTheAFXSDK.html); [AFX 3.0.0 user guide PDF](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf)
- The installed Linux layout (primary, git; third-party, AFX 2.x):
  - `Audio_Effects_SDK/nvafx/include/nvAudioEffects.h`
  - `nvafx/lib/libnv_audiofx.so` (versioned, e.g. `libnv_audiofx.so.2.1.0`)
  - `external/cuda/lib/` (bundled CUDA runtime)
  - `features/<effect>/lib/libnv_audiofx_<effect>.so`
  - `features/<effect>/models/<sm_XX>/<effect>_<rate>k.trtpkg`

  [tsuchim/nvafx-audio-cli docs/linux.md](https://github.com/tsuchim/nvafx-audio-cli)
- NVIDIA's official 3.0.0 Linux sample resolves the Speaker Focus model as `features/speaker_focus/models/${arch}/speaker_focus_${sample_rate}k.trtpkg`, supports rates "16 48", and exposes the chains `speaker_focus_16k_denoiser_16k` and `speaker_focus_48k_denoiser_48k` (primary, git; commit "3.0.0 release", 2026-09-10). [NVIDIA-Maxine/AFX-SDK-Samples linux/effects_demo/run_effect.sh](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)

**GitHub (API and samples only, no binaries)**
- `NVIDIA-Maxine/AFX-SDK-Samples` holds MIT-licensed sample apps for Linux and Windows. Commit history (primary, git):
  - 2.0.0: 2025-10-29
  - 2.1.0: 2026-03-16
  - 3.0.0: 2026-09-10
  - "N1X driver version fix": 2026-09-16

  The 3.0.0 release removes the AEC and Voice Font sample inputs and adds Studio Voice mic profiles. [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- `NVIDIA-Maxine/Maxine-AFX-SDK` (MIT API headers and samples) is still at tag **v1.3.0 (2025-06-07)** and Windows-only. Its README says the DLLs and models come from "an installer hosted on NVIDIA MAXINE developer page". It lists no Speaker Focus (primary, git). [NVIDIA-Maxine/Maxine-AFX-SDK](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK)
- The original `github.com/NVIDIA/MAXINE-AFX-SDK` asked about in the brief no longer resolves publicly: `git clone` asked for credentials. A Codeberg mirror describes itself as "Mirror of https://github.com/NVIDIA/MAXINE-AFX-SDK before it went private" (snippet, title). [Codeberg Freso/NVIDIA-MAXINE-AFX-SDK](https://codeberg.org/Freso/NVIDIA-MAXINE-AFX-SDK)

**Windows SDK**
- NGC resource "Windows Audio Effects SDK" (`orgs/nvidia/maxine/resources/maxine_windows_audio_effects_sdk`) (snippet). [NGC Windows AFX SDK](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_windows_audio_effects_sdk/-?_lr=1)
- Historic Windows end-user **redistributable installers** were public, one per RTX generation (20/30/40/50 series), hosted on `international.download.nvidia.com`. The latest listed is AFX 1.6.1, dated 2025-01-21, e.g. `2025-01-21_NVIDIA_AFX_SDK_Win_v1.6.1.2-GA_Blackwell.exe` (primary, git; third-party OBS StreamFX wiki). [StreamFX wiki: NVIDIA Maxine Redistributables](https://github.com/Vhonowslend/StreamFX-Public/wiki/NVIDIA-Maxine-Redistributables)

**Evaluation paths**
- **NVAIE 90-day evaluation**: "a free 90-day evaluation license that grants access to all software branches and enterprise support", applied for at the enterprise product registration page. One snippet says the trial requires an "NVIDIA-Certified server compatible with NVIDIA AI Enterprise"; the source page is uncertain (snippet). [NVAIE eval registration](https://enterpriseproductregistration.nvidia.com/?LicType=EVAL&ProductFamily=NVAIEnterprise); [Get Started with NVAIE](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/get-started/)
- **AI for Media Early Access Program**:
  - Covers "new AI for Media cloud-native UCF-compliant Audio Effects Microservice and Video Effects Microservice".
  - "available to a limited number of applicants based on use case/deployment and infrastructure fit".
  - "NVIDIA requires a mutual NDA to be executed before granting access".
  - The application "must be under your organization's email domain".

  (snippet) [NVIDIA AI for Media Early Access Program](https://developer.nvidia.com/ai-for-media/early-access); [older URL](https://developer.nvidia.com/maxine-early-access)
- The **NVIDIA Maxine Evaluation License Agreement** (dated 2024-12-06) "governs use of certain early access versions of NVIDIA Maxine software". It grants use "for development, test and evaluation purposes in systems with NVIDIA GPUs, **without use in production**". The licensed materials are confidential, and evaluation results may not be disclosed without NVIDIA's written consent (snippet). [Maxine evaluation license PDF](https://developer.download.nvidia.com/maxine/nvidia-maxine-evaluation-license-2024.12.06.pdf)
- Speaker Focus was first announced with Maxine updates at **CES 2023** (snippet). As of AFX 3.0.0 (Sept 2026) it is still Early Access in both the Linux and Windows SDKs (snippet). [AI for Media EA page (search summary)](https://developer.nvidia.com/ai-for-media/early-access); [AFX 3.0.0 Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)

### Inferences
- The practical route to production is an NVAIE entitlement (paid subscription, perpetual licence, a GPU bundle that includes NVAIE, or a 90-day trial for evaluation). That makes the Linux AFX collection's Artifacts tab visible in the user's NGC org. From there, download the core SDK and then `download_features.sh --effects speaker_focus-16k,denoiser-16k` (plus the 48k variants if needed) for each target GPU architecture. Applying to the EA Program is **not** needed for Speaker Focus, because SF ships as an EA feature inside the NVAIE SDK. The EA Program's evaluation licence also forbids production use.
- Speaker Focus has been "Early Access" for about 3.5 years (CES 2023 to AFX 3.0.0, Sept 2026). NVIDIA may keep it EA indefinitely or drop it. Plan for that risk (see Q2).
- The model files are TensorRT packages per compute capability (`sm_75/80/86/89/90/100/120`). Changing GPU family means downloading the matching feature package, so pin architecture-specific models in the deployment artefact.

### Gaps
- The NGC page bodies (licence text shown on NGC, version and date of the current Linux resource, file names) could not be read. The exact filename and size of the 3.0.0 Linux artefacts are unknown.
- Unverified: whether the **NVIDIA Developer Program** (free) unlocks the Linux AFX collection. All reachable evidence (the NGC "included with NVAIE" text, the June 2026 integrator report, the forum thread title) says it does not.
- Whether the Early Access Program's "UCF Audio Effects Microservice" exposes Speaker Focus is not documented in reachable sources.
- The Windows SDK's governing licence (the "LICENSE AGREEMENT FOR NVIDIA SOFTWARE DEVELOPMENT KITS" at developer.nvidia.com/downloads/maxine-sdk-license) could not be read in full.

---

## Q2. Licensing: NVAIE prices (2025–2026), whether Maxine/AFX is included, EULA terms for commercial server use and Early Access, runtime licence checks and telemetry, and product status in 2026

### Takeaway
- **Price:** NVAIE list prices (2025–2026) are **$4,500 per GPU per year**. Multi-year terms: $13,500 (3 years), $18,000 (5 years), or **$22,500 perpetual including 5 years of support**. Education and Inception pricing is **$1,125 per GPU per year**. The cloud-marketplace price is **$1 per GPU-hour** on top of instance cost. European resellers quote about **€5,800 per GPU-year**. H100 PCIe/NVL and H200 NVL cards ship with a **5-year NVAIE subscription included**.
- **Included products:** Maxine/AI for Media is inside NVAIE; no separate SKU was found.
- **Licence terms:** the NVAIE licence (NVIDIA Software License Agreement + AI Product-Specific Terms, May 2025) allows **offering the software as a service** and internal production use per licensed GPU. However, "Early Access" features are "Pre-Release": used "at Customer's risk", "not intended for use in business-critical systems", **excluded from Enterprise Support**, and can be withdrawn at any time. The EA Program's own evaluation licence forbids production use outright.
- **Runtime:** on bare metal no licence server is documented for AFX, and the public API has no licence calls. The licence reserves rights to collect data for compliance checks, to request usage reports and to audit.
- **Status:** the product line is alive and rebranded **"NVIDIA AI for Media"**. The SDK is now called "NVIDIA Audio Effects (AFX) SDK". AFX 3.0.0 shipped 10 Sept 2026, deprecating AEC and Voice Font. No end-of-life notice for AFX or Speaker Focus was found.

### Cited Findings
**Prices**
- NVAIE "can be purchased by enterprises as a subscription, on a consumption basis via cloud marketplaces and as a perpetual license with required 5-year support services". List prices (snippet of NVIDIA's licensing guide plus a 2026 reseller article):
  - 1 year: $4,500/GPU
  - 3 years: $13,500
  - 5 years: $18,000
  - perpetual with 5 years of support: $22,500
  - education/Inception: $1,125/GPU/year
  - marketplace: "$1/GPU/hour on top of whatever the cloud provider charges"

  [NVIDIA Licensing Guide: pricing](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/pricing.html); [pi3g: NVAIE cost in 2026](https://pi3g.com/nvidia-ai-enterprise-subscription-cost-in-2026/)
  - Caveat: one search summary listed "2 years: $9,000 … 4 years: $18,000, 5 years: $18,000", which is internally inconsistent. Treat 2- and 4-year figures as unverified.
- Europe, 2026: "A one-year subscription costs €5,800 (excluding VAT)" and education "€1,500 instead of €5,800" (snippet, pi3g). Another summary phrased a 5-year SKU as "€5,800 instead of €23,000", so the European SKU mapping is **ambiguous**. [pi3g](https://pi3g.com/nvidia-ai-enterprise-subscription-cost-in-2026/)
- Dell sells "NVIDIA AI Enterprise Subscription per GPU 5 Years Includes Standard 8x5 Support" (AC566093), a 3-year variant (AC566092), "NVIDIA AI Enterprise Perpetual License and Support per GPU 5 Years" (AC566097), and a 24x7 "Business Critical" support upgrade (snippet; prices not visible). [Dell 5-yr](https://www.dell.com/en-us/shop/nvidia-ai-enterprise-subscription-per-gpu-5-years-includes-standard-8x5-support/apd/ac566093/software); [Dell perpetual](https://www.dell.com/en-us/shop/nvidia-ai-enterprise-perpetual-license-and-support-per-gpu-5-years/apd/ac566097/software); [Dell 24x7 upgrade](https://www.dell.com/en-us/shop/nvidia-ai-enterprise-upgrade-to-24x7-enterprise-support-services-for-nvidia-ai-enterprise-per-gpu-1-year/apd/ac566099/software)
- NVIDIA published a "**NVIDIA Product and Pricing Update 2026**" support article, dated **24 June 2026** per a search summary. Its contents could not be read (snippet, title and date only). [NVIDIA enterprise support: pricing update 2026](https://enterprise-support.nvidia.com/s/article/nvidia-pricing-update-2026)
- GPU counting (The Register, 2025-04-01): NVIDIA counts each Blackwell Ultra die as a GPU for NVAIE, so an HGX B300 NVL16 counts as 16 GPUs. An HGX B200 with 8 modules was quoted at "$36,000 a year or $8 per hour in the cloud" (snippet). [The Register](https://www.theregister.com/2025/04/01/nvidia_ai_enterprise_cost/)
- "NVIDIA H200 NVL, H100 NVL, and H100 PCIe GPUs for mainstream servers include a five-year NVIDIA [AI] Enterprise subscription", redeemed through NVIDIA's activation page (snippet). [NVIDIA H200](https://www.nvidia.com/en-us/data-center/h200/); [Activate NVAIE](https://www.nvidia.com/en-us/data-center/activate-license/)

**What NVAIE covers, and per-GPU counting**
- "NVIDIA AI application frameworks, NVIDIA pretrained models and all other NVIDIA AI software available on NGC are supported with an NVIDIA AI Enterprise license, with 100+ AI frameworks and pretrained models including NeMo, **Maxine**, cuOpt" (snippet). [NVAIE Licensing Guide: platform overview](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/platform-overview.html)
- Licensing guide wording: "NVIDIA AI Enterprise software is licensed on a per-GPU basis, and a software license is required for **every GPU installed on the server** or workstation that will host any software included with NVIDIA AI Enterprise" (snippet). [NVAIE Licensing](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/licensing.html)
- The contract definition is narrower (NVIDIA Software License Agreement, 2025-05-05, §17.23, primary, git): "'GPU' means (i) for on-premise deployments, the number of physical GPUs in the computing environment **which is accessed by the Enterprise Product** … For per GPU licenses, NVIDIA requires one Enterprise Product license for each GPU." This **conflicts** in emphasis with the guide ("every GPU installed on the server"). [NVIDIA-Software-License-Agreement-2025.05.05.pdf in NVIDIA-Maxine/Maxine-Telepresence](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)

**EULA terms relevant to a commercial voice-agent server** (primary, git: *Product-Specific Terms for NVIDIA AI Products*, v. 5 May 2025, and the *NVIDIA Software License Agreement* 2025.05.05, both shipped by NVIDIA in the Maxine-Telepresence repo). [NVIDIA-Maxine/Maxine-Telepresence](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- **Scope**: "NVIDIA AI Enterprise" means "NVIDIA AI software in the NVIDIA NGC AI Enterprise catalog … including NVIDIA NIMs" (§1.3).
- **Grant for Enterprise Products** (§1.1): Customers may "install, use, reproduce … and configure", "**offer as a service** the Software … as part of a Customer Product", and "sublicense and distribute the Software … as part of a Customer Product". This is limited to "Compatible Application[s]" and applies "for the duration of the license".
- **Trials**: "trial licenses to Enterprise Products are licensed … solely for the trial period" (§1.2.7).
- **Developer program**: access is "solely for internal evaluation, development or test non-production purposes. Software offered as part of the developer program is **not for use, distribution or deployment in production**" (§1.2.8).
- **RTX-designated free NIMs**: usable without a subscription only on "a PC or workstation with NVIDIA RTX or NVIDIA GeForce RTX GPUs" and "**not used in a commercial kiosk, server or other system used to service multiple users**" (§1.2.10).
- **Obligations**: a "Use Report" upon NVIDIA's e-mail request, "no more than monthly" (§1.7.2). Benchmark and performance results may not be disclosed without permission (§8.9). NVIDIA SDKs (CUDA, TensorRT, cuDNN) and drivers are "licensed only to run on systems with NVIDIA Platforms" (§8.16). No circumventing "technical limitation … authentication mechanism" (§8.7). No use "for the purpose of emotion recognition" (§8.17).
- **Pre-Release / Early Access** (SLA §3 and §17.34): "'Pre-Release' means a version or feature … identified by NVIDIA as beta, developer preview, **early access** or otherwise as pre-release". Pre-Release "may have reduced or different security, privacy … and reliability standards". The customer uses it "at Customer's risk, understanding that such versions are **not intended for use in business-critical systems**". NVIDIA "may choose to abandon development and terminate the availability of a Pre-Release version at any time". Pre-Release versions are "AS-IS" and "**excluded from Enterprise Support**".
- **Term**: licences terminate automatically at expiry of the subscription (§10.1). A perpetual licence keeps the right to use "at the last-supported level" after services expire (§4.1).
- **Data collection** (SLA §11.1): "Software may collect data for the following purposes: … (c) **check for compliance with the license** or detect fraud …; (d) improve NVIDIA products". This may include "configuration data; operating system; installed applications and drivers … application settings, performance and usage data". Diagnostics and crash reports require consent. "Please review documentation accompanying the relevant Software for data collection specific to the Software."
- **Audit**: NVIDIA or an auditor may audit during the term and for 3 years after, at most annually (§16.7).
- **Maxine Evaluation License** (EA Program, 2024-12-06): "without use in production"; confidentiality; results may not be published (snippet). [Maxine evaluation license PDF](https://developer.download.nvidia.com/maxine/nvidia-maxine-evaluation-license-2024.12.06.pdf)
- **Branding**: products integrating the SDK must follow NVIDIA's branding guidelines (`https://www.nvidia.com/maxine-sdk-guidelines`) (primary, git). [AFX-SDK-Samples windows/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)

**Runtime licence checks and phone-home**
- The public AFX C API (`nvAudioEffects.h`, v1.3.0) and NVIDIA's 3.0.0 Linux and Windows samples contain **no licence, activation or key calls**. Effect setup is `NvAFX_CreateEffect` → `NvAFX_Set*` → `NvAFX_Load` → `NvAFX_Run`. Status codes cover GPU, CUDA and model errors (e.g. `NVAFX_STATUS_GPU_UNSUPPORTED`, `NVAFX_UNSUPPORTED_RUNTIME`), not licensing (primary, git). [Maxine-AFX-SDK nvafx/include/nvAudioEffects.h](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK); [AFX-SDK-Samples linux/effects_demo/effects_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- One integrator's Linux helper "does not use credential material" at run time. NGC keys are used "only to acquire SDK features and models" (primary, git; third-party). [tsuchim/nvafx-audio-cli docs/linux.md](https://github.com/tsuchim/nvafx-audio-cli)
- NVIDIA License System (CLS cloud-hosted, or DLS on-prem for air-gapped sites) is documented for **vGPU**. Per a third-party summary (Rafay, 2026-03-20): "Standard CUDA compute works without a license on bare metal", but NVAIE NGC software and NIMs are contractually licensed per physical GPU. vGPU VMs that fail to obtain an NLS licence degrade over time (snippet). [Rafay: when do you need an NVAIE license](https://docs.rafay.co/blog/2026/03/20/when-do-you-need-an-nvidia-ai-enterprise-license-with-gpu-virtualization/); [NVAIE bare-metal NLS page](https://docs.nvidia.com/ai-enterprise/deployment/bare-metal/latest/nls.html)

**Product status 2026**
- Developer pages now read "**NVIDIA AI for Media** (formerly NVIDIA Maxine) is a collection of SDKs, NVIDIA NIM and Blueprints …" (snippet). [NVIDIA AI for Media](https://developer.nvidia.com/ai-for-media); [docs index "NVIDIA AI for Media SDKs"](https://docs.nvidia.com/maxine/index.html)
- AFX doc titles changed from "NVIDIA **Maxine** Audio Effects (AFX) SDK" (2.0.0) to "NVIDIA Audio Effects (AFX) SDK" (2.1.0, 3.0.0, latest) (snippet). [AFX 2.0.0](https://docs.nvidia.com/maxine/afx/2.0.0/index.html); [AFX latest](https://docs.nvidia.com/maxine/afx/latest/index.html)
- AFX **3.0.0** (samples commit 2026-09-10) deprecates the "Acoustic Echo Cancellation (AEC) effect and Voice Font effect" (snippet). The samples commit deletes their inputs and options (primary, git). Speaker Focus remains Early Access. [AFX 3.0.0 user guide](https://docs.nvidia.com/maxine/afx/3.0.0/nvidia-afx-sdk-user-guide.pdf); [AFX-SDK-Samples commit 1707ee0](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- At **IBC 2026** (Amsterdam, Sept 2026) NVIDIA announced "a major expansion to NVIDIA AI for Media". Items in snippets: Studio Voice NIM, BNR, Synthetic Video Detector NIM, LipSync NIM update, Active Speaker Detection. Speaker Focus was **not mentioned** (snippet). [NVIDIA blog: IBC 2026](https://blogs.nvidia.com/blog/ibc-news-2026/); [Blockchain.News summary](https://blockchain.news/news/nvidia-expands-ai-media-ibc-2026)
- GitHub org `NVIDIA-Maxine` activity in Sept 2026 (primary, GitHub API): AFX-SDK-Samples pushed 2026-09-16, nim-clients 2026-09-18, VFX-SDK-Samples 2026-09-19. [github.com/NVIDIA-Maxine](https://github.com/NVIDIA-Maxine)

### Inferences
- **Cost floor for production**: 1 NVAIE licence per GPU that the AFX process can access. Examples:
  - one L4/T4 server: $4,500/yr (≈$375/month), or $22,500 perpetual over 5 years (≈$4,500/yr);
  - a 2-GPU server if the "every GPU installed" reading applies: $9,000/yr.
- **Per-minute arithmetic** (not a quote): one licence spread over N always-busy concurrent call slots costs $4,500 ÷ (N × 525,600 min/yr).
  - N = 10: ≈ $0.00086/min at 100% occupancy, ≈ $0.0029/min at 30%.
  - N = 50: ≈ $0.00017/min at 100% occupancy.

  At realistic volumes this is cheap per minute. It is a fixed cost, so it hurts only at very low volume.
- **Use the included-NVAIE bundles** if the user ever buys H100 PCIe/NVL or H200 NVL. The 5-year NVAIE entitlement then comes with the GPU and could cover AFX at no extra licence cost. Confirm eligibility with NVIDIA.
- **Early Access in production is contractually possible under a paid NVAIE licence but unsupported**:
  - no support tickets or SLAs for Speaker Focus;
  - it may be withdrawn without liability;
  - NVIDIA says it is not for "business-critical systems".

  Architect Speaker Focus as an **optional, bypassable stage** with a feature flag and automatic fallback to BNR-only or passthrough. Keep the Sortformer speaker-ID gating as the primary defence against TV and bystander speech. Do **not** go to production under the EA Program's evaluation licence ("without use in production").
- **Benchmark confidentiality (§8.9)** matters. The user can run internal A/B tests (Speaker Focus vs Krisp vs ai-coustics), but publishing the numbers requires NVIDIA's permission.
- **Offline operation**: nothing in the API or samples suggests a runtime licence server or activation for AFX on bare metal. The SLA still reserves the right to collect data for licence-compliance checks. Before production, run the SDK in a network-isolated container (no egress) and capture its traffic to confirm it never phones home. Also ask NVIDIA in writing whether AFX 3.x collects any telemetry.
- **The "every GPU installed" wording versus the "GPUs … accessed by the Enterprise Product" definition** determines how many licences a multi-GPU box needs. Pinning AFX to one GPU (`CUDA_VISIBLE_DEVICES`) may or may not reduce the count. Get the answer in writing from NVIDIA or the reseller.

### Gaps
- The contents of NVIDIA's "Product and Pricing Update 2026" (24 June 2026) are unknown. List prices above may have changed mid-2026.
- No reseller price (CDW, Thinkmate, Dell) was visible for a 1-year per-GPU SKU in 2026. The European €5,800 figure maps ambiguously to 1-year vs 5-year.
- No NVIDIA statement specific to AFX data collection or telemetry was reachable.
- Whether the NVAIE-bundled licence with H100/H200 is transferable across servers, and whether the marketplace per-hour entitlement unlocks the Linux AFX NGC collection, are both unverified.
- No end-of-life or deprecation notice for Speaker Focus was found. None was found for GA either.

---

## Q3. Runtime requirements: distros, drivers, CUDA/TensorRT, containers, Kubernetes, MIG and vGPU, GPU architectures, GeForce, ARM64

### Takeaway
- **Hardware:** Linux AFX runs only on NVIDIA **Tensor-Core** GPUs. The 3.0.0 sample's GPU list is T4 (sm_75); A2, A10, A16, A40 (sm_86); A30, A100 (sm_80); L4, L40 (sm_89); H100 (sm_90); B100, B200 (sm_100); **RTX PRO 6000 Blackwell** (sm_120); and V100 (sm_70). Models are auto-selected by compute capability.
- **Software:** CUDA, TensorRT and cuDNN are **bundled** in `external/cuda`. Recent docs quote CUDA 12.8.1 / TensorRT 10.9 / cuDNN 9.7.1 and a minimum driver of **570.26**. Hosts need at least 10 GB RAM.
- **Containers:** there is **no prebuilt nvcr.io AFX container**, only a sample `Dockerfile` (`FROM ubuntu:20.04`) that runs under the NVIDIA Container Toolkit using the host driver.
- **Partitioning:** MIG is supported only on **A30/A100**.
- **GeForce:** not supported on Linux. The SDK's device selector rejects GeForce, the GeForce driver EULA forbids datacenter use, and NVAIE doesn't cover GeForce.
- **ARM64:** Windows-on-Arm N1X is supported; Linux aarch64 (Grace/Jetson) shows no evidence of support.

### Cited Findings
- **GPU map in NVIDIA's AFX 3.0.0 Linux sample** (primary, git; `linux/effects_demo/run_effect.sh`, commit 2026-09-10):
  - `a100`, `a30` → `sm_80`
  - `a2`, `a10`, `a16`, `a40` → `sm_86`
  - `t4` → `sm_75`
  - `v100` → `sm_70`
  - `l4`, `l40` → `sm_89`
  - `h100` → `sm_90`
  - `b100`, `b200` → `sm_100`
  - `rtx_pro_6000` → `sm_120`
  - The default is `t4`. If `-g` is omitted, the script auto-detects compute capability ("Auto-detected GPU Compute capability = …, using models for this architecture").

  [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- **Docs** (snippet; the exact doc version for each item is uncertain):
  - "The Linux SDK is supported on systems that have a minimum of 10 GB RAM and NVIDIA GPUs with Tensor Cores".
  - Supported GPUs: Turing (T4), Ampere (A2, A10, A16, A30, A40, A100), Ada (L4, L40), Hopper (H100), Blackwell (B100, B200, RTX PRO 6000).
  - Distros: "Ubuntu 18.04, RHEL8, CentOS8, and Debian 10+". This likely comes from an older page, since the sample container uses Ubuntu 20.04.
  - Driver "570.26 or later".
  - "CUDA 12.8.1, TensorRT 10.9.0.34, and CuDNN 9.7.1, with all required libraries included in the package under external/cuda".

  [AFX 3.0.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/3.0.0/LinuxAFXSDK/GetStartedOnLinux.html); [AFX 2.1.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/GetStartedOnLinux.html)
  - The 2021 v1.0 Linux guide listed CUDA 11.1u1 / TensorRT 7.2.2.3 / cuDNN 8.0.5 and driver 455.23 (snippet). This shows the bundled stack moves with each SDK major version. [AFX Linux guide v1.0 (2021)](https://d29g4g2dyqv443.cloudfront.net/sites/default/files/akamai/maxine%2FNVIDIA_Audio_Effects_SDK_Programming_Guide_Linux.pdf)
- The sample prints an **unsupported CUDA runtime** error if the driver is too old. It suggests installing a newer driver "or if using FCU, library path contains the correct CUDA compat libraries", so CUDA forward-compatibility on datacenter drivers is anticipated (primary, git). [AFX-SDK-Samples effects_demo.cpp](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- **Container** (primary, git; `linux/container/`):
  - Prerequisites: "Minimum required driver version … installed on the host" and "Docker (with NVIDIA GPU support) >= 20.10.21".
  - The `Dockerfile` is `FROM ubuntu:20.04` plus `cmake make g++`, with the SDK added at `/opt/nvidia/Audio_Effects_SDK`.
  - Run with `docker run --gpus=all`.
  - "The container will use the driver installed on the host system (via Nvidia Container Toolkit), and does not require separate installation of the Nvidia driver or the CUDA toolkit."
  - The build script requires feature models to be downloaded first. The container tag in `config.sh` is still `2.1.0` in the 3.0.0 tree.

  [AFX-SDK-Samples linux/container](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- **Multi-GPU and MIG** (snippet): "The SDK supports Multi-Instance GPU (MIG) only on Tesla A30 and Ampere A100. When MIG is enabled, the GPU instance and corresponding compute instance must be defined". By default the application sets the GPU; optionally the SDK picks the best GPU. For chained effects on multi-GPU Linux hosts, "the device should be set before NvAFX_Load()", and different effects in a chain can run on different GPUs. [AFX 3.0.0 Use Multiple GPUs](https://docs.nvidia.com/maxine/afx/3.0.0/UseAFXInApps/UseMultipleGPUs.html); [AFX 2.1.0 Use Multiple GPUs](https://docs.nvidia.com/maxine/afx/2.1.0/UseAFXInApps/UseMultipleGPUs.html)
- **API knobs relevant to servers** (primary, git; header v1.3.0 plus the 3.0.0 samples):
  - `NVAFX_PARAM_NUM_STREAMS`: batch many streams in one effect handle.
  - `NVAFX_PARAM_ACTIVE_STREAMS`: Linux only; pause streams whose data isn't ready (demonstrated in `effects_delayed_streams_demo`).
  - `NVAFX_PARAM_USE_DEFAULT_GPU`.
  - `NVAFX_PARAM_USER_CUDA_CONTEXT`: the application manages its own CUDA context.
  - `NVAFX_PARAM_DISABLE_CUDA_GRAPH`: CUDA graphs are on by default.
  - `NVAFX_PARAM_CHAINED_EFFECT_GPU_LIST`.
  - Frame size 10 or 20 ms.
  - The sample app accepts up to 1024 inputs: "more may be supported by the SDK depending on GPU … refer to the programming guide for limits".
  - VAD is supported only for `denoiser` and `dereverb_denoiser`, not Speaker Focus.

  [Maxine-AFX-SDK header](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK); [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- **Speaker Focus I/O** (snippet): 32-bit float, mono, 16 kHz or 48 kHz; "supports audio with up to four speakers". [AFX latest: Speaker Focus](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html)
- **GeForce on Linux (unofficial)**:
  - arzvaak/linux-broadcast (Aug 2026) ships AFX-based bundles for GeForce RTX 20/30/40/50 and was hardware-tested on an RTX 4080. It maps sm_75→T4, sm_86→A10, sm_89→L40 and sm_120→RTX PRO 6000 models. It states: "**The Linux SDK's supported-device selector rejects GeForce cards**, so the engine retains CUDA device 0 and loads the matching model directly", and "The package equivalents … do not imply official GeForce support from NVIDIA" (primary, git; third-party). [arzvaak/linux-broadcast](https://github.com/arzvaak/linux-broadcast)
  - PINTO0309/Maxine-env ran the older Linux AFX SDK on an RTX 3070 (sm_86) by adding `["rtx3070"]="sm_86"` to the sample's GPU map, on Ubuntu 22.04 + Docker (primary, git; third-party; last commit 2024-10-02). [PINTO0309/Maxine-env](https://github.com/PINTO0309/Maxine-env)
- **GeForce driver EULA**: "No Datacenter Deployment. The SOFTWARE is not licensed for datacenter deployment, except that blockchain processing in a datacenter is permitted" (clause added in 2018; snippet). [TechPowerUp](https://www.techpowerup.com/239994/nvidia-forbids-geforce-driver-deployment-in-data-centers); [Phoronix](https://www.phoronix.com/news/GeForce-No-Datacenters)
- **NVAIE GPU support** (snippet):
  - NVAIE Infra 8.1 (May 2026) supports Ada (L4, L20, L40, L40S, RTX 6000 Ada), Hopper (H100, H200, H800, H20), Blackwell (B200, B300, RTX PRO 4500/6000 Blackwell), Ampere (A10, A16, A30, A40, A100, RTX A5000/A6000) and Turing (T4).
  - Infra 8.1 "removes V100 (Volta) and the 5 workstation-class GPUs".
  - Infra 4.10 LTSB reached EOL in July 2026.
  - "NVAIE infrastructure does not support the RTX 4090 GPU".

  [NVAIE 8.1 support matrix](https://docs.nvidia.com/ai-enterprise/release-8/latest/support/support-matrix-8/8.1.html); [NVAIE EOL notices](https://docs.nvidia.com/ai-enterprise/lifecycle/latest/eol-notices.html)
- **ARM64**:
  - The Windows AFX SDK supports "ARM64 (N1X): 616.41 or later" drivers. It was 615.15 until the 2026-09-16 commit. The Windows helper "selects the Blackwell Windows-on-Arm models automatically" on N1X (primary, git). [AFX-SDK-Samples windows/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
  - No Linux aarch64 build appears in the samples' GPU map, docs snippets or integrator repos. The integrator packages are all `x86_64`/`amd64`. [arzvaak/linux-broadcast](https://github.com/arzvaak/linux-broadcast); [tsuchim/nvafx-audio-cli](https://github.com/tsuchim/nvafx-audio-cli)
- **Windows SDK requirements** (primary, git; 3.0.0):
  - 64-bit Windows 10/11
  - MSVC 2015+ and CMake 3.10+
  - driver x86/x64 ≥ **520.46**
  - architectures `turing / ampere / ada / blackwell`
  - effects include `speaker_focus`

  [AFX-SDK-Samples windows](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)

### Inferences
- **Supported production targets on Linux** are T4, L4, A10, A2/A16, L40/L40S, RTX PRO 6000 Blackwell, H100 and B200. For a voice agent the realistic choices are **L4** (24 GB, ~72 W, sm_89) or **T4** (16 GB, older; still in NVAIE 8.1). **RTX PRO 6000 Blackwell** (96 GB) fits an all-in-one ASR + LLM + TTS + AFX box. V100 still appears in the AFX sample map but is dropped from NVAIE 8.1, so avoid it.
- **Kubernetes**: nothing AFX-specific exists (no Helm chart or operator). Build a container from the sample Dockerfile, bake the SDK plus the sm-specific `.trtpkg` models into a private image (never a public one; see redistribution terms in Q2), and schedule with the NVIDIA device plugin or GPU Operator. The driver must be ≥ the SDK minimum (570.26 per the snippet), or use CUDA forward-compat libraries on older datacenter branches.
- **MIG** (A30/A100 only) is unlikely to matter for a small L4/T4 fleet. Time-slicing or MPS are not documented for AFX either way; see Q4.
- **GeForce in production is excluded three times over**: NVIDIA's device selector rejects it, the GeForce driver EULA forbids datacenter deployment, and NVAIE doesn't cover GeForce. It may "work" technically (the RTX 4080 and 3070 reports), which is at most a private dev-box convenience. Even that sits outside the NVAIE-supported matrix.
- **No Grace/Jetson/Linux-ARM path** was found, so plan x86_64 Linux servers.

### Gaps
- The authoritative 3.0.0 Linux table (distros, minimum driver, bundled CUDA/TensorRT versions) was not readable; the values above may mix 2.1.0 and 3.0.0.
- vGPU support for AFX (NVAIE vGPU for Compute) is not documented in reachable sources.
- Whether AFX 3.0.0 still ships `sm_70` (V100) models is unverified. The sample map lists v100, but NVAIE 8.1 dropped V100.
- No official statement on Linux aarch64 (Grace, GH200/GB200 hosts) or Jetson.

---

## Q4. Co-location and sizing: sharing a GPU with riva_server (NeMo-Speech.cpp) and an LLM/TTS; memory per stream; streams per GPU; cheapest GPU for 10, 50 and 200 concurrent calls

### Takeaway
Nothing technical prevents Speaker Focus from sharing a GPU with NeMo-Speech.cpp and an LLM/TTS:
- AFX is an ordinary CUDA/TensorRT library;
- one handle can batch many streams (`NUM_STREAMS`, `ACTIVE_STREAMS`);
- it can run inside a caller-supplied CUDA context.

**NVIDIA's per-GPU Speaker Focus throughput and latency tables exist in the AFX docs but were not readable.** No verified per-stream memory figure or streams-per-GPU figure exists in these notes. The only numbers available are a hobbyist's unverified single-stream estimates: ~250 MB VRAM and ~3–7% of an RTX 3060, with ~10 ms latency. Sizing below is **inference** and must be benchmarked.

### Cited Findings
- The AFX docs have a Speaker Focus section giving "maximum throughput (the number of batches supported in real time)" on Linux. The search snippet did not include the numbers (snippet). [AFX 2.1.0: Speaker Focus](https://docs.nvidia.com/maxine/afx/2.1.0/AboutTheEffects/AboutSpeakerFocusEffect.html); [AFX 3.0.0: Speaker Focus](https://docs.nvidia.com/maxine/afx/3.0.0/AboutTheEffects/AboutSpeakerFocusEffect.html)
- AFX release-readiness criteria (Windows guide): reference workload Denoiser v2 with 10 ms (160-sample) frames at 16 kHz; p95 `NvAFX_Run` must stay below the 10 ms frame budget, and p05 throughput above 1.0× real time (snippet, from the earlier survey). [AFX Windows Performance and Deployment Guide](https://docs.nvidia.com/maxine/afx/latest/WindowsAFXSDK/ReleaseReadiness.html)
- Batching and stream control: `NVAFX_PARAM_NUM_STREAMS`; `NVAFX_PARAM_ACTIVE_STREAMS` ("On Linux only, during batching, you can temporarily pause streams … if data is not ready for that stream"); per-stream reset; the sample supports up to 1024 streams. Also `NVAFX_PARAM_USER_CUDA_CONTEXT` and `NVAFX_PARAM_DISABLE_CUDA_GRAPH` (primary, git plus snippet). [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples); [Maxine-AFX-SDK header](https://github.com/NVIDIA-Maxine/Maxine-AFX-SDK); [AFX effects_delayed_streams_demo docs](https://docs.nvidia.com/maxine/afx/latest/LinuxAFXSDK/SampleApplicationsLinux/EffectsDelayedStreamsDemoApplication.html)
- Third-party desktop estimates (maxine-pipewire `doc/EFFECTS.md`, 2026-03-22; methodology not stated; likely rough):
  - Speaker Focus: "~10 ms" latency, "~250 MB" VRAM, "~3–7%" of an RTX 3060, single stream.
  - Denoiser: ~200 MB.
  - Studio Voice HQ: ~350 MB.
  - Required hardware: "Minimum 4 GB VRAM (6+ GB recommended when stacking effects)".

  (Third-party, unverified.) [Darudas/maxine-pipewire](https://github.com/Darudas/maxine-pipewire)
- The Linux SDK host minimum is 10 GB system RAM (snippet). [AFX 3.0.0 Get Started on Linux](https://docs.nvidia.com/maxine/afx/3.0.0/LinuxAFXSDK/GetStartedOnLinux.html)
- Speaker Focus is 16 kHz or 48 kHz mono float32. It chains with BNR at the same rate (`speaker_focus16k → denoiser16k`) (primary, git; snippet). [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- The Maxine BNR NIM (a different product) scales concurrency per GPU with `MAXINE_MAX_CONCURRENCY_PER_GPU` (snippet, BNR NIM 2.0.0 docs). This shows NVIDIA's own serving pattern is many streams per GPU. [BNR NIM 2.0.0 Advanced Usage](https://docs.nvidia.com/nim/maxine/bnr/2.0.0/advanced-usage.html)

### Inferences
**Co-location pattern**
- Run AFX inside the LiveKit agent worker, or better, as a **single sidecar process per GPU** that owns one batched Speaker Focus handle (`NUM_STREAMS = max calls`). Mark idle or empty streams inactive with `ACTIVE_STREAMS`, and feed it 10 ms, 160-sample, 16 kHz float32 frames from all calls.
- One process and one CUDA context for all calls avoids per-call context overhead. Separate processes (AFX sidecar, `riva_server`, LLM, TTS) each create their own CUDA context, typically a few hundred MB each (general CUDA behaviour, not AFX-specific).
- Using 16 kHz end-to-end matches Nemotron/Sortformer and halves compute versus 48 kHz.

**Contention risk**
- AFX work is small but strictly periodic (every 10 or 20 ms). LLM prefill bursts on the same GPU can push AFX p95 above the frame budget. Mitigations:
  - give AFX its own CUDA stream and keep CUDA graphs on (the default);
  - consider CUDA MPS or separate GPUs for the LLM;
  - monitor p95 `NvAFX_Run` against the 10 ms budget, which is NVIDIA's own acceptance criterion.

**Sizing (inference only; replace with the NVIDIA table or measurement)**

Assuming a batched Speaker Focus stream costs roughly what a denoiser stream costs:
- **10 concurrent calls**: AFX alone is trivial for any supported GPU. The binding constraint is the *other* workloads. The cheapest supported option is **one T4 or L4 shared with riva_server** (and TTS if it fits). NVAIE cost: 1 GPU licence.
- **50 concurrent calls**: still very likely within one **L4** for AFX + ASR, **with the LLM on a separate GPU or server**. Licences: 1 (AFX GPU), plus possibly more under the "every GPU installed" reading if the LLM GPU is in the same server.
- **200 concurrent calls**: plan 1–2 **L4/L40S-class** GPUs dedicated to front-end audio (AFX + streaming ASR), sharded by call, with LLM/TTS elsewhere. Alternatively, one **RTX PRO 6000 Blackwell** for audio. Keep AFX on as few GPUs as possible, because NVAIE is charged per GPU.

**Licence-driven topology**
- Because NVAIE is per GPU, put AFX on a dedicated small GPU (T4/L4) in an otherwise non-NVAIE server, or on the ASR GPU. Avoid spreading it across every GPU. Confirm the counting rule (Q2) before buying.

### Gaps
- **NVIDIA's Speaker Focus throughput and latency table** (streams in real time per T4/L4/A10/etc., 10 vs 20 ms frames, 16 vs 48 kHz) could not be read because docs.nvidia.com was blocked. This is the most important missing number for sizing.
- Unknown:
  - per-stream and fixed GPU memory for Speaker Focus;
  - model load time;
  - Speaker Focus algorithmic look-ahead (the "~10 ms" figure is a hobbyist estimate);
  - whether CUDA MPS or time-slicing is supported or tested with AFX.
- No measured co-location data (AFX + ggml/CUDA riva_server + LLM on one GPU) exists in any reachable source.

---

## Q5. Windows alternative and the Mac-development problem

### Takeaway
- **Windows SDK:** free to download for RTX GPUs (20/30/40/50-series, RTX professional cards). It supports Speaker Focus (EA), BNR v1/v2, dereverb, super-resolution and Studio Voice. NVIDIA positions it as a **client-side** SDK, so it is a good **developer-workstation** option (a Windows PC with an RTX card) for listening tests and parameter tuning.
- **Windows server:** running it on a Windows server that serves many callers conflicts with its client-side positioning, and with GeForce driver terms if a GeForce card is used. Get licence confirmation before relying on it.
- **NVIDIA Broadcast:** a consumer app with no server API.
- **Mac:** no route exists. Develop against a remote Linux GPU box, either an on-prem dev server under an NVAIE 90-day trial or subscription, or a cloud GPU VM (L4 ≈ $0.80/h, T4 ≈ $0.53/h, us-east-1) using **synthetic or consented test audio only**. Keep a bypass flag on the Mac.

### Cited Findings
- **Windows AFX SDK 3.0.0 feature list**:
  1. Background Noise Removal v1 and v2
  2. Room Echo Cancellation
  3. REC + BNR
  4. Audio Super Resolution
  5. **Speaker Focus (SF)**
  6. Studio Voice HQ/LL + mic profiles

  Requirements: Windows 10/11 x64, driver ≥ 520.46 (ARM64 N1X ≥ 616.41). "The SDK is powered by NVIDIA RTX graphics processor units (GPUs) with Tensor Cores". Architecture selection is `turing / ampere / ada / blackwell` (primary, git; 2026-09). [AFX-SDK-Samples windows/README.md and scripts/README.md](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- "The Windows SDK is optimized for client-side application integration, and the Linux SDK is designed and optimized for server-side (datacenter/cloud) deployments" (snippet, AFX docs via search summary). [AFX 2.0.0 index](https://docs.nvidia.com/maxine/afx/2.0.0/index.html)
- Evidence that the Windows SDK is free versus the Linux SDK:
  - the forum thread title "Why is the Maxine Audio Effects SDK Free on windows, but not on Linux?" (snippet, title);
  - historic public Windows redistributable installers per RTX series (primary, git; third-party wiki).

  [NVIDIA forums 372446](https://forums.developer.nvidia.com/t/why-is-the-maxine-audio-effects-sdk-free-on-windows-but-not-on-linux/372446); [StreamFX wiki](https://github.com/Vhonowslend/StreamFX-Public/wiki/NVIDIA-Maxine-Redistributables)
- Maxine SDKs on Windows are governed by the "LICENSE AGREEMENT FOR NVIDIA SOFTWARE DEVELOPMENT KITS". It permits distributing SDK portions "identified … as distributable, as incorporated in object code format into a software application". Older Windows requirements named "GeForce RTX 20XX and 30XX Series, Quadro RTX 3000, TITAN RTX, or higher" (snippet). [Maxine SDK license](https://developer.nvidia.com/downloads/maxine-sdk-license)
- **NVIDIA Broadcast** is a Windows desktop app needing an RTX 2060 / Quadro RTX 3000 / TITAN RTX or better (snippet; from the earlier survey). [NVIDIA Broadcast FAQ](https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/faq/)
- **GeForce driver EULA**: "No Datacenter Deployment" (snippet). [TechPowerUp](https://www.techpowerup.com/239994/nvidia-forbids-geforce-driver-deployment-in-data-centers)
- RTX/GeForce-designated free NIMs are limited to "a PC or workstation" and "not used in a commercial kiosk, server or other system used to service multiple users" (primary, git; §1.2.10). This shows NVIDIA's general stance on free RTX-tier AI software versus multi-user servers. [Product-Specific Terms for NVIDIA AI Products (5 May 2025)](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- **Cloud dev GPU prices** (snippet, Sept 2026): AWS **g6.xlarge (L4) $0.8048/h** and **g4dn.xlarge (T4) $0.526/h**, on-demand, us-east-1. [Vantage g6.xlarge](https://instances.vantage.sh/aws/ec2/g6.xlarge); [Vantage g4dn.xlarge](https://instances.vantage.sh/aws/ec2/g4dn.xlarge)
- **NVIDIA Developer Program**: free; grants self-hosted **NIM** use "for research, application development, and experimentation on up to 16 GPUs"; "for prototyping, research, development and testing purposes only" (snippet). Under the contract this is non-production only (§1.2.8, primary). It is **not** shown to cover the Linux AFX SDK. [NVIDIA blog: NIM free to Developer Program members](https://developer.nvidia.com/blog/access-to-nvidia-nim-now-available-free-to-developer-program-members); [Product-Specific Terms](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)

### Inferences
**Recommended dev loop**
1. **Mac**: keep the LiveKit agent's audio front end behind an interface (`passthrough | afx_remote | krisp | …`).
2. **Remote Linux GPU dev box** (own server under the NVAIE 90-day trial, or a cloud L4 VM on the NVAIE trial):
   - run an **AFX sidecar exposing a tiny gRPC/WebSocket PCM-in/PCM-out service**;
   - the Mac-side agent calls it over a VPN or SSH tunnel with test audio.
3. **Production**: the same sidecar image on the prod GPUs.

Dev and prod then share one code path, and the Mac never needs NVIDIA software. Latency over the tunnel does not reflect prod, so measure latency on the server.

**Windows RTX PC** as a second dev option: useful for quick offline A/B listening tests of Speaker Focus on recorded TV and bystander audio (`run_effects_demo.bat -e speaker_focus`). Models and behaviour should match Linux for the same architecture family, but this is not guaranteed; verify.

**Windows server in production**: Windows SDK on a Windows Server with an RTX PRO/A-series card serving many callers. This is technically plausible, but the "client-side" positioning and the unreadable SDK licence make it a legal grey zone. Ask NVIDIA before choosing it; it also complicates the Linux-based stack.

**Caller-audio rule**: a cloud dev VM is acceptable only for synthetic or consented recordings. Real caller audio must stay on the user's own servers.

### Gaps
- The Windows SDK licence text (server use, multi-user use, redistribution of Speaker Focus EA models) could not be read.
- Unverified: whether the NVAIE 90-day trial can be activated on a cloud VM rather than an "NVIDIA-Certified server".
- Unverified: whether Windows and Linux Speaker Focus models are identical per architecture.

---

## Q6. Maxine / AI for Media NIMs in 2026: audio NIMs, Speaker Focus NIM status, licensing, APIs, on-prem

### Takeaway
As of Sept 2026 the AI for Media NIM line-up has two audio NIMs:
- **Background Noise Removal (BNR)**;
- **Studio Voice**, plus a Studio Voice ST 2110 / Holoscan-for-Media variant.

The other NIMs are video (Active Speaker Detection, Eye Contact, LipSync, Relighting, Synthetic Video Detector; Audio2Face-2D in earlier lists). **No Speaker Focus NIM exists or has been announced** (none at IBC 2026). NIMs use **gRPC** (streaming and transactional), are self-hostable on-prem as containers, and are licensed under **NVAIE** for production. The free Developer Program allows non-production use on up to 16 GPUs. The build.nvidia.com "Try API" sends audio to NVIDIA's cloud (NVCF), which violates the no-third-party-cloud rule.

### Cited Findings
- `NVIDIA-Maxine/nim-clients` README (primary, git; repo pushed 2026-09-18; latest commit in clone 2026-07-15 "Lipsync v1.3.0"):
  - "NVIDIA AI for Media NIM Clients" lists `active-speaker-detection`, `bnr`, `eye-contact`, `lipsync`, `relighting`, `studio-voice` and `synthetic-video-detector`.
  - "NVIDIA AI for Media ST 2110 NIMs" (Holoscan for Media) list `st2110/active-speaker-detection`, `st2110/lipsync` and `st2110/studio-voice`.
  - **No Speaker Focus.**

  [NVIDIA-Maxine/nim-clients](https://github.com/NVIDIA-Maxine/nim-clients)
- BNR NIM client (primary, git):
  - "NVIDIA NIM Client packages use gRPC APIs".
  - Streaming mode is the default ("recommended"); transactional mode is also available.
  - `--sample-rate` 16000 or 48000; `--intensity-ratio` 0–1; WAV only.
  - A cloud "Try API" preview at `grpc.nvcf.nvidia.com:443` needs an NGC API key and function ID.

  [nim-clients/bnr/README.md](https://github.com/NVIDIA-Maxine/nim-clients)
- Studio Voice NIM client: model types `48k-hq`, `48k-ll`, `16k-hq`; streaming mode "provides lower latency than transactional mode"; the model type must match `NIM_MODEL_PROFILE` (primary, git). [nim-clients/studio-voice/README.md](https://github.com/NVIDIA-Maxine/nim-clients)
- The BNR NIM docs exist for version **2.0.0**. Concurrency per GPU is set via `MAXINE_MAX_CONCURRENCY_PER_GPU` (snippet). [BNR NIM 2.0.0 Advanced Usage](https://docs.nvidia.com/nim/maxine/bnr/2.0.0/advanced-usage.html). The earlier survey found BNR NIM v1.0.0 released June 10, 2025 (snippet). [NGC BNR NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/maxine-bnr/-?_lr=1)
- Studio Voice Low-Latency (48 kHz) has **80 ms** algorithmic latency (snippet, from the earlier survey), too slow for barge-in-sensitive paths. [AFX docs index](https://docs.nvidia.com/maxine/afx/latest/index.html)
- "With NVIDIA NIM™, part of NVIDIA AI Enterprise, developers can access AI for Media capabilities with easy-to-use microservices designed for secure, reliable, high-performance deployment across clouds, data centers, and workstations" (snippet). [NVIDIA AI For Media developer page](https://developer.nvidia.com/maxine)
- NVAIE scope explicitly "including NVIDIA NIMs" (§1.3). Free RTX-tier NIMs are restricted to single-user PCs and workstations, not servers (§1.2.10) (primary, git). [Product-Specific Terms (5 May 2025)](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- IBC 2026 (Sept 2026) AI for Media announcements in snippets: Studio Voice NIM, BNR, Synthetic Video Detector NIM, LipSync update, Active Speaker Detection with VAD and gRPC. No Speaker Focus NIM (snippet). [NVIDIA blog IBC 2026](https://blogs.nvidia.com/blog/ibc-news-2026/)
- The EA Program mentions a "UCF-compliant Audio Effects Microservice" for early-access participants under NDA (snippet). [AI for Media Early Access](https://developer.nvidia.com/ai-for-media/early-access)

### Inferences
- For **Speaker Focus specifically**, the SDK is the only route: there is no NIM, and the EA "Audio Effects Microservice" is NDA/evaluation-only with an undocumented feature set. The BNR NIM is a reasonable **noise-only** fallback. It is self-hostable, uses gRPC streaming, fits the same NVAIE licence, and scales by concurrency. It does **not** remove competing talkers.
- If NVIDIA eventually ships a Speaker Focus NIM, it would plug into the same sidecar interface recommended in Q5. Design the sidecar with a gRPC PCM stream so the backend can be swapped.

### Gaps
- Unconfirmed from reachable pages: the GPU support matrix, per-stream memory and latency for the BNR 2.0.0 and Studio Voice NIMs.
- Whether BNR NIM 2.x exposes the ASR-tuned "Denoiser v2" model is unknown.
- No roadmap statement on a Speaker Focus NIM was found.

---

## Q7. Cloud GPU marketplaces offering NVAIE / Maxine, with prices (reference only)

### Takeaway
NVAIE is listed on the **AWS, Azure and Google Cloud marketplaces**. Pay-as-you-go is **$1 per GPU-hour** plus the instance cost; Azure calls it promotional and subject to change. No marketplace listing specific to Maxine or AFX was found. At 24/7 use, $1/h ≈ **$8,760 per GPU-year**, about 2× the $4,500 annual subscription. The marketplace route suits short cloud dev or eval stints only, and the no-third-party-cloud rule excludes it for real caller audio anyway.

### Cited Findings
- AWS Marketplace listing "NVIDIA AI Enterprise" (`prodview-ozgjkov6vq3l6`): "$1 per GPU-hour … equivalent to $375/GPU-month, or $4,500 per GPU per year" (snippet; the equivalence arithmetic is the summarizer's and assumes about 375 h/month, not 24/7); private pricing is available on request. [AWS Marketplace: NVIDIA AI Enterprise](https://aws.amazon.com/marketplace/pp/prodview-ozgjkov6vq3l6)
- Azure Marketplace "NVIDIA AI Enterprise": "The $1/GPU/Hr is promotional pricing and is subject to change"; plans per number of GPUs; includes NVIDIA Enterprise Support at 8am–5pm local business hours (snippet). [Azure Marketplace: NVIDIA AI Enterprise](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/nvidia.nvidia-ai-enterprise); [Microsoft Marketplace listing](https://marketplace.microsoft.com/en-us/product/virtual-machines/nvidia.nvidia-ai-enterprise?tab=overview)
- NVIDIA licensing guide: "NVIDIA AI Enterprise in cloud marketplaces is priced per GPU per hour on an on-demand/pay-as-you-go basis" (snippet). [NVAIE pricing](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/pricing.html)
- Blackwell HGX B200 (8 GPUs): quoted at "$8 per hour in the cloud" for NVAIE (snippet, The Register 2025-04-01). [The Register](https://www.theregister.com/2025/04/01/nvidia_ai_enterprise_cost/)
- Instance reference prices (us-east-1 on-demand, Sept 2026, snippet): g6.xlarge (1× L4) $0.8048/h; g4dn.xlarge (1× T4) $0.526/h. [Vantage g6.xlarge](https://instances.vantage.sh/aws/ec2/g6.xlarge); [Vantage g4dn.xlarge](https://instances.vantage.sh/aws/ec2/g4dn.xlarge)

### Inferences
- A cloud dev box running AFX from a marketplace NVAIE image costs about **$1.53/h (T4) to $1.80/h (L4)** all-in, if the marketplace entitlement exposes the Linux AFX collection (unverified). A month of 8 h/day workdays costs roughly $270–$320, cheaper than an annual subscription for a short evaluation. The free 90-day NVAIE trial is cheaper still if accepted.

### Gaps
- The GCP marketplace NVAIE listing and price were not verified (console pages blocked).
- Unverified: whether marketplace NVAIE entitlements grant NGC access to the Linux AFX SDK collection.
- No Maxine-specific marketplace product found.

---

## Q8. Synthesis: exactly what the user must do and pay to run Speaker Focus in production on-prem

### Takeaway
1. Obtain an NVAIE entitlement: a 90-day trial for evaluation, then about **$4,500 per GPU per year** (or $22,500 perpetual with 5 years of support) for each GPU running AFX. Europe ≈ €5,800 per GPU-year; free with H100 PCIe/NVL or H200 NVL.
2. Download the Linux AFX core SDK and the `speaker_focus-16k` (+ `denoiser-16k`) feature packages for the exact GPU architecture from NGC.
3. Build a private container on x86_64 Linux with an NVAIE-supported datacenter or RTX PRO GPU (T4/L4 are the cheapest) and driver ≥ 570.26.
4. Wrap the C API in a batched sidecar service fed with 10 ms, 16 kHz frames.
5. Accept that Speaker Focus is **Early Access**: usable under the paid licence at your own risk, with **no NVIDIA support and possible withdrawal**. Build a bypass and fallback, and validate WER, backchannel retention and latency in-house (results cannot be published without NVIDIA's consent).

### Cited Findings
- Linux SDK "included with NVAIE license" (snippet). [NGC Linux AFX](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/resources/maxine_linux_audio_effects_sdk/-)
- NVAIE list prices $4,500/yr, $22,500 perpetual with 5 years of support, $1/GPU-h marketplace (snippet). [NVAIE pricing](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/pricing.html)
- 90-day NVAIE evaluation (snippet). [NVAIE eval registration](https://enterpriseproductregistration.nvidia.com/?LicType=EVAL&ProductFamily=NVAIEnterprise)
- Speaker Focus feature packages `speaker_focus-16k/48k` named explicitly in `download_features.sh` (snippet). [AFX 2.1.0 Install](https://docs.nvidia.com/maxine/afx/2.1.0/LinuxAFXSDK/InstallTheAFXSDK.html)
- Early Access = Pre-Release: "not intended for use in business-critical systems", "excluded from Enterprise Support", may be terminated (primary, git). [NVIDIA SLA 2025.05.05 in Maxine-Telepresence](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- "Offer as a service" is allowed under an Enterprise Product licence; benchmark disclosure needs permission; use reports upon request (primary, git). [Product-Specific Terms 5 May 2025](https://github.com/NVIDIA-Maxine/Maxine-Telepresence)
- Sample container and GPU map (primary, git). [AFX-SDK-Samples](https://github.com/NVIDIA-Maxine/AFX-SDK-Samples)
- GeForce rejected by the SDK device selector (third-party); GeForce driver EULA forbids datacenter use (snippet). [arzvaak/linux-broadcast](https://github.com/arzvaak/linux-broadcast); [TechPowerUp](https://www.techpowerup.com/239994/nvidia-forbids-geforce-driver-deployment-in-data-centers)

### Inferences
**Step-by-step plan (inference, grounded in the findings above)**
1. **Eval (weeks 0–12, $0 licence)**:
   - apply for the NVAIE 90-day evaluation with a company e-mail;
   - use an own Linux box with a T4/L4 (or a cloud L4 VM at ≈$0.80/h plus possible marketplace fees);
   - in NGC, confirm the Linux AFX collection's Artifacts are visible;
   - download the core SDK and `speaker_focus-16k`, `denoiser-16k` for `sm_75`/`sm_89`;
   - run `run_effect.sh -e speaker_focus -s 16` on test files, then on the user's TV/bystander corpus;
   - measure Nemotron WER, Sortformer DER, backchannel recall, false barge-ins and p95 latency, and compare against Krisp and ai-coustics.
2. **Engineering**:
   - build the AFX sidecar: C++ or Python (ctypes) wrapper; a single process per GPU; one batched handle with `NUM_STREAMS = N` and `ACTIVE_STREAMS`;
   - use gRPC or WebSocket PCM streaming from LiveKit agent workers; feature flag and bypass;
   - health checks with fallback to passthrough or BNR if `NvAFX_Run` p95 exceeds 10 ms or the effect fails to load;
   - private container image from NVIDIA's Dockerfile pattern, pinned to SDK version plus `sm_XX` models;
   - driver ≥ SDK minimum; test inside a no-egress network namespace to confirm no phone-home.
3. **Procurement**:
   - buy NVAIE per GPU that AFX uses: 1-year $4,500, 3-year $13,500, 5-year $18,000, or perpetual $22,500 with 5 years of support; via Dell or other resellers; Inception $1,125/yr if eligible;
   - get written answers on:
     - (a) the licence count for multi-GPU servers when AFX is pinned to one GPU;
     - (b) production use of Early Access Speaker Focus under NVAIE;
     - (c) AFX data collection;
     - (d) redistribution of SDK binaries/models inside the user's private container images across the user's own servers.
4. **Hardware choice**: T4 (cheapest, older) or **L4** (recommended), shared with riva_server; LLM on a separate GPU. Avoid GeForce entirely in prod. If buying Hopper, prefer H100 PCIe/NVL or H200 NVL, which include 5-year NVAIE.
5. **Mac dev**: bypass or stand-in locally; call the remote AFX sidecar for integration tests; never send real caller audio to a cloud VM.

**Budget summary (arithmetic, not a quote)**
- Minimum production footprint: 1 GPU → **$4,500/yr** (or ≈$22,500 up front for perpetual with 5 years of support).
- Typical 2-GPU audio tier: **$9,000/yr**.
- Plus GPU hardware (T4/L4 class) and engineering time for the C-API sidecar.
- No per-minute fees.

### Gaps
- Speaker Focus quality and latency on telephony-grade 16 kHz speech with TV or bystander interference and backchannels is unmeasured in any reachable source. It must be tested.
- NVIDIA's official Speaker Focus throughput per GPU is unavailable here, so the per-call GPU sizing remains an estimate.
- The final 2026 price list (after the 24 June 2026 update) and NVIDIA's written position on Early Access features in production under NVAIE are unverified.
