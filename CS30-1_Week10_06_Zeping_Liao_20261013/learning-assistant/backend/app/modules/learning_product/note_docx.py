"""Render owned note exports as inert OOXML with real document headings."""

from io import BytesIO
import zipfile
from xml.sax.saxutils import escape


def _xml_text(value: str) -> str:
    # Invalid XML characters are represented visibly rather than breaking the export.
    cleaned = "".join(
        character
        if character in "\t\n\r"
        or "\u0020" <= character <= "\ud7ff"
        or "\ue000" <= character <= "\ufffd"
        or "\U00010000" <= character <= "\U0010ffff"
        else "\ufffd"
        for character in value
    )
    return escape(cleaned)


def notes_docx(markdown: str) -> bytes:
    """Retain note/citation text and order without executable or external parts.

    Only level-one and level-two heading markers have document formatting.
    URLs and all other note markup remain literal text, without active links.
    """
    paragraphs = []
    for line in markdown.splitlines():
        style = None
        if line.startswith("## "):
            style, line = "Heading1", line[3:]
        elif line.startswith("# "):
            style, line = "Title", line[2:]
        properties = (
            '<w:pPr><w:pStyle w:val="' + style + '"/><w:keepNext/></w:pPr>' if style else ""
        )
        paragraphs.append(
            "<w:p>"
            + properties
            + '<w:r><w:t xml:space="preserve">'
            + _xml_text(line)
            + "</w:t></w:r></w:p>"
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paragraphs) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        "</w:sectPr></w:body></w:document>"
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="22"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="100"/></w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/>'
        '<w:spacing w:before="0" w:after="180"/></w:pPr><w:rPr><w:b/>'
        '<w:sz w:val="36"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/>'
        '<w:spacing w:before="160" w:after="100"/><w:outlineLvl w:val="0"/></w:pPr>'
        '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style></w:styles>'
    )
    content = BytesIO()
    with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
    return content.getvalue()
