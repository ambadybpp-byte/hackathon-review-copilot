# Hackathon Review Copilot

AI-assisted hackathon submission review for judges and organizers.

## Current capabilities

- Upload and parse PPTX/PDF submissions
- Detect explicit BYT01-BYT05 references
- Baseline semantic problem-statement classification
- Rubric-based scoring across the official 100-point rubric
- Evidence snippets tied to slide/page markers
- Flags for placeholders, unsupported quantitative claims, low classification confidence, and problem-statement mismatch
- Batch analysis of multiple submissions
- Group submissions by problem statement
- Rank submissions by weighted score
- Human-in-the-loop recommendation instead of autonomous judging

## Official rubric

| Criterion | Weight |
|---|---:|
| Problem Identification & Relevance | 20 |
| Innovation & Originality | 25 |
| Technical Approach & Feasibility | 20 |
| Practical Impact & Applicability | 20 |
| Presentation & Clarity | 15 |

## Run locally

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

API documentation:

`http://127.0.0.1:8000/docs`

## Important

The scoring engine is intentionally a transparent baseline. It should assist human judges, not replace them. The next major layer is evidence-aware semantic evaluation and flexible finalist allocation across problem statements.
