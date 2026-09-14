"""Provider registry (Spec L01-L03, K09).

Providers register once at startup (code-declared, not remotely installed -
deliberately NOT a plugin marketplace). The capability discovery API reads
from here so the frontend never hardcodes buttons.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.core.exceptions import AppError

CONTRACT_VERSION = "1.0"


@dataclass
class ProviderDescriptor:
    provider_id: str
    capability_type: (
        str  # parser | chunker | embedding | retriever | reranker | generator | evaluator
    )
    version: str
    contract_version: str = CONTRACT_VERSION
    healthy: bool = True
    config_schema: dict = field(default_factory=dict)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderDescriptor] = {}

    def register(self, descriptor: ProviderDescriptor) -> None:
        if descriptor.provider_id in self._providers:
            raise AppError("CONFLICT", detail=f"Duplicate provider id: {descriptor.provider_id}")
        self._providers[descriptor.provider_id] = descriptor

    def get(self, provider_id: str) -> ProviderDescriptor:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise AppError("NOT_FOUND", detail=f"Unknown provider: {provider_id}") from exc

    def list(self) -> list[dict]:
        return [asdict(p) for p in self._providers.values()]

    def by_capability(self, capability_type: str) -> list[dict]:
        return [asdict(p) for p in self._providers.values() if p.capability_type == capability_type]


registry = ProviderRegistry()


def register_builtin_providers() -> None:
    """Demo providers so the capability API and pipeline have real entries."""
    for descriptor in (
        ProviderDescriptor("mock-parser", "parser", version="0.1.0"),
        ProviderDescriptor("mock-retriever", "retriever", version="0.1.0"),
        ProviderDescriptor("mock-generator", "generator", version="0.1.0"),
    ):
        if descriptor.provider_id not in registry._providers:
            registry.register(descriptor)
