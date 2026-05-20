from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from kuba.paths import resolve_episode_path


class KokoroAudioProvider:
    provider_name = "kokoro"

    def __init__(
        self,
        *,
        engine: Any | None = None,
        model_path: str | None = None,
        voices_path: str | None = None,
        voice: str = "af_heart",
        speed: float = 1.0,
    ) -> None:
        self.engine = engine or _load_kokoro_engine(
            model_path or os.environ.get("KOKORO_MODEL_PATH"),
            voices_path or os.environ.get("KOKORO_VOICES_PATH"),
        )
        self.voice = os.environ.get("KOKORO_VOICE", voice)
        self.speed = float(os.environ.get("KOKORO_SPEED", str(speed)))

    def generate_audio(
        self,
        episode_root: str,
        relative_path: str,
        text: str,
        duration_sec: float,
    ) -> str:
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(self.engine, "synthesize_to_wav"):
            self.engine.synthesize_to_wav(text, output_path, self.voice, self.speed)
        elif hasattr(self.engine, "create"):
            samples, sample_rate = self.engine.create(text, voice=self.voice, speed=self.speed)
            _write_samples(output_path, samples, sample_rate)
        else:
            raise RuntimeError("Kokoro engine does not expose synthesize_to_wav or create")
        return str(output_path)


def _load_kokoro_engine(model_path: str | None, voices_path: str | None) -> Any:
    if not model_path or not voices_path:
        raise RuntimeError("KOKORO_MODEL_PATH and KOKORO_VOICES_PATH are required")
    model = Path(model_path)
    voices = Path(voices_path)
    if model.suffix == ".pth":
        return KokoroTorchEngine(model, voices)
    try:
        from kokoro_onnx import Kokoro
    except ImportError as exc:
        raise RuntimeError("Install kokoro-onnx to use the Kokoro provider") from exc
    return Kokoro(model_path, voices_path)


class KokoroTorchEngine:
    def __init__(self, model_path: Path, voices_path: Path, lang_code: str = "a") -> None:
        if not model_path.exists():
            raise RuntimeError(f"Kokoro model does not exist: {model_path}")
        if not voices_path.exists():
            raise RuntimeError(f"Kokoro voices path does not exist: {voices_path}")
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise RuntimeError("Install kokoro to use .pth Kokoro models") from exc
        self.model_path = model_path
        self.voices_path = voices_path
        self.pipeline = KPipeline(lang_code=lang_code, model=str(model_path))

    def synthesize_to_wav(
        self,
        text: str,
        output_path: Path,
        voice: str,
        speed: float,
    ) -> None:
        chunks = []
        sample_rate = 24000
        for result in self.pipeline(text, voice=voice, speed=speed):
            audio = _extract_audio_chunk(result)
            if audio is not None:
                chunks.append(audio)
        if not chunks:
            raise RuntimeError("Kokoro generated no audio chunks")
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("numpy is required to write Kokoro samples") from exc
        samples = np.concatenate([np.asarray(chunk) for chunk in chunks])
        _write_samples(output_path, samples, sample_rate)


def _extract_audio_chunk(result: Any) -> Any | None:
    if isinstance(result, tuple) and len(result) >= 3:
        return result[2]
    if hasattr(result, "audio"):
        return result.audio
    return result


def _write_samples(path: Path, samples: Any, sample_rate: int) -> None:
    import wave

    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required to write Kokoro samples") from exc
    pcm = (np.asarray(samples).clip(-1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(int(sample_rate))
        wav_file.writeframes(pcm)
