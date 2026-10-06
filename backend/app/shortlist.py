from collections import Counter

def build_shortlist(items, limit=30):
    valid=[x for x in items if x.get("success") and x.get("evaluation")]
    ranked=sorted(valid,key=lambda x:x["evaluation"].get("final_score",0),reverse=True)
    selected=ranked[:max(0,limit)]
    allocation=Counter(x.get("classification",{}).get("primary","OPEN") for x in selected)
    reasons=[]
    if len(ranked)<=limit:
        reasons.append(f"All {len(ranked)} analyzed submissions fit within the finalist limit.")
    else:
        cutoff=selected[-1]["evaluation"]["final_score"] if selected else 0
        reasons.append(f"Selected the highest-scoring {limit} submissions globally; cutoff score is {cutoff}.")
    if allocation:
        strongest=allocation.most_common(1)[0]
        reasons.append(f"No equal category quota was imposed. {strongest[0]} receives {strongest[1]} finalist slots because its submissions ranked strongly enough to earn them.")
    rows=[]
    selected_names={x["filename"] for x in selected}
    for x in selected:
        rows.append({"filename":x["filename"],"score":x["evaluation"]["final_score"],"problem":x.get("classification",{}).get("primary","OPEN"),"reason":"Global score"})
    return {"selected":rows,"allocation":dict(sorted(allocation.items())),"cutoff":selected[-1]["evaluation"]["final_score"] if selected else None,"rationale":" ".join(reasons),"rejected_count":max(0,len(ranked)-len(selected)),"ranked_total":len(ranked)}