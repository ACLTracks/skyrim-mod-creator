from pathlib import Path

from app.mod_engine import ModSpec
from app.xedit_builder import build_xedit_script


def test_build_xedit_script_creates_pas(tmp_path: Path):
    spec = ModSpec(
        summary="test",
        gameplay_changes=[
            {"type": "gmst", "editor_id": "fJumpHeightMin", "value": 90.0},
            {"type": "gmst", "editor_id": "fMoveRunMult", "value": 1.2},
        ],
    )

    path = build_xedit_script("My Cool Mod", spec, tmp_path)
    data = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "AddNewFileName('My_Cool_Mod.esl'" in data
    assert "fJumpHeightMin" in data
    assert "fMoveRunMult" in data
