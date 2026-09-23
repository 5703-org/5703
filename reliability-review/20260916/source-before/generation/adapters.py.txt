"""One-call compatible HTTP adapter adapted from the supplied Sijin Lu handover."""

from __future__ import annotations
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
import re
import socket
import time
import unicodedata
from urllib import error, request as http

from .types import ModelConfig, ProviderResult, failure


def redact(value: str, limit: int = 400) -> str:
    value = re.sub(
        r"(?i)(bearer\s+|(?:api[_ -]?key|authorization)\s*[:=]\s*)\S+", r"\1[redacted]", str(value)
    )
    value = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[redacted]", value)
    return value[:limit]


def retry_after(value: str | None):
    if not value:
        return None
    try:
        return min(60.0, max(0.0, float(value)))
    except ValueError:
        try:
            return min(
                60.0,
                max(
                    0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                ),
            )
        except (TypeError, ValueError, OverflowError):
            return None


_UNSET = object()


class _NoRedirect(http.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise error.HTTPError(req.full_url, code, "Provider redirects are disabled", headers, fp)


def open_provider(envelope, timeout):
    """Never forward credentials across redirects; injectable one-call transport seam."""
    return http.build_opener(_NoRedirect()).open(envelope, timeout=timeout)


class LLMAdapter:
    """One external HTTP request per method, without retries or provider switching."""

    def __init__(self, config: ModelConfig, api_key=_UNSET):
        self.config = config
        self._api_key = api_key

    def _key(self):
        if self._api_key is not _UNSET:
            return self._api_key
        if self.config.configuration_id.startswith("model-settings:"):
            return None
        key_name = self.config.api_key_env or {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }.get(self.config.provider)
        return os.environ.get(key_name) if key_name else None

    def generate(
        self,
        messages,
        *,
        response_schema,
        response_schema_name,
        request_context=None,
        timeout_seconds=None,
    ):
        if self.config.provider == "mock":
            result = ProviderResult(
                provider="mock", model=self.config.model, request_submitted=True
            )
            try:
                self.config.validate()
                result.raw_text = json.dumps(
                    mock_payload(request_context or {}), ensure_ascii=False
                )
                result.finish_reason = "stop"
            except (TypeError, ValueError):
                result.error = failure("CONFIGURATION_ERROR", "Invalid mock configuration")
            return result
        return self._call(messages, response_schema, response_schema_name, timeout_seconds)

    def count_tokens(
        self, messages, *, response_schema, response_schema_name, timeout_seconds=None
    ):
        return self._call(
            messages, response_schema, response_schema_name, timeout_seconds, count=True
        )

    def _call(self, messages, schema, schema_name, timeout_seconds, *, count=False):
        from .providers import endpoint, headers, payload, decode_response

        cfg = self.config
        started = time.monotonic()
        result = ProviderResult(provider=cfg.provider, model=cfg.model, request_submitted=False)
        try:
            cfg.validate()
            key = self._key()
            if (
                cfg.api_key_env
                and not cfg.configuration_id.startswith("model-settings:")
                and self._api_key is _UNSET
                and not key
            ):
                raise ValueError("Configured credential environment variable is unavailable")
            envelope = http.Request(
                endpoint(cfg, count=count),
                data=json.dumps(
                    payload(cfg, messages, schema, schema_name, count=count), ensure_ascii=False
                ).encode(),
                headers=headers(cfg, key),
                method="POST",
            )
        except (ValueError, TypeError):
            result.error = failure(
                "CONFIGURATION_ERROR",
                "Provider endpoint, credential, or protocol configuration is invalid",
            )
            return result
        try:
            result.request_submitted = True
            with open_provider(
                envelope, timeout=min(timeout_seconds or cfg.timeout_seconds, cfg.timeout_seconds)
            ) as response:
                result.provider_request_id = (
                    response.headers.get("x-request-id") or response.headers.get("request-id")
                    if getattr(response, "headers", None)
                    else None
                )
                data = response.read(4_000_001)
                if len(data) > 4_000_000:
                    raise ValueError("Provider response is too large")
                decoded = json.loads(data.decode("utf-8"))
            decode_response(decoded, result, count=count)
        except error.HTTPError as exc:
            status = exc.code
            result.provider_request_id = (
                (exc.headers.get("x-request-id") or exc.headers.get("request-id"))
                if exc.headers
                else None
            )
            result.error = failure(
                "PROVIDER_HTTP_ERROR",
                f"Provider returned HTTP {status}",
                retryable=status in {429, 500, 502, 503, 504},
                http_status=status,
                retry_after_seconds=retry_after(
                    exc.headers.get("Retry-After") if exc.headers else None
                ),
                provider_request_id=result.provider_request_id,
            )
        except (TimeoutError, socket.timeout):
            result.error = failure(
                "PROVIDER_TIMEOUT", "Provider call timed out", retryable=True, uncertain=True
            )
        except error.URLError as exc:
            result.error = (
                failure(
                    "PROVIDER_TIMEOUT", "Provider call timed out", retryable=True, uncertain=True
                )
                if isinstance(exc.reason, (TimeoutError, socket.timeout))
                else failure(
                    "PROVIDER_NETWORK_ERROR",
                    "Provider endpoint could not be reached",
                    retryable=True,
                )
            )
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError):
            result.error = failure(
                "PROVIDER_RESPONSE_ERROR", "Provider returned an invalid response envelope"
            )
        result.latency_ms = int((time.monotonic() - started) * 1000)
        return result


def test_connection(config: ModelConfig, api_key=None) -> ProviderResult:
    """Single transport probe; no raw provider response escapes this boundary."""
    from dataclasses import replace
    from .parser import strict_json

    probe = replace(config, max_tokens=min(config.max_tokens, 128))
    if config.provider == "mock":
        return ProviderResult(
            raw_text='{"ok":true}', provider="mock", model=config.model, finish_reason="stop"
        )
    result = LLMAdapter(probe, api_key=api_key).generate(
        [{"role": "user", "content": 'Return exactly {"ok":true} as JSON.'}],
        response_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean", "const": True}},
            "required": ["ok"],
            "additionalProperties": False,
        },
        response_schema_name="connection_probe",
    )
    if result.error is None:
        try:
            value = strict_json(result.raw_text)
            if list(value) != ["ok"] or value["ok"] is not True:
                raise ValueError("Invalid probe")
        except ValueError:
            result.error = failure(
                "PROVIDER_PROBE_INVALID", "Provider did not return the required probe JSON"
            )
    result.raw_text = '{"ok":true}' if result.error is None else ""
    return result


STOPWORDS = set(
    "a an the is are was were be to of and in for how what why does do did it this that can you me i please explain about more with on as need needs use uses".split()
)


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.casefold())) - STOPWORDS


MOCK_QUESTION_WORDS = STOPWORDS | set(
    "who whom whose which when where would could should has have had will shall been being am "
    "at by from during between my your his her their our its tell describe show "
    "compare comparison difference differ function functions form forms kind kinds type types "
    "make makes made mean meant".split()
)
MOCK_STYLE_WORDS = set(
    "make give simpler simply simplify rephrase again example analogy detail detailed shorter "
    "summarize summarise topic terms briefly".split()
)


def mock_terms(text: str, *, query=False, reexplain=False) -> set[str]:
    """Small English lexical guard; never use similarity scores as support labels."""
    text = "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )
    text = re.sub(r"[’']s\b", "", text)
    terms = set(re.findall(r"[a-z0-9]+", text))
    if query:
        terms -= MOCK_QUESTION_WORDS
        if reexplain:
            terms -= MOCK_STYLE_WORDS
    return terms


def mock_inflections(term: str) -> set[str]:
    """Match ordinary inflections, without synonyms or removal of numbers/negation."""
    forms = {term}
    if len(term) > 4 and term.endswith("ies"):
        forms.add(term[:-3] + "y")
    elif len(term) > 3 and term.endswith("s") and not term.endswith(("ss", "is", "us")):
        forms.add(term[:-1])
    for form in tuple(forms):
        if len(form) > 4 and form.endswith("ed"):
            forms.update((form[:-2], form[:-1]))
        elif len(form) > 5 and form.endswith("ing"):
            forms.update((form[:-3], form[:-3] + "e"))
    return forms


def mock_excerpt(query: str, evidence: list[dict], *, reexplain=False):
    """Abstain unless one short contiguous extract covers every query content term.

    This deliberately misses synonyms and support requiring distant passages. Lexical
    coverage is only a conservative mock heuristic, never semantic entailment. The
    three-sentence ceiling bounds extract size independently of presentation style.
    """
    required = [
        mock_inflections(term) for term in mock_terms(query, query=True, reexplain=reexplain)
    ]
    if not required:
        return None

    def covers(text):
        present = set().union(*(mock_inflections(term) for term in mock_terms(text)))
        return all(forms & present for forms in required)

    candidates = []
    for index, item in enumerate(evidence):
        if not covers(item["text"]):
            continue
        sentences = [
            part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", item["text"]) if part.strip()
        ]
        for start in range(len(sentences)):
            for count in range(1, min(3, len(sentences) - start) + 1):
                selected_sentences = sentences[start : start + count]
                # A source exercise/question supplies no asserted answer, even if
                # its words cover the learner's query exactly.
                if any(sentence.endswith("?") for sentence in selected_sentences):
                    continue
                excerpt = " ".join(selected_sentences)
                if covers(excerpt):
                    candidates.append((count, len(excerpt), index, start, excerpt, item))
                    break
    if not candidates:
        return None
    best = min(candidates, key=lambda candidate: candidate[:4])
    return best[4], best[5]


def chat_value(
    response_type, text, *, citations=None, short_answer=None, reason=None, questions=None
):
    return {
        "schema_version": "chat_response_v1",
        "response_type": response_type,
        "answer_text": text,
        "short_answer": short_answer,
        "citations": citations or [],
        "refusal_reason": reason,
        "follow_up_questions": questions or [],
        "confidence": None,
    }


def mock_payload(context: dict):
    """Extract meaningful supplied evidence; explicitly not a scientific model."""
    if context.get("schema") == "teaching_study_response_v1":
        base = context["base_answer"]["answer_text"]
        level = context.get("target_level")
        condition = context.get("study_condition")
        prefix = (
            ""
            if condition == "C0"
            else {
                "beginner": "In plain language: ",
                "intermediate": "Connecting the concepts: ",
                "advanced": "With the stated qualifications: ",
            }.get(level, "")
        )
        return {
            "schema_version": "teaching_study_response_v1",
            "explanation": prefix + base,
            "citations": context["base_answer"].get("citations", []),
            "learning_check": None,
            "invariant_check": {"structural_valid": True, "human_review_status": "pending"},
        }
    question = context.get("question", "")
    prepared = context.get("prepared_query") or {}
    intent = prepared.get("intent", "factual")
    mode, condition = context.get("mode", "interactive_chat"), context.get("condition", "E1")
    evidence = context.get("evidence", [])
    query = prepared.get("standalone_query") or question
    if mode != "benchmark_mcq" and intent == "social":
        return chat_value(
            "social", "Hello. What would you like to understand or explore in the textbook?"
        )
    if mode != "benchmark_mcq" and (
        prepared.get("needs_clarification") or intent == "clarification"
    ):
        return chat_value(
            "clarification",
            "Which concept or earlier explanation would you like me to explain? Please name the topic.",
        )
    if mode == "benchmark_mcq":
        options = context["options"]
        corpus = " ".join(item["text"] for item in evidence).casefold()
        scores = {
            label: (10 if text.casefold().strip() in corpus else 0)
            + len(words(text) & words(corpus))
            for label, text in options.items()
        }
        selected = (
            max("ABCD", key=lambda label: (scores[label], -ord(label)))
            if evidence
            else "ABCD"[int(hashlib.sha256(question.encode()).hexdigest()[:8], 16) % 4]
        )
        refused = condition != "E0" and (not evidence or scores[selected] == 0)
        return {
            "question_id": context.get("question_id", ""),
            "answer": None if refused else selected,
            "answer_text": None if refused else options[selected],
            "citations": [] if refused or condition == "E0" else [evidence[0]["evidence_id"]],
            "confidence": None,
            "refused": refused,
            "refusal_reason": ("NO_EVIDENCE" if not evidence else "INSUFFICIENT_EVIDENCE")
            if refused
            else None,
            "short_explanation": "Deterministic offline option/evidence comparison; this is not a measured model prediction.",
        }
    if condition == "E0":
        return chat_value(
            "answer",
            "This offline no-retrieval control cannot independently establish a science answer. The question is: "
            + question,
        )
    if not evidence:
        return chat_value(
            "refusal",
            "I could not find an available textbook passage supporting this question. Try naming a concept covered by the current corpus.",
            reason="NO_EVIDENCE",
        )
    if intent == "source_request":
        items = evidence[:3]
        return chat_value(
            "answer",
            "The explanation uses "
            + "; ".join(
                f"{item['source_title']}, {item['locator']} [{item['evidence_id']}]"
                for item in items
            )
            + ".",
            citations=[e["evidence_id"] for e in items],
            short_answer="Sources for the previous explanation",
        )
    selected = mock_excerpt(query, evidence, reexplain=intent == "reexplain")
    if selected is None:
        return chat_value(
            "refusal",
            "This mock answerer could not match the full question to a short textbook excerpt. "
            "The retrieved passages may still be useful; try naming a narrower concept or inspect the original sources.",
            reason="INSUFFICIENT_EVIDENCE",
        )
    profile = (context.get("profile") or {}).get("profile") or {}
    override = (context.get("profile") or {}).get("turn_override") or {}
    style = override.get("style", profile.get("style", "concise"))
    excerpt, source = selected
    citations = [source["evidence_id"]]
    answer = f"{excerpt} [{source['evidence_id']}]"
    followups = ["Which part would you like to explore further?"] if style == "socratic" else []
    return chat_value(
        "answer", answer, citations=citations, short_answer=excerpt[:240], questions=followups
    )
