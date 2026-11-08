# Decoy Instruments

Replication materials for "Decoy Instruments: Do AI Research Agents Act on Documentation That Rules Out an Instrument?" (Crainic and Yee).

## Test your own agent

```
pip install "decoybench[all]"
decoybench --model anthropic:claude-haiku-4-5
```

See `decoybench/README.md`.

## Reproduce

```
pip install -r requirements.txt
python analyze_v2.py
python reproduce.py
```

`analyze_v2.py` is the analysis fixed in the plan (Table 1 and the main hypothesis tests). `reproduce.py` prints every other number in the paper and writes Figure 1. Neither needs API keys.

## Rerun the models

```
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... OPENROUTER_API_KEY=...
python abs_v2.py dry --tier B
python abs_v2.py run --tier B --models <model> --cap <model>=<USD>
python run_nat.py
```

`dry` renders all 5,432 prompts without calling any API; `out5/prompt_hashes_B.tsv` should be unchanged.

## Contents

| Path | Contents |
|---|---|
| `scenarios_v2.py`, `kill2.py`, `kill3.py` | The 20 settings and their codebooks |
| `scenarios_nat.py` | The six held-out published cases |
| `estimate_v2.py` | Simulated data and regression tables for the estimation step |
| `abs_v2.py`, `cost_v2.py`, `run_nat.py` | Runners and call manifest |
| `build_coding.py` | Draws the 240-response coding sample |
| `out5/`, `out_nat/`, `followup/` | Model responses (`out_nat/v1/` is the held-out run before calibration; `followup/multiturn.jsonl` is the multi-turn run) |
| `coding/` | Coding instructions, sampled responses, both coders' codes and the reconciled codes |
| `decoybench/`, `make_cases.py` | The installable test and the script that exports its cases |
| `docs/` | Analysis plan (`prereg.md`, not filed with a registry) and held-out case rules |
| `frozen/` | Runner as hashed in the plan |
