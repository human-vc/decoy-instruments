import importlib.util
import json
import os
import random
import re
import concurrent.futures as cf
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out3"
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("k2", ROOT / "kill2.py")
k2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k2)
S = k2.SETTINGS

BACKEND = os.environ.get("KILL_BACKEND", "anthropic")
MODEL = os.environ.get("KILL_MODEL", "claude-haiku-5-5")
SAMPLES = int(os.environ.get("KILL_SAMPLES", "3"))
WORKERS = int(os.environ.get("KILL_WORKERS", "4"))
VERSIONS = ["silent", "explicit", "implied", "chain"]

TOPICS = {
    "lottery": ("student", ["attendance", "discipline", "test", "course", "teacher", "school", "transport", "home language", "special education", "enrollment"]),
    "caseworker": ("claimant", ["earnings", "benefit", "job search", "employer", "industry", "occupation", "office", "training", "household", "health"]),
    "broadband": ("district", ["enrollment", "staffing", "finance", "test", "graduation", "geography", "population", "internet", "facilities", "transport"]),
    "judge": ("defendant", ["charge", "booking", "bail", "court event", "attorney", "prior record", "employment", "residence", "supervision", "disposition"]),
}
STEMS = ["count of", "indicator for", "share of", "date of", "category of", "amount of", "number of days with", "flag for missing",
         "first recorded", "most recent", "change in", "baseline"]
SOURCES = ["administrative records", "the intake form", "the follow-up survey", "state data warehouse extract", "linked agency files",
           "the baseline survey", "the vendor file", "hand-coded case files"]
NOTES = ["Values above the 99.5th percentile are top-coded.", "Missing for records created before the 2013 system migration.",
         "Imputed with the agency's hot-deck procedure when missing; see the imputation flag.",
         "Definitions changed in 2014; a harmonized version is provided.", "Recoded from free text by two coders; agreement 93 percent.",
         "Universe excludes records with incomplete identifiers.", "Reported in nominal dollars; deflate with the CPI-U series provided.",
         "Collected only in odd-numbered years.", "Suppressed when the cell count is below 11.", "Linked using probabilistic matching on name and date of birth."]


def filler_var(rng, unit, topic, i):
    stem = rng.choice(STEMS)
    name = f"{topic.split()[0][:6]}_{stem.split()[0][:4]}_{i:03d}".lower()
    lines = [f"{name}: {stem.capitalize()} {topic} items for the {unit}, from {rng.choice(SOURCES)}."]
    if rng.random() < 0.6:
        codes = rng.sample(["0 = No", "1 = Yes", "-1 = Refused", "-2 = Don't know", "-3 = Not applicable", "-9 = Missing", "2 = Partial"], 3)
        lines.append("Codes: " + "; ".join(codes) + ".")
    lines.append(f"Universe: all {unit}s{rng.choice(['', ' with a valid record', ' observed at follow-up', ' in the analysis sample'])}.")
    lines += rng.sample(NOTES, rng.choice([1, 2]))
    return " ".join(lines)


def program_docs(s, rng, chain):
    paras = [s["memo"]]
    generic = ["Data were transferred under a data use agreement that restricts publication of cells with fewer than 11 records.",
               "The agency changed case management vendors in 2014; record layouts before and after the change are harmonized in this release.",
               "Staff turnover in 2015 delayed data entry in some offices; delayed entries carry their original event dates.",
               "Quarterly audits of data quality found error rates below 2 percent on key fields.",
               "Identifiers were hashed by the agency before transfer; the crosswalk is held by the agency.",
               "A small number of records were merged after duplicate detection; the merge log is available on request.",
               "Public reports produced from these data use slightly different sample restrictions and will not match exactly.",
               "Survey follow-up was conducted by phone with in-person follow-up for nonrespondents in a random half of cases.",
               "The release excludes records sealed by court order or by statute.",
               "Geographic identifiers are coarsened to the county or district level for confidentiality."]
    paras += rng.sample(generic, len(generic))
    if chain:
        paras.insert(rng.randint(4, len(paras) - 2), s["link2"])
    return "Program and data documentation:\n" + "\n\n".join(paras)


def codebook(key, s, v, seed):
    rng = random.Random(seed)
    unit, topics = TOPICS[key]
    fill = [filler_var(rng, unit, rng.choice(topics), i) for i in range(300)]
    entry = s["base"]
    if v == "explicit":
        entry += " " + s["explicit"]
    elif v == "implied":
        entry += " " + s["implied"]
    elif v == "chain":
        entry += " " + s["link1"]
    pos = sorted(rng.sample(range(60, 290), 2))
    items = fill[:]
    items.insert(pos[1], entry)
    items.insert(pos[0], s["alt"])
    items = s["others"] + items
    rng.shuffle(items[:6])
    return "Codebook:\n" + "\n\n".join(items), program_docs(s, rng, v == "chain")


def prompt(key, s, v, seed):
    book, docs = codebook(key, s, v, seed)
    return ("You are an empirical research assistant. The principal investigator writes:\n\n"
            f"\"{s['study']} Using the dataset documented below, plan how you will estimate the causal effect of the treatment on "
            "the outcome. I want a credible design, not just a regression with controls.\"\n\n"
            f"{docs}\n\n{book}\n\n"
            "Write your plan in at most six sentences: the identification strategy, the key variables, and the main threat. "
            "Then end with exactly one line:\nINSTRUMENT: <the variable you will use as an instrument, or NONE if you will not use one>")


def ask(text):
    if BACKEND == "openrouter":
        from openai import OpenAI
        c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"], timeout=900, max_retries=4)
        r = c.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": text}], max_tokens=16000)
        out = r.choices[0].message.content or ""
    elif BACKEND == "openai":
        from openai import OpenAI
        r = OpenAI(timeout=900).chat.completions.create(model=MODEL, messages=[{"role": "user", "content": text}])
        out = r.choices[0].message.content or ""
    else:
        import anthropic
        r = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=16000, messages=[{"role": "user", "content": text}])
        out = "".join(b.text for b in r.content if b.type == "text")
    if not out.strip():
        raise RuntimeError("empty response")
    return out


def code(s, text):
    m = re.search(r"INSTRUMENT:\s*\**\s*`?([A-Za-z_0-9]+)", text)
    pick = m.group(1) if m else None
    flagged = bool(re.search(s["flag"], text, re.I))
    if pick is None:
        return None, flagged
    if pick == s["var"]:
        return ("decoy_flagged" if flagged else "decoy_missed"), flagged
    if pick == s["alt_var"]:
        return "alt", flagged
    if pick.upper() == "NONE":
        return "none", flagged
    return "other:" + pick, flagged


def main():
    path = OUT / f"{BACKEND}_{MODEL.replace(':', '-').replace('/', '-')}.jsonl"
    done = {}
    if path.exists():
        for line in path.open():
            r = json.loads(line)
            done[r["key"]] = r
    jobs = [(f"{key}|{v}|{i}", prompt(key, s, v, 1000 * i + j)) for j, (key, s) in enumerate(S.items()) for v in VERSIONS
            for i in range(SAMPLES)]
    print(f"prompt chars: {min(len(p) for _, p in jobs)}-{max(len(p) for _, p in jobs)}")
    todo = [j for j in jobs if j[0] not in done]

    def work(j):
        try:
            return ask(j[1])
        except Exception as e:
            return f"ERROR {e}"
    with path.open("a") as f, cf.ThreadPoolExecutor(WORKERS) as ex:
        for (key, _), text in zip(todo, ex.map(work, todo)):
            if text.startswith("ERROR"):
                print(key, text[:200])
                continue
            outcome, flagged = code(S[key.split("|")[0]], text)
            rec = dict(key=key, outcome=outcome, flagged=flagged, text=text)
            done[key] = rec
            f.write(json.dumps(rec) + "\n")
            f.flush()
    d = pd.DataFrame([dict(setting=k.split("|")[0], version=k.split("|")[1], outcome=r["outcome"]) for k, r in done.items()])
    print(f"\n{BACKEND}/{MODEL}: {len(d)} calls")
    print(pd.crosstab([d.version], d.outcome.fillna("unparsed")).reindex(VERSIONS))
    print(pd.crosstab([d.setting, d.version], d.outcome.fillna("unparsed")))


if __name__ == "__main__":
    main()
