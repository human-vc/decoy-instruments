import sys
from pathlib import Path
import abs_v2 as A
import scenarios_nat as N

A.OUT = Path(__file__).resolve().parent / "out_nat"
A.OUT.mkdir(exist_ok=True)
A.V = N
CAPS = {"gemma-4-31b": 0.5, "haiku-4.5": 1.0, "haiku-4.5-think": 2.0, "gpt-4o-mini": 0.5, "gpt-5-mini": 1.0,
        "opus-5.5": 5.0, "gpt-6.1-sol": 2.0, "gemini-4-argon": 2.0}
models = sys.argv[1:] or list(CAPS)
rows = {m: [(m, "agent", k, v, "neutral", True, i) for k in N.ORDER for v in ("silent", "implied", "chain") for i in range(3)]
        for m in models}
if __name__ == "__main__":
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(len(models)) as ex:
        list(ex.map(lambda m: A.run_sync(m, rows[m], CAPS[m], 3), models))
    print("ALLDONE")
