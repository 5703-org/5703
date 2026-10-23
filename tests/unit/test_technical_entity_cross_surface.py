"""Controls for a bounded negative follow-up of same-round copied witnesses."""

from copy import deepcopy
import unittest

from generation.reliability_v5 import evaluate_technical_entity_bindings


def inputs():
    fragments = [
        {
            "fragment_id": "F1",
            "evidence_id": "ev_001",
            "exact_text": "The system uses ALFB to transfer energy.",
        },
        {
            "fragment_id": "F2",
            "evidence_id": "ev_002",
            "exact_text": "The carriers travel into the next stage.",
        },
        {"fragment_id": "F3", "evidence_id": "ev_001", "exact_text": "ALFB is also called ALFA."},
        {
            "fragment_id": "F4",
            "evidence_id": "ev_001",
            "exact_text": "ALFB occurs in a separate glossary.",
        },
        {
            "fragment_id": "F5",
            "evidence_id": "ev_003",
            "exact_text": "ALFA is the carrier that transfers energy.",
        },
    ]
    claims = [
        {
            "claim_id": "body",
            "answer_field": "answer_text",
            "text": "The system uses ALFA to transfer energy [ev_001].",
        },
        {
            "claim_id": "short",
            "answer_field": "short_answer",
            "text": "Energy is carried by ALFA into the next stage [ev_001] [ev_002].",
        },
    ]
    bindings = [
        {
            "claim_id": "body",
            "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F1", "F3", "F4"]}],
        },
        {
            "claim_id": "short",
            "citations": [
                {"evidence_id": "ev_001", "allowed_fragment_ids": ["F1", "F3", "F4"]},
                {"evidence_id": "ev_002", "allowed_fragment_ids": ["F2"]},
                {"evidence_id": "ev_003", "allowed_fragment_ids": ["F5"]},
            ],
        },
    ]
    typed = {
        "claims": [
            {
                "claim_id": "body",
                "basis": "textbook",
                "status": "supported",
                "reason": "The source supports this.",
                "citations": [
                    {"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": ["F1"]}
                ],
            },
            {
                "claim_id": "short",
                "basis": "textbook",
                "status": "supported",
                "reason": "The source supports this.",
                "citations": [
                    {"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": ["F1"]},
                    {"evidence_id": "ev_002", "relation": "supporting", "fragment_ids": ["F2"]},
                ],
            },
        ]
    }
    return typed, claims, bindings, fragments


def diagnostics(values):
    return evaluate_technical_entity_bindings(*values)


class CrossSurfaceBindingTests(unittest.TestCase):
    def assert_claims(self, values, expected):
        before = deepcopy(values)
        issues = diagnostics(values)
        self.assertEqual([issue["claim_id"] for issue in issues], expected)
        self.assertEqual(values, before)
        for issue in issues:
            self.assertFalse(issue["source_entailment_certified"])
            self.assertFalse(issue["publication_override"])
        return issues

    def test_same_copied_witness_releases_paraphrased_other_surface(self):
        issues = self.assert_claims(inputs(), ["body", "short"])
        self.assertEqual(issues[1]["claimed_identifier"], "ALFA")
        self.assertEqual(issues[1]["source_identifiers"], ["ALFB"])
        self.assertEqual(issues[1]["selected_fragment_ids"], ["F1"])
        self.assertEqual(issues[1]["anchor_claim_id"], "body")
        self.assertEqual(issues[1]["binding_diagnostic_origin"], "cross_surface_copy_witness_v1")
        self.assertTrue(issues[1]["binding_recheck_required"])
        self.assertFalse(issues[1]["claim_relation_assessed"])

    def test_reason_wording_and_unselected_alias_do_not_clear(self):
        for reason in ("ALFB is ALFA.", "ALFA is named in the source.", "Completely supported."):
            with self.subTest(reason=reason):
                values = inputs()
                for row in values[0]["claims"]:
                    row["reason"] = reason
                self.assert_claims(values, ["body", "short"])

    def test_no_direct_copied_witness_means_no_cross_followup(self):
        values = inputs()
        values[1][0]["text"] = "ALFA is an energy carrier [ev_001]."
        self.assert_claims(values, [])

    def test_same_surface_never_propagates(self):
        values = inputs()
        values[1][1]["answer_field"] = "answer_text"
        self.assert_claims(values, ["body"])

    def test_unknown_missing_other_and_reverse_surfaces_never_propagate(self):
        for surface in (None, "other", ""):
            with self.subTest(origin=surface):
                values = inputs()
                if surface is None:
                    values[1][0].pop("answer_field")
                else:
                    values[1][0]["answer_field"] = surface
                self.assert_claims(values, ["body"])
            with self.subTest(destination=surface):
                values = inputs()
                if surface is None:
                    values[1][1].pop("answer_field")
                else:
                    values[1][1]["answer_field"] = surface
                self.assert_claims(values, ["body"])
        values = inputs()
        values[1][0]["answer_field"] = "short_answer"
        values[1][1]["answer_field"] = "answer_text"
        self.assert_claims(values, ["body"])

    def test_different_identifier_and_full_name_do_not_inherit(self):
        for text in (
            "Energy is carried by ALFC into the next stage [ev_001].",
            "Energy is carried by the alpha form reagent into the next stage [ev_001].",
        ):
            with self.subTest(text=text):
                values = inputs()
                values[1][1]["text"] = text
                self.assert_claims(values, ["body"])

    def test_same_evidence_different_fragment_is_not_the_witness(self):
        values = inputs()
        values[0]["claims"][1]["citations"][0]["fragment_ids"] = ["F4"]
        self.assert_claims(values, ["body"])

    def test_same_fragment_with_wrong_evidence_binding_is_not_selected(self):
        values = inputs()
        values[0]["claims"][1]["citations"][0]["evidence_id"] = "ev_002"
        values[2][1]["citations"][1]["allowed_fragment_ids"].append("F1")
        self.assert_claims(values, ["body"])

    def test_nearby_only_fragment_in_legacy_list_cannot_seed_propagation(self):
        values = inputs()
        values[0]["claims"][0]["citations"][0]["fragment_ids"] = ["F1", "F4"]
        values[0]["claims"][1]["citations"][0]["fragment_ids"] = ["F4"]
        issues = self.assert_claims(values, ["body"])
        self.assertEqual(issues[0]["selected_fragment_ids"], ["F1", "F4"])

    def test_actual_selected_literal_alias_or_correct_other_source_clears_only_short(self):
        for evidence_id, fragment_id in (("ev_001", "F3"), ("ev_003", "F5")):
            with self.subTest(evidence_id=evidence_id, fragment_id=fragment_id):
                values = inputs()
                values[0]["claims"][1]["citations"].append(
                    {
                        "evidence_id": evidence_id,
                        "relation": "supporting",
                        "fragment_ids": [fragment_id],
                    }
                )
                self.assert_claims(values, ["body"])

    def test_comparison_negation_and_explicit_full_name_abstain(self):
        for text in (
            "ALFA differs from ALFB [ev_001].",
            "ALFA and ALFB have distinct roles [ev_001].",
            "The source does not name ALFA [ev_001].",
            "ALFA isn't named in this fragment [ev_001].",
            "This fragment describes another role rather than ALFA [ev_001].",
            "ALFA (alpha form reagent) carries energy [ev_001].",
            "The alpha form reagent (ALFA) carries energy [ev_001].",
        ):
            with self.subTest(text=text):
                values = inputs()
                values[1][1]["text"] = text
                self.assert_claims(values, ["body"])

    def test_unexpressed_full_name_for_different_role_is_an_explicit_review_boundary(self):
        values = inputs()
        values[1][1]["text"] = "ALFA regulates receptor uptake [ev_001] [ev_002]."
        values[3][1]["exact_text"] = "The alpha form reagent regulates receptor uptake."
        issues = self.assert_claims(values, ["body", "short"])
        self.assertTrue(issues[1]["binding_recheck_required"])
        self.assertFalse(issues[1]["claim_relation_assessed"])
        # This result is a conservative request to re-evaluate the binding.
        # The literal rule cannot determine the full-name alias or other role.

    def test_negative_model_status_and_other_basis_are_unchanged(self):
        for key, value in (
            ("status", "partial"),
            ("status", "unsupported"),
            ("basis", "general_knowledge"),
            ("basis", "problem_given"),
        ):
            with self.subTest(key=key, value=value):
                values = inputs()
                values[0]["claims"][1][key] = value
                self.assert_claims(values, ["body"])

    def test_unallowed_or_non_supporting_shared_fragment_does_not_propagate(self):
        values = inputs()
        values[2][1]["citations"][0]["allowed_fragment_ids"] = []
        self.assert_claims(values, ["body"])
        for relation in ("contradicting", "related", "irrelevant"):
            with self.subTest(relation=relation):
                values = inputs()
                values[0]["claims"][1]["citations"][0]["relation"] = relation
                self.assert_claims(values, ["body"])

    def test_existing_source_negation_comparison_full_name_and_distant_label_controls(self):
        for source in (
            "The system does not use ALFB to transfer energy.",
            "The system compares ALFB with ALFA to transfer energy.",
            "The system uses alpha form reagent to transfer energy, unlike ALFB.",
            "The system uses OMEGA to transfer energy.",
        ):
            with self.subTest(source=source):
                values = inputs()
                values[3][0]["exact_text"] = source
                self.assert_claims(values, [])

    def test_fragment_stitching_cannot_create_direct_anchor(self):
        values = inputs()
        values[3][0]["exact_text"] = "The system uses ALFB"
        values[3][3]["exact_text"] = "to transfer energy."
        values[0]["claims"][0]["citations"][0]["fragment_ids"] = ["F1", "F4"]
        self.assert_claims(values, [])

    def test_duplicate_claim_identity_retains_existing_identity_owner(self):
        values = inputs()
        values[1].append(deepcopy(values[1][0]))
        self.assert_claims(values, [])

    def test_duplicate_anchors_emit_only_one_followup(self):
        values = inputs()
        duplicate = deepcopy(values[1][0])
        duplicate["claim_id"] = "body_two"
        values[1].append(duplicate)
        binding = deepcopy(values[2][0])
        binding["claim_id"] = "body_two"
        values[2].append(binding)
        judgment = deepcopy(values[0]["claims"][0])
        judgment["claim_id"] = "body_two"
        values[0]["claims"].append(judgment)
        issues = self.assert_claims(values, ["body", "body_two", "short"])
        self.assertEqual(sum(issue["claim_id"] == "short" for issue in issues), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
