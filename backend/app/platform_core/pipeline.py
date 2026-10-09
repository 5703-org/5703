"""Versioned pipeline skeleton (Spec L07-L13).

The executor + typed context ship first; the five preset routes
(E0 / E1 / oracle / optimised / personalised) are wired to real providers
when retrieval and generation land.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.exceptions import AppError


@dataclass
class PipelineStep:
    name: str
    capability_type: str
    provider_id: str
    required: bool = True
    condition: str | None = None  # evaluated against context flags, e.g. "has_evidence"


@dataclass
class PipelineDefinition:
    name: str
    version: str
    steps: list[PipelineStep] = field(default_factory=list)


@dataclass
class StepResult:
    step: str
    provider_id: str
    status: str  # completed | skipped | failed
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class PipelineContext:
    question: str = ""
    profile: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
    results: list[StepResult] = field(default_factory=list)


StepHandler = Callable[[PipelineContext, PipelineStep], Any]


class PipelineExecutor:
    """Executes steps in order; every step produces a StepResult (Spec L09)."""

    def __init__(self, handlers: dict[str, StepHandler] | None = None):
        self._handlers = handlers or {}

    def run(self, definition: PipelineDefinition, context: PipelineContext) -> PipelineContext:
        for step in definition.steps:
            if step.condition and not context.flags.get(step.condition, False):
                context.results.append(StepResult(step.name, step.provider_id, "skipped"))
                continue
            handler = self._handlers.get(step.capability_type)
            if handler is None:
                if step.required:
                    raise AppError(
                        "CONFLICT", detail=f"No handler for capability: {step.capability_type}"
                    )
                context.results.append(StepResult(step.name, step.provider_id, "skipped"))
                continue
            try:
                output = handler(context, step)
                context.results.append(
                    StepResult(step.name, step.provider_id, "completed", output=output)
                )
            except AppError as exc:
                if step.required:
                    raise
                context.results.append(
                    StepResult(step.name, step.provider_id, "failed", error=exc.code)
                )
        return context
