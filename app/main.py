import json
from pathlib import Path
import shutil

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.mod_engine import ModSpec, RejectedChange, ValidatedChange, create_mod_spec
from app.xedit_builder import build_xedit_script, verify_build_outputs

app = FastAPI(title="Skyrim AI ESL Creator")
templates = Jinja2Templates(directory="templates")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def _modspec_from_payload(payload: str) -> ModSpec:
    data = json.loads(payload)
    return ModSpec(
        summary=data["summary"],
        gameplay_changes=[ValidatedChange(**item) for item in data["gameplay_changes"]],
        warnings=data.get("warnings", []),
        rejected_changes=[RejectedChange(**item) for item in data.get("rejected_changes", [])],
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": None, "error": None, "preview": None},
    )


@app.post("/preview", response_class=HTMLResponse)
def preview_mod(request: Request, prompt: str = Form(...), mod_name: str = Form(...)):
    try:
        spec = create_mod_spec(prompt)
        safe_payload = json.dumps(
            {
                "summary": spec.summary,
                "gameplay_changes": [vars(change) for change in spec.gameplay_changes],
                "warnings": spec.warnings,
                "rejected_changes": [vars(change) for change in spec.rejected_changes],
            }
        )
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "error": None,
                "preview": {
                    "mod_name": mod_name,
                    "summary": spec.summary,
                    "changes": spec.gameplay_changes,
                    "warnings": spec.warnings,
                    "rejected_changes": spec.rejected_changes,
                    "spec_payload": safe_payload,
                },
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result": None, "error": str(exc), "preview": None},
        )


@app.post("/create", response_class=HTMLResponse)
def create_mod(request: Request, mod_name: str = Form(...), spec_payload: str = Form(...)):
    try:
        spec = _modspec_from_payload(spec_payload)
        mod_folder = OUTPUT_DIR / mod_name.replace(" ", "_")
        mod_folder.mkdir(parents=True, exist_ok=True)
        script_path, manifest_path, plugin_name = build_xedit_script(mod_name, spec, mod_folder)

        placeholder_esl = mod_folder / plugin_name
        placeholder_esl.write_bytes(b"TES4_PLACEHOLDER\nRun SSEEdit with generated script to build final ESL.\n")

        verification = verify_build_outputs(
            out_dir=mod_folder,
            plugin_name=plugin_name,
            manifest_path=manifest_path,
            spec=spec,
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {
                    "summary": spec.summary,
                    "script": str(script_path),
                    "plugin": str(placeholder_esl),
                    "manifest": str(manifest_path),
                    "download_name": placeholder_esl.name,
                    "download_manifest_name": manifest_path.name,
                    "folder": mod_folder.name,
                    "verification": verification["checks"],
                    "rejected_changes": spec.rejected_changes,
                },
                "error": None,
                "preview": None,
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result": None, "error": str(exc), "preview": None},
        )


@app.get("/download/{folder}/{filename}")
def download_mod(folder: str, filename: str):
    file_path = OUTPUT_DIR / folder / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)


@app.get("/download-script/{folder}/{filename}")
def download_script(folder: str, filename: str):
    file_path = OUTPUT_DIR / folder / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Script not found")
    return FileResponse(file_path, filename=filename)


@app.post("/cleanup")
def cleanup_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(exist_ok=True)
    return {"status": "ok"}
