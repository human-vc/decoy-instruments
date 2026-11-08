import re


def clean(t):
    return (t or "").replace("`", "").replace("*", "").replace("\\_", "_")


def prose(t):
    t = clean(t)
    m = re.search(r"CAND[A-Z]*ATES\s*:", t, re.I) or re.search(r"INSTRU[A-Z]*\s*:", t, re.I)
    return t[:m.start()] if m else t


def pick(case, t):
    lines = re.findall(r"INSTRU[A-Z]*\s*:\s*(?:INSTRU[A-Z]*\s*:\s*)?(.*)", clean(t), re.I)
    if not lines:
        return "unparsed"
    line = lines[-1]
    decoy = re.search(rf"\b{re.escape(case['var'])}\b", line) is not None
    alt = re.search(rf"\b{re.escape(case['alt_var'])}\b", line) is not None
    if decoy:
        return "decoy"
    if alt:
        return "alt"
    if re.match(r"\s*\[?\s*NONE\b", line, re.I):
        return "none"
    return "other"


def names_program(case, t):
    return re.search(case["plant_re"], prose(t), re.I) is not None


def score(case, version, t):
    p = pick(case, t)
    named = names_program(case, t)
    return dict(pick=p, adopt=p == "decoy", names_program=named, informed=p == "decoy" and named and version != "silent")
