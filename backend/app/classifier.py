import re

PROBLEM_IDS = ["BYT01","BYT02","BYT03","BYT04","BYT05","OPEN"]

# Weighted phrase evidence. Generic words such as "city" or "infrastructure"
# are intentionally weak so an Open Challenge project is not forced into BYT05.
KEYWORDS = {
    "BYT01": {
        "strong":["money laundering","money-laundering","financial institution","transactional patterns","suspicious transaction","financial network","layering","structuring","transaction network"],
        "medium":["banking","bank","transaction","transactions","fraud","financial crime","temporal pattern"],
    },
    "BYT02": {
        "strong":["disease progression","patient deterioration","clinical records","medical records","longitudinal patient","patient history","clinical timeline"],
        "medium":["patient","clinical","disease","healthcare","medical","diagnosis","hospital","symptoms"],
    },
    "BYT03": {
        "strong":["programming misconceptions","coding behavior","debugging behavior","adaptive personalized learning","personalized learning","student code analysis","learning misconception"],
        "medium":["student","students","programming","coding","debugging","education","learning","adaptive learning","misconception"],
    },
    "BYT04": {
        "strong":["multi-stage cyberattack","multi stage cyberattack","lateral movement","security telemetry","attack reconstruction","network telemetry","correlating security logs"],
        "medium":["cyberattack","cyber attack","cybersecurity","network security","malware","intrusion","threat detection","endpoint","firewall","security logs","siem"],
    },
    "BYT05": {
        "strong":["cascading failures","cascading failure","interconnected urban infrastructure","urban infrastructure failures","infrastructure dependency","emergency interventions","disruptive conditions","critical infrastructure network"],
        "medium":["urban infrastructure","public infrastructure","emergency response","city infrastructure","roads","traffic","power grid","water supply","disaster"],
    },
    "OPEN": {
        "strong":["open challenge","open innovation","open-ended challenge"],
        "medium":[]
    }
}

def _score(text, cfg):
    t=text.lower()
    strong=sum(t.count(k) for k in cfg["strong"])
    medium=sum(t.count(k) for k in cfg["medium"])
    return strong*5+medium*1, strong, medium

def detect_declared_problem(text):
    patterns=[
        r"problem\s*statement\s*(?:id|no|number)?\s*[:\-]?\s*(BYT0[1-5])",
        r"\b(BYT0[1-5])\b"
    ]
    for p in patterns:
        m=re.search(p,text,re.I)
        if m:
            return {"id":m.group(1).upper(),"source":"explicit_submission_reference","confidence":1.0}
    if re.search(r"\bopen\s+(?:challenge|innovation)\b",text,re.I):
        return {"id":"OPEN","source":"explicit_open_challenge_reference","confidence":0.95}
    return None

def semantic_classification(text):
    raw=[]
    for pid,cfg in KEYWORDS.items():
        score,strong,medium=_score(text,cfg)
        if score:
            raw.append((pid,score,strong,medium))
    raw.sort(key=lambda x:x[1],reverse=True)
    if not raw:return []
    total=sum(x[1] for x in raw)
    results=[]
    for pid,score,strong,medium in raw:
        results.append({
            "id":pid,
            "score":score,
            "confidence":round(score/total,3),
            "matched_keywords":[k for k in KEYWORDS[pid]["strong"]+KEYWORDS[pid]["medium"] if k.lower() in text.lower()][:12],
            "strong_matches":strong,
            "medium_matches":medium
        })
    return results

def classify_submission(text):
    declared=detect_declared_problem(text)
    semantic=semantic_classification(text)
    if declared:
        semantic_primary=semantic[0]["id"] if semantic else None
        return {
            "primary":declared["id"],
            "primary_source":declared["source"],
            "primary_confidence":declared["confidence"],
            "declared_problem_statement":declared["id"],
            "semantic_primary":semantic_primary,
            "semantic_matches":semantic
        }
    if not semantic:
        return {"primary":"OPEN","primary_source":"fallback","primary_confidence":0.25,"declared_problem_statement":None,"semantic_primary":None,"semantic_matches":[]}
    primary=semantic[0]
    return {
        "primary":primary["id"],
        "primary_source":"semantic_classification",
        "primary_confidence":primary["confidence"],
        "declared_problem_statement":None,
        "semantic_primary":primary["id"],
        "secondary":semantic[1] if len(semantic)>1 else None,
        "semantic_matches":semantic
    }
