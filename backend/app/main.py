from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .extractor import extract_document
from .classifier import classify_submission


# ============================================================
# APP CONFIGURATION
# ============================================================

app = FastAPI(
    title="Hackathon Review Copilot",
    description=(
        "AI-assisted hackathon submission analysis, "
        "problem-statement classification and evidence extraction."
    ),
    version="0.1.0"
)


# ============================================================
# CORS
# ============================================================
# Allows the frontend to communicate with the FastAPI backend.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"

UPLOAD_DIR = DATA_DIR / "submissions"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    """
    Simple API health check.
    """

    return {
        "status": "ok",
        "service": "hackathon-review-copilot",
        "version": "0.1.0"
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    """
    Basic API information.
    """

    return {
        "name": "Hackathon Review Copilot",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


# ============================================================
# ANALYZE SUBMISSION
# ============================================================

@app.post("/api/analyze")
async def analyze_submission(
    file: UploadFile = File(...)
):
    """
    Upload and analyze a hackathon submission.

    Currently supports:
        - .pptx
        - .pdf

    Pipeline:

        Upload
          ↓
        Save file
          ↓
        Extract text
          ↓
        Detect explicit problem statement
          ↓
        Semantic classification
          ↓
        Return analysis
    """

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided."
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    supported_extensions = {
        ".pptx",
        ".pdf"
    }

    if extension not in supported_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Currently supported: PPTX and PDF."
            )
        )

    # --------------------------------------------------------
    # Create safe-ish filename
    # --------------------------------------------------------

    filename = Path(
        file.filename
    ).name

    destination = UPLOAD_DIR / filename

    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------

    try:

        with destination.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {exc}"
        )

    # --------------------------------------------------------
    # Extract document text
    # --------------------------------------------------------

    try:

        extracted_text = extract_document(
            str(destination)
        )

    except Exception as exc:

        # Remove failed upload if possible
        try:
            destination.unlink()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Document extraction failed: {exc}"
        )

    # --------------------------------------------------------
    # Validate extraction
    # --------------------------------------------------------

    if not extracted_text.strip():

        return {
            "success": False,
            "filename": filename,
            "message": (
                "The document was uploaded successfully, "
                "but no readable text was extracted."
            ),
            "classification": None,
            "text_length": 0,
            "extracted_text_preview": ""
        }

    # --------------------------------------------------------
    # Classify submission
    # --------------------------------------------------------

    try:

        classification = classify_submission(
            extracted_text
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {exc}"
        )

    # --------------------------------------------------------
    # Return analysis
    # --------------------------------------------------------

    return {
        "success": True,

        "filename": filename,

        "file_type": extension,

        "file_path": str(destination),

        "classification": classification,

        "text_length": len(extracted_text),

        "extracted_text_preview": (
            extracted_text[:5000]
        )
    }


# ============================================================
# BATCH / FUTURE ENDPOINT PLACEHOLDER
# ============================================================

@app.get("/api/submissions")
def list_submissions():
    """
    List currently uploaded submissions.

    This will later become the main submission database
    endpoint for the reviewer dashboard.
    """

    submissions = []

    for file_path in UPLOAD_DIR.iterdir():

        if file_path.is_file():

            submissions.append({
                "filename": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size
            })

    return {
        "count": len(submissions),
        "submissions": submissions
    }