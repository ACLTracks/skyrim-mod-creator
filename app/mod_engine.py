import json
import os
from dataclasses import dataclass
from typing import Any

from app.gmst_catalog import GMST_CATALOG, allowed_editor_ids, get_definition


@dataclass
class ValidatedChange:
    type: str
    editor_id: str
    label: str
    value: int | float
    value_type: str
    risk_tier: str
    note: str
    rationale: str
    source: str = "ai_generated"


@dataclass
class RejectedChange:
    requested_change: dict[str, Any]
    reason: str


@dataclass
class ModSpec:
    summary: str
    gameplay_changes: list[ValidatedChange]
    warnings: list[str]
    rejected_changes: list[RejectedChange]


SYSTEM_PROMPT = f"""You convert Skyrim mod requests into a compact JSON mod spec.
Return ONLY JSON with this shape:
{{
  "summary": "string",
  "gameplay_changes": [
    {{
      "type": "gmst",
      "editor_id": "fJumpHeightMin",
      "value": 90.0,
      "note": "optional",
      "rationale": "short reason"
    }}
  ]
}}
Only use type=gmst for now.
Use only these GMST editor IDs: {', '.join(allowed_editor_ids())}.
"""


def _coerce_value(value: Any, expected_type: str) -> int | float:
    if expected_type == "int":
        if isinstance(value, bool):
            raise ValueError("Expected integer but got boolean")
        return int(value)
    if expected_type == "float":
        return float(value)
    raise ValueError(f"Unsupported value type: {expected_type}")


def validate_changes(raw_changes: list[dict[str, Any]]) -> tuple[list[ValidatedChange], list[str], list[RejectedChange]]:
    accepted: list[ValidatedChange] = []
    warnings: list[str] = []
    rejected: list[RejectedChange] = []

    for raw in raw_changes:
        if raw.get("type") != "gmst":
            rejected.append(
                RejectedChange(
                    requested_change=raw,
                    reason="Only GMST changes are currently supported in this safe MVP.",
                )
            )
            continue

        editor_id = str(raw.get("editor_id", "")).strip()
        definition = get_definition(editor_id)
        if definition is None:
            rejected.append(
                RejectedChange(
                    requested_change=raw,
                    reason=f"'{editor_id}' is not in the GMST allowlist.",
                )
            )
            continue

        try:
            coerced = _coerce_value(raw.get("value"), definition.value_type)
        except Exception as exc:
            rejected.append(
                RejectedChange(
                    requested_change=raw,
                    reason=f"Invalid value for {editor_id}: {exc}.",
                )
            )
            continue

        if definition.min_value is not None and coerced < definition.min_value:
            rejected.append(
                RejectedChange(
                    requested_change=raw,
                    reason=f"{editor_id} must be >= {definition.min_value}, got {coerced}.",
                )
            )
            continue

        if definition.max_value is not None and coerced > definition.max_value:
            rejected.append(
                RejectedChange(
                    requested_change=raw,
                    reason=f"{editor_id} must be <= {definition.max_value}, got {coerced}.",
                )
            )
            continue

        note = str(raw.get("note", "")).strip()
        rationale = str(raw.get("rationale", note or "Generated from user prompt")).strip()

        accepted.append(
            ValidatedChange(
                type="gmst",
                editor_id=editor_id,
                label=definition.label,
                value=coerced,
                value_type=definition.value_type,
                risk_tier=definition.risk_tier,
                note=note,
                rationale=rationale,
            )
        )

        if definition.risk_tier in {"medium", "high"}:
            warnings.append(
                f"[{definition.risk_tier.upper()}] {editor_id} ({definition.label}): {definition.description}"
            )

    return accepted, warnings, rejected


def _fallback_spec(prompt: str) -> ModSpec:
    lower = prompt.lower()
    changes: list[dict[str, Any]] = []
    if "jump" in lower:
        changes.append({"type": "gmst", "editor_id": "fJumpHeightMin", "value": 95.0, "note": "Higher jump", "rationale": "Improve traversal feel"})
    if "carry" in lower or "weight" in lower:
        changes.append({"type": "gmst", "editor_id": "fActorStrengthEncumbranceMult", "value": 7.0, "note": "More carry weight", "rationale": "Reduce inventory friction"})
    if not changes:
        changes.append({"type": "gmst", "editor_id": "fMoveRunMult", "value": 1.1, "note": "Slightly faster movement", "rationale": "Speed up exploration pacing"})

    accepted, warnings, rejected = validate_changes(changes)
    return ModSpec(
        summary=f"Auto-generated from prompt: {prompt[:120]}",
        gameplay_changes=accepted,
        warnings=warnings,
        rejected_changes=rejected,
    )


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
        accepted, warnings, rejected = validate_changes(data.get("gameplay_changes", []))
        return ModSpec(
            summary=data.get("summary", "Generated mod plan"),
            gameplay_changes=accepted,
            warnings=warnings,
            rejected_changes=rejected,
        )
    except Exception:
        return _fallback_spec(prompt)
