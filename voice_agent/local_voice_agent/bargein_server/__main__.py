"""python -m local_voice_agent.bargein_server  (option 2: local adaptive-interruption service)"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os

from aiohttp import web
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default=os.environ.get("BARGEIN_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("BARGEIN_PORT", "8765")))
    p.add_argument(
        "--riva",
        default=os.environ.get("RIVA_SERVER", "127.0.0.1:50051"),
        help="NeMo-Speech.cpp riva_server for overlap transcripts; empty string disables ASR",
    )
    p.add_argument("--maai", action="store_true", default=os.environ.get("MAAI_ENABLED") == "1")
    p.add_argument(
        "--gateway-stt", action="store_true", default=os.environ.get("GATEWAY_STT_ENABLED") == "1",
        help="serve streaming Nemotron on /stt; the agent sends all input audio here",
    )
    p.add_argument(
        "--aic", action="store_true", default=os.environ.get("GATEWAY_AIC_ENABLED") == "1",
        help="apply ai-coustics Voice Focus on the gateway before Nemotron",
    )
    p.add_argument(
        "--aic-vad", action="store_true", default=os.environ.get("GATEWAY_AIC_VAD_ENABLED") == "1",
        help="score the full input stream with Voice Focus VAD on the gateway",
    )
    p.add_argument(
        "--aic-vad-gate-threshold", type=float,
        default=float(os.environ["GATEWAY_AIC_VAD_GATE_THRESHOLD"])
        if os.environ.get("GATEWAY_AIC_VAD_GATE_THRESHOLD") else None,
        help="foreground VAD gate (default 0.2 when --aic-vad is enabled; 0 disables it)",
    )
    p.add_argument("--maai-device", default=os.environ.get("MAAI_DEVICE", "cpu"))
    p.add_argument("--threshold", type=float, default=float(os.environ.get("BARGEIN_THRESHOLD", "0.5")))
    p.add_argument(
        "--decision-log",
        default=os.environ.get("BARGEIN_DECISION_LOG"),
        help="JSONL file for every decision with its reason, signals and ASR/MaAI state",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    gateway_key = os.environ.get("LIVEKIT_INFERENCE_API_KEY")
    gateway_secret = os.environ.get("LIVEKIT_INFERENCE_API_SECRET")
    if bool(gateway_key) != bool(gateway_secret):
        p.error("both LIVEKIT_INFERENCE_API_KEY and LIVEKIT_INFERENCE_API_SECRET are required")
    if args.host not in ("127.0.0.1", "localhost", "::1") and not gateway_key:
        p.error("a gateway listening beyond loopback requires inference API credentials")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from ..jsonl import JsonlWriter
    from .server import BargeinServer
    from .transcriber import RivaTranscriber
    from .stt_route import GatewaySTTRoute
    from .classifier import ClassifierConfig

    if args.aic_vad_gate_threshold is not None and not args.aic_vad:
        p.error("--aic-vad-gate-threshold requires --aic-vad")
    if args.aic_vad_gate_threshold is not None and not 0 <= args.aic_vad_gate_threshold <= 1:
        p.error("--aic-vad-gate-threshold must be between 0 and 1")
    if args.aic_vad and args.aic_vad_gate_threshold is None:
        # A low foreground score holds the floor even if background ASR hears words.
        # Keep the threshold conservative until the call corpus calibrates it.
        args.aic_vad_gate_threshold = 0.2

    from ..settings import Settings

    gateway_settings = Settings()

    aic_vad_factory = None
    vad_hub = None
    if args.aic_vad:
        if not args.gateway_stt:
            p.error("--aic-vad requires --gateway-stt for full-stream speaker context")
        from .aic_vad import AicVadFactory, AicVadHub

        vad_settings = dataclasses.replace(
            gateway_settings,
            aic_vad_model=os.environ.get(
                "GATEWAY_AIC_VAD_MODEL", "vad-vf-2.0-s-16khz"
            ),
        )
        aic_vad_factory = AicVadFactory(vad_settings)
        vad_hub = AicVadHub()

    stt_route = None
    if args.aic and not args.gateway_stt:
        p.error("--aic requires --gateway-stt")
    if args.gateway_stt:
        from ..stt import build_direct_stt
        enhancer_factory = None
        if args.aic:
            if not gateway_settings.aic_license_key:
                p.error("--aic requires AIC_LICENSE_KEY or AIC_SDK_LICENSE on the gateway")
            from ..aic import build_enhancer

            def enhancer_factory():
                return build_enhancer(gateway_settings)
        stt_route = GatewaySTTRoute(
            stt_factory=lambda: build_direct_stt(gateway_settings),
            enhancer_factory=enhancer_factory,
            vad_factory=aic_vad_factory,
            vad_hub=vad_hub,
        )

    maai_factory = None
    if args.maai:
        from ..backchannel.maai_detector import MaaiBackchannelDetector

        def maai_factory() -> MaaiBackchannelDetector:
            # LiveKit only sends the user's audio, so the mono model is used here.
            return MaaiBackchannelDetector(two_channel=False, device=args.maai_device)

    server = BargeinServer(
        # Same values the agent signs its token with; unset = no auth (localhost only).
        api_key=gateway_key,
        api_secret=gateway_secret,
        transcriber=RivaTranscriber(args.riva) if args.riva else None,
        maai_factory=maai_factory,
        default_threshold=args.threshold,
        decision_log=JsonlWriter(args.decision_log) if args.decision_log else None,
        stt_route=stt_route,
        vad_hub=vad_hub,
        classifier_config=ClassifierConfig(vf_vad_gate_threshold=args.aic_vad_gate_threshold),
    )
    web.run_app(server.app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
