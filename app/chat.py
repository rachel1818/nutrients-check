"""
Per-nutrient RAG chatbot using Claude Sonnet 4.6 with Anthropic prompt caching.

The full DB record for the requested nutrient (plus an optional comparison
nutrient) is serialised into a context block and passed as the cached system
prompt.  Subsequent questions about the same nutrient within the 5-minute
cache TTL skip re-sending that context, cutting input-token cost ~80%.
"""
import os

import anthropic

from app.models import Nutrient

_SYSTEM_PROMPT = """\
You are a focused nutrition assistant for the Nutrient Check app.
You are answering questions about: {nutrient_title}.

Answer ONLY using the nutrient data provided below, which comes from trusted
sources (NIH ODS, USDA FoodData Central, Harvard T.H. Chan School of Public
Health, NIN Hyderabad, Cleveland Clinic, Mayo Clinic).
Cite the source name inline whenever you use a specific fact.
If the provided data is insufficient to answer, say so clearly — do not guess
or draw on outside knowledge.
Never give personal medical advice; always remind the user to consult a
qualified healthcare professional for personal health decisions.
Keep answers concise and friendly.
"""


def build_context(nutrient: Nutrient, comparison: "Nutrient | None" = None) -> str:
    """Serialise one (or two) nutrient DB records into a readable text block."""
    parts: list[str] = []

    def _section(n: Nutrient) -> str:
        lines: list[str] = [f"## {n.name}  ({n.category})"]
        if n.synonyms:
            lines.append("Also known as: " + ", ".join(s.synonym for s in n.synonyms))

        if n.food_sources:
            lines.append("\n### Food Sources")
            for f in sorted(n.food_sources, key=lambda x: x.amount, reverse=True)[:20]:
                line = f"- {f.food_name}: {f.amount} {f.unit} per {f.serving_size}"
                if f.bioavailability_note:
                    line += f"  [{f.bioavailability_note}]"
                if f.preparation_note:
                    line += f"  (Prep: {f.preparation_note})"
                line += f"  [Source: {f.source.name}]"
                lines.append(line)

        if n.absorption_helpers:
            lines.append("\n### What Improves Absorption")
            for h in n.absorption_helpers:
                lines.append(f"- {h.helper_name} ({h.helper_type}): {h.description}  [Source: {h.source.name}]")

        if n.absorption_blockers:
            lines.append("\n### What Reduces Absorption")
            for b in n.absorption_blockers:
                lines.append(f"- {b.blocker_name} ({b.blocker_type}): {b.description}  [Source: {b.source.name}]")

        if n.body_roles:
            lines.append("\n### Role in the Body")
            for r in n.body_roles:
                lines.append(f"- {r.body_system.title()}: {r.explanation}  [Source: {r.source.name}]")
                if r.deficiency_signs:
                    lines.append(f"  Deficiency signs: {r.deficiency_signs}")

        if n.rda_values:
            lines.append("\n### Recommended Daily Allowance / Adequate Intake")
            for rda in n.rda_values:
                ul = f"UL: {rda.upper_limit} {rda.unit}" if rda.upper_limit else "UL: not established"
                lines.append(
                    f"- {rda.age_group}, {rda.sex}: {rda.value} {rda.unit} ({rda.intake_type}) — {ul}  [Source: {rda.source.name}]"
                )

        return "\n".join(lines)

    parts.append(_section(nutrient))
    if comparison:
        parts.append("\n\n" + _section(comparison))

    return "\n".join(parts)


def answer_about_nutrient(
    nutrient: Nutrient,
    question: str,
    history: list[dict],
    comparison: "Nutrient | None" = None,
) -> dict:
    """
    Call Claude Sonnet 4.6 with the nutrient context cached.

    history items: [{"role": "user"|"assistant", "content": str}]
    Returns: {"answer": str}
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"answer": "Chat is unavailable — ANTHROPIC_API_KEY is not configured."}

    nutrient_title = (
        f"{nutrient.name} vs {comparison.name}" if comparison else nutrient.name
    )
    context = build_context(nutrient, comparison)
    system_text = _SYSTEM_PROMPT.format(nutrient_title=nutrient_title) + "\n\n" + context

    try:
        client = anthropic.Anthropic(
            api_key=api_key,
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )

        # Build messages: keep only the last 4 history turns (2 user + 2 assistant)
        trimmed = history[-4:] if len(history) > 4 else history
        messages = [
            {"role": m["role"], "content": m["content"]} for m in trimmed
        ] + [{"role": "user", "content": question}]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=[
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},  # cached for 5 min TTL
                }
            ],
            messages=messages,
        )
        return {"answer": response.content[0].text}

    except anthropic.AuthenticationError:
        return {"answer": "Chat is unavailable — invalid API key."}
    except anthropic.APIError as exc:
        return {"answer": f"Chat is temporarily unavailable. ({exc.message})"}
