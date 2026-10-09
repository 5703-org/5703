"""Relation quarantine, exact source review and learner provenance on PostgreSQL."""

from uuid import uuid4

from sqlalchemy import select

from app.modules.identity.models import User, Workspace
from app.modules.knowledge.models import Document
from app.modules.learning_product.models import StudyConceptRelation
from .test_chat_runtime import call


def related_source(rt):
    admin = rt.headers("admin@example.com")
    raw = (
        "# Diffusion\n"
        "Diffusion is a prerequisite concept for understanding osmosis in this lesson. "
        "Diffusion is related to osmosis because both involve particle movement. "
        "Students sometimes confuse diffusion with osmosis; osmosis is specifically "
        "the movement of water across a selectively permeable membrane.\n\n"
        "# Osmosis\n"
        "Osmosis is the movement of water across a selectively permeable membrane. " + uuid4().hex
    ).encode()
    upload = rt.client.post(
        "/api/v1/documents",
        headers=admin,
        data={"title": "Authored relation-review fixture " + uuid4().hex[:6]},
        files={"file": ("relation-" + uuid4().hex + ".txt", raw, "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    doc = upload.json()["data"]["document"]
    process = call(rt, "POST", f"/documents/{doc['id']}/process", {}, admin, 202)
    assert rt.work()
    assert call(rt, "GET", f"/jobs/{process['job_id']}", headers=admin)["state"] == "succeeded"
    build = call(
        rt,
        "POST",
        "/corpus/releases",
        {"processing_run_ids": [process["processing_id"]]},
        admin,
        202,
    )
    assert rt.work()
    call(rt, "POST", f"/corpus/releases/{build['release_id']}/activate", {}, admin)
    sections = call(rt, "GET", f"/learning/library/{doc['id']}/sections")
    page = call(rt, "GET", f"/learning/library/{doc['id']}/units")
    return doc, sections, page["items"]


def proposal(doc, sections, unit, relation_type, sentence):
    start = unit["text"].index(sentence)
    return {
        "document_id": doc["id"],
        "from_section_id": sections[0]["id"],
        "to_section_id": sections[1]["id"],
        "from_concept": "diffusion",
        "to_concept": "osmosis",
        "relation_type": relation_type,
        "source": {**unit["locator"], "start": start, "end": start + len(sentence)},
        "source_quote": sentence,
        "reason": "The quoted source explicitly states this relationship between the two concepts.",
    }


def test_reviewed_relations_are_quarantined_and_source_bound(runtime):
    rt = runtime
    doc, sections, units = related_source(rt)
    source = next(unit for unit in units if unit["section"] == "Diffusion")
    goal = call(
        rt,
        "POST",
        "/learning/goals",
        {
            "title": "Trace osmosis concepts",
            "document_id": doc["id"],
            "section_ids": [section["id"] for section in sections],
        },
        status=201,
    )
    assert goal["reviewed_relations"] == []
    assert goal["units"][1]["prerequisite_origin"] == "section_order_suggestion"
    admin = rt.headers("admin@example.com")
    examples = {
        "prerequisite": "Diffusion is a prerequisite concept for understanding osmosis in this lesson.",
        "related": "Diffusion is related to osmosis because both involve particle movement.",
        "confusion": "Students sometimes confuse diffusion with osmosis; osmosis is specifically the movement of water across a selectively permeable membrane.",
    }
    for relation_type, sentence in examples.items():
        body = proposal(doc, sections, source, relation_type, sentence)
        call(rt, "POST", "/admin/learning/concept-relations", body, status=403)
        bad = {**body, "source_quote": sentence[:-1] + "!"}
        call(rt, "POST", "/admin/learning/concept-relations", bad, admin, 422)
        created = call(rt, "POST", "/admin/learning/concept-relations", body, admin, 201)
        assert created["state"] == "proposed" and created["source_quote"] == sentence
        before_review = call(rt, "GET", f"/learning/goals/{goal['id']}")
        assert all(edge["id"] != created["id"] for edge in before_review["reviewed_relations"])
        call(
            rt,
            "POST",
            f"/admin/learning/concept-relations/{created['id']}/review",
            {
                "expected_version": created["version"],
                "decision": "approve",
                "verified_source_support": False,
                "review_note": "The exact textbook claim must be checked before learner publication.",
            },
            admin,
            422,
        )
        reviewed = call(
            rt,
            "POST",
            f"/admin/learning/concept-relations/{created['id']}/review",
            {
                "expected_version": created["version"],
                "decision": "approve",
                "verified_source_support": True,
                "review_note": "The exact source sentence explicitly supports this typed relation.",
            },
            admin,
        )
        assert reviewed["state"] == "approved" and reviewed["version"] == 2
        call(
            rt,
            "POST",
            f"/admin/learning/concept-relations/{created['id']}/review",
            {
                "expected_version": 1,
                "decision": "reject",
                "verified_source_support": False,
                "review_note": "This stale second review must not overwrite the approved decision.",
            },
            admin,
            409,
        )
    refreshed = call(rt, "GET", f"/learning/goals/{goal['id']}")
    assert {edge["relation_type"] for edge in refreshed["reviewed_relations"]} == set(examples)
    for edge in refreshed["reviewed_relations"]:
        assert edge["source_quote"] == examples[edge["relation_type"]]
        assert edge["source_book"] == doc["title"]
        assert edge["source_section"] == "Diffusion"
        assert edge["source_page"] >= 1
        assert edge["source"]["release_id"] == goal["release_id"]
        assert edge["provenance"] == "administrator_reviewed_released_source"
        assert edge["reason"]
        assert "review_note" not in edge
    read = call(
        rt,
        "POST",
        f"/learning/goals/{goal['id']}/units/{goal['units'][0]['id']}/read",
        {"expected_version": goal["version"]},
    )
    assert read["units"][0]["status"] == "read"
    assert "mastery" not in read["units"][0]
    with rt.db() as db:
        document = db.get(Document, doc["id"])
        document.revoked = True
        db.commit()
        assert db.scalar(
            select(StudyConceptRelation).where(StudyConceptRelation.state == "approved")
        )
    assert call(rt, "GET", f"/learning/goals/{goal['id']}")["reviewed_relations"] == []


def test_admin_relation_review_respects_workspace_and_rejection(runtime):
    rt = runtime
    doc, sections, units = related_source(rt)
    source = next(unit for unit in units if unit["section"] == "Diffusion")
    body = proposal(
        doc,
        sections,
        source,
        "related",
        "Diffusion is related to osmosis because both involve particle movement.",
    )
    admin_headers = rt.headers("admin@example.com")
    created = call(rt, "POST", "/admin/learning/concept-relations", body, admin_headers, 201)
    with rt.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        original_workspace = actor.workspace_id
        alternate = Workspace(name="Unrelated review workspace", slug="review-" + uuid4().hex)
        db.add(alternate)
        db.flush()
        actor.workspace_id = alternate.id
        db.commit()
    assert call(rt, "GET", "/admin/learning/concept-relations", headers=admin_headers) == []
    call(
        rt,
        "POST",
        f"/admin/learning/concept-relations/{created['id']}/review",
        {
            "expected_version": created["version"],
            "decision": "approve",
            "verified_source_support": True,
            "review_note": "Cross-workspace review access must be blocked for this source.",
        },
        admin_headers,
        404,
    )
    with rt.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        actor.workspace_id = original_workspace
        db.commit()
    rejected = call(
        rt,
        "POST",
        f"/admin/learning/concept-relations/{created['id']}/review",
        {
            "expected_version": created["version"],
            "decision": "reject",
            "verified_source_support": False,
            "review_note": "The proposed relationship should stay outside learner suggestions.",
        },
        admin_headers,
    )
    assert rejected["state"] == "rejected"
    assert (
        call(rt, "GET", "/admin/learning/concept-relations?state=rejected", headers=admin_headers)[
            0
        ]["id"]
        == created["id"]
    )
