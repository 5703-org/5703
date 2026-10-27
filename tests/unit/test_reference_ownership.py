from pathlib import Path
import ast, pytest
from copy import deepcopy
from conversation import query_v25, current_reference

try:
    from conversation import reference_ownership as guard
except ImportError:

    class Unrepaired:
        POLICY = "current_message_ownership_v1"

        @staticmethod
        def apply(value, policy):
            return value, None

    guard = Unrepaired()

R = Path(__file__).resolve().parents[2]


def literals(name, wanted):
    tree = ast.parse((R / "tests/unit" / name).read_text(encoding="utf-8"))
    return [
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in wanted
    ]


POSITIVE = (
    literals("test_query_v26_local_reference.py", {"R1", "R2"})
    + literals("test_current_reference_native.py", {"WATER", "ACID"})
    + [
        "A report describes one experiment. Can this experiment isolate humidity?",
        "Xenon is less concentrated outside a vessel than inside. Explain why it may need an opening to escape, and compare that escape with the sealed vessel.",
        "Give both voltages with their uncertainties. Pair each voltage with its frequency.",
        "Compare encryption and compression. Explain their differences.",
        "The circuit is disconnected. Explain why it does not conduct.",
        "The mixture is not heated. Why is it stable?",
        "Using Geography Table 3.1, compare rainfall. State the conditions in its footnote.",
        "Explain photosynthesis, including how it works.",
    ]
)
AMBIGUOUS = [
    "A sensor and a monitor are active. Explain why it fails.",
    "A car follows a bus. Why is it slower?",
    "A motor and a generator are damaged. Explain why it fails.",
    "A sample is heated. A container is cooled. Why does it expand?",
    "Compare copper and aluminium. Why is it denser?",
    "Give both voltages with their units. Why does it increase?",
    '"A sample is heated." Why does it expand?',
    '"A report describes one experiment." Can this experiment isolate humidity?',
    "No comparison was performed. Can this comparison isolate pressure?",
]
HIST = [
    {"message_id": "old-u", "role": "user", "content": "Explain ocean tides."},
    {
        "message_id": "old-a",
        "role": "assistant",
        "content": "An authored historical explanation of ocean tides.",
    },
]


@pytest.mark.parametrize("q", POSITIVE)
@pytest.mark.parametrize("history", [[], HIST])
def test_complete_current_question_not_replaced(q, history):
    base = query_v25.prepare_query(q, history).model_dump()
    snapshot = deepcopy(base)
    fixed, audit = guard.apply(base, guard.POLICY)
    assert not fixed["needs_clarification"]
    assert fixed["standalone_query"] == q
    assert fixed["referenced_message_ids"] == []
    assert base == snapshot


@pytest.mark.parametrize("q", AMBIGUOUS)
@pytest.mark.parametrize("history", [[], HIST])
def test_current_competition_or_unasserted_owner_never_inherits_old_topic(q, history):
    fixed, _ = guard.apply(query_v25.prepare_query(q, history).model_dump(), guard.POLICY)
    assert fixed["needs_clarification"]
    assert fixed["standalone_query"] is None and fixed["referenced_message_ids"] == []


@pytest.mark.parametrize(
    "q", ["Why does it expand?", "Explain that again.", "What are its effects?"]
)
def test_genuine_history_only_followup_keeps_existing_resolution(q):
    history = deepcopy(HIST)
    if q == "Explain that again.":
        history[-1].update(
            answer_response_type="answer",
            latest_exchange_available=True,
            answer_id="synthetic-answer",
        )
    base = query_v25.prepare_query(q, history).model_dump()
    fixed, _ = guard.apply(base, guard.POLICY)
    assert fixed == base and fixed["referenced_message_ids"]
    empty = query_v25.prepare_query(q, []).model_dump()
    assert guard.apply(empty, guard.POLICY)[0] == empty


@pytest.mark.parametrize("q", POSITIVE + AMBIGUOUS)
def test_absent_marker_preserves_every_old_command(q):
    base = query_v25.prepare_query(q, HIST).model_dump()
    assert guard.apply(base, None) == (base, None)


@pytest.mark.parametrize("q", ["Hello!", "What is osmosis?", "What is ATP?"])
def test_no_referent_no_new_behavior(q):
    base = query_v25.prepare_query(q, HIST).model_dump()
    assert guard.apply(base, guard.POLICY)[0] == base


def test_unrelated_semantic_guard_is_not_overridden():
    base = query_v25.prepare_query(POSITIVE[0]).model_dump()
    base["fallback_reason"] = "ambiguous_abbreviation"
    assert guard.apply(base, guard.POLICY)[0] == base


@pytest.mark.parametrize("q", POSITIVE + AMBIGUOUS)
def test_old_explicit_audit_policy_is_byte_equivalent_behavior(q):
    base = query_v25.prepare_query(q, HIST).model_dump()
    assert guard.apply(base, current_reference.POLICY) == current_reference.apply(
        base, current_reference.POLICY
    )


def test_invalid_policy_and_modified_audit_rejected():
    base = query_v25.prepare_query(POSITIVE[0]).model_dump()
    with pytest.raises(ValueError):
        guard.apply(base, "unknown-policy")
    fixed, audit = guard.apply(base, guard.POLICY)
    understanding = query_v25.describe_requirements(POSITIVE[0], fixed, [])
    assert (
        guard.attach_requirements(understanding, fixed, audit)["current_message_reference_audit"]
        == audit
    )
    changed = deepcopy(audit)
    changed["source_text"] = "Altered"
    with pytest.raises(ValueError):
        guard.attach_requirements(understanding, fixed, changed)
    wrong = deepcopy(fixed)
    wrong["referenced_message_ids"] = ["foreign-session"]
    with pytest.raises(ValueError):
        guard.attach_requirements(understanding, wrong, audit)


def test_concurrent_sessions_have_no_shared_owner_state():
    from concurrent.futures import ThreadPoolExecutor

    def run(topic):
        history = [{"message_id": topic, "role": "user", "content": "Explain " + topic + "."}]
        base = query_v25.prepare_query("Why does it expand?", history).model_dump()
        return guard.apply(base, guard.POLICY)[0]

    topics = ["copper", "steel", "rubber", "water"] * 4
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, topics))
    for topic, result in zip(topics, results):
        assert result["referenced_message_ids"] == [topic] and topic in result["standalone_query"]
