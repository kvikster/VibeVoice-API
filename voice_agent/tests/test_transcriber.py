import time

import numpy as np

from local_voice_agent.bargein_server.transcriber import RivaTranscriber


async def test_unreachable_server_returns_none_quickly():
    asr = RivaTranscriber("127.0.0.1:9", timeout_s=0.5)
    t0 = time.monotonic()
    assert await asr.transcribe(np.zeros(16000, dtype=np.int16)) is None
    assert time.monotonic() - t0 < 1.0
