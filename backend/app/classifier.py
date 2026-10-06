import re
from collections import Counter


PROBLEM_IDS = [
    "BYT01",
    "BYT02",
    "BYT03",
    "BYT04",
    "BYT05",
    "OPEN"
]


KEYWORDS = {
    "BYT01": [
        "money laundering",
        "financial crime",
        "transaction",
        "transactions",
        "bank",
        "banking",
        "financial institution",
        "fraud",
        "suspicious transaction",
        "temporal pattern",
        "money",
        "financial network"
    ],

    "BYT02": [
        "patient",
        "clinical",
        "disease",
        "healthcare",
        "medical record",
        "medical records",
        "diagnosis",
        "deterioration",
        "hospital",
        "health",
        "symptoms",
        "patient history"
    ],

    "BYT03": [
        "student",
        "students",
        "programming",
        "coding",
        "debugging",
        "learning",
        "education",
        "personalized learning",
        "adaptive learning",
        "misconception",
        "code behavior"
    ],

    "BYT04": [
        "cyberattack",
        "cyber attack",
        "cybersecurity",
        "security telemetry",
        "network security",
        "lateral movement",
        "malware",
        "intrusion",
        "attack detection",
        "threat detection",
        "endpoint",
        "firewall",
        "security logs",
        "siem"
    ],

    "BYT05": [
        "urban infrastructure",
        "infrastructure",
        "cascading failure",
        "emergency intervention",
        "city",
        "urban",
        "roads",
        "traffic",
        "power grid",
        "water supply",
        "public infrastructure",
        "disaster",
        "emergency response"
    ],

    "OPEN": [
        "open challenge",
        "open innovation"
    ]
}


def detect_declared_problem(text: str):

    patterns = [
        r"problem\s*statement\s*(?:id|no|number)?\s*[:\-]?\s*(BYT0[1-5])",
        r"\b(BYT0[1-5])\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return {
                "id": match.group(1).upper(),
                "source": "explicit_submission_reference",
                "confidence": 1.0
            }

    return None


def semantic_classification(text: str):

    normalized = text.lower()

    scores = {}

    for problem_id, keywords in KEYWORDS.items():

        score = 0
        matched = []

        for keyword in keywords:

            occurrences = normalized.count(
                keyword.lower()
            )

            if occurrences > 0:

                score += occurrences
                matched.append(keyword)

        scores[problem_id] = {
            "score": score,
            "matched_keywords": matched
        }

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1]["score"],
        reverse=True
    )

    total_score = sum(
        item[1]["score"]
        for item in ranked
    )

    results = []

    for problem_id, data in ranked:

        if data["score"] == 0:
            continue

        if total_score > 0:

            confidence = (
                data["score"] / total_score
            )

        else:

            confidence = 0

        results.append({
            "id": problem_id,
            "score": data["score"],
            "confidence": round(
                confidence,
                3
            ),
            "matched_keywords":
                data["matched_keywords"]
        })

    return results


def classify_submission(text: str):

    declared = detect_declared_problem(text)

    if declared:

        semantic = semantic_classification(text)

        return {
            "primary": declared["id"],
            "primary_source": "explicit_submission_reference",
            "primary_confidence": declared["confidence"],
            "declared_problem_statement":
                declared["id"],
            "semantic_matches": semantic
        }

    semantic = semantic_classification(text)

    if not semantic:

        return {
            "primary": "OPEN",
            "primary_source": "fallback",
            "primary_confidence": 0.25,
            "declared_problem_statement": None,
            "semantic_matches": []
        }

    primary = semantic[0]

    secondary = (
        semantic[1]
        if len(semantic) > 1
        else None
    )

    return {
        "primary": primary["id"],
        "primary_source": "semantic_classification",
        "primary_confidence":
            primary["confidence"],
        "declared_problem_statement": None,
        "secondary": secondary,
        "semantic_matches": semantic
    }