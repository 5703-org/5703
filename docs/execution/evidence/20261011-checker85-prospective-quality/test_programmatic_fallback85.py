"""Eight prepare-only controls for the exact W fallback candidate.

Root owns test execution and supplies Main on sys.path. These controls isolate
the candidate's fallback AST and use the real GenerationService entry/gates;
they do not claim complete live checker semantics or model-quality coverage.
"""

import ast
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
from pathlib import Path
import socket

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation import service as service_module
from generation.types import GenerationRequest

CANDIDATE = Path(__file__).with_name("checked.py")
BEFORE = Path(__file__).with_name("checked.py.before85")
CANDIDATE_SHA = "35338a904cec0297ece096f94b83d986c7e7014216b246c09725febeeba8246c"
BEFORE_SHA = "fd8f18a8a7dbed449654310fb17086ddb4207069a394ca4ac55cf2db3a6fab8c"
OUTPUT_POLICY = "lossless_unit_findings_v1"
PAYLOAD_POLICY = "lossless_full_checker_tables_v2"


def candidate_tree(path, expected_sha):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha
    return ast.parse(raw, filename=str(path))


def fallback_node(tree):
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "generate_checked")
    nodes = [node for node in ast.walk(function) if isinstance(node, ast.If)
             and "needs_clarification" in ast.unparse(node.test)
             and any(isinstance(item, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "programmatic_request"
                             for target in item.targets) for item in node.body)]
    assert len(nodes) == 1
    return nodes[0]


@pytest.fixture
def derived_fallback():
    # Extract the actual condition, both derived replacements, and service call.
    # Publication projection/accounting below the call is outside this narrow test.
    branch = deepcopy(fallback_node(candidate_tree(CANDIDATE, CANDIDATE_SHA)))
    branch.body = [node for node in branch.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name)
                           and target.id in {"programmatic_request", "result"}
                           for target in node.targets)]
    assert len(branch.body) == 3
    branch.body.append(ast.Return(value=ast.Name(id="result", ctx=ast.Load())))
    module = ast.parse(
        "def derived(legacy_request, effective, selected, pending_action_gate, service, budget, "
        "on_attempt=None, request=None):\n    pass\n"
    )
    # The real condition also consults the original request's answer_mode.
    module.body[0].body = [branch]
    namespace = {"replace": replace}
    exec(compile(ast.fix_missing_locations(module), str(CANDIDATE), "exec"), namespace)
    derived = namespace["derived"]
    assert Path(derived.__code__.co_filename) == CANDIDATE
    return derived


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("SYNTHETIC_NETWORK_FORBIDDEN")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


class NoAdapterCalls:
    def __init__(self):
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("SYNTHETIC_ADAPTER_FORBIDDEN")

    count_tokens = generate


class SpyService(GenerationService):
    def __init__(self):
        self.blocked_adapter = NoAdapterCalls()
        super().__init__(adapter=self.blocked_adapter, checker_adapter=self.blocked_adapter)
        self.observed = []

    def generate(self, request, budget=None, on_attempt=None, *, programmatic_only=False):
        self.observed.append((request, programmatic_only))
        return super().generate(request, budget, on_attempt, programmatic_only=programmatic_only)


def original_request(state="clarification"):
    clarification = state == "clarification"
    return GenerationRequest(
        request_id="synthetic-fallback85", question="What does the fixture process use?",
        mode="interactive_chat", condition="E1", answer_mode="textbook",
        enhancement_version="checked_attribution_v5", reliability_policy="evidence_reliability_v5",
        joint_checker_policy="typed_joint_v5", source_relation_policy="source_relation_contract_v2",
        checker_output_policy=OUTPUT_POLICY, checker_payload_policy=PAYLOAD_POLICY,
        config=ModelConfig(tokenizer_provider="estimate", structured_output_mode="json_object",
                           window_tokens=65536),
        teaching_context={"teaching_mode": "direct", "turn_role": "user_question"},
        prepared_query={"intent": "clarification" if clarification else "factual",
                        "needs_clarification": clarification},
    )


@pytest.mark.parametrize("pending", [False, True])
@pytest.mark.parametrize("state,origin", [
    ("clarification", "programmatic_ambiguity_clarification"),
    ("no_evidence", "programmatic_no_evidence"),
])
def test_derived_programmatic_origins_clear_both_optins_only_on_clone(
    derived_fallback, pending, state, origin,
):
    # pending is a branch-isolation input, not a claim that lossless output is
    # compatible with a live pending-action policy. Its original entry remains strict.
    original = original_request(state)
    original_bytes = asdict(original)
    legacy = replace(original, enhancement_version=None)
    service, budget = SpyService(), RequestBudget(max_calls=2)
    result = derived_fallback(legacy, legacy, [], pending, service, budget, request=original)
    observed, programmatic_only = service.observed[0]
    assert observed is not original and observed is not legacy
    assert observed.checker_output_policy is None
    assert observed.checker_payload_policy == "legacy_fragment_table_v1"
    assert observed.enhancement_version is None and programmatic_only is True
    assert result.succeeded and result.response_origin == origin
    assert result.attempts == [] and budget.consumed_calls == 0
    assert service.blocked_adapter.calls == 0 and asdict(original) == original_bytes
    assert legacy.checker_output_policy == OUTPUT_POLICY and legacy.checker_payload_policy == PAYLOAD_POLICY


def test_unexpected_fallback_cannot_dispatch_unchecked_generation(derived_fallback, monkeypatch):
    original = original_request()
    legacy = replace(original, enhancement_version=None)

    def unexpected_messages(request, counter=None):
        effective = replace(request, prepared_query={"intent": "factual", "needs_clarification": False})
        selected = [{"evidence_id": "ev_001", "chunk_id": "synthetic-chunk"}]
        return [], selected, {"output_reserved_tokens": request.config.max_tokens}, effective

    monkeypatch.setattr(service_module, "build_messages", unexpected_messages)
    service, budget = SpyService(), RequestBudget(max_calls=2)
    result = derived_fallback(legacy, legacy, [], False, service, budget, request=original)
    assert result.response is None and result.error["code"] == "PROGRAMMATIC_STATE_INVALID"
    assert service.observed[0][1] is True
    assert result.attempts == [] and budget.consumed_calls == service.blocked_adapter.calls == 0


@pytest.mark.parametrize("output,error", [
    (OUTPUT_POLICY, "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"),
    (None, "CHECKER_PAYLOAD_POLICY_INCOMPATIBLE"),
])
def test_real_original_service_entry_still_rejects_invalid_optins(output, error):
    original = replace(original_request(), enhancement_version=None, checker_output_policy=output)
    before = asdict(original)
    service, budget = SpyService(), RequestBudget(max_calls=2)
    result = service.generate(original, budget, programmatic_only=True)
    assert result.response is None and result.error["code"] == error
    assert result.attempts == [] and budget.consumed_calls == service.blocked_adapter.calls == 0
    assert asdict(original) == before


def test_normal_evidence_path_and_original_live_gates_are_unchanged(derived_fallback):
    candidate = candidate_tree(CANDIDATE, CANDIDATE_SHA)
    before = candidate_tree(BEFORE, BEFORE_SHA)
    for tree in (candidate, before):
        fallback_node(tree).body = [ast.Pass()]
    assert ast.dump(candidate, include_attributes=False) == ast.dump(before, include_attributes=False)

    original = original_request("no_evidence")
    saved = asdict(original)
    service, budget = SpyService(), RequestBudget(max_calls=2)
    legacy = replace(original, enhancement_version=None)
    assert derived_fallback(legacy, legacy, [{"evidence_id": "ev_001"}], False,
                            service, budget, request=original) is None
    assert service.observed == [] and service.blocked_adapter.calls == 0
    assert asdict(original) == saved and original.joint_checker_policy == "typed_joint_v5"
    assert original.checker_output_policy == OUTPUT_POLICY and original.checker_payload_policy == PAYLOAD_POLICY
