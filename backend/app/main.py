from pathlib import Path
import json
import re
import shutil
import zipfile
from typing import List
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .extractor import extract_document
from .classifier import classify_submission
from .evaluator import evaluate_submission
from .shortlist import build_shortlist

app = FastAPI(
    title="Hackathon Review Copilot",
    description="Judge dashboard for evidence-aware hackathon review, scoring and finalist shortlisting.",
    version="0.5.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "submissions"
RUNTIME_DIR = DATA_DIR / "runtime"
RESULTS_FILE = RUNTIME_DIR / "results.json"
FRONTEND_DIR = ROOT_DIR / "frontend"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

def analyze_file(path: Path) -> dict:
    text = extract_document(str(path))
    if not text.strip():
        return {"success":False,"filename":path.name,"message":"No readable text was extracted.","classification":None,"evaluation":None,"text_length":0}
    classification = classify_submission(text)
    evaluation = evaluate_submission(text, classification)
    return {
        "success":True,
        "filename":path.name,
        "file_type":path.suffix.lower(),
        "file_path":str(path),
        "classification":classification,
        "evaluation":evaluation,
        "text_length":len(text),
        "extracted_text_preview":text[:5000],
    }

def save_results(items, shortlist=None):
    payload={"items":items,"shortlist":shortlist,"updated_at":__import__("datetime").datetime.now().isoformat(timespec="seconds")}
    RESULTS_FILE.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

def load_results():
    if not RESULTS_FILE.exists(): return {"items":[],"shortlist":None}
    try: return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    except Exception: return {"items":[],"shortlist":None}

def safe_extract_zip(upload: UploadFile):
    batch_dir=UPLOAD_DIR / ("batch_"+uuid4().hex[:10])
    batch_dir.mkdir(parents=True,exist_ok=True)
    saved=[]
    data=upload.file.read()
    zip_path=batch_dir/"submission_bundle.zip"
    zip_path.write_bytes(data)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            name=Path(info.filename)
            if name.suffix.lower() not in {".pptx",".pdf"}: continue
            if name.name.startswith("."): continue
            target=batch_dir/name.name
            with z.open(info) as src, target.open("wb") as dst: shutil.copyfileobj(src,dst)
            saved.append(target)
    try: zip_path.unlink()
    except OSError: pass
    return saved

@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR/"index.html"))

@app.get("/api/health")
def health():
    return {"status":"ok","service":"hackathon-review-copilot","version":"0.5.0"}

@app.get("/api/results")
def results():
    return load_results()

@app.post("/api/analyze")
async def analyze_submission(file: UploadFile = File(...)):
    if not file.filename: raise HTTPException(status_code=400,detail="No filename was provided.")
    ext=Path(file.filename).suffix.lower()
    if ext not in {".pptx",".pdf"}: raise HTTPException(status_code=400,detail="Supported: PPTX or PDF.")
    dest=UPLOAD_DIR/Path(file.filename).name
    try:
        with dest.open("wb") as buffer: shutil.copyfileobj(file.file,buffer)
        result=analyze_file(dest)
        if result.get("success"):
            old=load_results().get("items",[])
            old=[x for x in old if x.get("filename")!=result["filename"]]+[result]
            ranked=sorted(old,key=lambda x:x["evaluation"]["final_score"],reverse=True)
            save_results(ranked)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500,detail=f"Analysis failed: {exc}")

@app.post("/api/analyze-batch")
async def analyze_batch(files: List[UploadFile] = File(...)):
    results=[]
    for upload in files:
        if not upload.filename: continue
        ext=Path(upload.filename).suffix.lower()
        paths=[]
        try:
            if ext==".zip":
                paths=safe_extract_zip(upload)
            elif ext in {".pptx",".pdf"}:
                dest=UPLOAD_DIR/Path(upload.filename).name
                with dest.open("wb") as buffer: shutil.copyfileobj(upload.file,buffer)
                paths=[dest]
            else:
                results.append({"success":False,"filename":upload.filename,"message":"Unsupported file type."})
                continue
            for path in paths:
                try: results.append(analyze_file(path))
                except Exception as exc: results.append({"success":False,"filename":path.name,"message":f"Analysis failed: {exc}"})
        except zipfile.BadZipFile:
            results.append({"success":False,"filename":upload.filename,"message":"Invalid ZIP archive."})
        except Exception as exc:
            results.append({"success":False,"filename":upload.filename,"message":f"Batch import failed: {exc}"})
    successful=[r for r in results if r.get("success")]
    existing=load_results().get("items",[])
    by_name={x["filename"]:x for x in existing}
    by_name.update({x["filename"]:x for x in successful})
    ranked=sorted(by_name.values(),key=lambda x:x["evaluation"]["final_score"],reverse=True)
    save_results(ranked)
    groups={}
    for item in ranked: groups.setdefault(item.get("classification",{}).get("primary","OPEN"),[]).append(item)
    return {"success":True,"total_received":len(files),"successful":len(successful),"failed":len(results)-len(successful),"ranked":ranked,"groups":{k:{"count":len(v),"teams":[{"filename":x["filename"],"score":x["evaluation"]["final_score"],"band":x["evaluation"]["band"],"decision":x["evaluation"]["decision"],"review_confidence":x["evaluation"]["review_confidence"]} for x in v]} for k,v in groups.items()}}

@app.post("/api/shortlist")
def shortlist(payload: dict):
    items=payload.get("items") or load_results().get("items",[])
    limit=int(payload.get("limit",30))
    result=build_shortlist(items,limit)
    save_results(items,result)
    return result

@app.get("/api/submissions")
def list_submissions():
    submissions=[]
    for file_path in UPLOAD_DIR.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".pptx",".pdf"}:
            submissions.append({"filename":file_path.name,"extension":file_path.suffix.lower(),"size_bytes":file_path.stat().st_size})
    return {"count":len(submissions),"submissions":submissions}
