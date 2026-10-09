"""Native context and immutable source-chain checks, without database or providers."""

from __future__ import annotations

import copy
from collections import Counter
import gzip
import json

import pymupdf
import pytest

from app.core.exceptions import AppError
from app.modules.learning_product.visual_catalog_versions import load_bundle, file_hash
from pipelines.native_formula_context_v1 import (
    recover_formula_context,
    validate_formula_context,
    validate_formula_context_against_page,
)
from pipelines.visual_candidate_boundaries import (
    is_inline_reference,
    rectangular_table_body,
    validate_reference_record,
    validate_reference_targets,
    validate_v4_parent_lineage,
)
from pipelines.visual_regions import extract_page_regions as v2, _identity
from pipelines.visual_regions_v3 import extract_page_regions as v3
from pipelines.visual_regions_v4 import extract_page_regions as v4
from pipelines.visual_regions_v5 import extract_page_regions as v5
from scripts.verify import build_visual_region_catalog as builder
from scripts.verify import prepare_visual_catalog_v5_bundle as preparer


def _page(text, *, width=612, height=792):
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    assert page.insert_textbox((72, 80, width - 72, 500), text, fontsize=10) > 0
    return doc


def _records(page, extractor=v5):
    return extractor(page, source_sha256="a" * 64, book="Authored source fixture", physical_page=1)


def _formula(page):
    return next(item for item in _records(page) if item["kind"] == "formula_candidate")


def test_split_arithmetic_retains_missing_native_term_without_merging_or_certifying():
    with _page(
        "Count the contributions.\n7 (from A) +\n4 (from B) = 11. The result continues\non this neighboring line."
    ) as doc:
        before = _records(doc[0], v4)
        current = _records(doc[0])
        assert before == _records(doc[0], v4)
        validate_v4_parent_lineage(current, before)
        item = current[0]
        context = item["details"]["formula_context"]
        assert item["native_text"].startswith("4 (from B) = 11")
        assert "7 (from A) +" in context["newline_joined_native_text_candidate"]
        assert context["heuristic_hints"]["preceding_native_line_ends_arithmetic_operator"]
        assert context["semantic_completeness"] is None
        assert context["notation_verified"] is False
        assert context["answer_evidence_eligible"] is False
        assert item["status"] == "needs_formula_review"
        assert item["bbox_points"] == before[0]["bbox_points"]
        assert item["region_id"] != before[0]["region_id"]
        validate_formula_context(item)
        validate_formula_context_against_page(item, doc[0])


@pytest.mark.parametrize(
    "text,relation_end,numeric",
    [
        ('The prefix thermo- =\n"heat" in this explanation.', True, False),
        ("The name has singular =\nexample in this explanation.", True, False),
        ("The specimen value is (pH = 6.8).", False, True),
        ("F = m a", False, False),
    ],
)
def test_glosses_numeric_examples_and_symbolic_relations_remain_unreviewed(
    text, relation_end, numeric
):
    with _page(text) as doc:
        item = _formula(doc[0])
        context = item["details"]["formula_context"]
        assert context["heuristic_hints"]["relation_operator_at_anchor_line_end"] is relation_end
        assert context["heuristic_hints"]["numeric_relation_rhs_pattern_present"] is numeric
        assert context["heuristic_hints"]["hint_semantics_verified"] is False
        assert "classification" not in context
        assert context["semantic_completeness"] is None
        assert item["kind"] == "formula_candidate"
        validate_formula_context(item)


def test_context_radius_is_bounded_and_retains_whole_lines():
    with _page(
        "Line zero\nLine one\nLine two\nLine three\nx = 9\nLine five\nLine six\nLine seven\nLine eight"
    ) as doc:
        item = _formula(doc[0])
        context = item["details"]["formula_context"]
        assert [line["native_text"] for line in context["lines"]] == [
            "Line two",
            "Line three",
            "x = 9",
            "Line five",
            "Line six",
        ]
        assert context["full_native_block_retained"] is False
        validate_formula_context(item)


def test_context_never_takes_a_separate_column_or_page():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_textbox((40, 80, 220, 200), "Column one\nx = 2\nOwn continuation", fontsize=10)
        page.insert_textbox((320, 80, 510, 200), "Other column\nDo not join here", fontsize=10)
        following = doc.new_page()
        following.insert_text((40, 80), "Do not join the following page")
        context = _formula(doc[0])["details"]["formula_context"]
        text = context["newline_joined_native_text_candidate"]
        assert "Own continuation" in text
        assert "Other column" not in text
        assert "following page" not in text


def test_glyph_baselines_survive_without_invented_superscript_markup():
    with pymupdf.open() as doc:
        page = doc.new_page()
        for point, text, size in [((72, 100), "E = m c", 10), ((108, 96), "2", 7)]:
            page.insert_text(point, text, fontsize=size)
        item = _formula(page)
        glyphs = [
            g for line in item["details"]["formula_context"]["lines"] for g in line["native_glyphs"]
        ]
        assert {g["font_size"] for g in glyphs} == {7, 10}
        assert {g["origin_points"][1] for g in glyphs} == {96, 100}
        assert not any("script_role" in g for g in glyphs)
        validate_formula_context(item)


def test_missing_native_anchor_stays_explicitly_unresolved():
    with _page("F = m a") as doc:
        parent = _records(doc[0], v4)[0]
        parent["native_text"] = "Absent = 8"
        parent["region_id"] = _identity(parent)
        context = recover_formula_context(doc[0], parent)
        assert context["anchor_state"] == "unresolved_native_anchor"
        assert context["lines"] == []
        assert context["semantic_completeness"] is None


@pytest.mark.parametrize(
    "character,replacements,controls", [("\ufffd", 1, 0), ("\x7f", 0, 1), ("\x93", 0, 1)]
)
def test_zero_width_native_glyph_and_character_quality_remain_visible(
    monkeypatch, character, replacements, controls
):
    from pipelines import native_formula_context_v1 as context_module

    with _page("x = 4") as doc:
        parent = _records(doc[0], v4)[0]
        blocks = context_module._native_lines(doc[0])
        anchor = blocks[0][0]
        glyph = anchor["native_glyphs"][0]
        glyph["bbox_points"][2] = glyph["bbox_points"][0]
        glyph["character"] = character
        anchor["native_text"] = "".join(g["character"] for g in anchor["native_glyphs"]).strip()
        parent["native_text"] = anchor["native_text"]
        parent["region_id"] = _identity(parent)
        monkeypatch.setattr(context_module, "_native_lines", lambda page: blocks)
        context = recover_formula_context(doc[0], parent)
        assert context["anchor_state"] == "unique_native_line"
        assert context["character_quality"]["zero_extent_glyph_count"] == 1
        assert context["character_quality"]["replacement_character_count"] == replacements
        assert context["character_quality"]["control_character_count"] == controls
        assert context["character_quality"]["corrected_characters"] == 0
        item = copy.deepcopy(parent)
        item["extractor_revision"] = "pymupdf_visual_regions_v5"
        item["details"].update(
            previous_version_region_id=parent["region_id"], formula_context=context
        )
        validate_formula_context(item)


@pytest.mark.parametrize(
    "mutation", ["source", "glyph_text", "glyph_geometry", "semantic", "anchor", "hint"]
)
def test_consumer_rejects_tampered_formula_context(mutation):
    with _page("Count\nx = 4\nAfter") as doc:
        item = _formula(doc[0])
    context = item["details"]["formula_context"]
    if mutation == "source":
        context["source_sha256"] = "b" * 64
    elif mutation == "glyph_text":
        context["lines"][0]["native_glyphs"][0]["character"] = "Z"
    elif mutation == "glyph_geometry":
        context["lines"][0]["native_glyphs"][0]["bbox_points"][2] = 900
    elif mutation == "semantic":
        context["semantic_completeness"] = True
    elif mutation == "anchor":
        context["anchor_native_order"] = [999, 999]
    elif mutation == "hint":
        context["heuristic_hints"]["hint_semantics_verified"] = True
    with pytest.raises(ValueError):
        validate_formula_context(item)


def test_actual_page_recomputation_rejects_plausible_but_forged_glyph_position():
    with _page("Count\nx = 4\nAfter") as doc:
        item = _formula(doc[0])
        item["details"]["formula_context"]["lines"][0]["native_glyphs"][0]["origin_points"][0] += (
            0.1
        )
        validate_formula_context(item)  # Shape alone cannot establish correspondence.
        with pytest.raises(ValueError, match="pinned original"):
            validate_formula_context_against_page(item, doc[0])


@pytest.mark.parametrize(
    "mutation",
    [
        "notation_false_to_zero",
        "eligibility_false_to_zero",
        "hint_false_to_zero",
        "quality_count_to_bool",
        "page_float_to_int",
    ],
)
def test_context_and_parent_identity_reject_python_boolean_numeric_aliases(mutation):
    with _page("x = 4") as doc:
        item = _formula(doc[0])
        context = item["details"]["formula_context"]
        if mutation == "notation_false_to_zero":
            context["notation_verified"] = 0
        elif mutation == "eligibility_false_to_zero":
            context["answer_evidence_eligible"] = 0
        elif mutation == "hint_false_to_zero":
            context["heuristic_hints"]["hint_semantics_verified"] = 0
        elif mutation == "quality_count_to_bool":
            context["character_quality"]["replacement_character_count"] = False
        else:
            context["page_size_points"][0] = int(context["page_size_points"][0])
        with pytest.raises(ValueError):
            validate_formula_context(item)
        with pytest.raises(ValueError):
            validate_formula_context_against_page(item, doc[0])


def test_v5_parent_restoration_rejects_integer_float_alias():
    with _page("F = m a") as doc:
        parents, items = _records(doc[0], v4), _records(doc[0])
    items[0]["details"]["page_size_points"][0] = int(items[0]["details"]["page_size_points"][0])
    with pytest.raises(ValueError, match="exact V4"):
        validate_v4_parent_lineage(items, parents)


def test_v5_parent_lineage_rejects_changed_source_text_even_with_new_identity():
    with _page("F = m a") as doc:
        parents, items = _records(doc[0], v4), _records(doc[0])
    items[0]["native_text"] = "E = m c"
    items[0]["region_id"] = _identity(items[0])
    with pytest.raises(ValueError, match="exact V4"):
        validate_v4_parent_lineage(items, parents)


def test_v5_retains_distinct_reference_target_and_raw_table_body():
    doc = pymupdf.open()
    doc.new_page(width=612, height=792)
    doc.new_page(width=612, height=792)
    source, target = doc[0], doc[1]
    source.insert_text((72, 200), "Table 9.9 describes the example data.", fontsize=9)
    source.insert_link(
        {
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(72, 189, 114, 204),
            "page": 1,
            "to": pymupdf.Point(0, 120),
        }
    )
    xs, ys = [60, 140, 300], [100, 130, 160, 190]
    for y in ys:
        target.draw_line((xs[0], y), (xs[-1], y), width=0.4)
    target.draw_line((xs[1], ys[1]), (xs[1], ys[-1]), width=0.4)
    for row, entries in enumerate([("Name", "Value"), ("A", "1"), ("B", "2")]):
        for col, text in enumerate(entries):
            target.insert_text((xs[col] + 5, ys[row] + 20), text, fontsize=10)
    target.insert_text((60, 210), "TABLE 9.9", fontsize=9)
    raw = doc.tobytes()
    doc.close()
    with pymupdf.open(stream=raw, filetype="pdf") as document:
        args = {"source_sha256": "a" * 64, "book": "Authored fixture"}
        parents = [item for p in range(2) for item in v4(document[p], physical_page=p + 1, **args)]
        items = [item for p in range(2) for item in v5(document[p], physical_page=p + 1, **args)]
    validate_v4_parent_lineage(items, parents)
    validate_reference_targets(items)
    reference = next(item for item in items if is_inline_reference(item))
    body = next(item for item in items if rectangular_table_body(item))
    validate_reference_record(reference, physical_pages=2)
    assert reference["details"]["cells"] is None
    assert reference["details"]["reference_target_locator"]["physical_pdf_page"] == 2
    assert body["details"]["cells"][1] == ["A", "1"]
    assert "formula_context" not in reference["details"]
    assert "formula_context" not in body["details"]


def _write_catalog(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")


def _fixtures(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(preparer, "ROOT", tmp_path)
    parent_dir = tmp_path / "v4-parent"
    parent_dir.mkdir()
    candidate_dir = tmp_path / "v5-catalog"
    books, totals, current_books = [], Counter(), []
    for index, slug in enumerate(builder.BOOKS):
        source = tmp_path / "originals" / f"{slug}.pdf"
        source.parent.mkdir(exist_ok=True)
        with _page(
            f"Authored fixture {index}\n7 (from A) +\n4 (from B) = 11\nContinued source prose"
        ) as doc:
            doc.save(source)
        source_hash = file_hash(source)
        acquisition = {
            "raw_path": source.relative_to(tmp_path).as_posix(),
            "sha256": source_hash,
            "title": f"Authored fixture {index}",
            "pdf_url": "https://example.invalid/source",
            "license_url": "https://example.invalid/license",
            "acquired_at": "synthetic fixture",
        }
        acquisition_path = tmp_path / "evidence/openstax" / f"{slug}-acquisition.json"
        acquisition_path.parent.mkdir(parents=True, exist_ok=True)
        acquisition_path.write_text(json.dumps(acquisition), encoding="utf-8")
        current_books.append(
            builder.scan_book(slug, candidate_dir, extractor_revision="pymupdf_visual_regions_v5")
        )
        with pymupdf.open(source) as doc:
            args = {"source_sha256": source_hash, "book": acquisition["title"], "physical_page": 1}
            old, previous, parents = v2(doc[0], **args), v3(doc[0], **args), v4(doc[0], **args)
        old_path = tmp_path / f"{slug}-v2.jsonl.gz"
        _write_catalog(old_path, old)
        catalog_name, v3_name = f"{slug}-v4.jsonl.gz", f"{slug}-v3.jsonl.gz"
        _write_catalog(parent_dir / catalog_name, parents)
        _write_catalog(parent_dir / v3_name, previous)
        totals.update(record["kind"] for record in parents)
        books.append(
            {
                "book": acquisition["title"],
                "slug": slug,
                "source_sha256": source_hash,
                "source_size_bytes": source.stat().st_size,
                "physical_pages": 1,
                "catalog_file": catalog_name,
                "catalog_sha256": file_hash(parent_dir / catalog_name),
                "previous_catalog_sha256": file_hash(old_path),
                "all_old_region_lineages_preserved": len(old),
                "parent_candidate_catalog_file": v3_name,
                "parent_candidate_catalog_sha256": file_hash(parent_dir / v3_name),
            }
        )
    parent_manifest = {
        "schema": "official_native_table_review_sources_v2",
        "candidate_revision": "pymupdf_visual_regions_v4",
        "books": books,
        "region_count": sum(totals.values()),
        "table_count": 0,
        "candidate_rectangular_grids": 0,
        "retained_unresolved_tables": 0,
        "native_glyph_records_in_table_candidates": 0,
        "inline_table_reference_count": 0,
        "linked_table_reference_count": 0,
        "human_ratings": 0,
        "semantic_approvals": 0,
        "answer_evidence_eligible_candidates": 0,
        "published_candidates": 0,
    }
    (parent_dir / "SOURCE_MANIFEST.json").write_text(json.dumps(parent_manifest), encoding="utf-8")
    current = {
        "extractor_revision": "pymupdf_visual_regions_v5",
        "scope": "full_originals",
        "pymupdf_version": pymupdf.VersionBind,
        "books": current_books,
    }
    (candidate_dir / "manifest.json").write_text(json.dumps(current), encoding="utf-8")
    source_freeze = tmp_path / "source-freeze.json"
    before = {}
    for relative in preparer.REQUIRED_SOURCE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic source-freeze fixture: " + relative, encoding="utf-8")
        before[relative] = file_hash(path)
    source_freeze.write_text(json.dumps({"before": before}), encoding="utf-8")
    return candidate_dir, parent_dir, source_freeze


def test_builder_keeps_v2_default_and_v4_v5_explicit(tmp_path, monkeypatch):
    candidate, parents, _ = _fixtures(tmp_path, monkeypatch)
    assert (
        builder.scan_book(builder.BOOKS[0], tmp_path / "default")["counts"]["formula_candidate"]
        == 1
    )
    with gzip.open(tmp_path / "default" / f"{builder.BOOKS[0]}-regions.jsonl.gz", "rt") as stream:
        assert json.loads(next(stream))["extractor_revision"] == "pymupdf_visual_regions_v2"
    manifest, books = load_bundle(
        parents, expected_manifest_sha256=file_hash(parents / "SOURCE_MANIFEST.json")
    )
    assert manifest["candidate_revision"] == "pymupdf_visual_regions_v4"
    assert len(books) == 4
    assert candidate.is_dir()


def test_v5_preparer_and_actual_consumer_retain_four_book_parent_chain(tmp_path, monkeypatch):
    candidate, parents, freeze = _fixtures(tmp_path, monkeypatch)
    output = tmp_path / "prepared-v5"
    manifest = preparer.prepare_bundle(
        candidate,
        parents,
        freeze,
        output,
        expected_parent_manifest_sha256=file_hash(parents / "SOURCE_MANIFEST.json"),
    )
    checked, books = load_bundle(
        output, expected_manifest_sha256=file_hash(output / "SOURCE_MANIFEST.json")
    )
    assert checked == manifest
    assert manifest["formula_context_count"] == 4
    assert manifest["unresolved_formula_context_count"] == 0
    assert manifest["native_glyph_records_in_formula_context_candidates"] > 0
    assert len(books) == 4
    assert all(item["status"] == "needs_formula_review" for _, items in books for item in items)
    with pytest.raises(FileExistsError):
        preparer.prepare_bundle(
            candidate,
            parents,
            freeze,
            output,
            expected_parent_manifest_sha256=file_hash(parents / "SOURCE_MANIFEST.json"),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "parent_path",
        "parent_bytes",
        "count",
        "version",
        "approval",
        "config_bool_alias",
        "counter_bool_alias",
        "approval_bool_alias",
    ],
)
def test_v5_bundle_rejects_parent_escape_corruption_counts_and_approval(
    tmp_path, monkeypatch, mutation
):
    candidate, parents, freeze = _fixtures(tmp_path, monkeypatch)
    output = tmp_path / "prepared-v5"
    manifest = preparer.prepare_bundle(
        candidate,
        parents,
        freeze,
        output,
        expected_parent_manifest_sha256=file_hash(parents / "SOURCE_MANIFEST.json"),
    )
    if mutation == "parent_path":
        manifest["books"][0]["previous_version_catalog_file"] = "../outside.jsonl.gz"
    elif mutation == "parent_bytes":
        (output / manifest["books"][0]["previous_version_catalog_file"]).write_bytes(b"changed")
    elif mutation == "count":
        manifest["formula_context_count"] += 1
    elif mutation == "version":
        manifest["candidate_revision"] = "pymupdf_visual_regions_v6"
    elif mutation == "config_bool_alias":
        manifest["frozen_configuration"]["formula_context"]["native_block_only"] = 1
    elif mutation == "counter_bool_alias":
        manifest["unresolved_formula_context_count"] = False
    elif mutation == "approval_bool_alias":
        manifest["semantic_approvals"] = False
    else:
        manifest["semantic_approvals"] = 1
    path = output / "SOURCE_MANIFEST.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AppError):
        load_bundle(output, expected_manifest_sha256=file_hash(path))


@pytest.mark.parametrize(
    "mutation",
    [
        "slug_escape",
        "duplicate_slug",
        "absolute_catalog",
        "relative_catalog_escape",
        "output_escape",
        "parent_pin",
    ],
)
def test_preparer_rejects_path_and_identity_escapes_before_writes(tmp_path, monkeypatch, mutation):
    candidate, parents, freeze = _fixtures(tmp_path, monkeypatch)
    output = tmp_path / "prepared-v5"
    parent_pin = file_hash(parents / "SOURCE_MANIFEST.json")
    path = candidate / "manifest.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "slug_escape":
        current["books"][0]["slug"] = "../escaped"
    elif mutation == "duplicate_slug":
        current["books"][1]["slug"] = current["books"][0]["slug"]
    elif mutation == "absolute_catalog":
        current["books"][0]["catalog_path"] = str(
            (tmp_path / current["books"][0]["catalog_path"]).resolve()
        )
    elif mutation == "relative_catalog_escape":
        current["books"][0]["catalog_path"] = "../outside.jsonl.gz"
    elif mutation == "output_escape":
        output = tmp_path.parent / "outside-output"
    else:
        parent_pin = "b" * 64
    path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises((ValueError, AppError)):
        preparer.prepare_bundle(
            candidate, parents, freeze, output, expected_parent_manifest_sha256=parent_pin
        )
    assert not output.exists()
    assert not (tmp_path / "escaped-parent-v3.jsonl.gz").exists()
