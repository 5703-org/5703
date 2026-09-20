"""Build matched E0 and E1 prompts; evidence is the only intentional difference."""

from __future__ import annotations


SYSTEM_PROMPT = (
    "You are a helpful learning assistant. Answer the user's question clearly. "
    "If evidence is provided, use only that evidence for factual claims and cite "
    "the supporting chunk IDs in square brackets, for example [chunk_12]."
)


def build_prompt(question: str, evidence: list[dict] | None = None) -> list[dict]:
    """Return OpenAI-compatible messages for E0 (no evidence) or E1 (evidence)."""
    if not question or not question.strip():
        raise ValueError("Question must not be empty")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if evidence:
        context = "\n\n".join(
            "[{}] {}\nSource: {}; Chapter: {}; Page: {}".format(
                item["chunk_id"],
                item["text"],
                item.get("document", "unknown"),
                item.get("chapter", "unknown"),
                item.get("page", "unknown"),
            )
            for item in evidence
        )
        user_content = f"Question: {question}\n\nRetrieved textbook evidence:\n{context}"
    else:
        user_content = f"Question: {question}"
    messages.append({"role": "user", "content": user_content})
    return messages
