from pathlib import Path
import shutil

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.mod_engine import create_mod_spec
from app.xedit_builder import build_xedit_script

app = FastAPI(title="Skyrim AI ESL Creator")
templates = Jinja2Templates(directory="templates")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": None})


@app.post("/create", response_class=HTMLResponse)
def create_mod(request: Request, prompt: str = Form(...), mod_name: str = Form(...)):
    try:
        spec = create_mod_spec(prompt)
        mod_folder = OUTPUT_DIR / mod_name.replace(" ", "_")
        mod_folder.mkdir(parents=True, exist_ok=True)
        script_path = build_xedit_script(mod_name, spec, mod_folder)

        placeholder_esl = mod_folder / f"{mod_name.replace(' ', '_')}.esl"
        placeholder_esl.write_bytes(b"TES4_PLACEHOLDER\nRun SSEEdit with generated script to build final ESL.\n")

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {
                    "summary": spec.summary,
                    "script": str(script_path),
                    "plugin": str(placeholder_esl),
                    "download_name": placeholder_esl.name,
                    "folder": mod_folder.name,
                },
                "error": None,
            },
        )
    except Exception as exc:
        return templates.TemplateResponse("index.html", {"request": request, "result": None, "error": str(exc)})


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
