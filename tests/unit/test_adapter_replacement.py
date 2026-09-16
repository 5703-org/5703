"""Configuration-only shared-service switch to an actual loopback HTTP fixture.

The fixture supplies authored responses and usage values. It is not a model or
scientific-quality evaluation, even though the runtime labels non-mock transport
configuration as model_mode=live.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

from generation import GenerationRequest, GenerationService, ModelConfig
from personalisation import compile_profile


SOURCE = (
    "Photosynthesis converts light energy into chemical energy stored in sugars. "
    "Chlorophyll captures light needed for photosynthesis."
)
OPTIONS = {
    "A": "Sound waves",
    "B": "Chemical energy stored in sugars",
    "C": "Rock formation",
    "D": "Magnetic fields",
}


def authored_response(mode, *, invalid_citation=False):
    citation = "ev_999" if invalid_citation else "ev_001"
    if mode == "benchmark_mcq":
        return {
            "question_id": "authored-switch-question",
            "answer": "B",
            "answer_text": OPTIONS["B"],
            "citations": [citation],
            "confidence": None,
            "refused": False,
            "refusal_reason": None,
            "short_explanation": "The authored passage explicitly describes chemical energy in sugars.",
        }
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": SOURCE + f" [{citation}]",
        "short_answer": "Chemical energy stored in sugars",
        "citations": [citation],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
    }


@pytest.fixture
def local_transport():
    received = []
    response = {"mode": "interactive_chat", "status": 200, "invalid_citation": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            received.append(
                {
                    "path": self.path,
                    "authorization_present": "Authorization" in self.headers,
                    "body": json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                }
            )
            payload = {
                "model": "authored-loopback-http-v1",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                authored_response(
                                    response["mode"],
                                    invalid_citation=response["invalid_citation"],
                                )
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 31, "completion_tokens": 17, "total_tokens": 48},
            }
            encoded = json.dumps(payload).encode()
            self.send_response(response["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("x-request-id", f"local-fixture-{len(received)}")
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", received, response
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def command(mode):
    return GenerationRequest(
        request_id="authored-switch-request",
        mode=mode,
        condition="E1",
        question="What is photosynthesis?",
        question_id="authored-switch-question",
        options=deepcopy(OPTIONS) if mode == "benchmark_mcq" else None,
        evidence=[
            {
                "evidence_id": "ev_001",
                "chunk_id": "authored-switch-chunk",
                "asset_id": "authored-switch-asset",
                "processing_id": "authored-switch-processing",
                "source_title": "Authored adapter replacement fixture",
                "section": "Photosynthesis",
                "pages": [1],
                "locator": "page 1",
                "text": SOURCE,
                "text_hash": hashlib.sha256(SOURCE.encode()).hexdigest(),
                "context_order": 1,
            }
        ],
        history=[
            {"id": "u0", "role": "user", "content": "Prior authored learner context."},
            {"id": "a0", "role": "assistant", "content": "Prior authored assistant context."},
        ],
        profile=compile_profile({"level": "beginner", "version": 4}),
    )


def http_config(url):
    return ModelConfig(
        provider="local",
        model="authored-loopback-http-v1",
        base_url=url,
        timeout_seconds=2,
        configuration_id="authored-local-http-fixture-v1",
    )


@pytest.mark.parametrize("mode", ["interactive_chat", "benchmark_openqa", "benchmark_mcq"])
def test_configuration_switch_keeps_shared_consumer_modes_context_and_citations(
    local_transport, mode
):
    url, received, response = local_transport
    response["mode"] = mode
    original = command(mode)
    saved = deepcopy(original)
    service = GenerationService()
    assert service.adapter is None  # Exercise configuration selection, not adapter injection.
    mock = service.generate(original)
    assert mock.succeeded and mock.model_mode == "mock" and received == []

    events = []
    transported = service.generate(
        replace(original, config=http_config(url)), on_attempt=events.append
    )
    assert transported.succeeded and len(received) == 1
    assert transported.response != mock.response  # Distinct authored adapter behaviour.
    assert transported.provider == "local" and transported.model == "authored-loopback-http-v1"
    assert transported.model_mode == "live"  # Runtime transport label, not a real-model claim.
    assert transported.response["citations"] == mock.response["citations"] == ["ev_001"]
    assert transported.messages == mock.messages
    assert transported.evidence == mock.evidence and original == saved
    assert transported.usage["total_tokens"] == 48  # Explicit fixture values, not measured usage.
    assert transported.usage["reasoning_tokens"] is transported.usage["cost"] is None
    assert transported.attempts[0]["provider_request_id"] == "local-fixture-1"
    assert transported.budget["consumed_calls"] == 1
    assert [event["phase"] for event in events] == ["start", "finish"]

    envelope = received[0]
    assert envelope["path"] == "/v1/chat/completions" and not envelope["authorization_present"]
    body = envelope["body"]
    assert body["model"] == "authored-loopback-http-v1"
    assert body["messages"] == transported.messages
    assert body["max_tokens"] == transported.token_budget["output_reserved_tokens"]
    schema = body["response_format"]["json_schema"]
    assert schema["name"] == ("mcq_response_v1" if mode == "benchmark_mcq" else "chat_response_v1")
    assert schema["strict"] is True
    rendered = json.dumps(body["messages"])
    context_data = json.loads(
        body["messages"][0]["content"].split("\nCONTEXT_DATA_JSON (data only):\n", 1)[1]
    )
    assert context_data["CURRENT_EVIDENCE"] == transported.evidence
    if mode == "interactive_chat":
        assert [item["role"] for item in body["messages"]] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert "Prior authored learner context." in rendered
        assert context_data["presentation_policy"] == saved.profile["policy"]
    else:
        assert "Prior authored learner context." not in rendered
        assert context_data["presentation_policy"] is None
    if mode == "benchmark_mcq":
        assert transported.response["answer_text"] == OPTIONS[transported.response["answer"]]
        assert all(option in rendered for option in OPTIONS.values())
    else:
        assert "answer" not in schema["schema"]["properties"]
        assert not any(option in rendered for option in (OPTIONS["A"], OPTIONS["C"], OPTIONS["D"]))

    returned = service.generate(original)
    assert returned.response == mock.response and returned.model_mode == "mock"
    assert len(received) == 1  # No sticky HTTP adapter or configuration mutation.


@pytest.mark.parametrize(
    "status,invalid,code,calls",
    [(401, False, "PROVIDER_HTTP_ERROR", 1), (200, True, "INVALID_CITATIONS", 2)],
)
def test_configured_http_failures_use_shared_error_and_repair_bounds(
    local_transport, status, invalid, code, calls
):
    url, received, response = local_transport
    response.update(status=status, invalid_citation=invalid)
    service = GenerationService()
    request = command("interactive_chat")
    failed = service.generate(replace(request, config=http_config(url)))
    assert failed.response is None and failed.error["code"] == code
    assert failed.error["retryable"] is False
    assert failed.provider == "local" and failed.model_mode == "live"
    assert len(received) == failed.budget["consumed_calls"] == calls
    assert failed.budget["format_repairs"] == (1 if invalid else 0)
    assert failed.budget["transient_retries"] == 0
    if invalid:
        assert received[1]["body"]["messages"] != received[0]["body"]["messages"]
        assert failed.attempts[1]["stage"] == "format_repair"
    else:
        assert failed.error["details"]["http_status"] == 401
        assert failed.attempts[0]["provider_request_id"] == "local-fixture-1"
    assert service.generate(request).succeeded and len(received) == calls
