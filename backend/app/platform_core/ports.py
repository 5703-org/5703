"""Capability ports (Spec L01, L03-L05).

Teammates' algorithms plug in through these Protocols. The core flow
depends on the contract, never on a concrete model or library.
"""

from __future__ import annotations

from typing import Any, Protocol


class ParserPort(Protocol):
    def parse(self, document_version_id: str) -> dict[str, Any]:
        """Parse a document version into chunks + metadata."""
        ...


class RetrieverPort(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Return ranked evidence candidates for a query."""
        ...


class GeneratorPort(Protocol):
    def generate(
        self, question: str, evidence: list[dict[str, Any]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an answer, refusal, or structured error."""
        ...
