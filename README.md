# Skyrim Safe Mod Design Assistant (ESL workflow)

A FastAPI app that turns a natural-language request into a **validated GMST plan** and then generates:

1. A generated xEdit (`SSEEdit`) Pascal script.
2. A placeholder ESL artifact in `output/`.
3. A machine-readable manifest JSON contract.

## MVP safety posture

This app is intentionally constrained to a safe surface area:

- **GMST-only allowlist** (no perks/spells/weapons/NPCs yet).
- **Canonical catalog module** (`app/gmst_catalog.py`) is the single source for validation rules, labels, and risk metadata.
- **Explicit type metadata** per allowed setting.
- **Range checks** (`min`/`max`) where relevant.
- **Human-readable validation errors** for rejected changes.
- **Rejected-change reporting** in preview and manifest.

## Flow

1. User submits `mod_name` + prompt.
2. App creates a draft spec (AI or fallback parser).
3. Validation enforces allowlist + type + min/max constraints.
4. User reviews a **preview page** before artifacts are generated.
5. User confirms generation.
6. App writes xEdit script + placeholder ESL + manifest and runs post-build verification hooks.

## Manifest contract

Every generation emits `*.manifest.json` with this shape:

```json
{
  "manifest_schema_version": "1.0.0",
  "mod_name": "Example Balance Patch",
  "game": "Skyrim SE",
  "record_type": "GMST",
  "changes": [
    {
      "editor_id": "fJumpHeightMin",
      "label": "Jump Height Minimum",
      "risk_tier": "low",
      "value": 96.0,
      "value_type": "float",
      "source": "ai_generated",
      "rationale": "Improve traversal feel"
    }
  ],
  "rejected_changes": []
}
```

## Post-build verification hooks

After writing outputs, the app reports checks for:

- expected plugin filename exists,
- manifest exists,
- output change count matches manifest,
- unsupported edits were skipped and reported,
- xEdit script execution status (`not_executed` is explicit and means no real SSEEdit build has happened yet).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.
