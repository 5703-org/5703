"""Record source-checked Anatomy OCR reading order and exact visible text."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "evidence/openstax/transcriptions"
OUTPUT.mkdir(exist_ok=True)
PDF_HASH = "aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46"

table = """Formed element | Major subtypes | Numbers present per microliter (μL) and mean (range) | Appearance in a standard blood smear | Summary of functions | Comments
Erythrocytes (red blood cells) | [blank cell] | 5.2 million (4.4–6.0 million) | Flattened biconcave disk; no nucleus; pale red color | Transport oxygen and some carbon dioxide between tissues and lungs | Lifespan of approximately 120 days
Leukocytes (white blood cells) | [blank cell] | 7000 (5000–10,000) | Obvious dark-staining nucleus | All function in body defenses | Exit capillaries and move into tissues; lifespan of usually a few hours or days
Leukocytes (white blood cells) | Granulocytes including neutrophils, eosinophils, and basophils | 4360 (1800–9950) | Abundant granules in cytoplasm; nucleus normally lobed | Nonspecific (innate) resistance to disease | Classified according to membrane-bound granules in cytoplasm
Leukocytes (white blood cells) | Neutrophils | 4150 (1800–7300) | Nuclear lobes increase with age; pale lilac granules | Phagocytic; particularly effective against bacteria. Release cytotoxic chemicals from granules | Most common leukocyte; lifespan of minutes to days
Leukocytes (white blood cells) | Eosinophils | 165 (0–700) | Nucleus generally two-lobed; bright red-orange granules | Phagocytic cells; particularly effective with antigen-antibody complexes. Release antihistamines. Increase in allergies and parasitic infections | Lifespan of minutes to days
Leukocytes (white blood cells) | Basophils | 44 (0–150) | Nucleus generally two-lobed but difficult to see due to presence of heavy, dense, dark purple granules | Promotes inflammation | Least common leukocyte; lifespan unknown
Leukocytes (white blood cells) | Agranulocytes including lymphocytes and monocytes | 2640 (1700–4950) | Lack abundant granules in cytoplasm; have a simple-shaped nucleus that may be indented | Body defenses | Group consists of two major cell types from different lineages
Leukocytes (white blood cells) | Lymphocytes | 2185 (1500–4000) | Spherical cells with a single often large nucleus occupying much of the cell’s volume; stains purple; seen in large (natural killer cells) and small (B and T cells) variants | Primarily specific (adaptive) immunity: T cells directly attack other cells (cellular immunity); B cells release antibodies (humoral immunity); natural killer cells are similar to T cells but nonspecific | Initial cells originate in bone marrow, but secondary production occurs in lymphatic tissue; several distinct subtypes; memory cells form after exposure to a pathogen and rapidly increase responses to subsequent exposure; lifespan of many years
Leukocytes (white blood cells) | Monocytes | 455 (200–950) | Largest leukocyte with an indented or horseshoe-shaped nucleus | Very effective phagocytic cells engulfing pathogens or worn out cells; also serve as antigen-presenting cells (APCs) for other components of the immune system | Produced in red bone marrow; referred to as macrophages after leaving circulation
Platelets | [blank cell] | 350,000 (150,000–500,000) | Cellular fragments surrounded by a plasma membrane and containing granules; purple stain | Hemostasis plus release growth factors for repair and healing of tissue | Formed from megakaryocytes that remain in the red bone marrow and shed platelets into circulation"""

labels = """21.1 • Anatomy of the Lymphatic and Immune Systems
Adenoid
Tonsil
Right lymphatic duct, entering vein
Lymph nodes
Thymus
Thymus [repeated label at enlarged inset]
Spleen
Lymph node
Bone marrow
Lymph vessel"""

foot_table = """FIGURE 11.35 Intrinsic Muscles in the Foot
Group | Movement | Target | Target motion direction | Prime mover | Origin | Insertion
Dorsal group | Extends toes 2–5 | Toes 2–5 | Extension | Extensor digitorum brevis | Calcaneus; extensor retinaculum | Base of proximal phalanx of big toe; extensor expansions on toes 2–5
Plantar group (layer 1) | Abducts and flexes big toe | Big toe | Adduction; flexion | Abductor hallucis | Calcaneal tuberosity; flexor retinaculum | Proximal phalanx of big toe
Plantar group (layer 1) | Flexes toes 2–4 | Middle toes | Flexion | Flexor digitorum brevis | Calcaneal tuberosity | Middle phalanx of toes 2–4
Plantar group (layer 1) | Abducts and flexes small toe | Toe 5 | Abduction; flexion | Abductor digiti minimi | Calcaneal tuberosity | Proximal phalanx of little toe
Plantar group (layer 2) | Assists in flexing toes 2–5 | Toes 2–5 | Flexion | Quadratus plantae | Medial and lateral sides of calcaneus | Tendon of flexor digitorum longus
Plantar group (layer 2) | Extends toes 2–5 at the interphalangeal joints; flexes the small toes at the metatarsophalangeal joints | Toes 2–5 | Extension; flexion | Lumbricals | Tendons of flexor digitorum longus | Medial side of proximal phalanx of toes 2–5
Plantar group (layer 3) | Flexes big toe | Big toe | Flexion | Flexor hallucis brevis | Lateral cuneiform; cuboid bones | Base of proximal phalanx of big toe
Plantar group (layer 3) | Adducts and flexes big toe | Big toe | Adduction; flexion | Adductor hallucis | Bases of metatarsals 2–4; fibularis longus tendon sheath; ligament across metatarsophalangeal joints | Base of proximal phalanx of big toe
Plantar group (layer 3) | Flexes small toe | Little toe | Flexion | Flexor digiti minimi brevis | Base of metatarsal 5; tendon sheath of fibularis longus | Base of proximal phalanx of little toe
Plantar group (layer 4) | Abducts and flexes middle toes at metatarsophalangeal joints; extends middle toes at interphalangeal joints | Middle toes | Abduction; flexion; extension | Dorsal interossei | Sides of metatarsals | Both sides of toe 2; for each other toe, extensor expansion over first phalanx on side opposite toe 2
Plantar group (layer 4) | Abducts toes 3–5; flexes proximal phalanges and extends distal phalanges | Small toes | Abduction; flexion; extension | Plantar interossei | Side of each metatarsal that faces metatarsal 2 (absent from metatarsal 2) | Extensor expansion on first phalanx of each toe (except toe 2) on side facing toe 2"""

for page, transcript, corrections, limits in [
    (
        470,
        foot_table,
        [
            "Reconstructed six original columns, eleven muscle rows and five group heading rows; added a repeated Group field to preserve each visible group-to-row relationship.",
            "Recovered OCR rotated/garbled digitorum and longus labels from the rendered source, restored dropped characters in direction/flexion/hallucis/joints and missing toe-range separators.",
            "Preserved the actual source inconsistency: the Abductor hallucis row says Abducts in Movement but Adduction in Target motion direction. Also retained the printed Abducts/Abduction wording for Plantar interossei. No anatomical correction was substituted.",
        ],
        "Every included cell was compared against the official page. Table geometry and type styling are normalized into labeled rows. The printed motion-label inconsistencies are retained, so this transcription does not certify scientific correctness. Independent human anatomical review remains pending.",
    ),
    (
        756,
        table,
        [
            "Reconstructed six table columns and ten body rows from visible cell boundaries; repeated the visibly merged Leukocytes label on its subtype rows for unambiguous text reading.",
            "Restored source-visible missing range separators in 1800–7300 and 150,000–500,000; corrected OCR neutrphils to neutrophils and ineages to lineages.",
            "Joined wrapped words/phrases, restored the visible opening parenthesis in (adaptive), and omitted OCR false characters detected inside cell illustrations.",
            "Explicit [blank cell] markers represent visibly empty cells. No values were filled from outside scientific knowledge.",
        ],
        "All included table text and numerical ranges were checked against the source rendering. Cell illustrations, colors and visual cell morphology are not reproduced as image data. Typography and merged labels are normalized for reading; this is agent source verification, not independent human or clinical review.",
    ),
    (
        935,
        labels,
        [
            "Discarded false OCR Y from the drawing; kept all visible body labels, including two Thymus labels.",
            "Recorded the repeated inset label explicitly. The publisher alternative mentions a lymph-node inset that is not on this PDF page, so that alternative was not used.",
        ],
        "Transcription contains the visible labels and identifies the repeated thymus inset label. It does not encode exact arrow coordinates, organ shapes, anatomical geometry or unlabeled visual information. Agent source verification is not independent human scientific review.",
    ),
]:
    value = {
        "pdf_sha256": PDF_HASH,
        "physical_page": page,
        "transcript": transcript,
        "review_status": "agent_source_verified",
        "review_method": "Compared actual RapidOCR output with the complete rendered official PDF page; verified visible labels, table cell assignments and printed numeric ranges; raw OCR boxes/confidences remain unchanged.",
        "review_limits": limits,
        "corrections": corrections,
    }
    (OUTPUT / f"anatomy-and-physiology-2e-{page}.json").write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
print("Wrote three Anatomy source-verified image text records.")
