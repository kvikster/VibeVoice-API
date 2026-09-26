"""Replay both interruption policies over logged events - no ASR, no agent.

    python -m local_voice_agent.tools.replay_policy events.jsonl \
        [--agent agent.jsonl] [--maai maai.jsonl] [--out decisions.jsonl]

Inputs are JSONL records, merged and processed in time order:

* ``kind: "stt"``   - STT events: ``type`` (interim / final / start_of_speech / ...)
  and ``text``. Accepts ``tools.replay_stt`` output (``--layer`` picks raw or
  adapter; default adapter, i.e. what the agent would see) and the live
  ``DECISION_LOG`` of shadow/filters mode. A ``maai`` object on the record is
  used as the MaAI reading for that event (this is how live logs replay exactly).
* ``kind: "agent"`` - agent state changes: ``state`` (speaking / listening / ...)
  and optionally ``text`` (what the agent said; a trailing "?" means it is now
  waiting for an answer).
* ``kind: "maai"``  - MaAI frames: ``p_bc`` (see ``tools.maai_scores``).

Time comes from ``--time-field`` (default: ``audio_pos_s`` when present, else ``t``);
all files must use the same clock. At equal times agent and MaAI inputs are
applied before STT events. Decisions only use inputs up to their own time, so
truncating the log never changes earlier decisions, and two runs give
identical output.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import fields
from pathlib import Path
from typing import Any

from ..backchannel.policy import FilterConfig, MaaiReading
from ..bargein_server.classifier import ClassifierConfig
from ..jsonl import read_jsonl, speech_duration
from ..policy_runner import PolicyRunner

_ORDER = {"agent": 0, "maai": 1, "stt": 2}


def _time(rec: dict[str, Any], field: str | None) -> float:
    if field:
        return float(rec[field])
    return float(rec["audio_pos_s"] if "audio_pos_s" in rec else rec["t"])


def merge(records: Iterable[dict[str, Any]], *, layer: str | None, time_field: str | None) -> list[tuple[float, dict]]:
    items = []
    for i, rec in enumerate(records):
        kind = rec.get("kind")
        if kind not in _ORDER:
            continue
        if kind == "stt" and layer and rec.get("layer", layer) != layer:
            continue
        items.append((_time(rec, time_field), _ORDER[kind], i, rec))
    items.sort(key=lambda x: x[:3])  # stable: time, then agent < maai < stt, then file order
    return [(t, rec) for t, _, _, rec in items]


def _reading(obj: dict[str, Any]) -> MaaiReading:
    known = {f.name for f in fields(MaaiReading)}
    return MaaiReading(**{k: v for k, v in obj.items() if k in known})


def replay(
    records: Iterable[dict[str, Any]],
    *,
    layer: str | None = "adapter",
    time_field: str | None = None,
    filter_cfg: FilterConfig | None = None,
    classifier_cfg: ClassifierConfig | None = None,
) -> Iterator[dict[str, Any]]:
    runner = PolicyRunner(filter_cfg, classifier_cfg, mode="replay")
    for t, rec in merge(records, layer=layer, time_field=time_field):
        kind = rec["kind"]
        if kind == "agent":
            runner.agent(t, rec["state"], rec.get("text"))
        elif kind == "maai":
            runner.maai(t, float(rec["p_bc"]))
        else:
            maai = _reading(rec["maai"]) if isinstance(rec.get("maai"), dict) else None
            yield from runner.stt(
                t, rec["type"], rec.get("text"), seq=rec.get("seq"), maai=maai, speech_duration_s=speech_duration(rec)
            )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("events", type=Path)
    p.add_argument("--agent", type=Path, action="append", default=[], help="agent timeline JSONL")
    p.add_argument("--maai", type=Path, action="append", default=[], help="MaAI frames JSONL")
    p.add_argument("--out", type=Path, help="decisions JSONL (default: stdout)")
    p.add_argument("--layer", default="adapter", help="raw | adapter | all (for replay_stt output)")
    p.add_argument("--time-field", help="record field holding the time (default: audio_pos_s, else t)")
    p.add_argument("--grace-s", type=float)
    p.add_argument("--interim-min-words", type=int)
    p.add_argument("--maai-threshold", type=float)
    args = p.parse_args(argv)

    overrides = {
        k: v
        for k, v in {
            "grace_s": args.grace_s,
            "interim_min_words": args.interim_min_words,
            "maai_threshold": args.maai_threshold,
        }.items()
        if v is not None
    }
    records = [*read_jsonl(args.events)]
    for path in [*args.agent, *args.maai]:
        records.extend(read_jsonl(path))

    out = args.out.open("w", encoding="utf-8") if args.out else sys.stdout
    counts: Counter[str] = Counter()
    try:
        for rec in replay(
            records,
            layer=None if args.layer == "all" else args.layer,
            time_field=args.time_field,
            filter_cfg=FilterConfig(**overrides),
        ):
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec["policy"] == "text_filter":
                counts[f"text_filter {rec['action']:<5} {rec['reason']}"] += 1
            else:
                counts[f"classifier  {rec['decision']:<14} {rec['reason']}"] += 1
    finally:
        if args.out:
            out.close()
    for key, n in sorted(counts.items()):
        print(f"{n:6d}  {key}", file=sys.stderr)


if __name__ == "__main__":
    main()
