"""Text-filter policy as a pure function of (event, agent context, MaAI reading).

Both the live ``InterruptionFilterMixin`` (enforce and shadow) and the offline
replay call ``decide_text``; that is what makes a replayed log reproduce the
live decisions. Nothing here reads a clock.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .lexicon import Verdict, analyze

Action = Literal["pass", "hold", "drop"]
InterruptionVerdict = Literal["interrupt", "no_interrupt", "not_applicable"]
TRANSCRIPT_TYPES = ("interim", "preflight", "final")


@dataclass(frozen=True)
class FilterConfig:
    grace_s: float = 1.0
    """Keep filtering this long after the agent stops speaking (unless it asked a question)."""
    interim_min_words: int = 3
    """While the agent speaks, interims with fewer content words wait for the final."""
    maai_threshold: float = 0.45
    """MaAI event-level operating point suggested by its authors."""
    maai_max_words: int = 2
    """MaAI may only veto utterances up to this many content words."""
    maai_window_s: float = 1.5
    """How far back to look for a MaAI backchannel peak."""
    min_interruption_words: int = 1
    """LiveKit ``interruption.min_words`` used with this filter (for the interruption verdict)."""


@dataclass(frozen=True)
class AgentContext:
    state: str
    """LiveKit agent state: speaking / listening / thinking / initializing / idle."""
    since_speaking_s: float | None
    """0 while speaking; seconds since it stopped; None if it has not spoken yet."""
    awaiting_answer: bool = False
    """The agent's last utterance ended with a question mark."""


@dataclass(frozen=True)
class MaaiReading:
    status: Literal["available", "unavailable"] = "unavailable"
    p_bc: float | None = None
    """Highest user backchannel probability inside the window."""
    evaluated_at: float | None = None
    """Time of the newest MaAI frame used, in the MaAI source's own clock."""
    window_s: float | None = None
    clock: str | None = None
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


UNAVAILABLE = MaaiReading()


@dataclass
class FilterDecision:
    action: Action
    reason: str
    interruption: InterruptionVerdict
    signals: dict[str, Any] = field(default_factory=dict)


def decide_text(
    ev_type: str, text: str | None, ctx: AgentContext, maai: MaaiReading, cfg: FilterConfig
) -> FilterDecision:
    speaking = ctx.state == "speaking"
    signals: dict[str, Any] = {"maai": maai.as_dict()}

    def verdict(action: Action, reason: str, interruption: InterruptionVerdict) -> FilterDecision:
        return FilterDecision(action, reason, interruption, signals)

    if ev_type not in TRANSCRIPT_TYPES:
        return verdict("pass", "non_transcript", "not_applicable")
    if not speaking:
        if ctx.since_speaking_s is None or ctx.since_speaking_s > cfg.grace_s:
            return verdict("pass", "agent_not_speaking", "not_applicable")
        if ctx.awaiting_answer:
            # AssemblyAI's grace window would drop a quick "Yes" to the agent's question.
            return verdict("pass", "awaiting_answer", "not_applicable")

    a = analyze(text or "")
    signals.update(tokens=list(a.tokens), content_words=a.content_words)
    if a.phrases:
        signals["phrases"] = list(a.phrases)
    if a.prefix_pending:
        signals["prefix_pending"] = True
    no_effect: InterruptionVerdict = "no_interrupt" if speaking else "not_applicable"

    if a.verdict is Verdict.EMPTY:
        # e.g. the empty final MultiSpeakerAdapter sends after dropping a background final
        return verdict("pass", "empty_transcript", no_effect)
    if a.verdict is Verdict.INTERRUPT:
        signals["interrupt_tokens"] = list(a.interrupt_tokens)
        return verdict("pass", "interrupt_token", "interrupt" if speaking else "not_applicable")
    if a.verdict is Verdict.BACKCHANNEL:
        return verdict("drop", a.kind, no_effect)

    if (
        maai.status == "available"
        and maai.p_bc is not None
        and a.content_words <= cfg.maai_max_words
        and maai.p_bc >= cfg.maai_threshold
    ):
        return verdict("drop", "maai_backchannel", no_effect)
    if ev_type != "final" and a.prefix_pending:
        return verdict("hold", "phrase_prefix_awaits_final", no_effect)
    if ev_type != "final" and a.content_words < cfg.interim_min_words:
        return verdict("hold", "short_interim_awaits_final", no_effect)
    if speaking and a.content_words >= cfg.min_interruption_words:
        return verdict("pass", "content_words", "interrupt")
    return verdict("pass", "content_words", no_effect)
