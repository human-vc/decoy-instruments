import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import analyze_v2 as Z

Z.DEVELOPER.setdefault("fable", "anthropic")

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        for src in ("out5", "out_addendum"):
            for f in (ROOT / src).glob("*.jsonl"):
                (Path(d) / f.name).symlink_to(f)
        Z.main(d)
