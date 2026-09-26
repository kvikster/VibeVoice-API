"""ai-coustics integration: speech enhancement and VAD, with your own license key.

Two building blocks, usable independently:

* ``build_enhancer`` - the official ``livekit-plugins-ai-coustics`` FrameProcessor
  (Quail / Quail Voice Focus models) with ``Auth.ai_coustics_api(license_key)``,
  i.e. without LiveKit Cloud. It goes into ``RoomOptions.audio_input.noise_cancellation``,
  so STT, VAD and the turn detector all get the enhanced audio. Voice Focus also
  suppresses background voices. LiveKit applies it in room mode (``dev`` / ``start``),
  not in ``console``. Every processed frame carries the enhancer's own VAD flag.

* VAD, selected with ``VAD_BACKEND``:
    ``silero``        LiveKit's Silero VAD (default);
    ``aic``           ``AicVAD``: a dedicated ai-coustics VAD model (``aic_sdk.Vad``)
                      driving Silero's state machine, so thresholds, min speech /
                      silence and prefix padding behave exactly like Silero and only
                      the speech probability differs. Works in console mode too;
    ``aic_enhancer``  ``ai_coustics.VAD()``: reads the flag the enhancer computes on
                      the original signal. Needs ``AUDIO_ENHANCEMENT=aic``.

Audio never leaves the machine, but the SDK activates a session and reports usage
against the license on ai-coustics' servers unless the license has an offline
entitlement. ``AIC_TELEMETRY=0`` (default) disables OpenTelemetry export for our
``aic_sdk`` objects and sets ``DO_NOT_TRACK=1`` for SDK error reporting.
"""

from __future__ import annotations

import logging
import os
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any

from livekit import agents
from livekit.plugins import silero
from livekit.plugins.silero.vad import VADStream as SileroVADStream
from livekit.plugins.silero.vad import _VADOptions

if TYPE_CHECKING:
    from .settings import Settings

logger = logging.getLogger("local_voice_agent.aic")

DEFAULT_VAD_MODEL = "vad-2.1-xxs-16khz"
DEFAULT_MODELS_DIR = Path.home() / ".cache" / "local-voice-agent" / "aic-models"
ENHANCER_MODELS = ("quail_vf_l", "quail_vf_s", "quail_l", "rook_s")


def configure_privacy(telemetry: bool) -> None:
    """Must run before aic_sdk / the plugin is imported: the SDK reads DO_NOT_TRACK once."""
    if not telemetry:
        os.environ.setdefault("DO_NOT_TRACK", "1")


class AicVadModel:
    """Silero's model interface (``sample_rate``, ``window_size_samples``, ``reset``,
    ``__call__``) over one ``aic_sdk.Vad``: returns the raw speech probability per block."""

    def __init__(self, aic_model: Any, license_key: str, *, telemetry: bool) -> None:
        import aic_sdk as aic

        self._config = aic.ProcessorConfig.optimal(aic_model)
        self._vad = aic.Vad(aic_model, license_key, self._config, otel_config=aic.OtelConfig(enable=telemetry))
        self._ctx = self._vad.get_context()

    @property
    def sample_rate(self) -> int:
        return self._config.sample_rate

    @property
    def window_size_samples(self) -> int:
        return self._config.block_size

    @property
    def prediction_delay_samples(self) -> int:
        return self._ctx.get_prediction_delay()

    def reset(self) -> None:
        self._ctx.reset()

    def __call__(self, x: Any) -> float:
        self._vad.process(x)
        return float(self._ctx.raw_vad_probability())


class AicVAD(silero.VAD):
    """Silero's VAD state machine fed by an ai-coustics VAD model."""

    @classmethod
    def load(  # type: ignore[override]
        cls,
        *,
        license_key: str,
        model_id: str = DEFAULT_VAD_MODEL,
        model_path: str | Path | None = None,
        models_dir: str | Path = DEFAULT_MODELS_DIR,
        telemetry: bool = False,
        min_speech_duration: float = 0.05,
        min_silence_duration: float = 0.55,
        prefix_padding_duration: float = 0.5,
        max_buffered_speech: float = 60.0,
        activation_threshold: float = 0.5,
        deactivation_threshold: float | None = None,
    ) -> AicVAD:
        configure_privacy(telemetry)
        import aic_sdk as aic

        if model_path is None:
            Path(models_dir).mkdir(parents=True, exist_ok=True)
            model_path = aic.Model.download(model_id, str(models_dir))
        model = aic.Model.from_file(str(model_path))
        opts = _VADOptions(
            min_speech_duration=min_speech_duration,
            min_silence_duration=min_silence_duration,
            prefix_padding_duration=prefix_padding_duration,
            max_buffered_speech=max_buffered_speech,
            activation_threshold=activation_threshold,
            deactivation_threshold=(
                deactivation_threshold
                if deactivation_threshold is not None
                else max(activation_threshold - 0.15, 0.01)
            ),
            sample_rate=model.get_optimal_sample_rate(),  # type: ignore[arg-type]
        )
        return cls(aic_model=model, license_key=license_key, opts=opts, telemetry=telemetry)

    def __init__(self, *, aic_model: Any, license_key: str, opts: _VADOptions, telemetry: bool = False) -> None:
        # Skip silero.VAD.__init__ (it wants an ONNX session); set what its methods use.
        agents.vad.VAD.__init__(self, capabilities=agents.vad.VADCapabilities(update_interval=0.032))
        self._opts = opts
        self._streams = weakref.WeakSet()
        self._aic_model = aic_model
        self._license_key = license_key
        self._telemetry = telemetry

    @property
    def model(self) -> str:
        return f"ai-coustics {self._aic_model.get_id()}"

    @property
    def provider(self) -> str:
        return "ai-coustics"

    def stream(self) -> SileroVADStream:
        stream = SileroVADStream(
            self, self._opts, AicVadModel(self._aic_model, self._license_key, telemetry=self._telemetry)  # type: ignore[arg-type]
        )
        self._streams.add(stream)
        return stream


def _enhancer_model(name: str) -> Any:
    from livekit.plugins import ai_coustics

    try:
        return ai_coustics.EnhancerModel[name.upper()]
    except KeyError:
        raise ValueError(f"AIC_ENHANCER_MODEL must be one of {', '.join(ENHANCER_MODELS)}, got {name!r}") from None


def build_enhancer(settings: Settings) -> Any:
    """The official plugin's FrameProcessor, authenticated with the ai-coustics key."""
    configure_privacy(settings.aic_telemetry)
    from livekit.plugins import ai_coustics

    return ai_coustics.audio_enhancement(
        model=_enhancer_model(settings.aic_enhancer_model),
        vad_settings=ai_coustics.VadSettings(
            speech_hold_duration=settings.aic_enhancer_vad_hold_s,
            sensitivity=settings.aic_vad_sensitivity,
            minimum_speech_duration=None,
        ),
        model_parameters=ai_coustics.ModelParameters(enhancement_level=settings.aic_enhancement_level),
        auth=ai_coustics.Auth.ai_coustics_api(license_key=_require_key(settings)),
    )


def build_vad(settings: Settings) -> agents.vad.VAD:
    if settings.vad_backend == "silero":
        return silero.VAD.load()
    if settings.vad_backend == "aic":
        return AicVAD.load(
            license_key=_require_key(settings),
            model_id=settings.aic_vad_model,
            model_path=settings.aic_vad_model_path,
            models_dir=settings.aic_models_dir,
            telemetry=settings.aic_telemetry,
            activation_threshold=settings.aic_vad_threshold,
        )
    from livekit.plugins import ai_coustics

    return ai_coustics.VAD()


def enhance(enhancer: Any, frame: Any) -> Any:
    """Run one frame through the enhancer outside a room (offline tools).

    ``_process`` is the ``rtc.FrameProcessor`` hook LiveKit itself calls on room
    input; on failure the plugin returns the frame unchanged and logs why.
    """
    return enhancer._process(frame)


def enhancer_description(settings: Settings) -> dict[str, Any]:
    return {
        "backend": "livekit-plugins-ai-coustics",
        "model": settings.aic_enhancer_model,
        "enhancement_level": settings.aic_enhancement_level,
        "vad_hold_s": settings.aic_enhancer_vad_hold_s,
        "vad_sensitivity": settings.aic_vad_sensitivity,
    }


def _require_key(settings: Settings) -> str:
    if not settings.aic_license_key:
        raise ValueError("set AIC_LICENSE_KEY (from developers.ai-coustics.com) to use ai-coustics")
    return settings.aic_license_key
