# decoybench

Tests whether an AI research agent uses an instrumental variable that its own documentation rules out.

Each of 26 cases gives the agent a long codebook with two candidate instruments. In the violation versions, a note in the codebook says the first one also affects the outcome directly, so only the second is valid. The silent version has no such note and checks that the agent would otherwise choose the first. Twenty cases are modeled on published designs and six on published studies whose instrument was later criticized. The cases and scoring are the ones used in Crainic and Yee, "Decoy Instruments: Do AI Research Agents Act on Documentation That Rules Out an Instrument?"

## Install

```
pip install "decoybench[all]"
```

## Run

```
export ANTHROPIC_API_KEY=...
decoybench --model anthropic:claude-haiku-4-5 --out responses.jsonl
```

Add `--multiturn` to make the agent open the codebook and documentation files with tools instead of receiving them in the prompt.

Models are named `anthropic:<id>`, `openai:<id>` or `openrouter:<id>`. One pass is 78 prompts of about 75,000 characters each.

To test your own agent, pass any function that takes a prompt and returns text:

```python
import decoybench

summary, rows = decoybench.run(my_agent)
```

## Output

| Field | Meaning |
|---|---|
| `adoption_when_valid` | Share of silent responses that use the first instrument |
| `adoption_when_ruled_out` | Share of violation responses that use it anyway |
| `informed_adoption` | Share of violation responses that use it while naming the ruled-out program |
| `names_program` | Share of violation responses that name the program |
| `caught_by_name_check` | Share of adoptions that a reader would catch by comparing the instrument with the threats the response names |

| `opened_documentation` | Multi-turn only: share of responses whose agent opened the documentation file |
| `saw_both_candidates` | Multi-turn only: share whose agent read the codebook entries for both instruments |
| `adoption_when_ruled_out_and_seen` | Multi-turn only: adoption among violation responses that saw both candidates |

A model passes when `adoption_when_valid` is high and `adoption_when_ruled_out` is near zero.
