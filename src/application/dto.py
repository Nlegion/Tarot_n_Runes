"""Shared DTOs for application layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationRequest:
    system_prompt: str
    user_content: str
    messages: list[dict[str, str]]


@dataclass(frozen=True)
class GenerationResponse:
    text: str
    model_name: str
    latency_ms: int
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
