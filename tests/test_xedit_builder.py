import json
from pathlib import Path

from app.gmst_catalog import GMST_CATALOG
from app.mod_engine import ModSpec, RejectedChange, ValidatedChange, validate_changes
from app.xedit_builder import MANIFEST_SCHEMA_VERSION, build_manifest, build_xedit_script, verify_build_outputs


def test_build_xedit_script_creates_pas_and_manifest(tmp_path: Path):
    spec = ModSpec(
        summary="test",
        gameplay_changes=[
            ValidatedChange(
                type="gmst",
                editor_id="fJumpHeightMin",
                label="Jump Height Minimum",
                value=90.0,
                value_type="float",
                risk_tier="low",
                note="",
                rationale="test",
            ),
            ValidatedChange(
                type="gmst",
                editor_id="fMoveRunMult",
                label="Run Speed Multiplier",
                value=1.2,
                value_type="float",
                risk_tier="medium",
                note="",
                rationale="test",
            ),
        ],
        warnings=[],
        rejected_changes=[],
    )

    script_path, manifest_path, plugin_name = build_xedit_script("My Cool Mod", spec, tmp_path)
    data = script_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert script_path.exists()
    assert "AddNewFileName('My_Cool_Mod.esl'" in data
    assert "fJumpHeightMin" in data
    assert "fMoveRunMult" in data
    assert plugin_name == "My_Cool_Mod.esl"
    assert manifest["manifest_schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["changes"][0]["label"] == "Jump Height Minimum"
    assert manifest["record_type"] == "GMST"
    assert len(manifest["changes"]) == 2


def test_validate_changes_reports_rejections_and_uses_catalog_metadata():
    accepted, warnings, rejected = validate_changes(
        [
            {"type": "gmst", "editor_id": "fMoveRunMult", "value": 1.25},
            {"type": "gmst", "editor_id": "NOT_ALLOWED", "value": 1},
            {"type": "weap", "editor_id": "x", "value": 1},
        ]
    )

    assert len(accepted) == 1
    assert accepted[0].label == GMST_CATALOG["fMoveRunMult"].label
    assert accepted[0].risk_tier == GMST_CATALOG["fMoveRunMult"].risk_tier
    assert len(warnings) == 1
    assert len(rejected) == 2


def test_verify_build_outputs_reports_manifest_match(tmp_path: Path):
    spec = ModSpec(
        summary="test",
        gameplay_changes=[
            ValidatedChange(
                type="gmst",
                editor_id="fJumpHeightMin",
                label="Jump Height Minimum",
                value=96.0,
                value_type="float",
                risk_tier="low",
                note="",
                rationale="test",
            )
        ],
        warnings=[],
        rejected_changes=[
            RejectedChange(requested_change={"type": "weap"}, reason="Only GMST supported")
        ],
    )

    manifest_path = tmp_path / "m.json"
    manifest_path.write_text(json.dumps(build_manifest("Example", spec)), encoding="utf-8")
    plugin_path = tmp_path / "Example.esl"
    plugin_path.write_bytes(b"placeholder")

    checks = verify_build_outputs(tmp_path, "Example.esl", manifest_path, spec)["checks"]
    statuses = {item["check"]: item["status"] for item in checks}

    assert statuses["expected_plugin_filename_exists"] == "pass"
    assert statuses["output_matches_requested_manifest"] == "pass"
    assert statuses["unsupported_edits_skipped_and_reported"] == "pass"
    assert statuses["xedit_script_completed_successfully"] == "not_executed"
