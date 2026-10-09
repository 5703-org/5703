"""Bounded pilot probes for non-factorial Week 9 application paths.

These probes preserve their actual scope. A memory selection or administrator
record is a diagnostic observation, never counted as a learner answer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from personalisation import memory_v2, memory_v3

from .http_backend import TextbookQAHttpBackend
from .protocol import load_frozen


def _diagnostic(value: dict, *, provider_calls: int | None = 0, usage: dict | None = None) -> dict:
    return {
        "state": "diagnostic_observation",
        "learner_visible_output": None,
        "admin_or_internal_observation": value,
        "provider_calls": provider_calls,
        "usage": usage
        if usage is not None
        else {"input_tokens": 0, "output_tokens": 0, "cache_hit_input_tokens": 0}
        if provider_calls == 0
        else {},
        "displayed_sources": [],
    }


class MemorySelectorPilotBackend:
    """Run the actual versioned selector on typed authored records, without persistence."""

    def __init__(self, *, counter, policy: dict | None = None):
        if counter is None or not callable(getattr(counter, "count", None)):
            raise ValueError("The production model token counter is required")
        self.counter = counter
        self.policy = memory_v3.validate_policy(policy)

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        if arm != "candidate":
            raise ValueError("This pilot selector implements the candidate arm only")
        entries = []
        for index, entry in enumerate(task["memory_entries"]):
            scope = entry["scope"]
            entries.append(
                {
                    **entry,
                    "id": hashlib.sha256(f"{identity}:{index}".encode()).hexdigest()[:32],
                    "version": 1,
                    "verification": "user_explicit",
                    "source_event_sequence": index + 1,
                    "scope_topics": memory_v2.topics(scope),
                }
            )
        selection = memory_v3.select(
            entries,
            task["question"],
            {"profile": {}},
            policy=self.policy,
            counter=self.counter,
        )
        return _diagnostic(
            {
                "scope": "selector_only_typed_authored_records_no_database_write_or_answer",
                "selected_memory_ids": selection.trace["selected_ids"],
                "selected_entries": selection.state["entries"],
                "fields": selection.state["fields"],
                "excluded": selection.state["excluded"],
                "selection_trace": selection.trace,
                "token_count": selection.state["token_count"],
                "token_counting": selection.state["token_counting"],
                "topic_policy": selection.state["topic_policy"],
            }
        ) | {"selected_memory_ids": selection.trace["selected_ids"]}


class VisualStructurePilotBackend:
    """Read the isolated administrator visual-region API without claiming geometry review."""

    def __init__(self, admin_chat):
        self.admin_chat = admin_chat

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        if arm != "candidate":
            raise ValueError("This visual pilot implements the candidate arm only")
        region = self.admin_chat._request(
            "GET", f"/admin/source-quality/visual-regions/{task['region_id']}"
        )
        return _diagnostic(
            {
                "scope": "administrator_source_structure_only_no_independent_visual_review",
                "region_id": region.get("id"),
                "document_id": region.get("document_id"),
                "physical_pdf_page": region.get("physical_pdf_page"),
                "kind": region.get("kind"),
                "candidate_status": region.get("candidate_status"),
                "latest_review": region.get("latest_review"),
                "catalog_sha256": region.get("catalog_sha256"),
                "native_text": region.get("native_text"),
                "bbox_points": region.get("bbox_points"),
                "answer_evidence_eligible": region.get("answer_evidence_eligible"),
                "task_structural_match": (
                    region.get("id") == task["region_id"]
                    and region.get("document_id") == task["document_id"]
                    and region.get("physical_pdf_page") == task["physical_page"]
                    and region.get("kind") == task["kind"]
                ),
            }
        )


class InteractivePilotBackend:
    """Use real isolated chat for attack and latency cases; cross-owner uses a second account."""

    def __init__(
        self,
        study_folder: Path,
        owner_chat,
        other_chat=None,
        *,
        trace_usage=None,
    ):
        self.study_folder = study_folder
        self.owner_chat = owner_chat
        self.other_chat = other_chat
        self.qa = TextbookQAHttpBackend(owner_chat, trace_usage)
        manifest = load_frozen(study_folder)
        self.family = {case["id"]: case["family"] for case in manifest["cases"]}

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        case_id, _ = identity.rsplit("::", 1)
        family = self.family[case_id]
        if arm != "candidate" or family not in {
            "textbook_qa",
            "safety_robustness",
            "performance_recovery",
        }:
            raise ValueError("This application adapter cannot execute the scheduled family/arm")
        if task.get("operation") == "read_other_owner_answer":
            return self._cross_owner()
        result = self.qa(task, arm, identity)
        return {
            **result,
            "pilot_scope": "isolated_live_http_chat",
            "attack_kind": task.get("attack_kind"),
            "performance_repeat": task.get("repeat"),
        }

    def _cross_owner(self) -> dict:
        if self.other_chat is None or self.other_chat.email == self.owner_chat.email:
            raise ValueError("Cross-owner probe requires a second isolated learner account")
        manifest = load_frozen(self.study_folder)
        for item in manifest["schedule"]:
            if item["family"] != "textbook_qa" or item["arm"] != "candidate":
                continue
            path = self.study_folder / "outcomes" / (item["id"].replace("::", "--") + ".json")
            if not path.is_file():
                continue
            row = json.loads(path.read_text(encoding="utf-8"))
            if (
                row.get("evaluation_owner_fingerprint")
                != hashlib.sha256(self.owner_chat.email.casefold().encode()).hexdigest()
            ):
                continue
            answer_id = (row.get("application_receipt") or {}).get("answer_id")
            if not answer_id:
                continue
            response = self.other_chat.client.get(
                "/api/v1/answers/" + answer_id,
                headers=self.other_chat.headers,
            )
            body_hash = hashlib.sha256(response.content).hexdigest()
            if response.status_code in {403, 404}:
                return {
                    "state": "security_block",
                    "learner_visible_output": None,
                    "provider_calls": 0,
                    "usage": {"input_tokens": 0, "output_tokens": 0, "cache_hit_input_tokens": 0},
                    "http_status": response.status_code,
                    "body_sha256": body_hash,
                    "tested_owned_answer_id": answer_id,
                    "owner_relationship": "different_isolated_learner_account",
                }
            return _diagnostic(
                {
                    "scope": "cross_owner_read_security_failure_if_2xx",
                    "http_status": response.status_code,
                    "body_sha256": body_hash,
                    "tested_owned_answer_id": answer_id,
                    "security_failure": 200 <= response.status_code < 300,
                }
            )
        raise ValueError("A completed owned QA answer is needed before cross-owner read")


class PracticeProposalPilotBackend:
    """Generate and validate an unpublished source-pinned administrator draft."""

    def __init__(
        self,
        admin_chat,
        *,
        frozen_manifest_sha256: str,
        candidate_source_sha256: str,
    ):
        for digest in (frozen_manifest_sha256, candidate_source_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("Practice proposals require frozen study and source hashes")
        self.admin_chat = admin_chat
        self.frozen_manifest_sha256 = frozen_manifest_sha256
        self.candidate_source_sha256 = candidate_source_sha256

    def idempotency_key(self, identity: str) -> str:
        """Retry within one study; never replay a previous candidate's proposal."""
        return hashlib.sha256(
            (
                f"week09-practice-v2:{self.frozen_manifest_sha256}:"
                f"{self.candidate_source_sha256}:{identity}"
            ).encode()
        ).hexdigest()

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        if arm != "candidate":
            raise ValueError("Practice pilot currently has only the candidate arm")
        concepts = task.get("concepts")
        if not isinstance(concepts, list) or not concepts:
            raise ValueError("A pre-frozen source concept is needed for a practice proposal")
        idempotency = self.idempotency_key(identity)
        draft = self.admin_chat._request(
            "POST",
            "/admin/learning/practice-proposals",
            {
                "source": task["source_locator"],
                "kind": task["kind"],
                "concepts": concepts,
                "conditions": task.get("conditions", []),
            },
            {"Idempotency-Key": idempotency},
        )
        item_id = draft["item"]["id"]
        validated = self.admin_chat._request("POST", f"/admin/learning/practice/{item_id}/validate")
        return _diagnostic(
            {
                "scope": "generated_admin_draft_and_structural_validation_only_unpublished",
                "item_id": item_id,
                "proposal_attempt_id": (draft.get("validation_details") or {}).get(
                    "proposal_attempt_id"
                ),
                "state": validated.get("state"),
                "validation_status": (validated.get("validation_details") or {}).get("status"),
                "validation_issues": (validated.get("validation_details") or {}).get("issues"),
                "requested_kind": task["kind"],
                "generated_kind": validated["item"].get("kind"),
                "requested_concepts": concepts,
                "generated_concepts": validated["item"].get("concepts"),
                "generated_question": validated["item"].get("prompt"),
                "generated_options": validated["item"].get("options"),
                "semantic_correctness_verified": None,
                "practice_attempt_executed": False,
            },
            provider_calls=None,
        )
