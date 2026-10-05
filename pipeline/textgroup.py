import math
def phrases(words, gap_k=1.3, line_k=0.7):
    """merge adjacent words (same line) into phrases. words: list of dict with X,Y,size,s,bbox(in pts) ; uses X,Y centers + size to estimate widths"""
    W=[w for w in words if w["s"].strip()]
    # estimate half-width of each word from char count * size*0.55
    for w in W:
        w["_hw"]=len(w["s"])*w["size"]*0.55/2*3.53   # cm approx at 1:100 (pt->cm factor ~3.53); refined by caller via size_cm
    W.sort(key=lambda w:(-round(w["Y"]/8),w["X"]))
    used=set(); out=[]
    for i,w in enumerate(W):
        if i in used: continue
        group=[w]; used.add(i)
        changed=True
        while changed:
            changed=False
            for j,v in enumerate(W):
                if j in used: continue
                # same line and close horizontally to any word in group
                for g in group:
                    if abs(v["Y"]-g["Y"])<=line_k*g["size"]*3.53*0.8:
                        dx=abs(v["X"]-g["X"])-(v["_hw"]+g["_hw"])
                        if dx<=gap_k*g["size"]*3.53*0.6:
                            group.append(v); used.add(j); changed=True; break
        group.sort(key=lambda g:g["X"])
        s=" ".join(g["s"] for g in group)
        out.append({"s":s,"X":sum(g["X"] for g in group)/len(group),"Y":sum(g["Y"] for g in group)/len(group),"n":len(group)})
    return out
