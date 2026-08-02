import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="音频识别程序", version="0.2.0")

from .routers import audio, chat, report, sessions

app.include_router(audio.router)
app.include_router(report.router)
app.include_router(chat.router)
app.include_router(sessions.router)

try:
    from .services import db

    db.init_db()
except Exception as exc:
    logging.getLogger("main").warning("MySQL 初始化失败: %s (聊天历史将不可用)", exc)

app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")
