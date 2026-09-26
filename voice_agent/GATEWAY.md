# Nemotron + ai-coustics gateway

The gateway and the LiveKit agent run in separate processes. Only the gateway
needs `aic-sdk`, the ai-coustics SDK license, access to the model CDN, and
outbound access for SDK authorization and usage reporting. The agent sends all
caller audio to `/stt`; LiveKit also sends overlap windows to `/bargein` when
adaptive interruption is enabled.

```
LiveKit agent -- raw PCM16/16k --> /stt gateway -- Voice Focus --> riva_server
                                  \-- Voice Focus VAD (full input stream)
              -- overlap windows --> /bargein gateway -- VAD score + policy
```

`/stt` returns streaming Nemotron events, including final speaker IDs and word
times. `MultiSpeakerAdapter` runs on the gateway after Voice Focus, so its
speaker decision sees the same enhanced audio as Nemotron. The agent receives
the adapted STT events. The SDK's local Silero VAD
triggers adaptive analysis; the gateway's Voice Focus VAD runs on the complete
raw input stream and supplies recent scores to the `/bargein` classifier.
The two WebSockets share LiveKit room/job headers. The
gateway currently runs an additional short Riva recognition for overlap text;
it does not reuse the `/stt` transcript.

## Gateway host

Install from `voice_agent/` with `pip install -e '.[aic]'`. Set these values in
the **gateway's** environment:

```dotenv
RIVA_SERVER=127.0.0.1:50051
AIC_LICENSE_KEY=<ai-coustics SDK license key>
LIVEKIT_INFERENCE_API_KEY=<shared private key id>
LIVEKIT_INFERENCE_API_SECRET=<shared long secret>
GATEWAY_STT_ENABLED=1
GATEWAY_AIC_ENABLED=1
GATEWAY_AIC_VAD_ENABLED=1
GATEWAY_AIC_VAD_MODEL=vad-vf-2.0-s-16khz
BARGEIN_HOST=0.0.0.0
BARGEIN_PORT=8765
```

Then run `python -m local_voice_agent.bargein_server`. Use TLS termination or a
private network between the agent and gateway. The process refuses to bind to
a non-loopback host without the shared inference credentials. The ai-coustics
cloud API key is a different product from the SDK license and is not accepted
as a substitute.

The enhancer model defaults to `quail_vf_l`; change it with
`AIC_ENHANCER_MODEL`. The VAD model may be preloaded with `AIC_VAD_MODEL_PATH`.
`AIC_SDK_LICENSE` is accepted as an alternative environment variable for the
same SDK license.
The older `quail-vf-vad-2.0-s-16khz` file is model format v5 and cannot be
loaded by the pinned SDK 3.2.0, which requires v7. The default above is the
current Voice Focus VAD v7 model.
The enhancer and VAD scorer are per STT connection, and model assets stay on
the gateway. Both WebSockets must reach the same gateway process while the
in-memory VAD correlation is in use. Console mode and requests without
room/job headers have no correlated VAD score. If the enhancer returns raw audio after
an authorization/model failure, `/stt` reports an error instead of silently
claiming enhanced recognition. `/health` checks only that the HTTP process is
alive; it does not prove Riva or the SDK license is usable.

## LiveKit agent host

Install from `voice_agent/` with `pip install -e .` (no `.[aic]`). Set these
values in the **agent's** environment:

```dotenv
STT_GATEWAY_URL=wss://gateway.internal/stt
LIVEKIT_INFERENCE_URL=https://gateway.internal
LIVEKIT_INFERENCE_API_KEY=<same shared private key id>
LIVEKIT_INFERENCE_API_SECRET=<same shared long secret>
INTERRUPTION_MODE=adaptive_local
VAD_BACKEND=silero
AUDIO_ENHANCEMENT=none
```

The agent does not need `AIC_LICENSE_KEY`, model files, or direct access to
ai-coustics. It still needs network access to the gateway and to whatever
LiveKit, LLM, and TTS endpoints its configuration names. The agent's
`TurnDetector(version="v1-mini")` runs locally; the shared
`LIVEKIT_INFERENCE_URL` points adaptive `/bargein` traffic at this gateway.

## Interruption policy and validation

Fresh Voice Focus VAD scores, score age, and prediction delay appear in each
`/bargein` decision log when `GATEWAY_AIC_VAD_ENABLED=1` and a matching
`/stt` stream is active. The gateway uses the foreground VAD as a **gate**:
a fresh score below 0.2 holds the floor even if short overlap ASR recognized
words. Riva supplies the text needed to distinguish “stop” from “uh-huh”
after the VAD gate; it is not the VAD. Set
`GATEWAY_AIC_VAD_GATE_THRESHOLD=0` to disable the gate, or another value
between 0 and 1 to tune it. The 0.2 default separates a local clean-speech
sample from silence but is not calibrated on caller, background-only, and
mixed calls. A false veto can suppress a real caller's “stop.” If VAD is
unavailable or its score is stale, the classifier continues without a VAD veto.

The `/bargein` message format is an undocumented LiveKit internal protocol.
This checkout pins `livekit-agents==1.8.3`; its protocol contract is exercised
by `tests/test_bargein_server.py`. `/stt` uses our own versioned WebSocket
contract, exercised end to end against the same LiveKit STT interface and a
scripted Riva server by `tests/test_gateway_stt.py`.

Run `pytest -q` from `voice_agent/` before changing the SDK, gateway wire
format, or policy. A local two-process smoke run with real Riva, licensed
ai-coustics enhancement, and Voice Focus VAD returned a final transcript and
speaker ID. That proves the components can run together. Recognition quality,
interruption accuracy, and latency on the call corpus still need a paired run
before deploying the default VAD gate to live calls.
