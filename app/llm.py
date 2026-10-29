"""Answer generation. Swap this module to use a different LLM provider."""

import os
from pathlib import Path

from openai import AzureOpenAI, OpenAIError

KNOWLEDGE_FILE = Path(__file__).resolve().parent.parent / "knowledge.md"

SYSTEM_PROMPT = """You are a friendly customer support voice agent.
Your answers are shown as text and also read aloud, so:
- Keep answers short (one to three sentences) and conversational.
- Don't use Markdown, lists, tables, emojis or URLs that are awkward to hear.
- Answer from the business knowledge below. If the answer isn't there,
  say you don't know and suggest contacting the team. Don't make things up.

Business knowledge:
{knowledge}
"""


def load_knowledge() -> str:
    try:
        return KNOWLEDGE_FILE.read_text(encoding="utf-8").strip() or "(none provided)"
    except FileNotFoundError:
        return "(none provided)"


def _client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in .env.")
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def answer_question(question: str, history: list[dict]) -> str:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT must be set in .env.")
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(knowledge=load_knowledge())}]
    messages += history
    messages.append({"role": "user", "content": question})
    try:
        resp = _client().chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=300,
            temperature=0.3,
        )
    except OpenAIError as exc:
        raise RuntimeError(f"Azure OpenAI request failed: {exc}") from exc
    return (resp.choices[0].message.content or "").strip()
