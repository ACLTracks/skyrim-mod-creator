import json
import os
from dataclasses import dataclass
from typing import Any



@dataclass
class ModSpec:
    summary: str
    gameplay_changes: list[dict[str, Any]]


SYSTEM_PROMPT = """You convert Skyrim mod requests into a compact JSON mod spec.
Return ONLY JSON with this shape:
{
  "summary": "string",
  "gameplay_changes": [
    {
      "type": "gmst",
      "editor_id": "fJumpHeightMin",
      "value": 90.0,
      "note": "optional"
    }
  ]
}
Only use type=gmst for now.
Use valid Skyrim GMST Editor IDs when possible.
"""


def _fallback_spec(prompt: str) -> ModSpec:
    lower = prompt.lower()
    changes: list[dict[str, Any]] = []
    if "jump" in lower:
        changes.append({"type": "gmst", "editor_id": "fJumpHeightMin", "value": 95.0, "note": "Higher jump"})
    if "carry" in lower or "weight" in lower:
        changes.append({"type": "gmst", "editor_id": "fActorStrengthEncumbranceMult", "value": 7.0, "note": "More carry weight"})
    if not changes:
        changes.append({"type": "gmst", "editor_id": "fMoveRunMult", "value": 1.1, "note": "Slightly faster movement"})
    return ModSpec(summary=f"Auto-generated from prompt: {prompt[:120]}", gameplay_changes=changes)


def create_mod_spec(prompt: str) -> ModSpec:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_spec(prompt)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    completion = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    text = completion.output_text.strip()
    try:
        data = json.loads(text)
        return ModSpec(summary=data["summary"], gameplay_changes=data["gameplay_changes"])
    except Exception:
        return _fallback_spec(prompt)
