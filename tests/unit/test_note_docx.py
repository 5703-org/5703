"""Inert, readable note exports preserve citation metadata and hostile input."""

from io import BytesIO
import zipfile
from xml.etree import ElementTree as ET

from app.modules.learning_product.note_docx import notes_docx

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def test_owned_text_and_provenance_survive_document_export_without_active_parts():
    source_url = "https://assets.openstax.org/" + "source-" * 60 + "biology.pdf"
    hostile = '<w:hyperlink r:id="remote">SECRET_MARKER</w:hyperlink> & [run](javascript:evil)'
    content = "\n".join(
        [
            "# Personal learning notes",
            "",
            "## Transport & gradients",
            hostile,
            "Source URL: " + source_url,
            "Original SHA256: " + "a" * 64,
            "The saved textbook source is currently unavailable.",
        ]
    )
    with zipfile.ZipFile(BytesIO(notes_docx(content))) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        text = "\n".join(node.text or "" for node in document.findall(".//w:t", NS))
        assert hostile in text and source_url in text and "a" * 64 in text
        assert "currently unavailable" in text
        assert not document.findall(".//w:hyperlink", NS)
        for name in archive.namelist():
            assert not name.endswith(".bin") and "embeddings/" not in name
            if name.endswith(".rels"):
                relationships = ET.fromstring(archive.read(name))
                assert all(row.attrib.get("TargetMode") != "External" for row in relationships)
        paragraphs = document.findall(".//w:body/w:p", NS)
        title = paragraphs[0].find("w:pPr/w:pStyle", NS)
        assert title.get("{" + NS["w"] + "}val") == "Title"
        heading = paragraphs[2].find("w:pPr/w:pStyle", NS)
        assert heading.get("{" + NS["w"] + "}val") == "Heading1"


def test_xml_invalid_controls_remain_visible_and_unicode_stays_readable():
    with zipfile.ZipFile(
        BytesIO(notes_docx("# Notes\nA\x00B\ud800C\nCO₂ → ΔG; 生物 🧬"))
    ) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        text = "\n".join(node.text or "" for node in document.findall(".//w:t", NS))
        assert "A\ufffdB\ufffdC" in text
        assert "CO₂ → ΔG; 生物 🧬" in text
