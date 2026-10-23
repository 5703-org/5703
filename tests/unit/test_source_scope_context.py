"""Portable synthetic controls for literal leading-scope source-context review."""

from copy import deepcopy
import unittest

from generation.reliability_v5 import evaluate_technical_entity_bindings


def inputs(
    claim="In the ALFA cycle, the reagent is converted into stored fuel [ev_001].",
    scope_context="The ALFA cycle includes the fuel conversion stage.",
):
    claims = [{"claim_id": "scope", "answer_field": "answer_text", "text": claim}]
    fragments = [
        {
            "fragment_id": "F1",
            "evidence_id": "ev_001",
            "complete_block": True,
            "exact_text": "The reagent is converted into stored fuel.",
        },
        {
            "fragment_id": "F2",
            "evidence_id": "ev_001",
            "complete_block": True,
            "exact_text": scope_context,
        },
    ]
    bindings = [
        {
            "claim_id": "scope",
            "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F1", "F2"]}],
        }
    ]
    typed = {
        "claims": [
            {
                "claim_id": "scope",
                "basis": "textbook",
                "status": "supported",
                "reason": "The selected source establishes the scope.",
                "citations": [
                    {"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": ["F1"]}
                ],
            }
        ]
    }
    return typed, claims, bindings, fragments


class ScopeContextBindingTests(unittest.TestCase):
    def assert_issues(self, values, expected):
        before = deepcopy(values)
        issues = evaluate_technical_entity_bindings(*values)
        self.assertEqual(len(issues), expected)
        self.assertEqual(values, before)
        for issue in issues:
            self.assertEqual(issue["code"], "SOURCE_SCOPE_CONTEXT_NOT_SELECTED")
            self.assertTrue(issue["binding_recheck_required"])
            self.assertFalse(issue["claim_relation_assessed"])
            self.assertFalse(issue["source_entailment_certified"])
            self.assertFalse(issue["publication_override"])
        return issues

    def test_named_prefix_missing_selected_context_is_only_a_recheck(self):
        values = inputs()
        issues = self.assert_issues(values, 1)
        issue = issues[0]
        self.assertEqual(issue["leading_scope"], "ALFA cycle")
        self.assertEqual(issue["selected_fragment_ids"], ["F1"])
        self.assertEqual(
            issue["context_candidate_fragments"],
            [{"evidence_id": "ev_001", "fragment_id": "F2", "scope_start": 4, "scope_end": 14}],
        )
        self.assertEqual(
            values[1][0]["text"][issue["scope_start"] : issue["scope_end"]], "ALFA cycle"
        )

    def test_hyphen_qualified_plural_subject_has_the_same_bounded_rule(self):
        values = inputs(
            "The heat-dependent reactions turn heat into stored fuel [ev_001].",
            "The products of the heat-dependent reactions have short lifetimes.",
        )
        issue = self.assert_issues(values, 1)[0]
        self.assertEqual(issue["leading_scope"], "heat-dependent reactions")

    def test_current_selected_scope_context_clears_the_literal_diagnostic(self):
        values = inputs()
        values[0]["claims"][0]["citations"][0]["fragment_ids"].append("F2")
        self.assert_issues(values, 0)

    def test_context_in_another_actually_selected_supporting_citation_clears(self):
        values = inputs()
        values[3][1]["evidence_id"] = "ev_002"
        values[2][0]["citations"].append({"evidence_id": "ev_002", "allowed_fragment_ids": ["F2"]})
        values[0]["claims"][0]["citations"].append(
            {"evidence_id": "ev_002", "relation": "supporting", "fragment_ids": ["F2"]}
        )
        self.assert_issues(values, 0)

    def test_reason_only_scope_does_not_clear_or_create_an_occurrence(self):
        values = inputs()
        values[0]["claims"][0]["reason"] = (
            "ALFA cycle is fully covered by F1, with a semantic alias."
        )
        self.assert_issues(values, 1)
        values[3][1]["exact_text"] = "The BETA cycle is another named stage."
        self.assert_issues(values, 0)

    def test_different_scope_and_word_substring_are_not_candidates(self):
        for scope_context in (
            "The BETA cycle includes fuel conversion.",
            "ALFA cycles include fuel conversion.",
            "The preALFA cycle includes fuel conversion.",
        ):
            with self.subTest(scope_context=scope_context):
                self.assert_issues(inputs(scope_context=scope_context), 0)

    def test_same_fragment_wrong_evidence_unallowed_or_incomplete_is_not_candidate(self):
        values = inputs()
        values[3][1]["evidence_id"] = "ev_002"
        self.assert_issues(values, 0)
        values = inputs()
        values[2][0]["citations"][0]["allowed_fragment_ids"] = ["F1"]
        self.assert_issues(values, 0)
        values = inputs()
        values[3][1]["complete_block"] = False
        self.assert_issues(values, 0)

    def test_unselected_other_citation_does_not_supply_a_scope_candidate(self):
        values = inputs()
        values[3][1]["evidence_id"] = "ev_002"
        values[2][0]["citations"].append({"evidence_id": "ev_002", "allowed_fragment_ids": ["F2"]})
        self.assert_issues(values, 0)

    def test_non_supporting_or_empty_selected_union_cannot_seed_scope_review(self):
        for relation in ("contradicting", "related", "irrelevant"):
            with self.subTest(relation=relation):
                values = inputs()
                values[0]["claims"][0]["citations"][0]["relation"] = relation
                self.assert_issues(values, 0)
        values = inputs()
        values[0]["claims"][0]["citations"] = []
        self.assert_issues(values, 0)

    def test_existing_negative_status_other_basis_and_unknown_surface_are_unchanged(self):
        for key, value in (
            ("status", "partial"),
            ("status", "unsupported"),
            ("basis", "general_knowledge"),
            ("basis", "problem_given"),
        ):
            with self.subTest(key=key, value=value):
                values = inputs()
                values[0]["claims"][0][key] = value
                self.assert_issues(values, 0)
        values = inputs()
        values[1][0]["answer_field"] = "metadata"
        self.assert_issues(values, 0)

    def test_comparison_and_negation_abstain_without_interpreting_their_truth(self):
        for text in (
            "In the ALFA cycle, compare the converted reagent with stored fuel [ev_001].",
            "In the ALFA cycle, the conversion differs from another stage [ev_001].",
            "In the ALFA cycle, the reagent is not converted into stored fuel [ev_001].",
            "In the ALFA cycle, the reagent isn't converted into stored fuel [ev_001].",
        ):
            with self.subTest(text=text):
                self.assert_issues(inputs(claim=text), 0)

    def test_only_two_explicit_prefix_shapes_are_recognized(self):
        for text in (
            "The reagent enters the ALFA cycle [ev_001].",
            "In the alfa cycle, the reagent becomes stored fuel [ev_001].",
            "The products of the heat-dependent reactions become stored fuel [ev_001].",
        ):
            with self.subTest(text=text):
                self.assert_issues(inputs(claim=text), 0)

    def test_case_only_source_spelling_and_unicode_offsets_are_literal_controls(self):
        values = inputs(scope_context="🧪 中—The alfa cycle contains a fuel conversion stage.")
        issue = self.assert_issues(values, 1)[0]
        location = issue["context_candidate_fragments"][0]
        source = values[3][1]["exact_text"]
        self.assertEqual(source[location["scope_start"] : location["scope_end"]], "alfa cycle")

    def test_selected_literal_alias_clears_but_unexpressed_alias_remains_a_boundary(self):
        values = inputs()
        values[3][0]["exact_text"] = (
            "The initial fuel loop, also called the ALFA cycle, converts the reagent."
        )
        self.assert_issues(values, 0)
        values = inputs()
        values[3][0]["exact_text"] = "The initial fuel loop converts the reagent into stored fuel."
        values[3][1]["exact_text"] = "ALFA cycle is another name for the initial fuel loop."
        issue = self.assert_issues(values, 1)[0]
        self.assertFalse(issue["claim_relation_assessed"])

    def test_heading_candidate_is_never_certified_as_support(self):
        values = inputs(scope_context="3.4 The ALFA cycle")
        issue = self.assert_issues(values, 1)[0]
        self.assertFalse(issue["source_entailment_certified"])
        self.assertFalse(issue["claim_relation_assessed"])

    def test_duplicate_identity_keeps_existing_identity_validation_owner(self):
        values = inputs()
        values[1].append(deepcopy(values[1][0]))
        self.assert_issues(values, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
