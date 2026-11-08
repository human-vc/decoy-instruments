# Reasoning configuration follow-up (written 2026-11-07, before any call)

Models: claude-haiku-5-5 with thinking disabled (no thinking parameter), and gpt-5-mini with reasoning_effort "minimal" (the lowest setting the API offers; not reasoning off). Everything else as in the main run: same prompts (scenarios_v2.agent_parts, neutral arm, threat request), implied and chain versions, 20 settings, draws 0 to 2, default sampling, same scorer (scenarios_v2.outcome).

Outcome: adoption (instrument line names the decoy). Estimand per model: the setting-level mean over implied and chain, as in the main analysis. Comparison: difference from the same model's main-run configuration, setting-cluster bootstrap 95% interval (4,000 draws, seed 0). Named adoption reported alongside. No threshold or decision rule; results are reported as estimated.

Addendum (2026-11-07, before any call for this model): claude-sonnet-5-5 with thinking disabled (no thinking parameter), same design, compared with the main-run sonnet-5.5 configuration (adaptive thinking, effort high). gpt-6.1-sol was not used because its API accepts no reasoning setting below "low".

Note (2026-11-07): the direct Anthropic API stopped after 91 of 120 sonnet-5.5-nothink calls (account credit exhausted). The remaining 29 calls go through OpenRouter (anthropic/claude-sonnet-5.5, provider pinned to Anthropic, no reasoning parameter), with identical prompts; the record field "params" shows the route of each call.
