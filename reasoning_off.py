import os
import sys
from pathlib import Path

import abs_v2 as A
import scenarios_v2 as V

CONFIGS = {
    "haiku-5.5-nothink": ("anthropic", "claude-haiku-5-5", {}, "haiku-5.5"),
    "gpt-5-mini-minimal": ("openai", "gpt-5-mini", dict(service_tier="flex", reasoning_effort="minimal"), "gpt-5-mini"),
    "sonnet-5.5-nothink": ("anthropic", "claude-sonnet-5-5", {}, "sonnet-5.5"),
}
ROUTES = {
    "openrouter": {"sonnet-5.5-nothink": ("openrouter", "anthropic/claude-sonnet-5.5",
                                          {"provider": {"only": ["anthropic"], "allow_fallbacks": False}}, "sonnet-5.5")},
}

CONFIGS.update(ROUTES.get(os.environ.get("ROUTE", ""), {}))
for name, (be, mid, extra, src) in CONFIGS.items():
    A.MODELS[name] = (be, mid, extra)
    A.PRICE[name] = A.PRICE[src]

if __name__ == "__main__":
    A.OUT = Path(__file__).resolve().parent / "followup" / "reasoning_off"
    A.OUT.mkdir(parents=True, exist_ok=True)
    for m in sys.argv[1:] or list(CONFIGS):
        rows = [(m, "agent", k, v, "neutral", True, i) for k in V.ORDER for v in ("implied", "chain") for i in range(3)]
        A.run_sync(m, rows, float(os.environ.get("CAP", "2.0")), 4)
