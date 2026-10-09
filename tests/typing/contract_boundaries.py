"""Static consumers exercise public field types and the evaluator protocol."""

from typing import Any

from contracts.http import Envelope, ResponseMeta
from contracts.models import ChatMessageCreate, ChatResponseV1, MCQCommand, MCQResponseV1
from evaluation.bridge import AnswerBackend
from generation.types import GenerationRequest, ModelConfig


def prepare_chat(content: str) -> Envelope[ChatMessageCreate]:
    return Envelope(data=ChatMessageCreate(content=content), meta=ResponseMeta(trace_id="typed"))


def selected_mcq(response: MCQResponseV1) -> str | None:
    return response.answer_text


def chat_text(response: ChatResponseV1) -> str:
    return response.answer_text


def generate_command(command: MCQCommand, config: ModelConfig) -> GenerationRequest:
    return GenerationRequest(
        request_id=command.item_id,
        mode=command.mode,
        condition="E1",
        question=command.question_text,
        options={str(label): text for label, text in command.options.items()},
        config=config,
    )


def submit_registered(
    backend: AnswerBackend, command: MCQCommand, manifest: dict[str, Any], key: str
) -> dict[str, Any]:
    backend.register_run(manifest)
    receipt = backend.lookup(key)
    if receipt is None:
        receipt = backend.submit(command.model_dump(), run_context=manifest, idempotency_key=key)
    return backend.poll(receipt)
