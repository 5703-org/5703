"""Fixed-pool Main integration, real retained classifier and failure boundaries.

No training, provider, service or database connection is performed. The Main
consumer test executes its exact AST slice with local inert host dependencies;
the JSON witness proves trace projection, not native database durability.
"""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from retrieval import chat
from retrieval import learned_budget_shadow as shadow

ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads((ROOT / "configs/retrieval/chat_cpu_learned_budget_shadow.json").read_text())
BASELINE = {k: v for k, v in POLICY.items() if k != "learned_budget_shadow"}
ADMITTED = dict.fromkeys(shadow.CHECKS, True)


def rows(count=20):
    return [
        {
            "chunk_id": f"c{i:02}",
            "text": "osmosis source text",
            "text_hash": f"h{i}",
            "score": 1.0 if i == 0 else 0.65 - i / 1000,
            "pages": [i + 1],
        }
        for i in range(count)
    ]


def fixed_ranker():
    ranker = Mock()
    ranker.rerank.side_effect = lambda query, values, *, k: list(reversed(values))
    return ranker


def test_default_off_has_no_shadow_import_artifact_read_or_timer_in_fresh_process():
    code = r"""
import builtins, json, pathlib, sys, time
from unittest.mock import patch
from retrieval import chat
policy = json.loads(pathlib.Path("configs/retrieval/chat_hybrid_minilm.json").read_text())
rows = [{"chunk_id": "a", "text": "source", "score": .2}]
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    assert "learned_budget" not in name
    return original_import(name, *args, **kwargs)
class Ranker:
    def rerank(self, query, values, *, k):
        assert k == 1
        return values
with patch("builtins.__import__", guarded_import), patch.object(pathlib.Path, "read_bytes", side_effect=AssertionError("artifact read")), patch.object(time, "perf_counter", side_effect=AssertionError("shadow timer")), patch.object(chat, "_reranker", return_value=Ranker()):
    for current in (policy, policy | {"learned_budget_shadow": None}):
        result, trace = chat.rerank_candidates("question", rows, current)
        assert result == rows and "learned_budget_shadow" not in trace
assert not any("learned_budget" in name for name in sys.modules)
print("default_off_zero_shadow_work")
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "default_off_zero_shadow_work"


def test_retained_model_exact_identity_and_lower_real_proposal_keep_original_twenty():
    from retrieval import learned_budget_candidate_v1 as candidate

    model = candidate.load_model(ROOT / shadow.MODEL_PATH)
    assert model["sha256"] == shadow.MODEL_PAYLOAD_SHA256
    assert model["iterations"][0] > 0 and any(any(w != 0 for w in row) for row in model["weights"])
    assert (
        hashlib.sha256((ROOT / shadow.MODEL_PATH).read_bytes()).hexdigest()
        == shadow.MODEL_FILE_SHA256
    )
    source = rows()
    original = deepcopy(source)
    ranker = fixed_ranker()
    with patch.object(chat, "_reranker", return_value=ranker):
        baseline, baseline_trace = chat.rerank_candidates("osmosis", source, BASELINE)
        result, trace = chat.rerank_candidates("osmosis", source, POLICY, shadow_admission=ADMITTED)
    observation = trace["learned_budget_shadow"]
    assert observation["proposed_budget"] in (5, 10) and not observation["fallback"]
    assert observation["executed_budget"] == observation["applied_candidate_budget"] == 20
    assert observation["actual_candidate_count"] == 20
    assert result == baseline and source == original
    assert (
        trace["submitted_candidate_ids"]
        == baseline_trace["submitted_candidate_ids"]
        == [r["chunk_id"] for r in original]
    )
    assert ranker.rerank.call_args.kwargs["k"] == 20
    assert ranker.rerank.call_args.args[1] == original
    assert observation["input_version"] == candidate.FEATURE_VERSION
    assert observation["model_version"] == candidate.MODEL_VERSION
    assert observation["model_sha256"] == shadow.MODEL_PAYLOAD_SHA256
    assert observation["model_file_sha256"] == shadow.MODEL_FILE_SHA256
    assert observation["shadow_overhead_ms"] >= observation["model_load_ms"] >= 0
    assert observation["decision_ms"] >= 0
    assert observation["provider_calls"] == observation["amount"] == 0
    assert observation["reduced_budget_quality_guard"].startswith("FAIL_")
    json.dumps(observation, allow_nan=False)


@pytest.mark.parametrize("count", [0, 3, 19])
def test_available_pool_is_never_padded_or_reduced(count):
    source = rows(count)
    ranker = fixed_ranker()
    with patch.object(chat, "_reranker", return_value=ranker):
        result, trace = chat.rerank_candidates("osmosis", source, POLICY, shadow_admission=ADMITTED)
    assert len(result) == count
    assert trace["learned_budget_shadow"]["actual_candidate_count"] == count
    assert trace["learned_budget_shadow"]["fallback"]
    if count:
        assert ranker.rerank.call_args.kwargs["k"] == count
    else:
        ranker.rerank.assert_not_called()


@pytest.mark.parametrize("case", ["missing", "corrupt", "different_identity", "incompatible"])
def test_artifact_failures_preserve_fixed_pool_and_record_fallback(case):
    from retrieval import learned_budget_candidate_v1 as candidate

    model = candidate.load_model(ROOT / shadow.MODEL_PATH)
    load = patch.object(candidate, "load_model", side_effect=FileNotFoundError())
    reads = patch.object(Path, "read_bytes", return_value=b"changed")
    if case == "corrupt":
        load = patch.object(candidate, "load_model", side_effect=ValueError("corrupt"))
    elif case == "incompatible":
        load = patch.object(candidate, "load_model", side_effect=ValueError("version"))
    elif case == "different_identity":
        load = patch.object(candidate, "load_model", return_value=model)
    with load, reads, patch.object(chat, "_reranker", return_value=fixed_ranker()):
        result, trace = chat.rerank_candidates("osmosis", rows(), POLICY, shadow_admission=ADMITTED)
    observation = trace["learned_budget_shadow"]
    assert len(result) == 20 and observation["fallback"]
    assert observation["proposed_budget"] == observation["baseline_budget"] == 20
    assert observation["reason"].startswith("model_unavailable")
    assert observation["executed_budget"] == 20


@pytest.mark.parametrize(
    "query,change",
    [
        ("", {}),
        ("osmosis", {"score": None}),
        ("osmosis", {"score": float("nan")}),
        ("osmosis", {"text": ""}),
    ],
)
def test_invalid_features_only_fall_back_and_never_change_reranker_input(query, change):
    source = rows()
    source[0].update(change)
    ranker = fixed_ranker()
    with patch.object(chat, "_reranker", return_value=ranker):
        result, trace = chat.rerank_candidates(query, source, POLICY, shadow_admission=ADMITTED)
    assert len(result) == 20
    observation = trace["learned_budget_shadow"]
    assert observation["fallback"] and observation["reason"] == "missing_or_invalid_inputs"
    assert ranker.rerank.call_args.kwargs["k"] == 20


@pytest.mark.parametrize("check", sorted(shadow.CHECKS))
def test_denied_host_check_stops_observation_without_reading_model(check):
    admission = ADMITTED | {check: False}
    with (
        patch.object(Path, "read_bytes", side_effect=AssertionError("denied model read")),
        patch.object(chat, "_reranker", return_value=fixed_ranker()),
    ):
        result, trace = chat.rerank_candidates(
            "osmosis", rows(), POLICY, shadow_admission=admission
        )
    observation = trace["learned_budget_shadow"]
    assert len(result) == 20 and observation["observation_stopped"]
    assert observation["action"] == "stop" and observation["proposed_budget"] is None
    assert observation["applied_candidate_budget"] == 20 and observation["fallback"]


def test_direct_rerank_without_host_context_keeps_baseline_and_stops_observer():
    with (
        patch.object(Path, "read_bytes", side_effect=AssertionError("unadmitted artifact read")),
        patch.object(chat, "_reranker", return_value=fixed_ranker()),
    ):
        result, trace = chat.rerank_candidates("osmosis", rows(), POLICY)
    observation = trace["learned_budget_shadow"]
    assert len(result) == 20 and observation["observation_stopped"]
    assert (
        observation["reason"] == "host_hard_constraint" and observation["proposed_budget"] is None
    )
    assert not any(observation["boundary"][name] for name in shadow.CHECKS)


def test_shadow_configuration_rejects_budget_mutation_and_experimental_modes():
    rule = POLICY["learned_budget_shadow"]["rule_policy"]
    experimental = json.loads((ROOT / "configs/retrieval/chat_cpu_shadow_budget.json").read_text())
    changes = [
        POLICY | {"candidate_count": 10},
        POLICY
        | {
            "learned_budget_shadow": POLICY["learned_budget_shadow"]
            | {"mode": "offline_experimental"}
        },
        POLICY
        | {
            "learned_budget_shadow": POLICY["learned_budget_shadow"]
            | {"rule_policy": rule | {"mode": "experimental"}}
        },
        experimental
        | {
            "adaptive_policy": rule | {"mode": "experimental"},
            "learned_budget_shadow": POLICY["learned_budget_shadow"],
        },
    ]
    for policy in changes:
        with (
            pytest.raises(ValueError),
            patch.object(Path, "read_bytes", side_effect=AssertionError("model read")),
        ):
            chat.validate_policy(policy)


def test_host_admission_uses_current_execution_budget_checker_and_source_receipt():
    req = SimpleNamespace(
        state="processing",
        mode="interactive_chat",
        owner_id="owner",
        release_id="release",
        budget={},
        command={"reliability_policy": "evidence_reliability_v5"},
    )
    job = SimpleNamespace(state="running", execution_token="token")
    assert (
        shadow.host_admission(
            req, job, "token", elapsed_active_seconds=1, source_visibility_verified=True
        )
        == ADMITTED
    )
    assert not shadow.host_admission(
        req, job, "wrong", elapsed_active_seconds=1, source_visibility_verified=True
    )["permission_granted"]
    assert not shadow.host_admission(
        req, job, "token", elapsed_active_seconds=180, source_visibility_verified=True
    )["amount_approved"]
    assert not shadow.host_admission(
        req, job, "token", elapsed_active_seconds=1, source_visibility_verified=False
    )["source_visibility_verified"]
    req.budget = {"format_repairs": 2}
    assert not shadow.host_admission(
        req, job, "token", elapsed_active_seconds=1, source_visibility_verified=True
    )["revision_limit_respected"]
    req.command = {}
    assert not shadow.host_admission(
        req, job, "token", elapsed_active_seconds=1, source_visibility_verified=True
    )["quality_gate_required"]


def test_main_ood_and_cooperative_timeout_use_rule_fallback_without_candidate_reduction():
    from retrieval import learned_budget_candidate_v1 as candidate

    source = rows()
    source[1]["score"] = 0.2
    with patch.object(chat, "_reranker", return_value=fixed_ranker()):
        result, trace = chat.rerank_candidates("osmosis", source, POLICY, shadow_admission=ADMITTED)
    assert (
        len(result) == 20
        and trace["learned_budget_shadow"]["reason"] == "out_of_distribution_range"
    )
    original = candidate.choose_budget
    times = iter([0.0, 0.0, 0.011, 0.011])

    def expired(query, supplied, model, rule, **options):
        return original(query, supplied, model, rule, **options, clock=lambda: next(times))

    with (
        patch.object(candidate, "choose_budget", side_effect=expired),
        patch.object(chat, "_reranker", return_value=fixed_ranker()),
    ):
        result, trace = chat.rerank_candidates("osmosis", rows(), POLICY, shadow_admission=ADMITTED)
    observation = trace["learned_budget_shadow"]
    assert len(result) == 20 and observation["reason"] == "decision_timeout"
    assert observation["fallback"] and observation["timeout_ms"] == 10


def test_model_pins_are_frozen_at_normal_policy_load_and_changed_file_cannot_replace_them(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(POLICY), encoding="utf-8")
    frozen = chat.load_policy(path)
    changed = deepcopy(POLICY)
    changed["learned_budget_shadow"]["model_payload_sha256"] = "0" * 64
    path.write_text(json.dumps(changed), encoding="utf-8")
    assert frozen["learned_budget_shadow"]["model_payload_sha256"] == shadow.MODEL_PAYLOAD_SHA256
    assert frozen["learned_budget_shadow"]["model_version"] == shadow.MODEL_VERSION
    assert frozen["learned_budget_shadow"]["input_version"] == shadow.INPUT_VERSION
    with pytest.raises(ValueError):
        chat.load_policy(path)


def test_actual_main_consumer_calls_shadow_after_retrieval_and_preserves_json_trace():
    source = ast.parse(
        (ROOT / "backend/app/modules/answering/service.py").read_text(encoding="utf-8")
    )
    execute = next(
        n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "execute_answer"
    )
    nodes = next(n.body for n in execute.body if isinstance(n, ast.With))
    retrieval_if = next(
        n
        for n in nodes
        if isinstance(n, ast.If)
        and any(isinstance(c, ast.Name) and c.id == "retrieval_started" for c in ast.walk(n))
    )
    start = next(
        i
        for i, n in enumerate(retrieval_if.body)
        if isinstance(n, ast.Assign)
        and any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "retrieve"
            for c in ast.walk(n)
        )
    )
    stop = next(
        i
        for i, n in enumerate(retrieval_if.body[start:], start)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "whole_rows" for t in n.targets)
    )
    projection = next(
        n
        for n in nodes
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == "trace" for t in n.targets)
        and any(
            isinstance(k, ast.Constant) and k.value == "retrieval_candidates" for k in ast.walk(n)
        )
    )
    req = SimpleNamespace(
        state="processing",
        mode="interactive_chat",
        owner_id="owner",
        release_id="release",
        budget={},
        command={"reliability_policy": "evidence_reliability_v5"},
        trace={"old": "retained"},
    )
    namespace = dict(
        req=req,
        job=SimpleNamespace(state="running", execution_token="token"),
        token="token",
        time=SimpleNamespace(perf_counter=lambda: 1.0),
        start=0.0,
        query="osmosis",
        question="osmosis",
        db=object(),
        frozen_policy=deepcopy(POLICY),
        runtime_options={},
        cache_options={},
        scope_options={},
        selection_policy=None,
        candidates=[],
        inherited_trace=None,
        retrieve=Mock(return_value=rows()),
        rerank_candidates=chat.rerank_candidates,
        prepared=None,
        understanding=None,
        progress_plan=None,
        strategy="retrieve",
        input_preparation_ms=0.0,
        stage_timing={},
    )
    with patch.object(chat, "_reranker", return_value=fixed_ranker()):
        exec(
            compile(
                ast.Module(body=retrieval_if.body[start:stop], type_ignores=[]),
                "Main-retrieval-slice",
                "exec",
            ),
            namespace,
        )
    assert namespace["retrieve"].call_args.kwargs["top_k"] == 20
    assert namespace["retrieval_execution"]["learned_budget_shadow"]["proposed_budget"] in (5, 10)
    namespace["candidates"] = namespace["retrieved"]
    exec(
        compile(ast.Module(body=[projection], type_ignores=[]), "Main-trace-projection", "exec"),
        namespace,
    )
    serialized = json.dumps(req.trace, allow_nan=False)
    restored = json.loads(serialized)
    assert restored["old"] == "retained"
    assert (
        restored["retrieval_execution"]["learned_budget_shadow"]["model_sha256"]
        == shadow.MODEL_PAYLOAD_SHA256
    )
    assert len(restored["retrieval_candidates"]) == 20
    # No future outcome, answer key or reference identity is admitted as a feature.
    assert set(restored["retrieval_execution"]["learned_budget_shadow"]["features"]) == {
        "complex",
        "lexical_overlap",
        "relative_gap",
        "candidate_count",
    }
