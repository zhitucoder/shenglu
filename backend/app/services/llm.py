import logging

from .. import config

logger = logging.getLogger("llm")

_client = None

SUMMARY_PROMPT = """你是一名专业的音频内容分析师。请根据下面提供的音频转写原文,生成一份结构化的总结报告。

报告要求(使用 Markdown 格式):
## 总结报告
### 一、内容概述
用 3-5 句话概括音频的核心内容。
### 二、主要内容/要点
分条列出关键信息、论点或事项,每条尽量具体。
### 三、关键数据与引用(如有)
列出原文中提到的数字、日期、人名、产品名等。
### 四、结论 / 行动项
总结最终结论或需要跟进的事项(如有)。
### 五、建议问题
根据内容提出 3-5 个用户可能关心的追问问题。

注意: 只基于音频原文内容,不要编造原文中没有的信息。以下是转写原文:"""

CHAT_PROMPT = """你是「音频内容助手」。以下是一段音频的转写原文,请基于原文内容回答用户的问题。
要求:
1. 只依据原文信息作答,原文没有的明确说明"原文中没有提到"。
2. 回答用简洁的中文,必要时分点。
3. 不要编造事实。

## 音频转写原文
{transcript}"""


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY or "missing",
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def _chat(messages: list[dict], temperature: float = 0.3) -> str:
    if not config.DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY 环境变量")
    resp = _get_client().chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def generate_summary(transcript: str) -> str:
    return _chat([
        {"role": "system", "content": "你是专业的音频内容分析师。"},
        {"role": "user", "content": SUMMARY_PROMPT + "\n\n" + transcript},
    ], temperature=0.2)


def chat(transcript: str, history: list[dict], question: str) -> str:
    messages = [{"role": "system", "content": CHAT_PROMPT.format(transcript=transcript)}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": question})
    return _chat(messages, temperature=0.3)
