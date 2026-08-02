# 音频识别助手

上传音频 → 自动转写原文 → 生成总结报告 → 基于原文智能问答。

## 功能

- **音频转写**：本地 Faster-Whisper (INT8) 提取音频原文，保存带时间戳的原文文件，完成后提示耗时
- **总结报告**：DeepSeek LLM 基于原文生成结构化 Markdown 报告
- **智能问答**：结合音频原文上下文回答用户提问，问答历史存入 MySQL
- **历史记录**：查看历史音频/原文/报告，继续问答，支持会话改名
- **下载**：转写原文与总结报告可下载为 md 文件
- **存储**：音频按月份存于 `data/audio/YYYY-MM/`，问答历史存于 MySQL `shenglu` 库

## 快速开始

```bash
conda activate shenglu
pip install -r requirements.txt

# 配置 DeepSeek API Key
cp .env.example .env
# 编辑 .env, 填入 DEEPSEEK_API_KEY

# 启动服务
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 http://localhost:8000

## 配置项 (环境变量)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key，必填 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | LLM 接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | LLM 模型名 |
| `SL_WHISPER_MODEL` | `medium` | Whisper 模型 (tiny/base/small/medium/large-v3) |
| `SL_WHISPER_DEVICE` | `auto` | auto / cuda / cpu |
| `SL_WHISPER_COMPUTE_TYPE` | `int8` | 量化精度 |
| `SL_MAX_UPLOAD_MB` | `500` | 上传大小限制 |
| `SL_MYSQL_HOST` / `SL_MYSQL_PORT` | `127.0.0.1` / `3306` | MySQL 连接 |
| `SL_MYSQL_USER` / `SL_MYSQL_PASSWORD` | `root` / 空 | MySQL 账号 |
| `SL_MYSQL_DB` | `shenglu` | MySQL 库名 |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/audio` | 上传音频，异步转写 |
| GET | `/api/audio/{id}` | 查询转写状态/结果 |
| POST | `/api/audio/{id}/report` | 生成总结报告 |
| GET | `/api/audio/{id}/report` | 获取报告 |
| POST | `/api/audio/{id}/chat` | 基于原文问答 |
| GET | `/api/audio/{id}/chat` | 获取聊天历史 |
| GET | `/api/sessions` | 历史会话列表 |
| PATCH | `/api/audio/{id}` | 会话改名 (body: `{"name":"..."}`) |
| GET | `/api/audio/{id}/transcript/download` | 下载原文 md |
| GET | `/api/audio/{id}/report/download` | 下载报告 md |

接口文档: http://localhost:8000/docs

## 目录结构

```
backend/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置
│   ├── schemas.py       # Pydantic 模型
│   ├── routers/         # 上传/报告/问答接口
│   └── services/        # ASR / LLM / 存储
└── static/              # 前端页面
data/                    # 运行时数据 (audio/transcripts/reports/sessions)
```
