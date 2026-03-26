import re
import subprocess
from pathlib import Path

from app.mod_engine import ModSpec


def _sanitize_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())
    return safe[:60] if safe else "ai_mod"


def build_xedit_script(mod_name: str, spec: ModSpec, out_dir: Path) -> Path:
    safe_name = _sanitize_filename(mod_name)
    script_path = out_dir / f"generate_{safe_name}.pas"
    plugin_name = f"{safe_name}.esl"

    gmst_lines = []
    for change in spec.gameplay_changes:
        if change.get("type") != "gmst":
            continue
        editor_id = change.get("editor_id", "")
        value = change.get("value", 1.0)
        gmst_lines.append(
            f"  rec := Add(GMSTGroup, 'GMST', True); SetElementEditValues(rec, 'EDID', '{editor_id}'); "
            f"SetElementNativeValues(rec, 'DATA\\Value', {value});"
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
    return script_path


def run_xedit(script_path: Path, xedit_exe: Path, game_mode: str = "-SSE") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(xedit_exe), game_mode, "-autogame", "-autoload", f"-script:{script_path.stem}"],
        cwd=script_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
