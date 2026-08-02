import logging
import threading
from pathlib import Path

from .. import config

logger = logging.getLogger("asr")

_model = None
_model_lock = threading.Lock()
_opencc = None


def _to_simplified(text: str) -> str:
    """繁体 -> 简体, Whisper 中文常输出繁体。"""
    global _opencc
    if _opencc is None:
        from opencc import OpenCC

        _opencc = OpenCC("t2s")
    return _opencc.convert(text)


def _detect_device() -> str:
    if config.WHISPER_DEVICE != "auto":
        return config.WHISPER_DEVICE
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel

                device = _detect_device()
                logger.info("loading whisper model=%s device=%s compute_type=%s",
                            config.WHISPER_MODEL, device, config.WHISPER_COMPUTE_TYPE)
                _model = WhisperModel(
                    config.WHISPER_MODEL,
                    device=device,
                    compute_type=config.WHISPER_COMPUTE_TYPE,
                )
    return _model


def get_media_duration(path: Path) -> float:
    """用 av 解析音频总时长(秒), 供进度计算。"""
    try:
        import av

        with av.open(str(path)) as container:
            return float(container.duration) / av.time_base
    except Exception:
        return 0.0


def transcribe(path: Path, language: str = None) -> list[dict]:
    """执行转写, 返回带时间戳的分段列表。"""
    model = get_model()
    duration = get_media_duration(path)
    segments_iter, info = model.transcribe(
        str(path),
        language=language or config.WHISPER_LANGUAGE,
        beam_size=config.WHISPER_BEAM_SIZE,
        vad_filter=config.WHISPER_VAD_FILTER,
    )
    segments = []
    for segment in segments_iter:
        seg = {
            "start": segment.start,
            "end": segment.end,
            "text": _to_simplified(segment.text),
        }
        segments.append(seg)
        yield len(segments), duration, info, seg
    yield None, duration, info, None
