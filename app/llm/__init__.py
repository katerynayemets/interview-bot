# app/llm/__init__.py
"""
LLM интеграция для interview-bot.
Поддержка OpenAI, Anthropic, и других провайдеров.
"""

from app.llm.client import LLMClient, LLMResponse, get_llm_client
from app.llm.prompts import PromptManager, InterviewPrompts
from app.llm.context import build_interview_context, ContextBuilder

__all__ = [
    "LLMClient",
    "LLMResponse",
    "get_llm_client",
    "PromptManager",
    "InterviewPrompts",
    "build_interview_context",
    "ContextBuilder",
]
