"""Source quality, safe normalization, physical pages and exact chunk spans."""

import hashlib
from unittest.mock import patch
from types import SimpleNamespace
import pytest
from pipelines.clean import clean_source_text
from pipelines.parse import parse
from pipelines.chunk import chunks
from pipelines.pdf_structure import split_bookmarked_page


def unit(id, text, sequence=1, page=1, section="Biology", quality="ready"):
    return {
        "id": id,
        "sequence": sequence,
        "page": page,
        "section": section,
        "cleaned_text": text,
        "quality": quality,
    }


def test_clean_preserves_scientific_symbols_and_ambiguous_hard_hyphens():
    raw = "\ufeffOpenStax Biology 2e\r\n\r\nThe equation is x² = 4.\r\nWell-\r\nknown reactions use ATP.\r\nPhoto\u00ad\r\nsynthesis captures energy."
    cleaned = clean_source_text(raw)
    assert "x² = 4" in cleaned and "x2" not in cleaned
    assert "Well-known" in cleaned and "Photosynthesis" in cleaned
    assert "OpenStax Biology 2e" not in cleaned and "\ufeff" not in cleaned
    assert clean_source_text(cleaned) == cleaned


def test_txt_heading_quality_and_original_text_remain_available(tmp_path):
    path = tmp_path / "source.txt"
    raw = "# Plants\nPhotosynthesis stores light energy in sugars.\n\n# Review\nUnusual \ufffd extraction needs review."
    path.write_text(raw, encoding="utf-8")
    units = parse(path, "text/plain")
    assert [u["section"] for u in units] == ["Plants", "Review"]
    assert all(u["page"] == 1 for u in units)
    assert units[0]["quality"] == "ready" and units[1]["quality"] == "blocked"
    assert units[1]["raw_text"].find("\ufffd") >= 0
    path.write_text("", encoding="utf-8")
    assert parse(path, "text/plain")[0]["issues"][0]["code"] == "EMPTY_UNIT"


def test_physical_pdf_pages_carry_real_sections_and_flag_removed_furniture(tmp_path):
    texts = [
        "Repeated Book Header\n1.1 Plants\nPlants use light.\nThe process stores energy.\nMore source text follows.\nRepeated footer",
        "Repeated Book Header\nPhotosynthesis also uses water.\nThese paragraphs continue the same section.\nAdditional source sentences.\nThe next paragraph continues.\nRepeated footer",
        "Repeated Book Header\n1.2 Cells\nCells contain membranes.\nThis is another section.\nMore original source text.\nRepeated footer",
    ]
    reader = SimpleNamespace(
        is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda t=t: t) for t in texts]
    )
    with patch("pipelines.parse.PdfReader", return_value=reader):
        units = parse(tmp_path / "synthetic.pdf", "application/pdf")
    page_two = [u for u in units if u["page"] == 2]
    assert page_two and all(u["section"] == "1.1 Plants" for u in page_two)
    assert any(u["section"] == "1.2 Cells" for u in units)
    assert any("Repeated Book Header" in u["raw_text"] for u in units)
    assert all("Repeated Book Header" not in u["cleaned_text"] for u in units)
    assert not any(u["quality"] == "blocked" for u in units)


def test_actual_pypdf_extracts_authored_bytes_with_physical_pages(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for heading, sentence in [
        ("1.1 Plants", "Photosynthesis captures light energy in sugars."),
        ("1.2 Cells", "Cell membranes regulate exchange with the environment."),
    ]:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 72 720 Td ({heading}) Tj 0 -24 Td ({sentence}) Tj ET".encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "authored-two-page.pdf"
    with path.open("wb") as output:
        writer.write(output)
    units = parse(path, "application/pdf")
    assert [(u["page"], u["section"]) for u in units] == [(1, "1.1 Plants"), (2, "1.2 Cells")]
    assert units[0]["cleaned_text"] == "Photosynthesis captures light energy in sugars."
    assert units[1]["quality"] == "ready" and "Cell membranes" in units[1]["raw_text"]


def test_pdf_page_extraction_failure_preserves_other_pages_and_blocks_publication(tmp_path):
    def broken_page():
        raise ValueError("Authored malformed page stream")

    reader = SimpleNamespace(
        is_encrypted=False,
        pages=[
            SimpleNamespace(
                extract_text=lambda: "1.1 Plants\nPhotosynthesis stores light energy in sugars."
            ),
            SimpleNamespace(extract_text=broken_page),
            SimpleNamespace(
                extract_text=lambda: "Unlabelled continuation remains available for source review."
            ),
        ],
    )
    with patch("pipelines.parse.PdfReader", return_value=reader):
        units = parse(tmp_path / "three-pages.pdf", "application/pdf")
    assert [u["page"] for u in units] == [1, 2, 3]
    assert [u["quality"] for u in units] == ["ready", "blocked", "ready"]
    failed = units[1]
    assert failed["raw_text"] == failed["cleaned_text"] == ""
    assert failed["issues"][0]["code"] == "PDF_PAGE_EXTRACTION_FAILED"
    assert "physical page 2" in failed["issues"][0]["message"]
    assert "malformed page stream" in failed["issues"][0]["message"]
    assert units[2]["section"] == "Page 3"
    assert len(chunks([{**u, "id": str(u["sequence"])} for u in units], "p")) == 2


def test_chunks_repeatable_unique_across_sections_and_reconstruct_exact_spans():
    units = [
        unit("u1", "Cells contain membranes and genetic material.", 1, 1, "Cells"),
        unit("u2", "Membranes regulate exchange with the environment.", 2, 2, "Cells"),
        unit("u3", "Cells contain membranes and genetic material.", 3, 3, "Review"),
    ]
    result = chunks(units, "processing1", target=20, cap=30, overlap=3)
    assert result == chunks(units, "processing1", target=20, cap=30, overlap=3)
    assert len({c["id"] for c in result}) == len(result)
    assert any(c["pages"] == [1, 2] for c in result)
    lookup = {u["id"]: u for u in units}
    for chunk in result:
        assert chunk["text_hash"] == hashlib.sha256(chunk["text"].encode()).hexdigest()
        for span in chunk["spans"]:
            assert (
                chunk["text"][span["chunk_start"] : span["chunk_end"]]
                == lookup[span["unit_id"]]["cleaned_text"][span["start"] : span["end"]]
            )
    duplicate_text = chunks(
        [
            unit("first", "identical text", section="One"),
            unit("second", "identical text", 2, section="Two"),
        ],
        "proc",
    )
    assert duplicate_text[0]["id"] != duplicate_text[1]["id"]


def test_exact_tokenizer_bounds_long_text_and_no_unmapped_character_loss():
    text = "abcdefghijklmnopqrstuvwxyz" * 10
    result = chunks(
        [unit("u1", text, section="S")],
        "proc",
        target=20,
        cap=25,
        overlap=0,
        tokenizer=lambda value: list(value),
        model_window=50,
    )
    assert "".join(c["text"] for c in result) == text
    assert all(c["tokens"] <= 20 and len("passage: S\n" + c["text"]) <= 50 for c in result)
    with pytest.raises(ValueError, match="heading"):
        chunks(
            [unit("u1", "content", section="Heading too long")],
            "proc",
            target=10,
            cap=10,
            overlap=0,
            tokenizer=lambda value: list(value),
            model_window=5,
        )


def test_excluded_units_and_section_changes_never_merge():
    units = [
        unit("u1", "First usable text.", 1),
        unit("u2", "Excluded source.", 2, quality="excluded"),
        unit("u3", "Third usable text.", 3),
    ]
    result = chunks(units, "proc")
    assert len(result) == 2
    assert all(len(c["spans"]) == 1 for c in result)
    assert "Excluded" not in " ".join(c["text"] for c in result)
    with pytest.raises(ValueError):
        chunks(units, "proc", target=10, overlap=10)


def test_fixed_and_structure_strategies_preserve_source_coverage_with_distinct_boundaries():
    sources = [
        unit(
            "u1",
            "Plants retain light energy in sugars.\n\nWater and carbon dioxide are required.",
            1,
        ),
        unit("u2", "Cells release useful energy from those sugars.\n\nATP transfers energy.", 2),
        unit(
            "excluded",
            "This quarantined text must never enter either strategy.",
            3,
            quality="excluded",
        ),
        unit("u4", "Genetic material carries inherited information. " * 20, 4),
    ]
    outputs = {
        strategy: chunks(
            sources, "same-processing-fixture", target=32, cap=40, overlap=3, strategy=strategy
        )
        for strategy in ("fixed", "structure")
    }
    assert any(len(c["spans"]) > 1 for c in outputs["structure"])
    assert all(len(c["spans"]) == 1 for c in outputs["fixed"])
    assert [c["text_hash"] for c in outputs["fixed"]] != [
        c["text_hash"] for c in outputs["structure"]
    ]
    lookup = {source["id"]: source for source in sources}
    for strategy, result in outputs.items():
        assert result == chunks(
            sources, "same-processing-fixture", target=32, cap=40, overlap=3, strategy=strategy
        )
        covered = {source["id"]: set() for source in sources}
        for chunk in result:
            assert chunk["tokens"] <= 32
            assert chunk["text_hash"] == hashlib.sha256(chunk["text"].encode()).hexdigest()
            for span in chunk["spans"]:
                source = lookup[span["unit_id"]]
                assert source["quality"] == "ready"
                assert (
                    chunk["text"][span["chunk_start"] : span["chunk_end"]]
                    == source["cleaned_text"][span["start"] : span["end"]]
                )
                covered[source["id"]].update(range(span["start"], span["end"]))
        for source in sources:
            if source["quality"] == "ready":
                assert all(
                    i in covered[source["id"]]
                    for i, ch in enumerate(source["cleaned_text"])
                    if not ch.isspace()
                )
            else:
                assert not covered[source["id"]]


def test_bookmarks_prevent_contents_false_sections_and_preserve_midpage_continuation():
    def destination(title, section=None, top=400, top_level=False):
        return {"title": title, "section": section or title, "top": top, "top_level": top_level}

    destinations = {
        1: [destination("Contents", top=734, top_level=True)],
        3: [destination("Preface", top=734, top_level=True)],
        5: [
            destination("Chapter 1 Plants", top=734, top_level=True),
            destination("1.1 Light", "Chapter 1 Plants / 1.1 Light", top=200),
        ],
        6: [destination("1.2 Water", "Chapter 1 Plants / 1.2 Water")],
    }
    toc = "Contents\n1.1 Light 4\n1.2 Water 5\n"
    parts, carry = split_bookmarked_page(toc, 1, destinations, None)
    assert len(parts) == 1 and parts[0][0] == "Contents" and parts[0][1] == toc
    parts, carry = split_bookmarked_page("More contents\n2.1 Cells 10\n", 2, destinations, carry)
    assert all(p[0] == "Contents" for p in parts)
    parts, carry = split_bookmarked_page("PREFACE\nAbout this source.\n", 3, destinations, carry)
    assert carry == "Preface"
    opening = "CHAPTER 1\nPlants\n1.1 Light\n1.2 Water\nChapter introduction.\n1.1 Light\nLEARNING OBJECTIVES\nPlants need light.\n"
    parts, carry = split_bookmarked_page(opening, 5, destinations, carry)
    assert len(parts) == 2 and parts[0][0] == "Chapter 1 Plants"
    assert "Chapter introduction." in parts[0][1]
    assert parts[1][1].startswith("1.1 Light\nLEARNING OBJECTIVES")
    continuation = "Previous section finishes here.\n1.2 Water\nLEARNING OBJECTIVES\nWater is used in photosynthesis.\n"
    parts, carry = split_bookmarked_page(continuation, 6, destinations, carry)
    assert parts[0][0] == "Chapter 1 Plants / 1.1 Light"
    assert parts[0][1] == "Previous section finishes here.\n"
    assert parts[1][0] == carry == "Chapter 1 Plants / 1.2 Water"
    assert "".join(p[1] for p in parts) == continuation


def test_low_text_visual_page_blocks_while_prose_retains_visual_limitations(tmp_path):
    def page(text):
        return SimpleNamespace(
            extract_text=lambda: text,
            get_contents=lambda: SimpleNamespace(operations=[([], b"Do")]),
        )

    reader = SimpleNamespace(
        is_encrypted=False,
        pages=[page("Preface 3"), page("Visible scientific prose is retained. " * 8)],
    )
    with patch("pipelines.parse.PdfReader", return_value=reader):
        units = parse(tmp_path / "illustrated.pdf", "application/pdf")
    assert units[0]["raw_text"] == "Preface 3" and units[0]["quality"] == "blocked"
    assert "LOW_TEXT_IMAGE_PAGE" in {i["code"] for i in units[0]["issues"]}
    assert units[1]["quality"] == "ready"
    assert "UNEXTRACTED_VISUAL_CONTENT" in {i["code"] for i in units[1]["issues"]}
    assert "LOW_TEXT_IMAGE_PAGE" not in {i["code"] for i in units[1]["issues"]}


def test_actual_unbookmarked_pdf_prefix_uses_page_local_labels_and_preserves_v4(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    texts = [
        "Authored title and publisher information before any bookmark.",
        "Copyright and licensing details on the second physical page.",
        "Contents\nSection 1 Plants and the environment 12",
        "Continued contents listing: Section 2 Cells and membranes 24",
    ]
    for source in texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        operations = " 0 -24 Td ".join(f"({line}) Tj" for line in source.splitlines())
        stream.set_data(f"BT /F1 12 Tf 72 720 Td {operations} ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_outline_item("Contents", 2)
    path = tmp_path / "unbookmarked-prefix.pdf"
    with path.open("wb") as destination:
        writer.write(destination)
    original = path.read_bytes()
    current = parse(path, "application/pdf")
    legacy = parse(path, "application/pdf", parser_revision="pypdf_bookmarks_v4")
    assert [u["section"] for u in current] == [
        "PDF physical page 1",
        "PDF physical page 2",
        "Contents",
        "Contents",
    ]
    assert [u["section"] for u in legacy] == [
        "PDF physical page 1",
        "PDF physical page 1",
        "Contents",
        "Contents",
    ]
    assert [u["page"] for u in current] == [1, 2, 3, 4]
    for old, new in zip(legacy, current, strict=True):
        assert {k: v for k, v in old.items() if k != "section"} == {
            k: v for k, v in new.items() if k != "section"
        }
    assert path.read_bytes() == original
