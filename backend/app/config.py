import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("HF_ENDPOINT", os.getenv("HF_ENDPOINT", "https://hf-mirror.com"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def _add_site_packages_libs() -> None:
    """将 pip 安装的 nvidia-*-cu12 动态库加入 LD_LIBRARY_PATH, 供 ctranslate2 加载。"""
    import site

    lib_dirs = [
        os.path.join(site.getsitepackages()[0], "nvidia", "cublas", "lib"),
        os.path.join(site.getsitepackages()[0], "nvidia", "cudnn", "lib"),
        os.path.join(site.getsitepackages()[0], "nvidia", "cuda_nvrtc", "lib"),
    ]
    existing = os.environ.get("LD_LIBRARY_PATH", "").split(":") if os.environ.get("LD_LIBRARY_PATH") else []
    paths = list(existing)
    for d in lib_dirs:
        if os.path.isdir(d) and d not in paths:
            paths.append(d)
    if paths:
        os.environ["LD_LIBRARY_PATH"] = ":".join(paths)


_add_site_packages_libs()

DATA_DIR = Path(os.getenv("SL_DATA_DIR", BASE_DIR / "data"))
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
REPORT_DIR = DATA_DIR / "reports"
SESSION_DIR = DATA_DIR / "sessions"
STATIC_DIR = Path(os.getenv("SL_STATIC_DIR", BASE_DIR / "backend" / "static"))

for _d in (AUDIO_DIR, TRANSCRIPT_DIR, REPORT_DIR, SESSION_DIR):
    _d.mkdir(parents=True, exist_ok=True)

WHISPER_MODEL = os.getenv("SL_WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("SL_WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("SL_WHISPER_COMPUTE_TYPE", "int8")
WHISPER_BEAM_SIZE = int(os.getenv("SL_WHISPER_BEAM_SIZE", "1"))
WHISPER_VAD_FILTER = os.getenv("SL_WHISPER_VAD_FILTER", "true").lower() == "true"
WHISPER_LANGUAGE = os.getenv("SL_WHISPER_LANGUAGE", "") or None

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

MYSQL_HOST = os.getenv("SL_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("SL_MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("SL_MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("SL_MYSQL_PASSWORD", "aitrading123")
MYSQL_DB = os.getenv("SL_MYSQL_DB", "shenglu")

MAX_UPLOAD_MB = int(os.getenv("SL_MAX_UPLOAD_MB", "500"))
