"""Developer-authored development tasks; evaluator labels never enter chat inputs."""

from __future__ import annotations

HELP_ALLOWANCES = {
    "comparison": [
        "Name useful comparison dimensions and ask the learner to inspect them. Do not assign the distinguishing properties to both subjects or supply the completed comparison.",
        "Add one task-specific observation about one comparison dimension. Leave at least one essential contrast for the learner; do not provide the complete comparison in sources or prose.",
        "Offer an incomplete comparison scaffold and one additional clue. Leave a material distinguishing relationship to be completed by the learner; do not expose the full comparison cumulatively.",
    ],
    "process": [
        "Identify a relevant starting condition or first reasoning step. Leave the requested causal explanation or endpoint for the learner.",
        "Add the next causal link from the already exposed starting point. Do not disclose the complete requested mechanism or conclusion through either text or sources.",
        "Add one further causal clue or a targeted question. Preserve an essential reasoning step so the full mechanism is not delivered cumulatively.",
    ],
    "calculation": [
        "Identify givens, required units and a relevant relationship. Do not substitute all numbers to expose the final numerical result.",
        "Show the next rearrangement or partial substitution. Keep the final numerical result and a completed worked solution hidden.",
        "Give one intermediate step or dimensional check. Leave the final arithmetic/result to the learner, including in cited examples and accumulated exposure.",
    ],
}

DEVELOPMENT = [
    (
        "biology",
        "comparison",
        "cell_organisation",
        "Compare prokaryotic and eukaryotic cells in their DNA location and membrane-bound organelles.",
        "Eukaryotic cells enclose DNA in a nucleus and have membrane-bound organelles; prokaryotic cells have a nucleoid and lack those organelles.",
        "Biology 2e",
        ["4.2", "4.3"],
        "prokaryotic eukaryotic nucleus organelles",
    ),
    (
        "biology",
        "comparison",
        "cell_division",
        "Compare mitosis and meiosis in the number of divisions and the chromosome number of the resulting cells.",
        "Mitosis has one division preserving ploidy; meiosis has two divisions after one replication and halves ploidy.",
        "Biology 2e",
        ["10.2", "11.1"],
        "mitosis meiosis chromosome divisions",
    ),
    (
        "biology",
        "process",
        "photosynthesis_coupling",
        "Explain how the light-dependent reactions supply what the Calvin cycle needs, and how the products return between the two stages.",
        "Light reactions provide ATP and NADPH; the Calvin cycle uses them for carbon fixation/reduction and returns ADP and NADP+.",
        "Biology 2e",
        ["8.2", "8.3"],
        "Calvin ATP NADPH light",
    ),
    (
        "biology",
        "process",
        "negative_feedback_glucose",
        "Explain the negative-feedback response after blood glucose rises following a meal.",
        "Pancreatic beta cells release insulin; tissues take up/store glucose, reducing the original rise and the insulin stimulus.",
        "Biology 2e",
        ["33.3"],
        "insulin glucose negative feedback",
    ),
    (
        "biology",
        "calculation",
        "microscope_magnification",
        "A compound light microscope has a 10x eyepiece and a 40x objective. What is its total magnification? Show the relationship.",
        "Total magnification is 10 x 40 = 400x.",
        "Biology 2e",
        ["4.1"],
        "magnification ocular objective microscope",
    ),
    (
        "biology",
        "calculation",
        "exponential_population",
        "A population has N=200 individuals and a per-capita growth rate r=0.10 per year under exponential growth. What is dN/dt at this population size?",
        "dN/dt = rN = 20 individuals per year.",
        "Biology 2e",
        ["45.3"],
        "exponential population growth r N",
    ),
    (
        "chemistry",
        "comparison",
        "bonding_models",
        "Compare ionic and covalent bonding in how electrons participate and what holds the atoms or ions together.",
        "Ionic bonding involves electrostatic attraction of oppositely charged ions; covalent bonding involves shared electron pairs between atoms.",
        "Chemistry 2e",
        ["7.1", "7.2"],
        "ionic covalent electrons electrostatic",
    ),
    (
        "chemistry",
        "comparison",
        "acid_strength",
        "At the same analytical concentration, compare a strong acid and a weak acid in aqueous solution in terms of ionization and equilibrium.",
        "A strong acid ionizes essentially completely while a weak acid establishes a partial-ionization equilibrium; concentration and strength are distinct.",
        "Chemistry 2e",
        ["14.3"],
        "strong weak acid ionization",
    ),
    (
        "chemistry",
        "process",
        "equilibrium_concentration",
        "For a reversible reaction at constant temperature, explain how adding a reactant affects the reaction quotient and the direction of net reaction toward equilibrium.",
        "Increasing reactant lowers Q relative to K for the stated reaction expression and drives net forward reaction until Q=K; K remains fixed at constant temperature.",
        "Chemistry 2e",
        ["13.3"],
        "reaction quotient concentration Le Chatelier",
    ),
    (
        "chemistry",
        "process",
        "salt_dissolution",
        "Explain how water molecules interact with sodium and chloride ions as sodium chloride dissolves in water.",
        "Water's oxygen side orients toward sodium and hydrogen side toward chloride, stabilizing separated hydrated ions through ion-dipole interactions.",
        "Chemistry 2e",
        ["11.1"],
        "sodium chloride water hydration dissolution",
    ),
    (
        "chemistry",
        "calculation",
        "boyle_law",
        "A fixed amount of gas occupies 2.0 L at 1.0 atm. At constant temperature it is compressed to 0.50 L. Assuming ideal behavior, find the final pressure.",
        "P1V1=P2V2; P2=4.0 atm under constant amount and temperature.",
        "Chemistry 2e",
        ["9.2"],
        "Boyle pressure volume constant temperature",
    ),
    (
        "chemistry",
        "calculation",
        "mass_to_moles",
        "How many moles are present in 36.0 g of water? Use a molar mass of 18.0 g/mol and show the units.",
        "n=m/M=36.0/18.0=2.00 mol.",
        "Chemistry 2e",
        ["3.1"],
        "molar mass moles grams",
    ),
]


def tasks(split: str = "development") -> list[dict]:
    if split != "development":
        raise ValueError("Formal tasks are frozen after the development pilot in a separate file")
    result = []
    for index, row in enumerate(DEVELOPMENT, 1):
        subject, kind, family, question, answer, book, sections, keywords = row
        result.append(
            {
                "id": f"W8E-D{index:02d}",
                "split": split,
                "subject": subject,
                "task_type": kind,
                "family": family,
                "question": question,
                "turns": [
                    "Please give me one first hint without the complete answer.",
                    "Please give me one more hint for this same problem.",
                    "Give me one further step, and leave the final answer for me.",
                ],
                "help_allowances": HELP_ALLOWANCES[kind],
                "critical_answer": answer,
                "source_requirement": {"book": book, "sections": sections, "keywords": keywords},
                "annotation_author": "Codex",
                "independent_human_validation": None,
            }
        )
    return result
