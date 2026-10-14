"""Prepared synthetic stdlib tests. No Main imports, IO, API, DB or fixtures.

These tests are intentionally NOT executed by their authoring agent. Root may
review and explicitly run them in the designated workspace later.
"""

from copy import deepcopy
import json
import unittest

from generation.claim_feedback_transport_v1 import (
    BODY, DRAFT, HEADER, VERSION, FULL, CONTEXT_PREFIX, FeedbackEncodingError,
    canonical_bytes, canonical_hash, decode_claim_feedback, encode_claim_feedback,
)


def strict_snapshot(value, *, object_order=True):
    if type(value) is dict:
        keys = list(value) if object_order else sorted(value)
        return (dict, [(key, strict_snapshot(value[key], object_order=object_order)) for key in keys])
    if type(value) is list:
        return (list, [strict_snapshot(item, object_order=object_order) for item in value])
    if type(value) is float:
        return (float, value.hex())
    return (type(value), value)


def fixture(protected=True, quotes=True):
    sentences = [f"Claim {index}: " + (f"exact Unicode 🧬 中\nvalue {index}; " * 45) for index in range(4)]
    answer = "\n\n".join(sentences)
    claims, start = [], 0
    for index, text in enumerate(sentences):
        claims.append({"text": text, "claim_id": f"claim_stable_{index}", "end": start + len(text),
                       "answer_field": "answer_text", "start": start, "evidence_ids": ["ev_001"],
                       "unknown": {"z": [True, 1, 1.0, -0.0, None], "a": "literal"}})
        start += len(text) + 2
    source = "complete source 🧬 paragraph with exact line endings\r\n" * 100
    selected = [{"text": "prefix\n" + source + "\nsuffix", "evidence_id": "ev_001", "unknown": 2}]
    fragments = [{"fragment_id": "ev_001#public_full_fragment", "evidence_id": "ev_001",
                  "exact_text": source, "complete_block": True, "block_kind": "paragraph"}]
    messages = [{"role": "system", "content": CONTEXT_PREFIX + json.dumps(
        {"CURRENT_EVIDENCE": selected, "unknown": ["kept"]}, ensure_ascii=False, sort_keys=True)}]
    feedback = {"draft": {"short_answer": "", "answer_text": answer, "unknown": {"z": 1, "a": 2}},
                "original_claims": claims,
                "judgment": {"issues": [{"reason": "keep exact error, condition and repair instruction", "code": "X"}]},
                "structural_issues": [{"z": True, "a": 1}], "teaching_policy": {"exact": "instruction"},
                "repair_plan": {"append_answer_text": ""},
                "source_ref_version": "repair_feedback_v2",
                "source_repair_candidates": [{"fragment_id": fragments[0]["fragment_id"],
                                               "evidence_id": "ev_001", "text_ref": [7, 7 + len(source)]}],
                "unknown": {"z": {"quote": "must not rewrite", "source_span": ["literal", 0, 2]},
                            "a": [False, 0, 0.0]}}
    if protected:
        feedback["protected_exact_claims"] = deepcopy(claims[:3])
        feedback["editable_claim_ids"] = [claims[3]["claim_id"]]
    if quotes:
        feedback["source_relation_assessment"] = {
            "version": "source_relation_v2", "claims": [{"claim_id": claims[0]["claim_id"],
                "obligations": [{"unit_id": "u_1", "claim_quote": sentences[0], "claim_start": 0,
                                 "claim_end": len(sentences[0]), "defect_codes": ["EXACT_ERROR"],
                                 "source_quotes": [{"evidence_id": "ev_001", "fragment_id": "F001",
                                                    "quote": source, "unknown": {"z": 3, "a": 4}}]}]}]}
    options = {"messages": messages, "selected": selected, "fragments": fragments,
               "aliases": {"F001": fragments[0]["fragment_id"]}}
    return feedback, options


class LosslessClaimFeedback27Tests(unittest.TestCase):
    def assert_round_trip(self, feedback, options, expect_encoded=True):
        before = strict_snapshot(feedback)
        options_before = strict_snapshot(options)
        payload, proof = encode_claim_feedback(feedback, **options)
        self.assertEqual(before, strict_snapshot(feedback))
        self.assertEqual(options_before, strict_snapshot(options))
        encoded = proof["encoding"] == VERSION
        self.assertEqual(encoded, expect_encoded)
        # Existing transport canonicalizes object keys; preserve exact scalar
        # types/values, key sets and list order across actual sorted transport.
        wire = json.loads(canonical_bytes(payload)) if encoded else payload
        restored = decode_claim_feedback(wire, encoded=encoded, **options)
        self.assertEqual(strict_snapshot(feedback, object_order=False),
                         strict_snapshot(restored, object_order=False))
        self.assertEqual(canonical_hash(feedback), canonical_hash(restored))
        self.assertEqual(proof["original_sha256"], proof["restored_sha256"])
        self.assertEqual(proof["transmitted_utf8_bytes"], len(canonical_bytes(payload)))
        if encoded:
            self.assertLess(proof["transmitted_utf8_bytes"], proof["original_utf8_bytes"])
            self.assertGreater(proof["saved_utf8_bytes"], 0)
        else:
            self.assertEqual(proof["encoding"], FULL)
            self.assertEqual(proof["saved_utf8_bytes"], 0)
        return payload, proof

    def test_protected_branch_exact_complete_round_trip(self):
        feedback, options = fixture(protected=True)
        payload, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["claim_span_count"], 4)
        self.assertEqual(proof["protected_claim_ref_count"], 3)
        self.assertEqual(proof["source_quote_ref_count"], 1)
        self.assertEqual(payload[BODY]["source_repair_candidates"], feedback["source_repair_candidates"])
        self.assertEqual(payload[BODY]["source_ref_version"], feedback["source_ref_version"])

    def test_nonprotected_branch_exact_complete_round_trip(self):
        feedback, options = fixture(protected=False)
        _, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["protected_claim_ref_count"], 0)
        self.assertEqual(proof["source_quote_ref_count"], 1)

    def test_claim_only_two_branches(self):
        for protected in (False, True):
            with self.subTest(protected=protected):
                feedback, options = fixture(protected=protected, quotes=False)
                self.assert_round_trip(feedback, {})

    def test_unknown_values_and_protected_extra_fields_are_literal(self):
        feedback, options = fixture()
        feedback["protected_exact_claims"][0]["extra_unknown"] = {"claim_ref": "literal", "z": 1}
        payload, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["protected_claim_ref_count"], 2)
        self.assertEqual(payload[BODY]["protected_exact_claims"][0], feedback["protected_exact_claims"][0])
        self.assertEqual(payload[BODY]["unknown"], feedback["unknown"])

    def test_typed_unknown_values_and_canonical_object_keys_preserved(self):
        feedback, options = fixture()
        feedback["unknown"]["ordered"] = {"z": True, "a": 1, "m": 1.0, "n": -0.0}
        self.assert_round_trip(feedback, options)

    def test_collision_full_fallback_does_not_mutate(self):
        feedback, options = fixture()
        feedback["original_claims"][1]["claim_id"] = feedback["original_claims"][0]["claim_id"]
        _, proof = self.assert_round_trip(feedback, options, expect_encoded=False)
        self.assertEqual(proof["reason"], "CLAIM_ID_COLLISION")

    def test_wrapper_collision_full_branch_is_explicitly_decoded(self):
        feedback, options = fixture()
        feedback[HEADER] = {"version": VERSION, "unknown": "literal"}
        self.assert_round_trip(feedback, options, expect_encoded=False)

    def test_invalid_claim_spans_remain_full_text(self):
        for bad in ({"start": True}, {"end": 1.0}, {"answer_field": "unknown"},
                    {"text": "changed"}, {"start": -1}):
            with self.subTest(bad=bad):
                feedback, options = fixture(protected=False)
                feedback["original_claims"][0].update(bad)
                payload, proof = self.assert_round_trip(feedback, options)
                self.assertEqual(proof["claim_span_count"], 3)
                self.assertEqual(payload[BODY]["original_claims"][0], feedback["original_claims"][0])

    def test_repeated_text_uses_explicit_offsets_and_missing_span_is_literal(self):
        feedback, options = fixture(protected=False)
        text = feedback["original_claims"][0]["text"]
        feedback["draft"]["answer_text"] = text + "\n" + text
        feedback["original_claims"] = [deepcopy(feedback["original_claims"][0]) for _ in range(2)]
        second = feedback["original_claims"][1]
        second.update(claim_id="claim_repeated_second", start=len(text) + 1, end=2 * len(text) + 1)
        _, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["claim_span_count"], 2)
        del second["start"]
        payload, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["claim_span_count"], 1)
        self.assertEqual(payload[BODY]["original_claims"][1]["text"], text)

    def test_source_quote_direct_identity_and_alias_both_work(self):
        for use_alias in (False, True):
            feedback, options = fixture()
            if not use_alias:
                feedback["source_relation_assessment"]["claims"][0]["obligations"][0]["source_quotes"][0]["fragment_id"] = options["fragments"][0]["fragment_id"]
            _, proof = self.assert_round_trip(feedback, options)
            self.assertEqual(proof["source_quote_ref_count"], 1)

    def test_wrong_owner_unmatched_and_ambiguous_quotes_stay_verbatim(self):
        for condition in ("wrong_owner", "unmatched", "ambiguous"):
            with self.subTest(condition=condition):
                feedback, options = fixture()
                row = feedback["source_relation_assessment"]["claims"][0]["obligations"][0]["source_quotes"][0]
                if condition == "wrong_owner":
                    row["evidence_id"] = "ev_other"
                elif condition == "unmatched":
                    row["quote"] += "changed"
                else:
                    options["selected"][0]["text"] += row["quote"]
                    options["messages"][0]["content"] = CONTEXT_PREFIX + json.dumps({"CURRENT_EVIDENCE": options["selected"]})
                payload, proof = self.assert_round_trip(feedback, options)
                self.assertEqual(proof["source_quote_ref_count"], 0)
                self.assertEqual(payload[BODY]["source_relation_assessment"], feedback["source_relation_assessment"])

    def test_context_only_refs_preserve_unmapped_ids_without_ownership_claims(self):
        for condition in ("unmapped", "no_fragment_map"):
            with self.subTest(condition=condition):
                feedback, options = fixture()
                row = feedback["source_relation_assessment"]["claims"][0]["obligations"][0]["source_quotes"][0]
                if condition == "unmapped":
                    row["fragment_id"] = "original_unknown_fid_unchanged"
                else:
                    options["fragments"] = None
                    options["aliases"] = None
                payload, proof = self.assert_round_trip(feedback, options)
                encoded_row = payload[BODY]["source_relation_assessment"]["claims"][0]["obligations"][0]["source_quotes"][0]
                self.assertEqual(encoded_row["fragment_id"], row["fragment_id"])
                self.assertEqual(proof["source_quote_ref_count"], 1)
                self.assertEqual(proof["source_quote_context_only_count"], 1)
                self.assertFalse(proof["source_quote_refs_are_ownership_certificates"])

    def test_resolvable_wrong_owner_rejected_even_when_same_text_exists(self):
        feedback, options = fixture()
        row = feedback["source_relation_assessment"]["claims"][0]["obligations"][0]["source_quotes"][0]
        row["evidence_id"] = "ev_other"
        options["selected"].append({"evidence_id": "ev_other", "text": row["quote"]})
        options["messages"][0]["content"] = CONTEXT_PREFIX + json.dumps({"CURRENT_EVIDENCE": options["selected"]})
        _, proof = self.assert_round_trip(feedback, options)
        self.assertEqual(proof["source_quote_ref_count"], 0)

    def test_alias_and_fragment_collisions_disable_source_refs(self):
        for condition in ("alias_many_to_one", "alias_shadows_full", "duplicate_fragment"):
            with self.subTest(condition=condition):
                feedback, options = fixture()
                fid = options["fragments"][0]["fragment_id"]
                if condition == "alias_many_to_one":
                    options["aliases"]["F002"] = fid
                elif condition == "alias_shadows_full":
                    other = deepcopy(options["fragments"][0])
                    other["fragment_id"] = "full_other"
                    options["fragments"].append(other)
                    options["aliases"][fid] = "full_other"
                else:
                    options["fragments"].append(deepcopy(options["fragments"][0]))
                _, proof = self.assert_round_trip(feedback, options)
                self.assertEqual(proof["source_quote_ref_count"], 0)

    def test_changed_context_and_missing_context_disable_source_refs(self):
        for options_change in ("changed", "missing"):
            feedback, options = fixture()
            if options_change == "changed":
                options["selected"][0]["text"] += "change"
            else:
                options["messages"] = []
            _, proof = self.assert_round_trip(feedback, options)
            self.assertEqual(proof["source_quote_ref_count"], 0)

    def test_invalid_optional_source_graphs_fall_back_without_losing_claim_refs(self):
        for condition in ("surrogate_selected", "cyclic_selected", "surrogate_alias", "cyclic_fragments"):
            with self.subTest(condition=condition):
                feedback, options = fixture()
                before = strict_snapshot(feedback)
                if condition == "surrogate_selected":
                    options["selected"][0]["unknown"] = "\ud800"
                elif condition == "cyclic_selected":
                    options["selected"].append(options["selected"])
                elif condition == "surrogate_alias":
                    options["aliases"]["bad"] = "\ud800"
                else:
                    options["fragments"].append(options["fragments"])
                payload, proof = encode_claim_feedback(feedback, **options)
                self.assertEqual(proof["encoding"], VERSION)
                self.assertEqual(proof["source_quote_ref_count"], 0)
                self.assertEqual(proof["claim_span_count"], 4)
                restored = decode_claim_feedback(json.loads(canonical_bytes(payload)), encoded=True)
                self.assertEqual(strict_snapshot(restored, object_order=False),
                                 strict_snapshot(feedback, object_order=False))
                self.assertEqual(before, strict_snapshot(feedback))

    def test_only_strictly_smaller_candidate_is_used(self):
        feedback = {"draft": {"answer_text": "abc", "short_answer": ""}, "original_claims": [
            {"claim_id": "c", "answer_field": "answer_text", "start": 0, "end": 3, "text": "abc"}]}
        _, proof = self.assert_round_trip(feedback, {}, expect_encoded=False)
        self.assertEqual(proof["reason"], "NOT_STRICTLY_SMALLER")

    def test_returned_graph_does_not_alias_input(self):
        feedback, options = fixture()
        payload, proof = self.assert_round_trip(feedback, options)
        payload[DRAFT]["answer_text"] = "mutated returned value"
        self.assertNotEqual(payload[DRAFT]["answer_text"], feedback["draft"]["answer_text"])
        restored = decode_claim_feedback(feedback, encoded=False)
        restored["draft"]["answer_text"] = "another mutation"
        self.assertNotEqual(restored["draft"]["answer_text"], feedback["draft"]["answer_text"])

    def test_deterministic_encoding_and_hashes(self):
        feedback, options = fixture()
        first, first_proof = encode_claim_feedback(feedback, **options)
        second, second_proof = encode_claim_feedback(feedback, **options)
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(first_proof, second_proof)

    def test_tampered_reference_hash_manifest_and_context_fail_closed(self):
        feedback, options = fixture()
        payload, proof = self.assert_round_trip(feedback, options)
        variants = []
        changed = deepcopy(payload)
        changed[BODY]["original_claims"][0]["text"]["draft_span"][1] += 1
        variants.append(changed)
        changed = deepcopy(payload)
        changed[HEADER]["claim_span_indices"].append(0)
        variants.append(changed)
        changed = deepcopy(payload)
        changed[HEADER]["original_sha256"] = "0" * 64
        variants.append(changed)
        changed = deepcopy(payload)
        changed[HEADER]["protected_claim_indices"][0] = True
        variants.append(changed)
        for changed in variants:
            with self.assertRaises(FeedbackEncodingError):
                decode_claim_feedback(changed, encoded=True, **options)
        options["selected"][0]["text"] += "changed"
        with self.assertRaises(FeedbackEncodingError):
            decode_claim_feedback(payload, encoded=True, **options)

    def test_entire_message_binding_is_unchanged_even_with_same_evidence(self):
        feedback, options = fixture()
        payload, proof = self.assert_round_trip(feedback, options)
        changed = deepcopy(options)
        changed["messages"].append({"role": "user", "content": "changed unrelated instruction"})
        with self.assertRaises(FeedbackEncodingError):
            decode_claim_feedback(payload, encoded=True, **changed)

    def test_non_json_values_and_nonfinite_floats_rejected_without_coercion(self):
        for bad in (float("nan"), float("inf"), (1, 2), b"bytes", {1: "key"}, "\ud800"):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaises(FeedbackEncodingError):
                    encode_claim_feedback({"draft": {"answer_text": "x"}, "unknown": bad})

    def test_explicit_decode_flag_is_required(self):
        with self.assertRaises(TypeError):
            decode_claim_feedback({})
        with self.assertRaises(FeedbackEncodingError):
            decode_claim_feedback({}, encoded=1)


if __name__ == "__main__":
    unittest.main()
