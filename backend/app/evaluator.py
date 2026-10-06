import re
from typing import Dict, List, Tuple

RUBRIC = [
    {"id": "problem_relevance", "name": "Problem Identification & Relevance", "weight": 20},
    {"id": "innovation", "name": "Innovation & Originality", "weight": 25},
    {"id": "technical", "name": "Technical Approach & Feasibility", "weight": 20},
    {"id": "impact", "name": "Practical Impact & Applicability", "weight": 20},
    {"id": "presentation", "name": "Presentation & Clarity", "weight": 15},
]

SIGNALS = {
    "problem_relevance": {
        "strong": ["problem statement", "pain point", "target users", "problem", "challenge", "need", "evidence", "root cause", "gap", "survey"],
        "quality": ["measurable", "specific", "existing", "current", "fragmented", "lack of"],
    },
    "innovation": {
        "strong": ["novel", "innovative", "innovation", "unique", "differentiator", "new approach", "existing solutions"],
        "quality": ["multimodal", "agentic", "on-device", "real-time", "adaptive", "personalized", "graph", "forecast", "correlation"],
    },
    "technical": {
        "strong": ["architecture", "pipeline", "api", "model", "algorithm", "dataset", "database", "backend", "frontend", "deployment", "implementation", "technology", "tech stack", "python", "tensorflow", "pytorch", "scikit-learn", "fastapi", "react", "flutter"],
        "quality": ["prototype", "working model", "github", "repository", "latency", "accuracy", "precision", "recall", "f1", "evaluation", "testing", "integration", "scalable", "security"],
    },
    "impact": {
        "strong": ["impact", "beneficiaries", "users", "deployment", "adoption", "cost", "reduce", "improve", "accessibility", "scalability", "authorities", "hospital", "school", "community"],
        "quality": ["measurable", "roi", "time saved", "cost reduction", "outcome", "real-world", "production", "pilot", "partnership"],
    },
    "presentation": {
        "strong": ["solution", "how it works", "workflow", "architecture", "demo", "results", "conclusion", "roadmap", "future scope", "team", "references"],
        "quality": ["step 1", "step 2", "step 3", "timeline", "milestone"],
    },
}

WEAK_SIGNALS = ["placeholder", "to be replaced", "tbd", "coming soon", "not implemented"]
PERFORMANCE_PATTERNS = [
    r"\b\d+(?:\.\d+)?%\s*(?:accuracy|precision|recall|f1|improvement|reduction|increase)",
    r"\b(?:accuracy|precision|recall|f1)\s*(?:of|is|=)\s*\d+(?:\.\d+)?%?",
]

def _count_matches(text: str, terms: List[str]) -> Tuple[int, List[str]]:
    normalized = text.lower()
    total, matched = 0, []
    for term in terms:
        count = normalized.count(term.lower())
        if count:
            total += count
            matched.append(term)
    return total, matched

def _blocks(text: str):
    return [b.strip() for b in re.split(r"(?=\[(?:SLIDE|PAGE)\s+\d+\])", text) if b.strip()]

def _evidence(text: str, terms: List[str], limit: int = 4) -> List[Dict]:
    results = []
    for block in _blocks(text):
        marker = re.match(r"(\[(?:SLIDE|PAGE)\s+\d+\])", block)
        if not marker:
            continue
        body = block[len(marker.group(1)):].strip()
        if any(term.lower() in body.lower() for term in terms):
            snippet = re.sub(r"\s+", " ", body)
            results.append({"location": marker.group(1), "snippet": snippet[:240]})
            if len(results) >= limit:
                break
    return results

def _criterion(text: str, criterion_id: str) -> Dict:
    cfg = SIGNALS[criterion_id]
    strong_count, strong = _count_matches(text, cfg["strong"])
    quality_count, quality = _count_matches(text, cfg["quality"])
    weak_count, weak = _count_matches(text, WEAK_SIGNALS)

    # Transparent baseline only. It deliberately avoids pretending keyword density is expert judgement.
    score = 45 + min(strong_count * 4, 30) + min(quality_count * 3, 20) - min(weak_count * 5, 20)
    score = max(0, min(100, round(score)))
    terms = list(dict.fromkeys(strong + quality))

    return {
        "criterion_id": criterion_id,
        "name": next(x["name"] for x in RUBRIC if x["id"] == criterion_id),
        "weight": next(x["weight"] for x in RUBRIC if x["id"] == criterion_id),
        "score": score,
        "confidence": round(min(0.95, 0.45 + min((strong_count + quality_count) / 30, 0.5)), 2),
        "matched_signals": terms[:12],
        "weak_signals": weak,
        "evidence": _evidence(text, terms),
        "note": "Text-based baseline. Human review is required for final judging.",
    }

def _flags(text: str, classification: Dict) -> List[Dict]:
    findings = []

    for pattern in PERFORMANCE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            before = text[:match.start()]
            locations = re.findall(r"\[(?:SLIDE|PAGE)\s+\d+\]", before)
            findings.append({
                "type": "unsupported_performance_claim",
                "location": locations[-1] if locations else "unknown",
                "claim": match.group(0),
                "context": re.sub(r"\s+", " ", text[max(0, match.start()-80):match.end()+120]),
                "reason": "Quantitative performance claims should be backed by reproducible evaluation evidence.",
            })

    for block in _blocks(text):
        if any(signal in block.lower() for signal in ["placeholder", "to be replaced", "tbd"]):
            marker = re.match(r"(\[(?:SLIDE|PAGE)\s+\d+\])", block)
            findings.append({
                "type": "placeholder_content",
                "location": marker.group(1) if marker else "unknown",
                "claim": "Placeholder or unverified content detected",
                "context": re.sub(r"\s+", " ", block)[:300],
                "reason": "Do not award full evidence credit until the claim is verified.",
            })

    if classification.get("primary_confidence", 0) < 0.60:
        findings.append({
            "type": "classification_uncertain",
            "location": "document",
            "claim": classification.get("primary"),
            "context": "",
            "reason": "Problem-statement classification confidence is below the recommended review threshold.",
        })

    declared = classification.get("declared_problem_statement")
    semantic = classification.get("semantic_matches", [])
    if declared and semantic and semantic[0].get("id") not in (declared, "OPEN"):
        findings.append({
            "type": "problem_statement_mismatch",
            "location": "document",
            "claim": declared,
            "context": "",
            "reason": f"Submission explicitly references {declared}, but semantic evidence points more strongly to {semantic[0]['id']}.",
        })

    unique = {}
    for item in findings:
        unique[(item["type"], item["location"], item["claim"])] = item
    return list(unique.values())

def evaluate_submission(text: str, classification: Dict) -> Dict:
    rubric = [_criterion(text, item["id"]) for item in RUBRIC]
    weighted_total = sum(item["score"] * item["weight"] / 100 for item in rubric)
    flags = _flags(text, classification)

    if flags:
        weighted_total -= min(len(flags) * 1.5, 7.5)

    final_score = round(max(0, min(100, weighted_total)), 1)
    band = "STRONG" if final_score >= 80 else "COMPETITIVE" if final_score >= 70 else "BORDERLINE" if final_score >= 60 else "WEAK"

    ordered = sorted(rubric, key=lambda x: x["score"], reverse=True)
    weak = sorted(rubric, key=lambda x: x["score"])

    return {
        "final_score": final_score,
        "band": band,
        "rubric": rubric,
        "strengths": [x["name"] for x in ordered[:2]],
        "weaknesses": [x["name"] for x in weak[:2]],
        "flags": flags,
        "review_confidence": round(max(0.35, min(0.95, 0.75 - len(flags) * 0.05)), 2),
        "decision": "REVIEW" if flags or classification.get("primary_confidence", 0) < 0.75 else "RECOMMEND",
        "disclaimer": "AI-assisted baseline recommendation, not an autonomous judge. Final selection should be made by human judges.",
    }
