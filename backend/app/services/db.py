"""MySQL 存取问答历史。表结构由 db.sql / 首次启动自动创建。"""
import logging

import pymysql

from .. import config

logger = logging.getLogger("db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id VARCHAR(32) NOT NULL,
  role VARCHAR(16) NOT NULL,
  content MEDIUMTEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session (session_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _connect(db: str | None = None) -> pymysql.Connection:
    return pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=db or config.MYSQL_DB,
        charset="utf8mb4",
        autocommit=True,
    )


def init_db() -> None:
    conn = _connect(db=None)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DB}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{config.MYSQL_DB}`")
            cur.execute(SCHEMA)
    finally:
        conn.close()


def add_message(session_id: str, role: str, content: str) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content),
            )
    finally:
        conn.close()


def get_messages(session_id: str, limit: int = 50) -> list[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM chat_messages WHERE session_id=%s "
                "ORDER BY id DESC LIMIT %s",
                (session_id, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
