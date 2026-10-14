"""A document-shaped fixture checks geometry, lineage and review boundaries."""

import pymupdf

from pipelines.visual_regions import EXTRACTOR_REVISION, extract_page_regions


def test_visual_regions_are_source_bound_and_never_marked_verified(tmp_path):
    file = tmp_path / "fixture.pdf"
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    pixmap.clear_with(0xFF0000)
    page.insert_image(pymupdf.Rect(72, 80, 172, 180), stream=pixmap.tobytes("png"))
    page.insert_text((72, 205), "FIGURE 1.2 Cell diagram")
    page.insert_text((72, 240), "TABLE 1.3 Measurements")
    page.insert_text((72, 270), "E = mc2")
    document.save(file)
    document.close()

    with pymupdf.open(file) as source:
        first = extract_page_regions(
            source[0], source_sha256="a" * 64, book="Fixture", physical_page=1
        )
        second = extract_page_regions(
            source[0], source_sha256="a" * 64, book="Fixture", physical_page=1
        )
        other_source = extract_page_regions(
            source[0], source_sha256="b" * 64, book="Fixture", physical_page=1
        )
    assert first == second
    assert {item["kind"] for item in first} == {
        "figure_image",
        "table_candidate",
        "formula_candidate",
    }
    assert all(item["status"].startswith("needs_") for item in first)
    assert all(item["extractor_revision"] == EXTRACTOR_REVISION for item in first)
    assert {item["region_id"] for item in first}.isdisjoint(
        {item["region_id"] for item in other_source}
    )
    figure = next(item for item in first if item["kind"] == "figure_image")
    assert figure["details"]["caption_label"] == "Figure 1.2"
    assert figure["physical_pdf_page"] == 1
    assert len(figure["bbox_points"]) == 4


def test_formula_candidate_retains_exact_native_line_without_claiming_semantics(tmp_path):
    file = tmp_path / "symbols.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 70), "F = m a")
    document.save(file)
    document.close()
    with pymupdf.open(file) as source:
        regions = extract_page_regions(
            source[0], source_sha256="c" * 64, book="Fixture", physical_page=1
        )
    assert len(regions) == 1
    assert regions[0]["native_text"] == "F = m a"
    assert regions[0]["status"] == "needs_formula_review"
