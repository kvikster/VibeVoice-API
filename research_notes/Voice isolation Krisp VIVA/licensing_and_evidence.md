# Krisp VIVA / Krisp AI Voice SDK: access, licensing, pricing, runtime licence behaviour, platforms, company, and independent quality evidence for a self-hosted LiveKit Agents 1.8.3 voice agent (as of 2026-09-26)

Method note. The environment's egress proxy blocked all of these on 2026-09-26: krisp.ai, sdk-docs.krisp.ai, usagepricing.com, livekit.com, docs.pipecat.ai, ai-coustics.com, callsphere.ai, news.ycombinator.com, web.archive.org and huggingface.co. The GitHub API was also blocked for repos outside this session. Facts from those sites come from WebSearch result snippets, marked **(snippet)**. Snippets can be paraphrased by the search engine, so treat them as weaker than a full read. Facts marked **(code/repo read)** come from my own reading of Krisp's first-party GitHub repos (`krispai/gst-krisp-audio`, `krispai/Krisp-SDK-Sample-Apps`), the Pipecat docs and code repos, and wheels downloaded from PyPI (`livekit-plugins-krisp` 0.4.3, `livekit-plugins-krisp-internal` 0.2.0). Facts marked **(third-party profile)** come from `api-evangelist/krisp`, an independent profile of Krisp's public pages captured 2026-07-19 and last committed 2026-09-22. It quotes Krisp's docs and changelog, but it is secondary. This note extends `research_notes/Огляд рішень voice isolation/krisp.md` and does not repeat its model and integration details.

## Q0. Bottom line: what the user must do and pay to run Krisp VIVA on-prem, and what depends on Krisp's servers at runtime

### Takeaway
There is no self-serve path for VIVA:
- **Access.** Apply through the Krisp developer portal. You are placed on an "Early-stage" or "Enterprise" track, and the price is quoted by sales. No public price list exists.
- **Price.** Reference prices are about $0.001/min at volume (third-party estimate). Resellers charge $0.0012–0.0015/min after 10k free minutes/month.
- **Installation.** You download a licensed `krisp_audio` wheel and `.kef` models (not on PyPI). You run them in-process through `livekit-plugins-krisp` in `krisp_license` mode.
- **Audio stays local.** Krisp states that audio never leaves the host and that "the SDK accesses the network only for license verification needs".
- **The SDK does call home.** The standard Python package Pipecat documents is a **"UAR" (usage auto reporting)** build (`krisp-viva-uar-python-sdk-1.8.0`). Licensing code links libcurl/OpenSSL. If licence verification fails, the SDK keeps working through a "grace period". What happens afterwards is not documented.
- **Offline option.** Krisp builds **non-UAR** SDK variants: a separate non-UAR Go SDK build is documented. That is the likely route to an offline or metered-by-contract licence, but it has to be negotiated. No public offline or air-gapped licence exists.

### Cited Findings
- Access is through a Krisp developer account. You "download the Python SDK, models, and generate an API key" from `https://sdk.krisp.ai/` ("Server SDK Version" tab). The example package is `krisp-viva-uar-python-sdk-1.8.0/dist/krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl` (Pipecat docs, repo HEAD 2026-09-25; code/repo read). — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- The "Separated Go SDK UAR (usage auto reporting) and non-UAR builds; new builds no longer require build tags" (VIVA Go SDK v1.4.0 changelog; third-party profile 2026-07-19, plus snippet). — [api-evangelist changelog capture](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml); [sdk-docs VIVA Go SDK v1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)
- "The SDK accesses the network only for license verification needs. Krisp does not access, collect, or store any audio data" (Krisp SDK Security page, snippet, undated). — [sdk-docs: Security](https://sdk-docs.krisp.ai/docs/privacy)
- "A licensing error is non-fatal — the SDK continues to pass audio through its grace period, so we post a warning to the bus and keep processing" (code comment in Krisp's own GStreamer plugin, committed 2026-04-15/16; code/repo read). — [krispai/gst-krisp-audio gstkrisp_common.cpp](https://github.com/krispai/gst-krisp-audio/blob/243bbecfd98d78fb1b7e82895dd223e5f1fb0e2b/src/gstkrisp_common.cpp)
- The LiveKit plugin's license path for "Livekit OSS server" uses `krisp_audio` plus `KRISP_VIVA_SDK_LICENSE_KEY` plus a `.kef` file. It is "governed by your agreement with Krisp" (livekit-plugins-krisp 0.4.3 README, 2026-09-23; code/repo read). — [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)
- Pricing is "mostly application-gated, with an Early-stage startup track and an Enterprise track quoted via volume pricing", and "per-minute via SDK token; volume tiers go down to ~$0.001/min at scale" (third-party pricing profile, snippet, 2026, not a Krisp source). — [UsagePricing: Krisp](https://www.usagepricing.com/blueprint/krisp)

### Inferences
**What the user must do:**
1. Apply on the Krisp portal and get onto the Early-stage track.
2. Negotiate the following in writing:
   - a per-minute rate, or a flat or annual fee for self-hosted use
   - a **non-UAR (no usage auto-reporting) Python build** and an **offline or long-grace licence**
   - the model entitlements: VI-tel v2.1 / VI 2.5, IP v1.1, Turn v3, TTS-detect
   - Linux aarch64 wheels
3. Install the wheel and `.kef` files into the worker image.
4. Use `krisp.voice_isolation(auth_provider=krisp.auth.krisp_license(...))`.

**Runtime dependency on Krisp's servers (as documented by default):** a licence-verification call at start-up and on some schedule, plus usage auto-reporting in UAR builds. Audio is not sent.

**Comparison with the alternatives the user is weighing:**
- *ai-coustics.* Its standard key hard-stops enhancement after about 10 s without activation or about 5 min without usage reporting. Krisp's documented failure mode is gentler: a "grace period", non-fatal. The duration and the behaviour after expiry are unknown.
- *NVIDIA AFX.* It makes no runtime licence calls. Krisp does, unless the non-UAR/offline terms are negotiated.

### Gaps
- None of these is published: the grace-period length, the re-verification interval, whether processing stops, passes through or outputs silence after the grace period, and what a UAR report contains (minutes? stream counts? metadata?). sdk-docs.krisp.ai was blocked and the SDK binary is gated.
- No public statement that a non-UAR **Python** build or an offline/air-gapped licence is offered to customers. Only the Go SDK UAR/non-UAR split is documented.

## Q1. Access: developer portal, application/approval, trial/evaluation terms, what is downloadable, model coverage

### Takeaway
Access runs through Krisp's developer dashboard (`sdk.krisp.ai`, also `developers.krisp.ai`) after an application. The dashboard lists "licensed SDK version IDs" per platform and lets you generate an API key. There is also a REST API that returns 5-minute S3 URLs for an SDK build plus its model files, useful for CI. None of these are published:
- VIVA trial terms (duration, minute cap, watermark or time-bomb)
- the startup track's free allowance
- whether all VIVA models come with every licence

A competitor says Krisp does not allow production use during trials.

### Cited Findings
**Portal and downloads**
- The dashboard at `https://developers.krisp.ai/` is where "API keys are issued and licensed SDK version IDs are listed". The playground is `https://lab.krisp.ai/`. There are "no test-vs-live key prefix, no sandbox host" (third-party profile, 2026-07-19). — [api-evangelist sandbox](https://github.com/api-evangelist/krisp/blob/main/sandbox/krisp-sandbox.yml)
- The SDK & Model Downloads API:
  - `GET https://api.developers.krisp.ai/v2/sdk/versions/{id}/download-urls` with header `Authorization: api-key …`.
  - It returns `version{version, display_name:"VIVA", os:"windows_x64", platform:"server", technologies:["viva"], download_url}` and `models[]{technology:"voice_isolation", product:"viva", …}`, with `expires_in: 300`.
  - "A VIVA build without its model files will not run."
  - Source: third-party profile of Krisp's doc `programmatic-sdk-model-downloads-api.md`, 2026-07-19. — [api-evangelist SDK download skill](https://github.com/api-evangelist/krisp/blob/main/skills/krisp-sdk-download-pipeline.md); [openapi capture](https://github.com/api-evangelist/krisp/blob/main/openapi/_original/krisp-developers-openapi.yml)
- The core VIVA/RTC SDKs are "licensed distribution — they are not on npm, PyPI, Maven, or crates.io" (third-party profile). I confirmed that `pypi.org/pypi/krisp-audio/json` and `krisp_audio` both return 404 (own check, 2026-09-26). — [api-evangelist packages](https://github.com/api-evangelist/krisp/blob/main/packages/krisp-packages.yml)
- Krisp's own server SDK package layout: `include/krisp-audio-sdk*.hpp`, `lib/static/libkrisp-audio-sdk.a`, and `external/` holding "bundled third-party libs (libcurl, OpenSSL, …)". A `.kef` model per element (gst-krisp-audio README, 2026-04/05; code/repo read). — [krispai/gst-krisp-audio README](https://github.com/krispai/gst-krisp-audio)
- The example C++ server SDK folder name is `krisp-audio-sdk-9.9.0-server-lin_x64` (Krisp sample apps README; code/repo read). — [Krisp-SDK-Sample-Apps native-cpp README](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/README.md)

**Tracks and trials**
- VIVA plans (snippets):
  - "Early Stage (Developers) offers contact sales custom pricing … ideal for startups, early-stage builders, and teams experimenting with Voice AI".
  - The Enterprise plan adds "SSO/SCIM, … HIPAA/SOC 2/GDPR compliance, BAA signing, and a dedicated account manager".
  - Both require contacting Krisp.
  - Source: [UsagePricing: Krisp](https://www.usagepricing.com/blueprint/krisp); [krisp.ai/developers](https://krisp.ai/developers/)
- Competitor claim (ai-coustics blog, 2025-11-10, snippet): "Krisp requires manual contracts and doesn't allow production testing during the trial period." **Vendor-authored by a competitor.** — [ai-coustics: Comparing Krisp and ai-coustics](https://ai-coustics.com/blog/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you)
- The only self-serve Krisp developer product is the cloud **Voice Translation API**: self-serve since July 2026, 60-minute free credit, Starter $249/mo and Advanced $799/mo. It is irrelevant for local isolation (snippet and third-party profile). — [api-evangelist sandbox](https://github.com/api-evangelist/krisp/blob/main/sandbox/krisp-sandbox.yml); [UsagePricing](https://www.usagepricing.com/blueprint/krisp)

**Model families**
- VIVA SDK capabilities are voice isolation, turn prediction, interruption prediction and VAD. The RTC SDK covers accent conversion, outbound/inbound NC and BVC (third-party profile). — [api-evangelist packages](https://github.com/api-evangelist/krisp/blob/main/packages/krisp-packages.yml)
- Latest named model files in the changelog (VIVA C/C++ SDK 9.19.0, third-party profile 2026-07-19):
  - `krisp-viva-vi-tel-v2.1`, a 16 kHz VI model "optimized for 8–16 kHz telephony, reducing voice suppression and improving WER accuracy over krisp-viva-vi-tel-v2"
  - `krisp-viva-ip-v1.1`, with "updated model encryption"
  - a new TTS detection API
  - The **previous IP model file is not compatible with the new SDK.**
  - Source: [api-evangelist changelog](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml)
- Pipecat Cloud's managed Krisp provisions **only the voice-isolation model**, not IP or Turn. A Pipecat Cloud customer notes that Krisp's models "can only be distributed on Pipecat Cloud", which creates a catch-22 for self-provisioning (issue opened 2026-07-09, closed). — [pipecat#4994](https://github.com/pipecat-ai/pipecat/issues/4994)

### Inferences
- Model entitlements appear to be granted per model family. Pipecat Cloud resells only VI, and the download API lists models per "technology". The user should ask explicitly for VI (tel/pro/2.5/lite), IP v1.1, Turn v3 and TTS-detect in the order form. Do not assume "VIVA" means all of them.
- Model files are versioned and encrypted together with the SDK (IP v1.1 does not work on older SDKs). Upgrades therefore mean re-downloading `.kef` files from the portal. Pin SDK and model versions together in the Docker image.

### Gaps
- VIVA trial length, minute cap, and any watermark, time-bomb or degradation during evaluation: not found.
- Approval criteria and turnaround time for applications: not found.
- Whether VI 2.5 / VI lite 2.5 (blog, 2026-08-12) are already downloadable, and under which file names: not confirmed.

## Q2. Licensing and pricing models and reference price points (2025–2026)

### Takeaway
Krisp publishes **no VIVA price list**. The only numbers are these:
- Third-party estimate: per-minute metering "via SDK token" with volume tiers down to about $0.001/min.
- Resellers:
  - Pipecat Cloud: $0.0015/min after 10,000 free min/month.
  - LiveKit Cloud: voice isolation after included minutes, $0.0012/min per one snippet or $0.002–0.004/min per a third-party blog; metered since 2026-05-01.
  - Retell's (vendor unconfirmed) denoising add-on: $0.005/min.

Minimum commitments are not public. One MSA clause auto-terminates the agreement if no licences are purchased within six months.

### Cited Findings
- Licence model "per-minute via SDK token; volume tiers go down to ~$0.001/min at scale" (third-party, snippet). — [UsagePricing: Krisp](https://www.usagepricing.com/blueprint/krisp)
- Pipecat Cloud Krisp VIVA: "First 10,000 minutes per month | Free" and "Additional minutes | $0.0015 per minute". Also: "Krisp cannot be used in local development environments, as it requires a proprietary SDK and model which can only be distributed on Pipecat Cloud" (Pipecat docs repo, HEAD 2026-09-25; code/repo read). — [pipecat-cloud/guides/krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)
- LiveKit Cloud:
  - Voice isolation includes 100 min on Build, 1,000 on Ship and 10,000 on Scale, then "$0.0012/min" (snippet of the pricing page, not verified) — [livekit.com/pricing](https://livekit.com/pricing)
  - A third-party blog says "$0.002–$0.004 per minute" and "Starting May 1, 2026, Krisp voice isolation is metered on top of the base agent minute". **This conflicts with the $0.0012 figure.** — [forasoft LiveKit playbook](https://www.forasoft.com/blog/article/voice-ai-agents-livekit-guide)
  - Community thread (2026-07-15, snippet): voice isolation on Build "with 100 minutes free", and "all voice isolation models incur an additional cost". — [community.livekit.io/t/1657](https://community.livekit.io/t/voice-isolation-system-payment/1657/3)
- Retell "prices denoising at $0.005 per minute" (third-party blog, snippet). Retell's denoiser vendor is not confirmed as Krisp. — [cekura: Retell pricing](https://www.cekura.ai/blogs/retell-ai-pricing-per-minute)
- Vapi's "Smart Denoising uses Krisp's AI-powered technology" (from earlier note). I found no separate Vapi price for it. — [Vapi docs](https://docs.vapi.ai/documentation/assistants/conversation-behavior/background-speech-denoising)
- Krisp Master Subscription Agreement (snippet):
  - "If the Purchaser fails to purchase licenses in accordance with the terms of the Agreement within six months after the Effective Date, the Agreement shall be considered automatically terminated".
  - "no fees are refundable upon termination … except in the case of Company's material breach".
  - Source: [krisp.ai/master-subscription-agreement](https://krisp.ai/master-subscription-agreement/)
- LiveKit's Cloud-bundled Krisp build contains a LiveKit `drm` module (`reporter_task`, `Credentials`, `StreamInfo`) and the string "Update stream metadata used for usage reporting." In other words, the reseller path meters per stream (own `strings` inspection of `livekit-plugins-krisp-internal` 0.2.0, 2026-07-22). — [PyPI livekit-plugins-krisp-internal](https://pypi.org/project/livekit-plugins-krisp-internal/)

### Inferences
- **Budget.** At 100k–500k min/month (the user's ai-coustics comparison range), per-minute pricing in the $0.001–0.0015 range works out to about **$100–750/month**. That is comparable to or below ai-coustics self-serve ($149–599/month) and far below NVAIE's $4,500/GPU/year, *if* Krisp quotes in that range for a small self-hosted customer. The early-stage track may carry minimum fees that are not visible publicly.
- Metering is per minute of SDK processing ("via SDK token" / UAR). A self-hosted deployment will therefore report minutes to Krisp unless the contract specifies a flat-fee or non-UAR build.
- Resale terms (Pipecat's "can only be distributed on Pipecat Cloud") show that Krisp tightly controls where its binaries and models may be deployed. The user's own contract should explicitly name its own servers and dev Macs.

### Gaps
- There is no official Krisp VIVA price, minimum commit, annual-licence option, per-concurrent-stream or per-server pricing, and no AWS/Azure/GCP marketplace listing. The marketplace search returned nothing relevant.
- LiveKit's exact per-minute voice-isolation price is unresolved ($0.0012 vs $0.002–0.004). livekit.com was blocked.
- Twilio's current price for the Krisp plug-in is not found.

## Q3. Runtime licence behaviour, telemetry, privacy/certifications

### Takeaway
Krisp's documentation and code together give this picture:
1. `globalInit(workingDir, licenseKey, licensingErrorCallback, logCallback, logLevel)` validates the key **asynchronously** and reports through a callback (`LicensingError::Success` or an error).
2. Licensing needs network access. The samples link **libcurl + OpenSSL** when `ENABLE_LICENSING` is on.
3. A licensing failure is **non-fatal during a grace period**.
4. "UAR" builds **auto-report usage**. Non-UAR builds exist, at least for Go.
5. Krisp states that audio and on-device metadata are never transmitted. Network use is "only for license verification".
6. Company-level certifications: SOC 2, PCI DSS and HIPAA, with availability "dependent on plan". Some sources add ISO 27001 and GDPR. There is a Vanta trust centre and a DPA.

### Cited Findings
**Licence validation mechanics**
- Krisp's GStreamer plugin (first-party, 2026-04; code/repo read):
  - The `license-key` property is described as "Krisp SDK license key (required for the server SDK)".
  - `Krisp::AudioSdk::globalInit(L"", licenseKey, [](LicensingError err, const std::string& msg){ if (err != LicensingError::Success) … }, logCallback, logLevel)`.
  - The errors are "posted asynchronously by the SDK callback", and the plugin checks once on the first frame.
  - Source: [gst-krisp-audio krisp_session.hpp](https://github.com/krispai/gst-krisp-audio/blob/243bbecfd98d78fb1b7e82895dd223e5f1fb0e2b/src/krisp_session.hpp); [gstkrisp_common.cpp](https://github.com/krispai/gst-krisp-audio/blob/243bbecfd98d78fb1b7e82895dd223e5f1fb0e2b/src/gstkrisp_common.cpp)
- Same file: "A licensing error is non-fatal — the SDK continues to pass audio through its grace period". — [gstkrisp_common.cpp](https://github.com/krispai/gst-krisp-audio/blob/243bbecfd98d78fb1b7e82895dd223e5f1fb0e2b/src/gstkrisp_common.cpp)
- Krisp's public sample apps (code/repo read; commits 2025-09-18 and 2026-02-17):
  - `option(ENABLE_LICENSING "Enable Licensing" OFF)`.
  - The Linux x64 and aarch64 third-party link lists add `libcurl.a` and `libz.a` "When ENABLE_LICENSING is on".
  - macOS additionally links the `Security` and `SystemConfiguration` frameworks.
  - `wav-cli` then calls `globalInit(L"", "", licensingErrorCallback, …)`, printing "Licensing error: <code> - <msg>".
  - The repo's own CLAUDE.md (2026-08-28) says "no further licensing detail is in this repo".
  - Source: [CMakeLists.txt](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/CMakeLists.txt); [krisp.third.party.linux.aarch64.cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.third.party.linux.aarch64.cmake); [krisp.cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.cmake); [wav-cli main.cpp](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/wav-cli/main.cpp)
- The API key has been required since Python SDK 1.6.1, passed via constructor or `KRISP_VIVA_API_KEY` (Pipecat docs; snippet). — [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)
- How integrations handle licence errors:
  - Pipecat's `_license_callback` only logs "Krisp licensing error" — [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)
  - LiveKit's license mode only logs `[Krisp Licensing Error: …]` (livekit-plugins-krisp 0.4.3, code/repo read). Its README troubleshooting lists "Silent output — Verify the model file is valid *(license auth only)*". — [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)

**Usage reporting**
- There are UAR (usage auto reporting) and non-UAR Go SDK builds (Go SDK v1.4.0). The Python package name Pipecat documents contains "uar". — [api-evangelist changelog](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml); [pipecat-ai/docs krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)

**Data handling (Krisp claims)**
- Security page claims (snippet):
  - "Krisp SDK is expressly designed to operate solely on the SDK customer's premises, with all processing—including any optional generation of metadata such as voice and noise durations, noise levels, and voice energy metrics—performed exclusively on the customer-side."
  - "Metadata generation is only activated upon the customer's explicit instruction, and any metadata produced is not stored or transmitted."
  - "The SDK accesses the network only for license verification needs."
  - Source: [sdk-docs: Security](https://sdk-docs.krisp.ai/docs/privacy)
- A VIVA marketing snippet says it can be "deployed server-side, on-premise or in your own cloud" (Python, Node.js, Go and iOS SDKs). — [krisp.ai/developers/viva](https://krisp.ai/developers/viva/)

**Certifications**
- Krisp's llms.txt, quoted in the third-party profile (2026-07-19): "support for compliance and data protection requirements, including SOC 2, PCI DSS, and HIPAA (availability depends on plan, configuration, and organizational requirements)". trust.krisp.ai is a Vanta Trust Center. — [api-evangelist trust center](https://github.com/api-evangelist/krisp/blob/main/security/krisp-trust-center.yml)
- Snippets from Krisp security pages list "SOC 2 Type II and ISO 27001", GDPR, PCI, HIPAA, "FedRamp" and CSA STAR L1. These come from a search summary and look inflated: I would not rely on "FedRAMP" without the trust-centre document. HIPAA BAA is on the Enterprise plan. — [krisp.ai security for call centers](https://krisp.ai/security-for-call-centers-enterprises/); [Nudge Security profile](https://www.nudgesecurity.com/security-profile/krisp-ai)
- A DPA exists at krisp.ai/Krisp-DPA.pdf (not read). — [Krisp DPA](https://krisp.ai/Krisp-DPA.pdf)

### Inferences
**The "grace period" wording is ambiguous.** It can be read two ways:
- (a) The SDK keeps *processing* normally during a grace period after a failed check. This is the more natural reading of the plugin's "keep processing".
- (b) It *passes audio through unprocessed*.

Either way, a Krisp outage or a blocked egress path does not crash the pipeline immediately. Filtering could, however, silently stop after the grace window. In production:
- Alert on the licensing callback.
- Test with egress blocked.
- Put the grace length and the post-expiry behaviour into the contract.

**What crosses the network.** Licence verification needs outbound HTTPS from every worker. For "no caller audio to third parties" this is acceptable: only licence and usage data leaves, per Krisp's statement. For "no runtime dependency on the vendor" it is not acceptable unless Krisp supplies an offline or non-UAR build.

**The metadata claim and UAR are in tension.** "Metadata … not stored or transmitted" sits next to UAR builds. Most likely the UAR payload is licence/usage counters (minutes, sessions), which Krisp does not count as "metadata". The contents need to be confirmed.

### Gaps
- Not found: licence-server hostnames, re-validation interval, grace length, whether processing stops or passes through after grace, the UAR payload schema, and whether a non-UAR build or offline licence file exists for Python/Linux.
- The trust-centre certification list could not be read (rendered client-side and blocked). ISO 27001 and FedRAMP claims are unverified.

## Q4. EULA / SDK licence terms relevant to server use

### Takeaway
The SDK is "a commercial product" under a negotiated licence with Krisp Technologies, Inc. The SDK-specific licence text is not public, so nothing is known about benchmarking publication, container redistribution, server counts, audit rights or termination specific to the SDK. What is visible:
- The public Terms of Use ban reverse engineering.
- A competitive-benchmarking clause bars competitors unless they waive their own benchmarking restrictions.
- The MSA auto-terminates if no licences are bought within six months, and fees are non-refundable.
- Reseller language ("can only be distributed on Pipecat Cloud") shows that deployment scope is contractually restricted.

### Cited Findings
- "Krisp SDK is a commercial product … need to obtain a commercial license from Krisp Technologies, Inc … apply for a license on Krisp developer website" (snippet). — [sdk-docs: Licensing](https://sdk-docs.krisp.ai/docs/licensing-information)
- Terms of Use (snippet):
  - Users may not "reverse engineer, disassemble, decompile, decode, or otherwise attempt to derive or gain access to the source code of Krisp".
  - "If you are a direct competitor and access or use Krisp for purposes of competitive benchmarking … you waive any competitive use, access, and benchmarking test restrictions in the terms governing your software …; if you do not waive … you are not allowed to access or use Krisp."
  - These are consumer/service terms. Their applicability to SDK licences is unconfirmed.
  - Source: [krisp.ai/terms-of-use](https://krisp.ai/terms-of-use/)
- MSA (snippet):
  - Six-month auto-termination if licences are not purchased.
  - No refunds except for Krisp's uncured material breach.
  - "Any audit reports or certifications provided by Krisp shall be subject to a non-disclosure agreement". These are security audit reports provided to the customer, not a licence-audit right.
  - Source: [krisp.ai/master-subscription-agreement](https://krisp.ai/master-subscription-agreement/)
- LiveKit: the license path is "governed by your agreement with Krisp", while LiveKit's bundled Krisp is under the LiveKit ToS. — [PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)
- Pipecat Cloud: Krisp's "proprietary SDK and model … can only be distributed on Pipecat Cloud". — [pipecat-cloud/guides/krisp-viva.mdx](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)

### Inferences
- The competitor-benchmarking clause is aimed at competitors, not customers. Publishing the user's own A/B results (for example, Krisp vs ai-coustics vs AFX WER on internal data) may still be restricted by the SDK licence. Ask for explicit permission for internal benchmarking and non-publication.
- Baking the wheel and `.kef` files into private container images is presumably allowed as "internal deployment", but it should be stated in the contract. So should: dev Macs, number of hosts, and use in CI.

### Gaps
- The SDK licence agreement text is not public or not found. Unknown: benchmark-publication clause, redistribution in containers, per-server or per-host limits, licence-audit rights, termination-for-convenience, and what happens to deployed binaries on termination.

## Q5. Platforms, Python/ABI, CPU requirements and per-stream cost

### Takeaway
The server SDK supports **Linux x64 and armv8a (aarch64)**, macOS arm64 and x64, and Windows x64 (and arm64 for the C++ SDK). Linux ARM has existed since SDK v7.0.2, and aarch64 samples since 2025-09. The C++ server SDK is v9.9+ (currently 9.19.0) and needs GCC 9.4+.

The Python `krisp_audio` wheel:
- 1.8.0: shipped as cp312.
- 1.12.0 (Aug 2026): `cp312-abi3` built with nanobind, i.e. Python ≥3.12.
- A snippet claims Python 3.10–3.13 support, probably for older releases.

On CPU cost, there is **no official per-stream figure**:
- Krisp claims a 30 MB model, 15 ms latency, CPU-only, and one model shared across streams.
- VI got 30–40% cheaper on armv8a in 9.19.0 / Python 1.11.0.
- An unverified third-party snippet puts it at about 6–10% of one core per stream.

### Cited Findings
**OS and architecture**
- "For Desktop, Linux is supported on x86_64 and armv8a architectures … for server platforms, Linux supports both x64 and armv8a". Linux armv8a was added in SDK v7.0.2 (snippets). — [sdk-docs: Supported Platforms (server)](https://sdk-docs.krisp.ai/docs/supported-platforms-server); [SDK v7.0.2: Linux ARM](https://sdk-docs.krisp.ai/changelog/%EF%B8%8F-sdk-v702-linux-arm)
- The sample apps are "compatible with Krisp SDK Desktop/Server v9.9 or later on: Linux (x64, arm64) with GCC 9.4+; macOS (x64, arm64) with Clang 15+; Windows (x64, arm64) with Visual Studio 2019+". The commit "Added support for Linux aarch64" is dated 2025-09-18 (code/repo read). — [Krisp-SDK-Sample-Apps README](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/README.md)
- gst-krisp-audio supports "macOS (arm64, x86_64) · Linux (x86_64, arm64) · Windows (x86_64, MSVC)", mono S16LE/F32LE at 8–96 kHz. — [gst-krisp-audio](https://github.com/krispai/gst-krisp-audio)
- The statically linked third-party libraries on Linux include OpenBLAS, abseil, flatbuffers, nsync, cpuinfo and libresample, plus OpenSSL/libcrypto (and curl/zlib when licensing is on). — [krisp.third.party.linux.aarch64.cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.third.party.linux.aarch64.cmake)

**Python wheels**
- Python SDK support: "3.10, 3.11, 3.12, and 3.13"; OS "Linux x64, Windows x64, and Mac arm64". This is a snippet, likely from Krisp's Python SDK page, with its date unknown. It omits Linux arm64, which conflicts with the armv8a optimisations in the Python 1.11.0 changelog. — [Pipecat/Krisp docs snippet](https://docs.pipecat.ai/pipecat/features/krisp-viva); [sdk-docs Python SDK v1.0.0](https://sdk-docs.krisp.ai/changelog/python-sdk-v100)
- VIVA Python SDK 1.11.0 (third-party profile 2026-07-19): "Introduced stats API", "Reduced CPU consumption for Voice Isolation models by 30–40% on armv8a hardware using FP16 SIMD", and the IP model file krisp-viva-ip-v1.1. — [api-evangelist changelog](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml)
- krisp_audio 1.12.0 wheels are "cp312-abi3" and moved from pybind11 to nanobind. They reject read-only NumPy arrays and lists, which made Pipecat's filter silently pass audio through unfiltered (issue 2026-08-24, closed). Pipecat's own code comment dates the nanobind switch to 1.11.0, a minor conflict. — [pipecat#5413](https://github.com/pipecat-ai/pipecat/issues/5413); [pipecat krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)
- LiveKit's own Krisp-bundling wheels are `cp310-abi3` for manylinux_2_28 x86_64/aarch64, macOS x86_64/arm64 and win_amd64. These are LiveKit's builds, not Krisp's public wheel. — [PyPI livekit-plugins-krisp-internal](https://pypi.org/project/livekit-plugins-krisp-internal/)

**CPU cost and performance claims**
- Krisp claims (snippets):
  - "VIVA processes on CPU with a 30 MB model footprint and 15 ms algorithmic latency".
  - "supports the real-time processing of multiple audio streams using a single model loaded into memory".
  - "krisp-viva-tel-lite-v1 model is 3.5x smaller … at much lower CPU computational cost".
  - Source: [krisp.ai/developers/viva](https://krisp.ai/developers/viva/); [Krisp blog small VI model](https://krisp.ai/blog/small-voice-isolation-model/)
- "VIVA-VC adds approximately 6-10% single-core CPU per stream" (search snippet, apparently from a third-party blog. The source is uncertain, the "VIVA-VC" naming is odd, and it is **unverified**). — [callsphere.ai blog](https://callsphere.ai/blog/vw9h-build-voice-agent-krisp-audio-filter-viva-2026)
- LiveKit's packaging of Krisp NC/BVC crashed on some AMD CPUs until `OPENBLAS_CORETYPE=Haswell` was set, and forces `OPENBLAS_NUM_THREADS=1` (from earlier note). — [PyPI livekit-plugins-noise-cancellation](https://pypi.org/project/livekit-plugins-noise-cancellation/)

### Inferences
**Python version.** For current SDKs (≥1.11/1.12, nanobind, `cp312-abi3`), the agent's Python must be **≥3.12**. If the LiveKit Agents worker runs on 3.10 or 3.11, ask Krisp for matching wheels or upgrade Python.

**Linux aarch64 is very likely available:**
- the server SDK supports armv8a
- the samples build it
- there are armv8a-specific CPU optimisations in Python 1.11.0

Confirm with Krisp that the **Python** wheel ships for `manylinux…aarch64`.

**AVX2 and glibc.** The SDK uses OpenBLAS and cpuinfo, which dispatch at runtime. An AVX2 hard requirement is unlikely but not documented. The glibc level is likely manylinux_2_28-class, given the GCC 9.4+ requirement and LiveKit's own builds, but it is unconfirmed.

**Capacity planning.** No figure is trustworthy yet. Measure with the SDK's stats API (1.11.0+) on the target x86 and ARM hosts, for VI-tel vs VI-lite, at 10 ms frames.

### Gaps
- Official per-stream CPU/RAM figures, streams-per-core, AVX/NEON requirements, the manylinux/glibc tag of `krisp_audio`, and musl support: none found. The wheel is gated.
- No Docker guidance from Krisp was found, beyond the CI download API with its 5-minute S3 URLs.

## Q6. Company status, customers, support, roadmap

### Takeaway
Krisp is an established, profitable-looking vendor of about 350 people. Its VIVA agent SDK launched in July 2025 and is embedded in more than 130 voice-AI products, among them Daily/Pipecat, Vapi, LiveKit, Ultravox and Telnyx, with Twilio as a long-standing partner. Krisp reports more than 12 billion agent minutes per year. There is no public SDK SLA or public status page. Releases are frequent and sometimes break model compatibility.

### Cited Findings
**Launch and scale**
- VIVA SDK launched 2025-07-16, "surpass[ing] 1B minutes of Voice AI processing per month". — [Krisp blog](https://krisp.ai/blog/krisp-launches-viva-sdk-and-surpasses-1b-minutes-of-voice-ai-processing-per-month-milestone/); [Yahoo Finance/BusinessWire](https://finance.yahoo.com/news/krisp-launches-viva-sdk-surpasses-130000582.html)
- VIVA 2.0 (2026-05-06): "processes more than 12 billion minutes of voice AI agent traffic a year and is embedded in over 130 voice AI products, including Daily, Vapi, LiveKit, Ultravox, Telnyx, the world's leading AI labs, and the largest enterprise contact centers". Vendor outcome claims: "3.5x better turn-taking accuracy, 50% fewer dropped calls, 30% higher customer satisfaction" (snippet, vendor PR). — [BusinessWire 2026-05-06](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)
- Models "run on over 200 million devices, licensed by Discord, Twilio, and VMware among others" (third-party profile). — [api-evangelist/krisp](https://github.com/api-evangelist/krisp)

**Funding and size (unverified aggregator estimates, which conflict)**
- About $15.5M raised over 3 rounds, including a $9M round, backed by Sierra Ventures. One source says "bootstrapped". — [Tracxn](https://tracxn.com/d/companies/krisp-technologies/__rd-xYlpOUB0k7qLEd6Z8tY5DRc_8-Oerl1lBjUa6Wkc); [Signalbase](https://www.trysignalbase.com/news/funding/krisp-raises-90m-series); [api-evangelist](https://github.com/api-evangelist/krisp)
- Revenue is estimated at $37.7M ARR (Getlatka, 2025) vs $18.7M (another aggregator). — [Getlatka](https://getlatka.com/companies/krisp.ai)
- Headcount is about 343 (2026) or 370 (2026-04-30). — [Owler](https://www.owler.com/company/krisptechnologies); [growjo](https://growjo.com/company/Krisp)

**Support and reliability**
- Channels are help.krisp.ai, a contact-sales form and the dashboard. `status.krisp.ai` "is gated behind Cloudflare Access (HTTP 403)", so it is not public. A "99.9%" uptime target is advertised **only for the Voice Translation API**. There is no published deprecation policy (third-party profile, 2026-07-19). — [api-evangelist lifecycle](https://github.com/api-evangelist/krisp/blob/main/lifecycle/krisp-lifecycle.yml)

**Roadmap signals**
- Accent-conversion SDK (2026-03-03)
- GStreamer plugin (2026-04)
- VIVA 2.0 with Turn v3, VI v3 and IP v1 (2026-05-06)
- Voice Translation API self-serve (2026-07)
- VI 2.5 and VI-lite 2.5 (2026-08-12 blog)
- The CEO's post about "VIVA 2.5"
- Sources: earlier note's sources; [gst-krisp-audio commits](https://github.com/krispai/gst-krisp-audio); [Krisp-SDK-Sample-Apps commits](https://github.com/krispai/Krisp-SDK-Sample-Apps)

### Inferences
- Vendor viability risk is low. **Commercial-access risk** is the real one: an application-gated, sales-led process, and resellers restricted from redistributing the models.
- There is no public SDK SLA. An SLA would only matter for licence-server availability, which the grace period partly mitigates, so it should be negotiated.

### Gaps
- There is no public list of self-hosted/on-prem VIVA customers, and no SDK support tiers or response-time SLAs.
- Krisp's funding figures are inconsistent across aggregators, and there is no primary funding announcement after about 2021.

## Q7. Independent evidence and community feedback on quality

### Takeaway
There is **no independent, third-party quantitative benchmark** of Krisp VIVA in the sources I could reach. Everything quantitative falls into three groups:
- **Krisp's own numbers**: VI 2.5 cuts WER about 43–46%, 69.7% on background speech, and "no harm on clean audio"; BVC cuts VAD false positives 3.5×.
- **Its direct competitor ai-coustics**: Krisp is a "perceptual" denoiser that can *raise* WER, and Quail beats Krisp by a few points.
- **SEO-style agency blogs**: "20–40% relative" WER cuts.

Community reports are sparse. They are mostly integration and operations problems:
- silent pass-through after an SDK ABI change
- the "LiveKit Cloud is required" error
- AMD crashes and segfaults

There is also a little anecdotal quality feedback on over-aggressiveness: "audio degradation after enabling BVC", "BVCTelephony overly aggressive". Krisp itself acknowledges voice suppression in VI-tel v2, which v2.1 is said to reduce. I found no Reddit or HN threads with substantive VIVA quality reports.

### Cited Findings
**Vendor-authored (Krisp)**
- VI 2.5: "46.4% average reduction in WER … across 10 STT engines from 7 vendors … 69.7% fewer on background speech … no harm on clean audio". Another snippet says 43% (17.9%→10.2%) across 11 engines (2026-08-12, from earlier note). — [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)
- BVC: VAD false positives cut "3.5x on average"; Whisper-v3 WER on AMI improved more than 2×. — [Krisp blog BVC turn-taking](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/)
- `krisp-viva-vi-tel-v2.1` was released for "reducing voice suppression and improving WER accuracy over krisp-viva-vi-tel-v2". This is **Krisp's acknowledgement that v2 over-suppressed voice** (C/C++ SDK 9.19.0 changelog). — [api-evangelist changelog](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml)
- The Pipecat TTS-detection gate exists to prevent "suppressing real human speech that immediately follows bot TTS playback" (from earlier note). — [krisp-viva-filter.mdx](https://github.com/pipecat-ai/docs/blob/main/api-reference/server/services/audio-filters/krisp-viva-filter.mdx)

**Vendor-authored by a competitor (ai-coustics)**
- These claims come from search summaries of ai-coustics pages dated 2025-11-10, 2026-01-28 and later:
  - Krisp is described as "Perceptual enhancement models like Krisp are built for human ears, not to improve STT/ASR … they often make transcripts less accurate".
  - "Quail consistently delivers 10–25% relative WER reduction … outperforming Krisp by several percentage points on challenging audio".
  - "On German … Krisp's perceptual denoising introduces more substitutions and deletions".
  - A search summary says an ai-coustics benchmark "found that Krisp NC raised WER by over 10pp on English competing speech".
  - These comparisons appear to use Krisp's **NC/meeting-class** models, not necessarily VIVA VI 2.x.
  - Source: [ai-coustics benchmarks](https://ai-coustics.com/benchmarks-quantitative); [ai-coustics vs Krisp blog](https://ai-coustics.com/blog/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you); [Quail blog](https://ai-coustics.com/blog/quail-stt-asr-transcription)

**Third-party blogs (not independent measurements)**
- A dev agency's blog (forasoft, 2026) says "a Krisp-class suppressor alone cuts noisy WER by 20–40% relative". It gives no methodology. — [forasoft: Speech recognition accuracy in noise](https://www.forasoft.com/blog/article/speech-recognition-accuracy-noisy-environments)
- Another snippet: "VIVA 2.0 … cuts WER 10–30% on noisy audio" (uncited aggregator). — [Coval STT benchmarks blog](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/)

**Community reports (anecdotal)**
- LiveKit community, "Unexpected Audio Degradation After Enabling BVC Noise Cancellation in LiveKit Voice Agent": processed audio "seems to degrade or behave unexpectedly" (snippet, date unknown). — [community.livekit.io/t/745](https://community.livekit.io/t/unexpected-audio-degradation-after-enabling-bvc-noise-cancellation-in-livekit-voice-agent/745)
- LiveKit community, "Audio gain before BVCTelephony()": a user found BVCTelephony "overly aggressive" and asked about gain/normalisation first (snippet). This bears directly on **over-suppression of quiet callers**. — [community.livekit.io/t/300](https://community.livekit.io/t/audio-gain-before-bvctelephony/300)
- pipecat#5413 (2026-08-24): with krisp_audio 1.12.0, "noise cancellation is silently disabled — no crash, no warning, just unfiltered audio". — [GitHub](https://github.com/pipecat-ai/pipecat/issues/5413)
- pipecat#4994 (2026-07-09):
  - In a production phone agent without Krisp IP, "Across 153 real calls: 34% contained a reply aborted by a false turn-start … 6.5% … degenerated into a loop".
  - The reporter wanted Krisp IP to fix this but could not get the model on Pipecat Cloud.
  - This shows demand for IP, **not** measured IP quality.
  - Source: [GitHub](https://github.com/pipecat-ai/pipecat/issues/4994)
- livekit/agents#6033 (2026-06-09, open, no staff reply seen): a self-hosted SIP deployment (Hindi/Telugu) found backchannels ("haa, avunu, hmm, yeah, okay") trigger interruptions. LiveKit's Adaptive Interruption "relies on LiveKit-hosted inference". The reporter requests an official self-hosted Krisp VIVA IP/Turn integration. — [GitHub](https://github.com/livekit/agents/issues/6033)
- Earlier LiveKit issues (Cloud-bundled Krisp):
  - livekit/agents#3073 (2025-08-04): "audio filter cannot be enabled: LiveKit Cloud is required" — [GitHub](https://github.com/livekit/agents/issues/3073)
  - #1696 (2025-03-21): segfault on `import noise_cancellation` — [GitHub](https://github.com/livekit/agents/issues/1696)
  - pipecat#2507 (2025-08-26): Krisp guide outdated against new SDK/models — [GitHub](https://github.com/pipecat-ai/pipecat/issues/2507)
- HN thread "Noise cancellation improves turn-taking for AI Voice Agents" (April 2025, a Krisp blog post). The comments could not be read (blocked). — [HN 43467988](https://news.ycombinator.com/item?id=43467988)
- G2 reviews (4.6–4.7★, more than 1,100 reviews) concern the **consumer meeting app**, not the SDK. — [G2 Krisp](https://www.g2.com/products/krisp/reviews)

### Inferences
- The one consistent qualitative risk signal points at the user's concern: **over-suppression**. It shows up in three places: Krisp's own v2→v2.1 "reducing voice suppression" note, the LiveKit community's "overly aggressive" BVCTelephony report, and ai-coustics' deletion/substitution claim. Quiet or far-field callers and short backchannels are the most at risk.
- Mitigations to test:
  - suppression level 75 vs 100
  - VI-tel v2.1 or 2.5 rather than older BVC
  - gain normalisation before the filter
  - the TTS-detection gate
- Quality evidence for the user's exact stack (NVIDIA riva/Parakeet ASR, English telephony, TV and nearby-talker interference) must come from a local A/B test. Measure:
  - WER (Krisp's VI 2.5 eval includes an unnamed NVIDIA engine)
  - backchannel recall
  - false barge-in rate
  - primary-speaker loss for far-field callers
- Integration fragility is real: silent pass-through after ABI changes. Add a runtime check that output differs from input (or check the stats API), and alert on licensing callbacks.

### Gaps
- No independent DNSMOS/WER/speaker-suppression benchmark of Krisp VIVA VI (tel/pro/2.5) vs ai-coustics Quail Voice Focus vs NVIDIA AFX was found.
- No measured precision/recall for Krisp IP v1/v1.1 on backchannels. No independent latency measurements.
- Reddit (r/VoiceAI, r/LocalLLaMA) turned up no relevant threads. The LiveKit community thread bodies and HN comments could not be read because they were blocked.
