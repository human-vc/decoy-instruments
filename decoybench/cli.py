import argparse
import json

from .agentic import loop_from_name
from .agents import from_name
from .run import VERSIONS, run


def main():
    ap = argparse.ArgumentParser(prog="decoybench", description="Test whether an AI agent uses an instrument its documentation rules out.")
    ap.add_argument("--model", required=True, help="anthropic:<id>, openai:<id> or openrouter:<id>")
    ap.add_argument("--source", default="all", choices=["all", "main", "published"])
    ap.add_argument("--versions", nargs="+", default=list(VERSIONS), choices=list(VERSIONS))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--multiturn", action="store_true", help="the agent must open the codebook and documentation files with tools")
    ap.add_argument("--out", help="write every response and score to this JSONL file")
    a = ap.parse_args()
    agent = loop_from_name(a.model) if a.multiturn else from_name(a.model)
    summary, rows = run(agent, a.source, a.versions, a.repeats, a.workers, a.multiturn)
    if a.out:
        with open(a.out, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
