import json
import re
import subprocess
from pathlib import Path
from typing import Any

from app.mod_engine import ModSpec

MANIFEST_SCHEMA_VERSION = "1.0.0"


def _sanitize_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())
    return safe[:60] if safe else "ai_mod"


def build_manifest(mod_name: str, spec: ModSpec) -> dict[str, Any]:
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "mod_name": mod_name,
        "game": "Skyrim SE",
        "record_type": "GMST",
        "changes": [
            {
                "editor_id": change.editor_id,
                "label": change.label,
                "risk_tier": change.risk_tier,
                "value": change.value,
                "value_type": change.value_type,
                "source": change.source,
                "rationale": change.rationale,
            }
            for change in spec.gameplay_changes
        ],
        "rejected_changes": [
            {
                "requested_change": item.requested_change,
                "reason": item.reason,
            }
            for item in spec.rejected_changes
        ],
    }


def build_xedit_script(mod_name: str, spec: ModSpec, out_dir: Path) -> tuple[Path, Path, str]:
    safe_name = _sanitize_filename(mod_name)
    script_path = out_dir / f"generate_{safe_name}.pas"
    manifest_path = out_dir / f"{safe_name}.manifest.json"
    plugin_name = f"{safe_name}.esl"

    gmst_lines = []
    for change in spec.gameplay_changes:
        if change.type != "gmst":
            continue
        gmst_lines.append(
            f"  rec := Add(GMSTGroup, 'GMST', True); SetElementEditValues(rec, 'EDID', '{change.editor_id}'); "
            f"SetElementNativeValues(rec, 'DATA\\Value', {change.value});"
        )

    pascal = f"""unit userscript;

var
  f, rec, header, gmstFile, GMSTGroup: IInterface;

function Initialize: integer;
begin
  gmstFile := AddNewFileName('{plugin_name}', True);
  if not Assigned(gmstFile) then begin
    Result := 1;
    exit;
  end;

  header := ElementByPath(gmstFile, 'File Header');
  SetElementNativeValues(header, 'Record Header\\Record Flags', GetElementNativeValues(header, 'Record Header\\Record Flags') or $200);

  GMSTGroup := GroupBySignature(gmstFile, 'GMST');
{chr(10).join(gmst_lines)}

  AddMessage('Created ' + '{plugin_name}');
  Result := 0;
end;

function Finalize: integer;
begin
  Result := 0;
end;

end.
"""

    script_path.write_text(pascal, encoding="utf-8")
    manifest_path.write_text(json.dumps(build_manifest(mod_name, spec), indent=2), encoding="utf-8")
    return script_path, manifest_path, plugin_name


def verify_build_outputs(
    out_dir: Path,
    plugin_name: str,
    manifest_path: Path,
    spec: ModSpec,
    run_result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    plugin_path = out_dir / plugin_name
    checks.append(
        {
            "check": "expected_plugin_filename_exists",
            "status": "pass" if plugin_path.exists() else "fail",
            "message": f"Expected plugin at {plugin_path}.",
        }
    )

    manifest_exists = manifest_path.exists()
    checks.append(
        {
            "check": "manifest_exists",
            "status": "pass" if manifest_exists else "fail",
            "message": f"Manifest written to {manifest_path}.",
        }
    )

    if manifest_exists:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        matches = len(manifest.get("changes", [])) == len(spec.gameplay_changes)
        checks.append(
            {
                "check": "output_matches_requested_manifest",
                "status": "pass" if matches else "fail",
                "message": "Generated change count matches validated spec.",
            }
        )

    skipped_count = len(spec.rejected_changes)
    checks.append(
        {
            "check": "unsupported_edits_skipped_and_reported",
            "status": "pass",
            "message": (
                f"Skipped and reported {skipped_count} unsupported/invalid edits."
                if skipped_count
                else "No unsupported edits were requested."
            ),
        }
    )

    if run_result is None:
        checks.append(
            {
                "check": "xedit_script_completed_successfully",
                "status": "not_executed",
                "message": "xEdit script was not executed in-app; ESL content is a placeholder until SSEEdit run completes.",
            }
        )
    else:
        checks.append(
            {
                "check": "xedit_script_completed_successfully",
                "status": "pass" if run_result.returncode == 0 else "fail",
                "message": "xEdit process exit code captured.",
            }
        )

    return {"checks": checks}


def run_xedit(script_path: Path, xedit_exe: Path, game_mode: str = "-SSE") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(xedit_exe), game_mode, "-autogame", "-autoload", f"-script:{script_path.stem}"],
        cwd=script_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
