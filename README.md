# Decoy Instruments

Replication materials for "Decoy Instruments: Do AI Research Agents Act on Documentation That Rules Out an Instrument?" (Crainic and Yee). The pre-registration is `prereg.md`; the rules for the held-out published cases are `natural_rules.md`.

## Setup

```
pip install -r requirements.txt
```

All commands run from the repository root. Analysis needs no API keys.

## Reproduce the results

| Result | Command |
|---|---|
| Main tables, H1 to H3 (confirmatory) | `python analyze_v2.py` |
| Claude Haiku 4.5 with reasoning (exploratory) | `python analyze_addendum.py` |
| Claude Fable 5.1, main settings | `python score_fable.py` |
| Held-out published cases | `python score_nat.py fable/natural_index.json fable/natural_results.json` |
| Silent responses that raise the published critique | `python silent_hits.py` |
| Coder agreement and pattern validation | `python agreement.py` |
| Figure 1 | `python fig_adoption.py` |

## Rerun the models

```
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... OPENROUTER_API_KEY=...
python abs_v2.py dry --tier B
python abs_v2.py run --tier B --models <model> --cap <model>=<USD>
python run_nat.py
```

`dry` renders all 5,432 prompts without calling any API; `out5/prompt_hashes_B.tsv` should be unchanged. `run` and `run_nat.py` write to `out5/` and `out_nat/`. Model settings are in `abs_v2.py`.

## Files

| Path | Contents |
|---|---|
| `scenarios_v2.py` | The 20 settings, codebooks, planted violations and scoring patterns |
| `kill2.py`, `kill3.py` | Filler variables and documentation paragraphs used to pad the codebooks |
| `estimate_v2.py` | Simulated data and regression tables for the estimation step |
| `scenarios_nat.py` | The six held-out published cases |
| `cost_v2.py`, `power_v2.py` | Call manifest and power calculations |
| `abs_v2.py` | Runner (`abs_v2_frozen.py` is the version hashed in the pre-registration) |
| `out5/` | 5,430 confirmatory responses, one JSON line per call |
| `out_addendum/` | Claude Haiku 4.5 with reasoning |
| `out_nat/` | Held-out case responses |
| `fable/` | Claude Fable 5.1 responses |
| `build_coding.py` | Draws the 240-response coding sample (seed 20261105) and builds the coder sheets |
| `coding/instructions.txt` | Coding rules given to both coders |
| `coding/responses.csv` | The 240 sampled responses |
| `coding/JC.csv`, `coding/BY.csv` | Each coder's independent codes |
| `coding/consensus.csv` | Reconciled codes for items where the coders disagreed |
| `coding/key.csv` | Model, version and pattern result for each sampled response |

The SHA-256 hashes of the frozen files are listed in prereg section 12 and can be checked with `shasum -a 256 <file>`.
