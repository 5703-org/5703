"""Run a bounded, offline ordering/source-availability study of 13 wire items.

No retrieval or model is invoked. Existing Main BM25/tokenizer definitions are
AST-extracted without importing embedding/runtime/model modules. All selected
source fragments remain separate immutable records. Fragment union text is
used only as the lexical ranking input, not relabelled as whole retrieved chunks.
"""

from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from heapq import nsmallest
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time

def load_pure_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference_module = load_pure_module(Path(__file__).resolve().parent / "coverage_reference06.py", "offline_coverage_reference06")
evaluate = reference_module.evaluate
run_controls = reference_module.run_controls


MAIN = Path(r"E:\5703\learning-assistant")
W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
D = W / "5703-week10-native-pair-20261009-01/diagnostic-preparation"
A = D / "attempt-evaluation-conditional-preparation01"
R = A / "retained-checker-diagnostic-preparation01"
OUT = Path(__file__).resolve().parent.parent
DECODED = R / "fresh-targeted-patch-recheck-preparation01/compound-predicate-recheck05/three-predicate-final01/PREDICATE_SCOPED_DECODED_INPUT05.json"
ATTRIBUTION = A / "actual-checker-repaired04/private-diagnostic/generation-final-outcome01.json"
REQUIREMENTS = OUT / "independent-predicate-requirements06.json"
ROOT_HELPER = OUT / "root-module06/fragment_coverage_v1.py"
TOP_K = [1, 3, 5, 10, 13]


def deny_external(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system"}:
        raise RuntimeError(f"Offline study forbids external operation: {event}")


sys.addaudithook(deny_external)


def read(path, pins):
    raw = path.read_bytes()
    pins.append({"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return json.loads(raw)


def source_definitions(pins):
    namespace = {"Counter": Counter, "deepcopy": deepcopy, "math": math, "nsmallest": nsmallest, "re": re}
    selections = [
        ("retrieval/embedding.py", "tokens", ast.FunctionDef),
        ("retrieval/ranking.py", "bm25", ast.FunctionDef),
        ("retrieval/lexical.py", "LexicalIndex", ast.ClassDef),
    ]
    for relative, name, node_type in selections:
        path = MAIN / relative
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        tree = ast.parse(text, filename=str(path))
        nodes = [node for node in tree.body if isinstance(node, node_type) and node.name == name]
        if len(nodes) != 1:
            raise ValueError(f"Missing or ambiguous actual source definition: {name}")
        module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
        exact_definition = ast.get_source_segment(text, nodes[0])
        pins.append({
            "path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "selected_definition": name,
            "definition_sha256": hashlib.sha256(exact_definition.encode()).hexdigest(),
            "entire_module_imported": False,
        })
        exec(compile(module, str(path), "exec"), namespace)
    return namespace["tokens"], namespace["bm25"], namespace["LexicalIndex"]


def build_pool(decoded, attribution, requirements, tokens):
    fragments = decoded["SOURCE_FRAGMENTS"]
    assert len(fragments) == 67 and len(decoded["CLAIMS"]) == 10
    assert len(decoded["question"]) == 86
    assert not any("score" in key for row in fragments for key in row)
    aliases = attribution["checks"][0]["fragment_aliases"]
    original_by_id = {row["fragment_id"]: row for row in attribution["attribution"]["fragments"]}
    assert len(aliases) == len(original_by_id) == 67
    reviewer_mapping = {row["alias"]: row for row in requirements["fragment_mapping"]}
    assert len(reviewer_mapping) == 67
    pool = {}
    mapped = []
    for position, fragment in enumerate(fragments):
        alias = fragment["fragment_id"]
        actual = original_by_id[aliases[alias]]
        reviewed = reviewer_mapping[alias]
        assert fragment["exact_text"] == actual["exact_text"] == reviewed["exact_text"]
        assert fragment["evidence_id"] == actual["evidence_id"] == reviewed["evidence_id"]
        assert reviewed["actual_fragment_id"] == actual["fragment_id"]
        assert reviewed["chunk_id"] == actual["chunk_id"]
        assert reviewed["source_unit_id"] == actual["source_unit_id"]
        assert reviewed["page"] == actual["page"]
        assert hashlib.sha256(fragment["exact_text"].encode()).hexdigest() == actual["text_hash"] == reviewed["text_hash"]
        mapped_row = deepcopy(actual) | {"alias": alias, "wire_fragment_order": position}
        mapped.append(mapped_row)
        eid = fragment["evidence_id"]
        if eid not in pool:
            pool[eid] = {
                "evidence_id": eid, "chunk_id": actual["chunk_id"],
                "retained_wire_order": len(pool) + 1, "fragments": [],
            }
        assert pool[eid]["chunk_id"] == actual["chunk_id"]
        pool[eid]["fragments"].append(mapped_row)
    items = list(pool.values())
    assert len(items) == 13
    assert len({item["chunk_id"] for item in items}) == 13
    for item in items:
        item["text"] = "\n".join(fragment["exact_text"] for fragment in item["fragments"])
        item["rank_text_sha256"] = hashlib.sha256(item["text"].encode()).hexdigest()
        item["rank_text_chars"] = len(item["text"])
        item["rank_text_lexical_tokens"] = len(tokens(item["text"]))
        item["fragment_aliases"] = [f["alias"] for f in item["fragments"]]
    return items, mapped


def main_controls(tokens, bm25, index_type, items, query):
    controls = []
    reference = bm25(query, items, k=13, k1=1.5, b=0.75)
    index = index_type(items, k1=1.5, b=0.75)
    indexed = index.search(query, k=13)
    assert [(r["chunk_id"], r["score"]) for r in reference] == [(r["chunk_id"], r["score"]) for r in indexed]
    controls.append({"name": "actual Main index and reference BM25 exact order/float scores equal", "PASS": True})
    for k in TOP_K:
        assert [r["chunk_id"] for r in index.search(query, k=k)] == [r["chunk_id"] for r in indexed[:k]]
        controls.append({"name": f"actual pool top{k} preserves prefix of full ranking", "PASS": True})
    tie_rows = [
        {"chunk_id": "z", "text": "beta"}, {"chunk_id": "a", "text": "alpha"},
        {"chunk_id": "m", "text": "gamma"},
    ]
    tied = index_type(tie_rows).search("nonexistenttoken", k=3)
    assert [r["chunk_id"] for r in tied] == ["a", "m", "z"]
    assert [r["score"] for r in tied] == [0.0] * 3
    assert tied == bm25("nonexistenttoken", tie_rows, k=3)
    controls.append({"name": "zero-score tie follows original chunk-ID rule", "PASS": True})
    for name, operation in [
        ("duplicate candidate identities rejected", lambda: index_type([tie_rows[0], tie_rows[0]])),
        ("invalid k rejected", lambda: index.search(query, k=0)),
    ]:
        try:
            operation()
        except ValueError:
            controls.append({"name": name, "PASS": True})
        else:
            raise AssertionError(name)
    assert index_type([]).search(query, k=1) == []
    controls.append({"name": "empty pool remains empty", "PASS": True})
    assert tokens("Light-dependent ATP/NADPH") == ["light", "dependent", "atp", "nadph"]
    controls.append({"name": "actual source tokenizer preserves original lexical normalization", "PASS": True})
    return indexed, controls


def budget_controls(mapped, requirements):
    by_alias = {row["alias"]: row for row in mapped}
    first, second = by_alias["F054"], by_alias["F055"]
    assert first["evidence_id"] == second["evidence_id"]
    allowed = [row["alias"] for row in mapped]
    scoped = [{"id": "budget_compound", "kind": "claim_support", "complete_support_bundles": [["F054", "F055"]]}]
    assert evaluate(scoped, selected_fragment_ids=["F054"], allowed_fragment_ids=allowed)[0]["covered"] is False
    assert evaluate(scoped, selected_fragment_ids=["F054", "F055"], allowed_fragment_ids=allowed)[0]["covered"] is True
    return [
        {"name": "synthetic whole-fragment budget leaving F054 only fails F054 AND F055", "PASS": True,
         "whole_fragment_char_allowance": len(first["exact_text"]), "production_budget_changed": False},
        {"name": "synthetic budget with both complete exact fragments passes set coverage", "PASS": True,
         "whole_fragment_char_allowance": len(first["exact_text"]) + 1 + len(second["exact_text"]),
         "scientific_entailment_inferred_from_chars": False, "production_budget_changed": False},
    ]


def root_adapter(root_measure, requirements, *, selected_fragment_ids, allowed_fragment_ids):
    data = root_measure(selected_fragment_ids, requirements, known_fragment_ids=allowed_fragment_ids)
    return [{"id": row["id"], "kind": row["kind"], "covered": row["covered"],
        "missing_ids_per_complete_bundle": row["missing_fragment_ids_by_alternative"]} for row in data["requirements"]]


def stage(arm, ordered, k, generic, allowed, tokens, root_measure):
    selected = ordered[:k]
    selected_aliases = [alias for item in selected for alias in item["fragment_aliases"]]
    reference = evaluate(generic, selected_fragment_ids=selected_aliases, allowed_fragment_ids=allowed)
    authoritative = root_measure(selected_aliases, generic, known_fragment_ids=allowed)
    rows = authoritative["requirements"]
    assert [(r["id"], r["kind"], r["covered"], r["missing_ids_per_complete_bundle"]) for r in reference] == [
        (r["id"], r["kind"], r["covered"], r["missing_fragment_ids_by_alternative"]) for r in rows]
    by_kind = {}
    for kind in sorted({row["kind"] for row in rows}):
        group = [row for row in rows if row["kind"] == kind]
        by_kind[kind] = {
            "covered_count": sum(row["covered"] for row in group), "requirement_count": len(group),
            "uncovered_requirement_ids": [row["id"] for row in group if not row["covered"]],
        }
    projection = "\n".join(item["text"] for item in selected)
    return {
        "arm": arm, "k": k, "selected_evidence_ids": [item["evidence_id"] for item in selected],
        "selected_actual_chunk_ids": [item["chunk_id"] for item in selected],
        "selected_fragment_aliases": selected_aliases,
        "selected_actual_fragment_ids": [fragment["fragment_id"] for item in selected for fragment in item["fragments"]],
        "body_projection_policy": "All unchanged separate fragments of each selected wire evidence item; no truncation",
        "projection_chars_including_newline_separators": len(projection),
        "projection_lexical_tokens": len(tokens(projection)),
        "projection_sha256": hashlib.sha256(projection.encode()).hexdigest(),
        "projection_is_a_model_submission": False,
        "production_context_budget_or_window_changed": False,
        "all_selected_exact_fragment_hashes_validated": True,
        "source_set_coverage_by_kind": by_kind, "per_requirement": rows,
        "Root_generic_helper_and_independent_reference_exact_coverage_and_missing_IDs_equal": True,
        "semantic_model_or_human_accuracy": None,
    }


def write_new(name, data):
    path = OUT / name
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    return path


def main():
    started = time.perf_counter()
    pins = []
    definitions_pins = []
    tokens, bm25, index_type = source_definitions(definitions_pins)
    decoded = read(DECODED, pins)
    attribution = read(ATTRIBUTION, pins)
    requirements = read(REQUIREMENTS, pins)
    root_bytes = ROOT_HELPER.read_bytes()
    root_pin = {"path": str(ROOT_HELPER), "bytes": len(root_bytes), "sha256": hashlib.sha256(root_bytes).hexdigest()}
    assert root_pin["sha256"] == "91dc728a5c2c349355461ca46859cba8ac18f1abc41bf544e53309441a932303"
    root_module = load_pure_module(ROOT_HELPER, "root_fragment_coverage_v1")
    root_measure = root_module.measure_fragment_coverage
    generic = requirements["requirements"]
    assert len(generic) == 14
    assert sum(row["kind"] == "claim_support" for row in generic) == 10
    assert sum(row["kind"] == "question_facet" for row in generic) == 4
    items, mapped = build_pool(decoded, attribution, requirements, tokens)
    allowed = [row["alias"] for row in mapped]
    assert set(allowed) == set(requirements["allowed_fragment_aliases"])
    bm25_order, rank_controls = main_controls(tokens, bm25, index_type, items, decoded["question"])
    independent_controls = run_controls()
    root_controls = run_controls(evaluator=lambda requirements, **kwargs: root_adapter(root_measure, requirements, **kwargs))
    assert independent_controls == root_controls
    controls = [{**row, "independent_reference_and_Root_generic_helper_both_PASS": True} for row in root_controls] + rank_controls + budget_controls(mapped, requirements)
    stages = [stage(arm, ordering, k, generic, allowed, tokens, root_measure) for arm, ordering in [
        ("retained_wire_evidence_order", items), ("candidate_local_Main_BM25_fragment_union_text", bm25_order),
    ] for k in TOP_K]
    full = [s for s in stages if s["k"] == 13]
    assert len(full) == 2
    assert full[0]["source_set_coverage_by_kind"] == full[1]["source_set_coverage_by_kind"]
    expected_declared = {kind: sum(bool(r["complete_support_bundles"]) for r in generic if r["kind"] == kind)
        for kind in {r["kind"] for r in generic}}
    for kind, group in full[0]["source_set_coverage_by_kind"].items():
        assert group["covered_count"] == expected_declared[kind]
    controls.append({"name": "full unchanged source pool covers all declared complete bundles equally under both orders; no support declaration stays uncovered", "PASS": True})
    pool_input = {
        "status": "ACTUAL_FROZEN_BIOLOGY_WIRE_POOL_RECONSTRUCTED_OFFLINE",
        "question": decoded["question"], "question_chars": 86,
        "source_pool": "13 actual checker-wire evidence items containing67 exact retained source fragments",
        "retrieval20_reconstructed": False, "full_chunk_texts_reconstructed": False,
        "retained_dense_scores_available": False, "RRF_computed": False,
        "rank_text_policy": "Join each item's exact fragments with one newline only for Main lexical ranking",
        "bm25_parameters": {"k1": 1.5, "b": 0.75},
        "actual_Python_version": sys.version,
        "source_input_pins": pins, "exact_Main_definition_pins": definitions_pins,
        "Root_generic_coverage_helper_pin": root_pin,
        "items": items,
        "analyst_requirements_are_human_Gold": False,
    }
    result = {
        "status": "ACTUAL_FREE_OFFLINE_BIOLOGY_ORDERING_SOURCE_COVERAGE_COMPLETE",
        "at_UTC": datetime.now(timezone.utc).isoformat(),
        "scheduled_cells": 10, "completed_cells": len(stages),
        "pool_evidence_count": 13, "pool_fragment_count": 67,
        "repaired_claim_count": 10, "analyst_question_facet_count": 4,
        "query_lexical_tokens": len(tokens(decoded["question"])),
        "source_input_pins": pins, "exact_Main_definition_pins": definitions_pins,
        "Root_generic_coverage_helper_pin": root_pin,
        "ranks": {
            "retained_wire_evidence_order": [{"rank": i + 1, "evidence_id": item["evidence_id"],
                "chunk_id": item["chunk_id"], "score": None, "score_type": None} for i, item in enumerate(items)],
            "candidate_local_Main_BM25_fragment_union_text": [{"rank": i + 1, "evidence_id": item["evidence_id"],
                "chunk_id": item["chunk_id"], "score": item["score"], "score_type": item["score_type"]} for i, item in enumerate(bm25_order)],
        },
        "stages": stages,
        "controls_PASS_count": len(controls), "controls_fail_count": 0,
        "new_local_offline_analysis_elapsed_ms_not_answer_latency": round((time.perf_counter() - started) * 1000, 3),
        "operations": {"API_POSTs": 0, "network_calls": 0, "database_reads_or_writes": 0,
            "credential_seed_binder_reads": 0, "model_loads": 0, "dependency_installs": 0,
            "Gold_reads": 0, "Main_writes": 0, "production_source_gate_or_label_mutations": 0},
        "support_set_coverage_scope": "Analyst-defined complete source availability, conditional on reviewer bundles; not automatic entailment",
        "scientific_or_citation_model_gates_executed": False,
        "native_publication_or_browser_full_answer_verified": False,
        "full_corpus_recall": None, "human_gold_retrieval_metrics": None,
        "answer_accuracy_or_learning_gain": None, "answer_latency_ms": None,
        "production_default_recommendation": None, "project_complete": False,
        "new_re_review_denial_preserved": "ROOT_REPORTED_RE_REVIEW_DENIAL06.json",
        "paid_action_retry_or_protected_native_field_bypass": False,
    }
    for name in ["OFFLINE_BIOLOGY_WIRE_POOL_INPUT06.json", "ACTUAL_OFFLINE_RANKING_COVERAGE06.json", "ACTUAL_FREE_OFFLINE_CONTROLS06.json"]:
        if (OUT / name).exists():
            raise FileExistsError(f"Preserve existing experiment artifact: {name}")
    write_new("OFFLINE_BIOLOGY_WIRE_POOL_INPUT06.json", pool_input)
    write_new("ACTUAL_OFFLINE_RANKING_COVERAGE06.json", result)
    write_new("ACTUAL_FREE_OFFLINE_CONTROLS06.json", {"status": "ACTUAL_FREE_CONTROLS_PASS", "controls": controls,
        "model_gates_or_human_Gold_tested": False, "actual_sources_mutated": False})
    print(json.dumps({"status": result["status"], "cells": len(stages), "controls_PASS": len(controls),
        "curves": [{"arm": s["arm"], "k": s["k"], "coverage": s["source_set_coverage_by_kind"]} for s in stages],
        "API_POSTs": 0, "database_operations": 0}, indent=2))


if __name__ == "__main__":
    main()
