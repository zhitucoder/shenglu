<div align="center">

# 声录 · 音频智能助手

<p align="center">
  <img src="assets/hero.gif" alt="声录音频智能助手演示动画" />
  <br/>
  <sub><a href="assets/hero-animation.html">查看动画源文件</a></sub>
</p>

> 让每段声音，都成为可检索、可提问的知识。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.14-teal)](https://fastapi.tiangolo.com/)
[![Faster-Whisper](https://img.shields.io/badge/ASR-Faster--Whisper-orange)](https://github.com/SYSTRAN/faster-whisper)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-brightgreen)](https://platform.deepseek.com)
[![MySQL](https://img.shields.io/badge/DB-MySQL-blueviolet)](#存储设计)

<br>

**上传一段音频 → AI 自动转写原文 → 生成总结报告 → 基于原文智能问答。**

<br>

本地 Faster-Whisper (INT8) 语音识别，DeepSeek 大模型总结与问答，问答历史持久化到 MySQL，音频按月份归档。

[功能特性](#功能特性) · [效果演示](#效果演示) · [快速开始](#快速开始) · [API](#api) · [项目结构](#项目结构) · [存储设计](#存储设计)

</div>

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🎙️ **音频转写** | 本地 Faster-Whisper (INT8) 提取原文，带时间戳，繁体自动转简体，完成后提示耗时 |
| 📊 **总结报告** | DeepSeek 基于原文生成结构化 Markdown 报告 |
| 💬 **智能问答** | 结合音频原文上下文回答，问答历史存入 MySQL |
| 🗂️ **历史记录** | 查看历史音频 / 原文 / 报告，继续问答，支持会话改名 |
| ⬇️ **下载导出** | 转写原文与总结报告一键下载为 md 文件 |
| 🗄️ **存储归档** | 音频按月份存于 `data/audio/YYYY-MM/`，问答历史存 MySQL |

---

## 效果演示

### 转写原文（带时间戳）

```
[00:00:00 -> 00:00:04] 大家好，今天我们来讨论一下本季度的销售情况
[00:00:04 -> 00:00:09] 我们一共卖出了500台设备，同比增长了20%
[00:00:09 -> 00:00:13] 接下来，需要重点跟进华东地区的客户
```

### 自动生成的总结报告

```
## 总结报告
### 一、内容概述
本段音频为一次简短的销售情况汇报，本季度共售出 500 台设备，同比增长 20%，
并提出下一阶段重点跟进华东地区客户的工作方向。

### 二、主要内容/要点
- 本季度销售总量为 500 台设备
- 销售量同比增长 20%
- 下一阶段工作重点是跟进华东地区客户

### 四、结论 / 行动项
- 本季度销售表现良好，实现同比增长
- 行动项：重点跟进华东地区客户
```

### 基于原文提问

```
Q ❯ 这个季度卖出了多少台设备？同比增长多少？
A   本季度卖出了500台设备，同比增长了20%。
```

---

## 快速开始

### 环境要求

- Python 3.12 (conda 环境 `shenglu`)
- NVIDIA GPU 12GB+（可选，默认 `medium` + INT8 约 5GB 显存）
- MySQL 8.0（本机 3306，存储问答历史）
- `ffmpeg`（音频解码）

### 1. 安装依赖

```bash
conda create -n shenglu python=3.12 -y
conda activate shenglu
pip install -r requirements.txt
```

> 网络说明：HuggingFace 模型下载走 `hf-mirror.com` 镜像（config.py 自动配置）；CUDA cuBLAS 由 `nvidia-cublas-cu12` 提供，config.py 自动加入 `LD_LIBRARY_PATH`。

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env, 填入 DEEPSEEK_API_KEY
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key（必填，用于总结与问答） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | LLM 接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | LLM 模型名 |
| `SL_WHISPER_MODEL` | `medium` | Whisper 模型 (tiny/base/small/medium/large-v3) |
| `SL_WHISPER_DEVICE` | `auto` | auto / cuda / cpu |
| `SL_WHISPER_COMPUTE_TYPE` | `int8` | 量化精度 |
| `SL_MAX_UPLOAD_MB` | `500` | 上传大小限制 |
| `SL_MYSQL_HOST` / `SL_MYSQL_PORT` | `127.0.0.1` / `3306` | MySQL 连接 |
| `SL_MYSQL_USER` / `SL_MYSQL_PASSWORD` | `root` / 空 | MySQL 账号 |
| `SL_MYSQL_DB` | `shenglu` | MySQL 库名 |

### 3. 启动服务

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 http://localhost:8000

> 首次启动会自动下载 Whisper 模型（`medium` 约 1.5GB）并自动创建 MySQL 数据库与表。

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/audio` | 上传音频，异步转写 |
| GET | `/api/audio/{id}` | 查询转写状态 / 结果 |
| PATCH | `/api/audio/{id}` | 会话改名 (body: `{"name":"..."}`) |
| GET | `/api/audio/{id}/transcript/download` | 下载原文 md |
| GET | `/api/audio/{id}/report/download` | 下载报告 md |
| POST | `/api/audio/{id}/report` | 生成总结报告 |
| GET | `/api/audio/{id}/report` | 获取报告 |
| POST | `/api/audio/{id}/chat` | 基于原文问答 |
| GET | `/api/audio/{id}/chat` | 获取聊天历史 |
| GET | `/api/sessions` | 历史会话列表 |

接口文档（Swagger UI）：http://localhost:8000/docs

---

## 项目结构

```
ShengLu/
├── 需求/需求.md
├── 设计文档.md
├── README.md
├── requirements.txt
├── .env.example
├── assets/
│   ├── hero.gif                          # 首页演示动画 GIF
│   └── hero-animation.html               # 动画源文件
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI 入口，MySQL 初始化
│   │   ├── config.py                     # 配置（模型、DeepSeek、MySQL、目录）
│   │   ├── schemas.py                    # Pydantic 模型
│   │   ├── routers/
│   │   │   ├── audio.py                  # 上传 / 状态 / 改名 / 下载
│   │   │   ├── report.py                 # 总结报告
│   │   │   ├── chat.py                   # 问答（历史存 MySQL）
│   │   │   └── sessions.py               # 历史会话列表
│   │   └── services/
│   │       ├── asr.py                    # Faster-Whisper 封装（繁体转简体）
│   │       ├── llm.py                    # DeepSeek 封装
│   │       ├── db.py                     # MySQL 问答历史
│   │       └── storage.py                # 文件与会话管理（按月归档）
│   └── static/                           # Web 前端（暖调录音室风格）
│       ├── index.html
│       ├── app.js
│       ├── style.css
│       └── fonts/                        # 思源宋体
├── data/                                 # 运行时数据（gitignore）
│   ├── audio/YYYY-MM/                    # 原始音频，按月子目录
│   ├── transcripts/
│   ├── reports/
│   └── sessions/
└── tests/
    └── test_api.py                       # 接口测试（转写/报告/问答/历史/改名/下载）
```

---

## 存储设计

**问答历史 → MySQL**（数据库 `shenglu`，启动自动建库建表）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK AUTO_INCREMENT | 主键 |
| session_id | VARCHAR(32) | 会话 ID，索引 |
| role | VARCHAR(16) | `user` / `assistant` |
| content | MEDIUMTEXT | 消息内容 |
| created_at | DATETIME | 创建时间 |

**音频文件 → 服务工程目录，月份子目录归档**：

```
data/
├── audio/2026-08/{session_id}.mp3      # 原始音频，按月上架
├── transcripts/{session_id}.md          # 转写原文（含时间戳）
├── reports/{session_id}.md              # 总结报告
└── sessions/{session_id}.json           # 会话元数据（名称/状态/耗时/路径）
```

---

## 技术栈

| 层 | 选型 |
|----|------|
| 语音识别 | **Faster-Whisper**（本地，INT8 量化，CTranslate2 + VAD） |
| 大模型 | **DeepSeek**（OpenAI 兼容接口，总结 + 问答） |
| 后端 | **FastAPI + Uvicorn** |
| 数据库 | **MySQL 8.0**（pymysql） |
| 前端 | 原生 HTML/CSS/JS（暖调录音室风格，思源宋体） |
| 中文处理 | OpenCC 繁体转简体 |

---

## 许可证

MIT — 随便用，随便改。

---

## 关于作者

**zhituCodder** — AI Native Coder，独立开发者

| 平台 | 链接 |
|------|------|
| 🌐 官网 |  |
| 📺 B站 | [浩哥讲大模型与AI应用](https://space.bilibili.com/1235336642) |
| 📕 小红书 | [知途程序员]|
| 💬 CSDN | [星星之火](https://blog.csdn.net/spark_dev) |
| 📈 雪球 | [浩哥AI量化财报](https://xueqiu.com/u/haoai) |
| 📮 公众号 | 微信搜「知途程序员知识体系」或扫码关注 ↓ |

<img src="wechat-qrcode.png" alt="公众号二维码" width="360">

<div align="center">

*不破楼兰终不还。*

<br>

MIT License © [zhituCodder](https://github.com/zhitucoder)


</div>
