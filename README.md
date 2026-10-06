# Hackathon Review Copilot

A local-first judge dashboard for reviewing 100+ hackathon submissions and producing a transparent Top 30 shortlist.

## What it does

- Drag-and-drop PPTX/PDF submissions or upload one ZIP containing many decks
- Extracts slide/page evidence automatically
- Classifies submissions against BYT01-BYT05 or Open Challenge
- Detects explicit problem-statement references and semantic mismatch
- Scores the official 100-point rubric:
  - Problem Identification & Relevance — 20
  - Innovation & Originality — 25
  - Technical Approach & Feasibility — 20
  - Practical Impact & Applicability — 20
  - Presentation & Clarity — 15
- Flags placeholders, suspicious unsupported performance claims, and uncertain classification
- Persists analyzed results locally so a browser refresh does not erase the review session
- Search, filter, sort and inspect evidence per submission
- Builds a flexible Top 30 using global score rather than artificial equal category quotas
- Shows category allocation and shortlist rationale
- Runs entirely on the local machine by default

## Run

From the repository root on Windows:

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Then open:

**http://127.0.0.1:8000/**

The old Swagger/API page remains available at:

**http://127.0.0.1:8000/docs**

## Judge workflow

1. Put all submission PPTX/PDF files into a ZIP, or select them directly.
2. Open the dashboard and drop the ZIP/files.
3. Click **Analyze submissions**.
4. Review scores, classification, flags and slide/page evidence.
5. Click **Build Top 30**.
6. Use the allocation as the shortlist recommendation, then apply human judgement for the final decision.

## Important limitation

This version is a transparent text/evidence baseline, not an autonomous expert judge. Image-only content, live demos, videos, GitHub implementation quality and verbal pitches are not fully evaluated yet. The dashboard deliberately exposes evidence and uncertainty so a human judge can override the recommendation.

Do not treat the score as objective truth. Humanity has already suffered enough from spreadsheets pretending to be morality.
