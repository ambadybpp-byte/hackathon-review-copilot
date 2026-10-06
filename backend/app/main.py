from pathlib import Path
import shutil
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .extractor import extract_document
from .classifier import classify_submission
from .evaluator import evaluate_submission

app = FastAPI(
    title="Hackathon Review Copilot",
    description="AI-assisted hackathon submission analysis, scoring, evidence extraction and shortlist support.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "submissions"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def analyze_file(path: Path) -> dict:
    text = extract_document(str(path))
    if not text.strip():
        return {
            "success": False,
            "filename": path.name,
            "message": "No readable text was extracted.",
            "classification": None,
            "evaluation": None,
            "text_length": 0,
        }

    classification = classify_submission(text)
    evaluation = evaluate_submission(text, classification)

    return {
        "success": True,
        "filename": path.name,
        "file_type": path.suffix.lower(),
        "file_path": str(path),
        "classification": classification,
        "evaluation": evaluation,
        "text_length": len(text),
        "extracted_text_preview": text[:5000],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "hackathon-review-copilot", "version": "0.2.0"}


@app.get("/")
def root():
    return {"name": "Hackathon Review Copilot", "version": "0.2.0", "status": "running", "docs": "/docs"}


@app.post("/api/analyze")
async def analyze_submission(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename was provided.")

    extension = Path(file.filename).suffix.lower()
    if extension not in {".pptx", ".pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Currently supported: PPTX and PDF.")

    filename = Path(file.filename).name
    destination = UPLOAD_DIR / filename

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return analyze_file(destination)
    except HTTPException:
        raise
    except Exception as exc:
        if destination.exists():
            try:
                destination.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")


@app.post("/api/analyze-batch")
async def analyze_batch(files: List[UploadFile] = File(...)):
    results = []

    for upload in files:
        if not upload.filename:
            continue

        extension = Path(upload.filename).suffix.lower()
        if extension not in {".pptx", ".pdf"}:
            results.append({
                "success": False,
                "filename": upload.filename,
                "message": "Unsupported file type.",
            })
            continue

        destination = UPLOAD_DIR / Path(upload.filename).name

        try:
            with destination.open("wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)
            results.append(analyze_file(destination))
        except Exception as exc:
            results.append({
                "success": False,
                "filename": upload.filename,
                "message": f"Analysis failed: {exc}",
            })

    successful = [r for r in results if r.get("success")]
    ranked = sorted(
        successful,
        key=lambda r: r.get("evaluation", {}).get("final_score", 0),
        reverse=True,
    )

    groups = {}
    for item in successful:
        problem = item.get("classification", {}).get("primary", "OPEN")
        groups.setdefault(problem, []).append(item)

    for problem in groups:
        groups[problem].sort(
            key=lambda r: r.get("evaluation", {}).get("final_score", 0),
            reverse=True
        )

    return {
        "success": True,
        "total_received": len(files),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "ranked": ranked,
        "groups": {
            key: {
                "count": len(value),
                "teams": [
                    {
                        "filename": item["filename"],
                        "score": item["evaluation"]["final_score"],
                        "band": item["evaluation"]["band"],
                        "decision": item["evaluation"]["decision"],
                        "review_confidence": item["evaluation"]["review_confidence"],
                    }
                    for item in value
                ],
            }
            for key, value in groups.items()
        },
    }


@app.get("/api/submissions")
def list_submissions():
    submissions = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {".pptx", ".pdf"}:
            submissions.append({
                "filename": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size,
            })

    return {"count": len(submissions), "submissions": submissions}
