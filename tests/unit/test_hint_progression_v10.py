"""Pure Python author checks; independent checker/release gates remain required."""

import copy
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "generation" / "hint_progression_v10.py"
SPEC = importlib.util.spec_from_file_location("authored_hint_progression_v10", SOURCE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def fixture(problem="Find the next useful question.", level=1):
    request = {
        "question": "Give a hint.",
        "generation_policy": {"version": "generation_controls_v10"},
        "teaching_context": {"teaching_mode": "hint", "current_problem": problem},
    }
    plan = {
        "policy_flags": {"version": "generation_controls_v10"},
        "recorded_step_goal": {"operation": "Select the equation relating the variables."},
        "hint_stage": {"level": level, "kind": guard._KINDS[level]},
    }
    return request, plan


def check(text, problem="Find the next useful question.", **kwargs):
    request, plan = fixture(problem)
    return guard.expression_issues(request, {"answer_text": text}, None, {}, plan, **kwargs)


class HintProgressionGuardTests(unittest.TestCase):
    def test_explicit_saved_math_goals(self):
        for goal in (
            "Select the equation.",
            "Choose the formula.",
            "Identify the mathematical relation.",
            "Select a relation between variables.",
            "Choose a relation before substituting the givens.",
            "Choose an inverse operation.",
            "Choose the operation to isolate the unknown.",
            "选择数学关系。",
            "请选择方程。",
        ):
            with self.subTest(goal=goal):
                self.assertTrue(guard.selection_goal({"operation": goal}))
        for goal in (
            "Apply the equation.",
            "Explain the formula.",
            "Evaluate the answer.",
            "Select a relationship between characters.",
            "Identify the operation of the factory.",
            "Choose the relation between pressure and volume.",
            "Do not select the equation.",
            "Never choose the formula.",
            "Choose an example.",
            None,
        ):
            with self.subTest(goal=goal):
                self.assertFalse(guard.selection_goal(goal))

    def test_all_hint_stages_and_advisory_flag(self):
        for level in (1, 2, 3):
            request, plan = fixture(level=level)
            plan["hint_stage"]["selection_expression_guard"] = False
            self.assertTrue(
                guard.expression_issues(request, {"answer_text": "x+y=2"}, None, {}, plan)
            )

    def test_scope_requires_exact_versions_kind_mode_and_selection(self):
        request, plan = fixture()
        mutations = (
            ("request", ("generation_policy", "version"), "generation_controls_v9"),
            ("request", ("teaching_context", "teaching_mode"), "explain"),
            ("plan", ("policy_flags", "version"), "generation_controls_v9"),
            ("plan", ("hint_stage", "level"), True),
            ("plan", ("hint_stage", "kind"), "guided_cue"),
            ("plan", ("recorded_step_goal", "operation"), "Apply the formula."),
        )
        for target, path, value in mutations:
            with self.subTest(target=target, path=path):
                r, p = copy.deepcopy(request), copy.deepcopy(plan)
                parent = r if target == "request" else p
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                self.assertEqual(
                    [], guard.expression_issues(r, {"answer_text": "x+y=2"}, None, {}, p)
                )

    def test_recognizable_multidomain_notation(self):
        expressions = (
            "3x+5=20",
            "P1V1=P2V2",
            "P₁ V₁ = P₂ V₂",
            "PV=nRT",
            "F=ma",
            "E=mc^2",
            "y=mx+b",
            "A=πr²",
            "V=IR",
            "a²+b²=c²",
            "x≤4",
            "p≈0.5",
            "y∝x",
            "-4+8",
            "10÷2",
            "2×(x+1)",
            "4:2",
            "x^(-2)",
            "y=sin(x)",
            r"P_{1}V_{1}=P_{2}V_{2}",
            r"y=\frac{x+1}{2}",
            r"x\geq2",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertTrue(check(expression))
        for cue in (
            "Which quantities matter?",
            "Look at the constant term.",
            "Consider x and y.",
            "100 kPa",
            "x",
        ):
            with self.subTest(cue=cue):
                self.assertEqual([], check(cue))

    def test_grouped_relations_and_repeated_signs_cannot_hide(self):
        for expression in (
            "(x=1)",
            "[x=1]",
            "{x=1}",
            "((x=1))",
            "x=(y=2)",
            "(x=1)+y",
            r"\left(x=1\right)",
            r"\sqrt{x=1}",
            "x=--2",
            "x=+-2",
        ):
            with self.subTest(expression=expression):
                self.assertTrue(check(expression))
        for expression in ("--x+y=2", "---x+y=2", "- -x+y=2", "+-x+y=2"):
            with self.subTest(expression=expression):
                self.assertTrue(check(expression, "-x+y=2"))

    def test_url_is_not_a_ratio_and_later_math_keeps_original_offsets(self):
        self.assertEqual([], check("See https://x/y."))
        text = "See https://x/y, then compare P1 / P2."
        issues = check(text)
        self.assertEqual(["P1 / P2"], [text[row["start"] : row["end"]] for row in issues])
        self.assertTrue(check("x/y"))

    def test_clock_is_not_a_ratio_and_actual_ratio_remains_guarded(self):
        self.assertEqual([], check("The lab opens at 12:30."))
        text = "The lab opens at 12:30. Compare 4:2."
        issues = check(text)
        self.assertEqual(["4:2"], [text[row["start"] : row["end"]] for row in issues])
        self.assertTrue(check("P1 / P2"))

    def test_finite_slash_labels_are_context_bound_and_later_math_is_guarded(self):
        for label in ("I/O", "Y/N", "R/W"):
            self.assertEqual([], check("Read the " + label + " label."))
            self.assertTrue(check("Compare " + label + "."))
        text = "Read the I/O label. Compare P1 / P2."
        issues = check(text)
        self.assertEqual(["P1 / P2"], [text[row["start"] : row["end"]] for row in issues])

    def test_whole_given_only_and_no_recombination(self):
        self.assertEqual([], check("Recall 3x + 5 = 20.", "Solve 3x+5=20."))
        for expression in ("3x+5", "3x=15", "-3x+5=20", "3(x+5)=20", "3x+5=20+y"):
            with self.subTest(expression=expression):
                self.assertTrue(check(expression, "Solve 3x+5=20."))
        self.assertEqual(
            [], check("P1=130 kPa; V1=2 L", "The initial pressure is 130 kPa and volume is 2 L.")
        )
        self.assertEqual([], check("x=5"))  # Scalar-assignment safety remains a model judgment.
        self.assertTrue(check("P1 * V1 = P2 * V2", "P1=130 kPa; V1=2 L; P2=65 kPa; V2=4 L"))
        self.assertTrue(check("P1 / P2", "P1=130 kPa; P2=65 kPa"))
        request, plan = fixture()
        request["teaching_context"]["practice_context"] = {
            "given_conditions": ["P1=100 kPa", "V1=2 mL", "P2=50 kPa"]
        }
        for text in ("P₁ = 100 kPa", "V_1=2 mL", "P_{2}=50 kPa"):
            with self.subTest(text=text):
                self.assertEqual(
                    [], guard.expression_issues(request, {"answer_text": text}, None, {}, plan)
                )
        self.assertTrue(
            guard.expression_issues(request, {"answer_text": "P1V1=P2V2"}, None, {}, plan)
        )

    def test_faithful_subscripts_whitespace_and_cosmetic_operators(self):
        for text in ("P₁ V₁ = P₂ V₂", "P_1 V_1=P_2 V_2", r"P_{1}V_{1}=P_{2}V_{2}"):
            with self.subTest(text=text):
                self.assertEqual([], check(text, "P1V1=P2V2"))
        self.assertEqual([], check("x−2=0", "x-2=0"))
        self.assertEqual([], check(r"2\cdot x=4", "2*x=4"))
        for text in ("P1V2=P2V1", "p1V1=P2V2", "P1/V1=P2/V2", "P1(V1)=P2V2"):
            with self.subTest(text=text):
                self.assertTrue(check(text, "P1V1=P2V2"))

    def test_no_source_history_attempt_assistant_or_prepared_query_exemption(self):
        request, plan = fixture()
        request["question"] = "x+y=2"
        request["prepared_query"] = {"original_message": "x+y=2"}
        request["source"] = "x+y=2"
        request["teaching_context"].update(
            {
                "delivered_turns": [{"answer_text": "x+y=2"}],
                "learner_attempt": "x+y=2",
                "assistant_history": "x+y=2",
                "pending_tutor_question": "x+y=2",
            }
        )
        self.assertTrue(guard.expression_issues(request, {"answer_text": "x+y=2"}, None, {}, plan))
        del request["teaching_context"]["current_problem"]
        self.assertEqual(
            [], guard.expression_issues(request, {"answer_text": "x+y=2"}, None, {}, plan)
        )

    def test_every_delivered_surface_and_split_citation(self):
        request, plan = fixture()
        response = {
            "answer_text": "x+y=2",
            "short_answer": "y+z=3",
            "follow_up_questions": ["z+x=4"],
        }
        projection = {
            "citation_views": [
                {
                    "title": "a+b=5",
                    "segments": [{"text": "P1V1", "label": "b+c=6"}, {"text": "=P2V2"}],
                    "preview": "c+d=7",
                    "claim_ids": ["protected"],
                }
            ]
        }
        issues = guard.expression_issues(
            request,
            response,
            {"question": "d+e=8"},
            projection,
            plan,
            attempt_evaluation={"feedback": "e+f=9"},
        )
        self.assertEqual(
            {
                "answer_text",
                "short_answer",
                "suggestion:0",
                "tutor_question",
                "learner_attempt_evaluation",
                "citation:0:metadata",
                "citation:0:segment:0:metadata",
                "citation:0:joined_segments",
                "citation:0:preview",
            },
            {row["surface_id"] for row in issues},
        )
        self.assertTrue(
            all(row["code"] == guard.CODE and row["start"] < row["end"] for row in issues)
        )

    def test_projection_response_and_duplicate_spans(self):
        request, plan = fixture()
        response = {
            "answer_text": "Use x+y=2.",
            "tutor_question": {"question": "Is y+z=3 relevant?"},
        }
        issues = guard.expression_issues(
            request, response, response["tutor_question"], {"response": response}, plan
        )
        self.assertEqual(2, len(issues))
        body = next(row for row in issues if row["surface_id"] == "answer_text")
        self.assertEqual("x+y=2", response["answer_text"][body["start"] : body["end"]])

    def test_claim_release_is_exact_field_overlap_only(self):
        claims = [
            {"claim_id": "safe", "answer_field": "answer_text", "start": 0, "end": 4},
            {"claim_id": "unsafe", "answer_field": "answer_text", "start": 5, "end": 12},
            {"claim_id": "adjacent", "answer_field": "answer_text", "start": 12, "end": 20},
            {"claim_id": "short", "answer_field": "short_answer", "start": 5, "end": 12},
        ]
        issue = {"code": guard.CODE, "surface_id": "answer_text", "start": 10, "end": 12}
        self.assertEqual(["unsafe"], guard.affected_claim_ids([issue], claims, {}))
        projection = {"citation_views": [{"claim_ids": ["safe", "unsafe", "adjacent"]}]}
        for surface in (
            "citation:0:metadata",
            "citation:0:segment:0",
            "citation:0:preview",
            "citation:0:joined_segments",
            "tutor_question",
            "suggestion:0",
            "learner_attempt_evaluation",
        ):
            with self.subTest(surface=surface):
                self.assertEqual(
                    [],
                    guard.affected_claim_ids(
                        [{**issue, "surface_id": surface}], claims, projection
                    ),
                )
        for start, end in ((True, 12), (-1, 12), (12, 12), (14, 12)):
            self.assertEqual(
                [], guard.affected_claim_ids([{**issue, "start": start, "end": end}], claims, {})
            )

    def test_summary_is_count_only_and_declares_limits(self):
        summary = guard.issue_summary(check("x+y=2"))
        self.assertEqual(1, summary["issue_count"])
        self.assertEqual(["answer_text"], summary["surface_ids"])
        self.assertFalse(summary["local_semantic_certification"])
        self.assertNotIn("x+y=2", repr(summary))
        self.assertIn("no_algebraic_equivalence", summary["limitations"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
