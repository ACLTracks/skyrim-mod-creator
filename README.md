# Skyrim AI Mod Creator (ESL workflow)

A small FastAPI app that turns a natural-language prompt into:

1. A generated xEdit (`SSEEdit`) Pascal script.
2. An ESL artifact in `output/` for download.

> This project currently creates a **workflow-ready ESL artifact** and a generated xEdit script. For production-safe ESLs, run the generated script inside SSEEdit for Skyrim SE/AE.

## Features

- Prompt in, mod generation out.
- Uses OpenAI (if `OPENAI_API_KEY` exists) to convert prompt to a compact mod spec.
- Fallback non-AI parser when API key is missing.
- Generates `GMST` changes in xEdit script form.
- Download links for both `.esl` and `.pas` files.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## How the ESL generation works

- The app converts prompt -> `ModSpec`.
- `ModSpec` -> xEdit Pascal script via `app/xedit_builder.py`.
- A placeholder ESL file is generated for immediate download.
- Use SSEEdit to execute the script and produce a final plugin in your local modding environment.

## Next steps for real modding pipelines

- Add support for records beyond GMST (WEAP, ARMO, NPC_, MGEF, SPEL).
- Add direct SSEEdit invocation when installed path is configured.
- Add ESL validation pass and smoke tests against Skyrim runtime loaders.
