"""Keep exact publisher alternatives and separate accepted/rejected visual matches."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
PDF_SHA = "fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6"
REVIEW = [
    (
        475,
        "9-exercises",
        "f219e76dcd5d15375e8e6c354bbf78b501451a17",
        False,
        "Six Gas A-F panels match the page layout and most curve descriptions.",
        "PDF Gas C and D vertical axes are labeled Z, but publisher alternative calls them Moles. Alternative also adds an n,P constant label to Gas D that is absent from the PDF. Reject as a faithful full-image transcription.",
    ),
    (
        1008,
        "20-4-amines-and-amides",
        "40592effc64d3941984b390f67cacd68da8392a5",
        False,
        "Ten functional-group table rows and their formula/model/name columns match the PDF figure, which is an image in both sources, not a native HTML table.",
        "Publisher alternative names the ether example (C2H5)2O 'ethanal'; the PDF explicitly names it 'diethyl ether'. Alternative also contains a conflicting aldehyde model description ('two black bonds bonded to two red balls') before its next sentence. Reject the complete alternative; no silent correction of publisher text.",
    ),
    (
        1071,
        "a-the-periodic-table",
        "d3d45f73798bd713c14d3518aa2c65e8956b2954",
        False,
        "Periodic-table structure, detached series and hydrogen inset correspond to the PDF.",
        "Alternative is a generic layout summary, without the individual element values needed to replace the image. It describes nonmetal cells as peach, while the PDF legend/cells are pale blue-green. Reject as complete faithful transcription; preserve original and require reviewed extraction.",
    ),
    (
        1079,
        "b-essential-mathematics",
        "f743d5d5701024bd51baa19d69b301209465d6d4",
        True,
        "Agent visually matched graph title y=x^2+2, x range0-4.5, y range0-20, and four plotted points (1,3),(2,6),(3,11),(4,18) to the PDF rendering.",
        "Alternative describes the graph, not the two-row continuation table above it. Native PDF text already preserves those table values. This is bounded source matching, not independent human scientific review.",
    ),
    (
        1160,
        "chapter-10",
        "e378508f27e62b5e35760baac2f329b09dd35039",
        False,
        "Top phase-diagram axes and geometric layout correspond to the PDF's carbon liquid/vapor panel.",
        "Alternative calls the phases Water(liquid) and Water vapor(gas), whereas the PDF says Carbon(liquid) and Carbon vapor(gas). It calls the near-vertical boundary negatively sloped, while the PDF boundary slopes positively. Reject; do not import these conflicting labels.",
    ),
    (
        1160,
        "chapter-10",
        "3ef87d848f6c20e30649653f8a380246cc64a02a",
        False,
        "Lower phase diagram's Graphite label and overall axes match the PDF.",
        "Alternative describes the near-vertical boundary as negatively sloped, while the PDF boundary slopes positively. Reject as a full-image transcription; preserve PDF for reviewed OCR.",
    ),
]


def main():
    acquisitions = json.loads(
        (ROOT / "evidence/openstax/chemistry-supplement-candidate-acquisitions.json").read_text(
            encoding="utf-8"
        )
    )
    entries, rejected = [], []
    for physical, page_slug, resource, accepted, scope, limits in REVIEW:
        acquisition = next(a for a in acquisitions if a["page_slug"] == page_slug)
        raw = (ROOT / acquisition["original_path"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == acquisition["html_sha256"]
        matches = [i for i in acquisition["candidate_images"] if i["src"].endswith("/" + resource)]
        assert len(matches) == 1
        alternative = matches[0]["alt"]
        target = ROOT / "artifacts/storage/supplements" / (digest + ".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as output:
                output.write(raw)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        item = {
            "kind": "official_html_image_alt",
            "physical_page": physical,
            "pdf_sha256": PDF_SHA,
            "source_url": acquisition["requested_url"],
            "acquired_at": acquisition["acquired_at"],
            "acquisition_time_basis": "HTTP response completed and immutable source bytes saved in this audit run",
            "html_sha256": digest,
            "html_size_bytes": len(raw),
            "image_resource": resource,
            "image_url": urljoin("https://openstax.org", matches[0]["src"]),
            "text_sha256": hashlib.sha256(alternative.encode("utf-8")).hexdigest(),
            "storage_path": target.relative_to(ROOT / "artifacts/storage").as_posix(),
            "original_path": acquisition["original_path"],
            "review_evidence": f"evidence/openstax/inspection/chemistry-2e/physical-{physical:04}.png",
            "review_scope": scope,
            "remaining_limits": limits,
            "license": "Official page states CC BY-NC-SA4.0 with OpenStax/Rice University attribution; original HTML and PDF terms retained.",
            "exact_publisher_text": alternative,
            "review_status": "accepted_bounded_visual_match"
            if accepted
            else "rejected_incomplete_or_contradictory",
            "applied_to_processing": False,
        }
        (entries if accepted else rejected).append(item)
    result = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "rejected_candidates": rejected,
        "scope": "Five requested Chemistry PDF pages compared with immutable official HTML. Only graph1079 has an accepted faithful alternative. Rejected source bytes/text remain retained for audit; their presence does not clear quality gates.",
        "original_rutherford_supplement": "evidence/openstax/chemistry-publisher-supplement.json",
        "acquisitions": "evidence/openstax/chemistry-supplement-candidate-acquisitions.json",
        "native_html_table_status": "The PDF1008 summary table is an image in official HTML, with one full-image alt. No native HTML table replacement was fabricated.",
    }
    path = ROOT / "evidence/openstax/chemistry-additional-supplements.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"accepted": len(entries), "rejected": len(rejected), "path": str(path)}))


if __name__ == "__main__":
    main()
