import concurrent.futures as cf
import gzip
import json
from importlib import resources

from .score import score

VERSIONS = ("silent", "implied", "chain")


def load_cases(source="all"):
    with gzip.open(resources.files("decoybench") / "cases.json.gz", "rt") as f:
        cases = json.load(f)
    return [c for c in cases if source == "all" or c["source"] == source]


def run(agent, source="all", versions=VERSIONS, repeats=1, workers=4):
    cases = load_cases(source)
    jobs = [(c, v, i) for c in cases for v in versions for i in range(repeats)]

    def one(job):
        c, v, i = job
        text = agent(c["prompts"][v])
        return dict(case=c["key"], source=c["source"], version=v, draw=i, response=text, **score(c, v, text))

    with cf.ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, jobs))
    return summarize(rows), rows


def summarize(rows):
    def rate(sub, k):
        return round(sum(r[k] for r in sub) / len(sub), 3) if sub else None

    silent = [r for r in rows if r["version"] == "silent"]
    viol = [r for r in rows if r["version"] != "silent"]
    adopted = [r for r in viol if r["adopt"]]
    return dict(responses=len(rows),
                adoption_when_valid=rate(silent, "adopt"),
                adoption_when_ruled_out=rate(viol, "adopt"),
                informed_adoption=rate(viol, "informed"),
                names_program=rate(viol, "names_program"),
                caught_by_name_check=rate(adopted, "names_program"))
