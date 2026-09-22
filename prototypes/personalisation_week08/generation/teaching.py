"""Executable presentation plans for interactive responses, not mastery inference."""

import re

LEVELS = {
    "beginner": [
        "Start with the direct supported idea in everyday language.",
        "Define each necessary technical term at first use; explain one step at a time.",
        "Use a short supported concrete example only if it clarifies the idea.",
    ],
    "intermediate": [
        "Connect the supported mechanism to its result.",
        "Explain non-obvious terms and a relevant supported application.",
    ],
    "advanced": [
        "Use precise scientific terms and supported relationships.",
        "State assumptions, boundary conditions and limitations; do not invent a derivation.",
    ],
}


def teaching_plan(question, profile=None, understanding=None):
    compiled = profile or {}
    saved = compiled.get("profile") or {}
    override = compiled.get("turn_override") or {}
    level = (
        override.get("level", saved.get("level"))
        if compiled.get("use_profile", bool(saved))
        else None
    )
    style = override.get("style", saved.get("style"))
    # The current explicit request also applies when saved preferences are off.
    if re.search(r"\b(simpler|simplify|plain language|beginner)\b", question, re.I):
        level = "beginner"
    if re.search(r"\b(?:short answer|briefly|in one sentence|be concise)\b", question, re.I):
        style = "concise"
    elif re.search(
        r"\b(?:long explanation|in detail|step by step|full explanation)\b", question, re.I
    ):
        style = "detailed"
    mode = "explanation"
    hint = re.search(r"\b(?:a |one |only a |just a )?hints?\b", question, re.I)
    if hint and not re.search(
        r"\b(?:no|without|do not give|don't give)\s+(?:(?:me|a|any)\s+)*hints?\b", question, re.I
    ):
        mode = "hint"
    elif re.search(
        r"\b(?:i think|i thought|is it true|isn't it|am i right|misconception)\b", question, re.I
    ):
        mode = "misconception_check"
    rules = list(
        LEVELS.get(
            level,
            ["Use clear English and explain necessary terms without assuming a learner level."],
        )
    )
    if mode == "hint":
        rules += [
            "Give exactly one supported next step or clue, then one brief question inviting the learner to try.",
            "Do not reveal the final requested result or complete solution; short_answer must be null for a hint.",
        ]
    elif mode == "misconception_check":
        rules += [
            "Check the learner's premise against the current sources before agreeing or correcting.",
            "If contradicted, name the mistaken link respectfully, give the supported correction and its citation; if undecidable, say what cannot be checked.",
        ]
    if style == "concise":
        rules.append("Keep the response brief while retaining necessary conditions and exceptions.")
    elif style == "detailed":
        rules.append(
            "Explain supported intermediate steps and conditions within the output reservation; do not fill space with unsupported facts."
        )
    rules += ["Presentation changes neither the evidence nor the standard of factual support."]
    return {
        "version": "interactive_teaching_v1",
        "level": level,
        "style": style,
        "mode": mode,
        "rules": rules,
        "scope": "Presentation plan only; learner mastery and scientific/pedagogical quality are not automatically judged.",
    }
