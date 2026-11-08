import concurrent.futures as cf
import gzip
import json
from importlib import resources

from .agentic import Folder, saw, split
from .score import score

VERSIONS = ("silent", "implied", "chain")


def load_cases(source="all"):
    with gzip.open(resources.files("decoybench") / "cases.json.gz", "rt") as f:
        cases = json.load(f)
    return [c for c in cases if source == "all" or c["source"] == source]


def run(agent, source="all", versions=VERSIONS, repeats=1, workers=4, multiturn=False):
    cases = load_cases(source)
    jobs = [(c, v, i) for c in cases for v in versions for i in range(repeats)]

    def one(job):
        c, v, i = job
        if not multiturn:
            text = agent(c["prompts"][v])
            return dict(case=c["key"], source=c["source"], version=v, draw=i, response=text, **score(c, v, text))
        message, files = split(c["prompts"][v])
        folder = Folder(files)
        text, usage = agent(message, folder)
        return dict(case=c["key"], source=c["source"], version=v, draw=i, response=text, **score(c, v, text),
                    opened_documentation=any(p == "documentation.txt" for p, _, _ in folder.opened),
                    saw_both_candidates=saw(c, v, folder, "var") and saw(c, v, folder, "alt_var"),
                    reads=folder.opened, usage=usage)

    with cf.ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, jobs))
    return summarize(rows), rows


def summarize(rows):
    def rate(sub, k):
        return round(sum(r[k] for r in sub) / len(sub), 3) if sub else None

    silent = [r for r in rows if r["version"] == "silent"]
    viol = [r for r in rows if r["version"] != "silent"]
    adopted = [r for r in viol if r["adopt"]]
    out = dict(responses=len(rows),
                adoption_when_valid=rate(silent, "adopt"),
                adoption_when_ruled_out=rate(viol, "adopt"),
                informed_adoption=rate(viol, "informed"),
                names_program=rate(viol, "names_program"),
                caught_by_name_check=rate(adopted, "names_program"))
    if rows and "opened_documentation" in rows[0]:
        seen = [r for r in viol if r["saw_both_candidates"]]
        out.update(opened_documentation=rate(rows, "opened_documentation"),
                   saw_both_candidates=rate(rows, "saw_both_candidates"),
                   adoption_when_ruled_out_and_seen=rate(seen, "adopt"))
    return out
