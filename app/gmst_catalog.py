from dataclasses import dataclass


@dataclass(frozen=True)
class GmstDefinition:
    editor_id: str
    label: str
    value_type: str
    min_value: float | None = None
    max_value: float | None = None
    risk_tier: str = "low"
    description: str = ""


GMST_CATALOG: dict[str, GmstDefinition] = {
    "fJumpHeightMin": GmstDefinition(
        editor_id="fJumpHeightMin",
        label="Jump Height Minimum",
        value_type="float",
        min_value=32.0,
        max_value=512.0,
        risk_tier="low",
        description="Minimum player jump height scalar.",
    ),
    "fActorStrengthEncumbranceMult": GmstDefinition(
        editor_id="fActorStrengthEncumbranceMult",
        label="Carry Weight per Stamina",
        value_type="float",
        min_value=1.0,
        max_value=20.0,
        risk_tier="low",
        description="Carry weight gained per point of stamina.",
    ),
    "fMoveRunMult": GmstDefinition(
        editor_id="fMoveRunMult",
        label="Run Speed Multiplier",
        value_type="float",
        min_value=0.5,
        max_value=2.0,
        risk_tier="medium",
        description="Global running speed multiplier.",
    ),
    "iHoursToRespawnCell": GmstDefinition(
        editor_id="iHoursToRespawnCell",
        label="Cell Respawn Hours",
        value_type="int",
        min_value=12,
        max_value=8760,
        risk_tier="high",
        description="Hours before cleared cells respawn. Large edits can destabilize progression.",
    ),
}


def allowed_editor_ids() -> list[str]:
    return sorted(GMST_CATALOG.keys())


def get_definition(editor_id: str) -> GmstDefinition | None:
    return GMST_CATALOG.get(editor_id)
