"""python -m local_voice_agent.bargein_server  (option 2: local adaptive-interruption service)"""

from __future__ import annotations

import argparse
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
    p.add_argument("--maai-device", default=os.environ.get("MAAI_DEVICE", "cpu"))
    p.add_argument("--threshold", type=float, default=float(os.environ.get("BARGEIN_THRESHOLD", "0.5")))
    p.add_argument(
        "--decision-log",
        default=os.environ.get("BARGEIN_DECISION_LOG"),
        help="JSONL file for every decision with its reason, signals and ASR/MaAI state",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from ..jsonl import JsonlWriter
    from .server import BargeinServer
    from .transcriber import RivaTranscriber

    maai_factory = None
    if args.maai:
        from ..backchannel.maai_detector import MaaiBackchannelDetector

        def maai_factory() -> MaaiBackchannelDetector:
            # LiveKit only sends the user's audio, so the mono model is used here.
            return MaaiBackchannelDetector(two_channel=False, device=args.maai_device)

    server = BargeinServer(
        # Same values the agent signs its token with; unset = no auth (localhost only).
        api_key=os.environ.get("LIVEKIT_INFERENCE_API_KEY"),
        api_secret=os.environ.get("LIVEKIT_INFERENCE_API_SECRET"),
        transcriber=RivaTranscriber(args.riva) if args.riva else None,
        maai_factory=maai_factory,
        default_threshold=args.threshold,
        decision_log=JsonlWriter(args.decision_log) if args.decision_log else None,
    )
    web.run_app(server.app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
