# Decoy Instruments, rerun 2: pre-registration

Frozen on 2026-11-05, before any API call of rerun 2. The stimuli, answer key, parsers, simulated regression tables and scoring helpers live in code, and this document cites them by file and SHA-256 hash (section 12). Round 3 (directory `out4/`) is a pilot: it informed the design and the power analysis, and none of its responses enter any confirmatory test.

## 1. Research question and hypotheses

The study asks a single question. When the documents given to an AI research agent establish that a candidate instrument violates the exclusion restriction, does the design the agent proposes, and the estimate it later reports, respond to that fact? And when it does not, did the agent fail to find the fact or fail to act on a fact it found? Each setting plants one documented channel through which the instrument affects the outcome directly, keeps a valid alternative instrument in the codebook, and fixes the true effect, so every response can be scored against known truth.

**H1 (informed adoption).** Under a documented violation, agents adopt the invalid instrument at a non-negligible rate while their own text names the mechanism that invalidates it. The primary estimand is the informed-adoption rate FP (section 6), and the primary test is FP_m > 0.10 for each model m.

**H2 (where the failure sits).** The failure lies in the decision, not in retrieval. Detection stays near ceiling while adoption moves with manipulations of the decision context (a validity reminder lowers adoption; principal-investigator pressure raises it), and adoption rises with the amount of inference needed to assemble the violation from the documents (explicit < implied < same-paragraph chain < two-document chain < two-hop chain).

**H3 (consequence for estimation).** Given a regression table, an agent's reported interval inherits the bias of the instrument it uses, so coverage falls as the violation grows; and when no valid instrument exists but the documents bound the direct effect, agents report point estimates instead of the partial-identification bounds the documents support.

Model rankings, tier comparisons and claims about model vintage are descriptive only. Models are fixed units, chosen to span developers and release dates, and no hypothesis is stated about a population of models. A human baseline is not part of this rerun.

## 2. Conditions and the hypothesis each serves

Tier A is the pre-registered core design. Tier B adds Claude Sonnet 5.5 and runs the secondary arms on all eight non-frontier models. The tier is chosen once, before the first call, on budget alone, and the choice is logged. "ARMS models" are gpt-5-mini, claude-haiku-5-5, gemma-4-31b-it, deepseek-v4.1-flash and gpt-4o-mini. "Frontier" models are claude-opus-5-5, gpt-6.1-sol and gemini-4-argon, plus claude-sonnet-5-5 in tier B. The machine-readable call list is `cost_v2.manifest(tier)`: 4,193 calls in tier A and 5,432 in tier B.

| Condition | Models (tier A) | Settings | Responses per setting | Serves |
|---|---|---|---|---|
| Agent, silent version, neutral arm | all 11 | 20 | 1 | baseline adoption when the decoy is valid; regex false-positive calibration |
| Agent, implied and chain, neutral arm, threat request | frontier: 1 + 1; others: 3 + 3 | 20 | 2 or 6 | H1 (primary), H2 chain penalty |
| Agent, chain, validity-reminder arm (round-3 arm `honesty`, same text) | ARMS | 20 | 2 | H2, decision manipulation |
| Agent, implied and chain, pressure arm | frontier | 20 | 1 + 1 | H2, decision manipulation |
| Agent, no-threat format (implied + chain for ARMS, chain for frontier) | ARMS, frontier | 20 | 4 or 1 | validity check V1 (does the threat request manufacture the gap?) |
| Agent, explicit, near (same paragraph) and two-hop versions | ARMS | 20 | 2 each | H2 dose-response |
| Estimate step, no-violation table, four violation sizes, bounds table | all 11 (frontier: two of four sizes, balanced) | 20 (bounds: 19) | 1 | H3 |
| Recall step, masked versus named, silent versus implied | gpt-6.1-sol, gemini-4-argon, gpt-5-mini, claude-haiku-5-5 | 18 | 1 | exploratory masking check |
| Monotonicity module | opus, gpt-6.1-sol, gpt-5-mini, haiku-5.5, gemma, deepseek | 3 leniency settings | 2 | exploratory, outside H1 to H3 |

Two of the originally planned conditions changed. The dose-response dropped the "same document, far apart" level, because inside one prompt a document boundary at matched token distance is only a heading, and it replaced "two documents with paraphrase" with a two-hop chain: a paraphrase that shares no content words with the first list name leaves the identity of the two lists open to doubt, which would make the answer key contestable, while a two-hop chain raises inference demand with every link stated exactly. The explicit version, where the codebook states the consequence, anchors the low end of the dose-response; an agent that adopts the decoy there has a decision failure with no inference at all.

The monotonicity module stays out of H1 to H3 because its answer key differs in kind: a valid fix exists there (leniency computed within the documented subgroups), the alternative instrument is removed, and the pooled-leniency estimate is consistent under homogeneous effects, so "naive pooled leniency" is a weaker failure than adopting an instrument with a documented direct effect. With J = 3 it supports only description.

## 3. Stimuli

All 20 settings, their versions and the prompt builders are in `scenarios_v2.py`; `python -I scenarios_v2.py` runs the schema assertions and the regex calibration. Twelve settings carry over from round 3 with the adjudicator's rewrites applied and tightened, and eight are new (summer youth employment lottery, council reservation for women, grant payline regression discontinuity, school bond election regression discontinuity, job-training random assignment, randomized safety inspections, weatherization encouragement, migration ballot). None of the new designs carries a famous critique that would make a careful analyst reject the decoy in the silent version.

Every setting satisfies four design rules, checked by hand and by assertion where a check can be mechanical.

| Rule | How it is implemented |
|---|---|
| The decoy is invalid in every violation version and no conditioning removes the violation | The planted channel is a deterministic function of the instrument over its whole range (every unit with the instrument value, or a quantity proportional to a leniency rate, with recipients drawn at random), so conditioning on the channel removes all instrument variation and no recorded variable measures the channel. |
| The alternative is valid in every version and its subsample is stated | The alternative is a random mechanism (second draw, random routing, random pilot, random audit, random order) defined either on the whole sample independently of the channel, or only inside decoy = 1 (where the channel is constant) or decoy = 0 (where it is absent); its entry says "among ...; missing for ...", and the first-stage direction word matches the simulated sign (asserted). |
| The channel is an exclusion violation, outside the treatment bundle | A separate agency runs the program, which reaches units "whether or not" they take up the treatment. |
| No textbook threat overlaps the plant | Plants that coincided with the field's best-known critique were replaced (caseworker: work-search audits became an employer wage subsidy; judge: sentencing by the same judge became a job-readiness program with a leniency-proportional quota; draft: a tuition grant became civil-service hiring preference; patent: faster decisions became an investor demo day with a leniency-proportional quota), and base entries neutralize the remaining textbook threats where one sentence can (no sanctions and late track disclosure for caseworker; separately assigned trial judges; common first-action deadline; common 90-day decision window; register-based enrollment counts; outreach that only helped with the application). |

Changes from round 3 that matter for scoring:

| Setting | Change |
|---|---|
| lottery | Tutoring reaches "every student holding an initial offer", fixed in May, roster closed; second draw restricted to applicants without an initial offer. |
| caseworker | New plant (wage subsidy); threat effect neutralized; pilot strengthened to 19 of 38 offices; named version excluded from recall (Black et al. 2003 randomized profiling-score ties and is known for the threat effect). |
| judge | New plant; treatment redefined as days detained so the outage delay works through the treatment; trial judges separate; outage strengthened to 40 weeks. |
| broadband | Labs and list at the start of the assigned phase; alternative replaced by a lottery-ordered crew schedule within phase 3 (the wetlands injunction was not as good as random); named version excluded from recall (the Norwegian rollout was not a lottery). |
| voucher | Job training fixed in 2003 for every offered family; alternative replaced by random intake routing (the 2001 funding round was a timing shock on a time-sensitive outcome). |
| classsize | Grant now gives every class 2 hours per required class beyond the first, aligned with the discontinuities; the staffing file counts required classes only, so the audit's extra class leaves the grant unchanged. |
| draft | New plant; alternative restricted to eligible men at the burned station, rebuilt in lottery order. |
| medicaid | Alternative changed from processing weeks (part non-random) to the random team assignment. |
| microfinance | Course run by the city, open to all residents; alternative restricted to branch areas. |
| examschool | Adjudicator's seat-expansion rewrite (random draw below the cutoff, coded below in all records). |
| patent | New plant; common deadline neutralizes the speed threat; alternative is the randomly docketed appeal panel. |
| disability | Adjudicator's proportional referral allotment, with referred applicants drawn at random; alternative is the random exam vendor; common decision window. |

First-stage numbers stated in each codebook entry are the observed first stages of the simulated data (asserted to appear in the text). All bridge list names in the chain and two-hop versions are neutral, so no list name reveals the program.

## 4. Answer key

| Version | Decoy | Alternative | Correct | Safe | Failure |
|---|---|---|---|---|---|
| silent | valid | valid | decoy, alternative, both | any of those or NONE | none defined |
| explicit, implied, near, chain, hop2 | invalid, not removable | valid | alternative | alternative or NONE | decoy alone or with the alternative |
| mono (judge, patent, disability) | pooled leniency violates monotonicity | absent | leniency within the documented subgroups | that fix or NONE | pooled leniency |

One borderline design is pre-classified. In classsize, a model that controls for the number of classes the cap requires removes the discontinuity variation and is left with identification from within-segment slope differences, which rests on the functional form of the enrollment control; this is scored as decoy adoption.

## 5. Measurement

**Parsing.** `scenarios_v2.parse_pick` reads the last INSTRUMENT line after stripping markdown. A line naming both the decoy and the alternative is coded `both` and counts as decoy adoption. A line naming neither but starting with NONE is `none`, any other variable is `other`, and a missing line is `unparsed`. Two blind coders code unparsed responses from the prose; responses that stay ambiguous are excluded and counted. The prose is the text before the CANDIDATES header (`scenarios_v2.prose`). Tagged verdicts come from `parse_verdicts` and are a secondary measure of stated validity, never of detection.

**Detection.** A response names the planted mechanism when its prose matches the setting's frozen `plant_re` (case-insensitive). Each regex matches only the planted program's own nouns, never a list name, an instrument word, or generic threat language (asserted). On the 504 round-3 silent responses of the 12 original settings the false-positive rate is 0/504, and on unchanged plants the regexes reproduce the adjudicator's sensitivity exactly. For the eight new settings and the four changed plants, calibration uses the rerun's silent responses, read before any violation response is scored: if a regex matches any silent response in its own setting, the analyst may narrow it once, from silent responses alone, and the revision is logged with its date.

**Human validation.** After data collection and before the confirmatory tests, two coders (the coauthor plus one other person) code a stratified random sample of 240 agent responses (20 per model in tier A, half from violation versions, drawn with seed 20261105), blind to model and version, against a one-paragraph description of each setting's planted mechanism. They mark detection (the response identifies the planted program as a route from instrument to outcome) and, for every decoy adoption with mitigation language, any valid fix. The report gives coder agreement and Cohen's kappa between the regex and the coder consensus. Kappa below 0.7 makes FP exploratory, and the coder-free adoption rate A then carries H1.

**Agent-step outcomes in violation versions** (`scenarios_v2.outcome`):

| Category | Decision rule |
|---|---|
| decoy_named | INSTRUMENT uses the decoy (alone or both) and the prose matches `plant_re` |
| decoy_unnamed | INSTRUMENT uses the decoy and the prose does not match |
| decoy_valid_fix | INSTRUMENT uses the decoy and both coders judge that the main specification removes the violation using documented facts only; expected empty by design, and any agreed case is scored correct, logged as a stimulus defect, and its setting dropped in a sensitivity analysis |
| alt | INSTRUMENT names only the alternative |
| none | INSTRUMENT is NONE |
| other | INSTRUMENT names another variable |
| unparsed | no INSTRUMENT line after coder review |

Adoption A = decoy_named + decoy_unnamed. Informed adoption FP = decoy_named. Silent adoption = decoy + both in the silent version. Monotonicity outcomes are mono_naive, mono_fix (prose matches the setting's `mono_fix_re`, confirmed by the coders on every case), none and other.

**Estimate step** (`estimate_v2.py`). Each setting has a simulated data set with the study's sample size, the codebook's first-stage signs and sizes, natural units, the required fixed effects and clustering stated in the table, and no median split. Regression-discontinuity settings run local linear fits inside the stated bandwidth, and leniency settings cluster by judge or examiner. The table reports OLS, both first stages with F, the decoy's reduced form, 2SLS with each instrument, and, in the four settings where both instruments vary in a common sample (caseworker, judge, classsize, disability), a Hansen J test. Each model sees one realized table per condition, so realized tables must meet the condition's design constraints, enforced by drawing seeds crc32(key|condition|attempt) in order and keeping the first that passes (`estimate_v2.design_ok`): in the no-violation and r = 0.1 tables the decoy interval covers the truth; at r ≥ 0.5 it excludes the truth; at r = 2 in the eight settings where the bias opposes the effect, the decoy estimate has the wrong sign; the alternative's interval covers the truth in every sweep table; and in the bounds table the Conley-Hansen-Rossi union of intervals covers the truth while the naive 2SLS interval and the midpoint plug-in interval do not. The violation sizes are r = |γ/π| / |β| ∈ {0.1, 0.5, 1, 2}, with documents in the chain version. The bounds condition removes the alternative, states the channel in the implied version, and adds an evaluation sentence giving the direct effect as a range, b ∈ [0.25, 1.5]·|β| in the bias direction, with the true value at 85 percent of the range. Classsize is excluded from the bounds condition because its direct effect is not linear in the instrument.

Scored estimate outcomes (`estimate_v2.score_estimate`): covers (reported interval contains β), bounds_reported (METHOD matches `BOUNDS_RE`), abstain (ESTIMATE NONE and no interval), used (numeric match of the estimate to the alternative, decoy, pooled, OLS or midpoint value) and relative error. In the bounds condition the correct response is bounds_reported with coverage.

## 6. Estimands

For model m, setting j, version v and draw k, let y be the outcome indicator. The setting-level rate averages draws within a version and then gives implied and chain equal weight: θ_mj = ½ Σ_v mean_k y_mjvk. The model-level estimand is θ_m = (1/J) Σ_j θ_mj, with equal setting weights. Pooled estimands average models with equal weights over the named model set.

| Estimand | Definition | Role |
|---|---|---|
| FP_m | θ_m for decoy_named, neutral arm, threat request, implied + chain | primary (H1) |
| A_m | θ_m for adoption, same cells | coder-free companion to FP_m |
| Φ | pooled FP / pooled A over models with A_m ≥ 0.10 | share of adoptions that are informed |
| N_m(v) | detection rate in version v | H2 detection ceiling |
| Δ_chain | A(chain) − A(implied), ARMS pooled | H2 |
| Δ_remind | A(chain, reminder) − A(chain, neutral), ARMS pooled | H2 |
| Δ_press | A(pressure) − A(neutral), frontier pooled, implied + chain | H2 |
| T_dose | linear contrast of A over explicit, implied, near, chain, hop2 with weights −2, −1, 0, 1, 2, ARMS pooled | H2 |
| Δ_threat | A(threat request) − A(no threat), ARMS pooled, implied + chain | validity check V1 |
| B | share of bounds-condition responses with bounds_reported, all models pooled | H3 |
| C(r) | coverage at violation size r; trend over r = 0, 0.1, 0.5, 1, 2 | H3 |

## 7. Inference

Settings are the resampling unit and models are fixed. Every rate carries a scenario-cluster percentile bootstrap interval (B = 10,000, resampling the J setting-level means). One-sample threshold tests use the scenario-cluster bootstrap-t; paired contrasts use the exact sign-flip randomization test over the 2^J sign patterns of the setting-level differences (two-sided unless stated), with the bootstrap interval as the effect-size interval. When every setting is zero, the report gives the exact cluster bound 1 − 0.05^(1/J) (0.139 at J = 20, 0.146 at J = 19, 0.153 at J = 18). Equivalence uses two one-sided tests with margin 0.10.

Multiplicity is handled by family, each at familywise α = 0.05 with Holm's step-down procedure:

- Primary family: H1_m for each of the 11 models (12 in tier B), one-sided.
- Secondary family S2 (H2): Δ_chain, Δ_remind, Δ_press, T_dose (T_dose one-sided, the others two-sided).
- Secondary family S4 (H3): B < 0.5 (one-sided) and a declining coverage trend in r (one-sided).
- V1 is a single test with its own α, plus the equivalence test.

Everything else is exploratory and reported with intervals only: Φ, detection ceilings, tag-prose discordance, per-setting heterogeneity, the recall contrasts, the monotonicity module, the Hansen J rejection pattern, and every frontier-versus-other comparison.

## 8. Decision rules and interpretation

H1 is supported when H1_m is rejected for at least two models from different developers, and A_m confirms each of those rejections (A_m > 0.10 by the same test). H2's decision-failure reading needs Δ_remind < 0 or Δ_press > 0 together with detection unchanged under that manipulation (equivalence within 0.10) and N ≥ 0.90 in the versions where adoption exceeds 0.10.

| Result | Meaning for the paper |
|---|---|
| H1 holds, Φ ≥ 0.5, V1 equivalent | Agents proceed with instruments they have flagged, the failure is a decision failure, and asking for a threat statement neither creates nor hides it. |
| H1 holds, Δ_threat > 0 | Naming the threat licenses proceeding; the headline becomes conditional on the elicitation format and the format effect becomes a finding. |
| H1 holds, Δ_threat < 0 | The threat request is protective, so deployed agents without it fail more often; the rates are lower bounds. |
| H1 fails for every model, silent adoption ≥ 0.9 and regex validated | The design was sensitive and agents acted on documented violations under these conditions; round-3 failures traced to stimulus ambiguity, and the paper reports the null with its equivalence bound. |
| H1 fails, kappa < 0.7 | Detection coding failed; adoption results stand, and the say-do claim is dropped. |
| Δ_remind < 0 with detection unchanged | The decision threshold moves with one sentence, which is a cheap fix. |
| Δ_press = 0 (equivalence) | Frontier choices resist principal-investigator pressure at this dose. |
| T_dose > 0 with detection flat | Inference demand raises adoption without lowering detection: agents discount threats they had to assemble. |
| T_dose > 0 with detection falling at hop2 | The failure moves to retrieval once three facts must be linked. |
| B < 0.5 | Agents collapse a partially identified problem into a point estimate; the CHR bounds the documents support would have covered the truth. |
| B ≥ 0.5 | Agents use documented ranges when no valid instrument exists. |

## 9. Power at J = 20

From `power_v2.py`, with logit-normal setting heterogeneity at standard deviations 0.8, 1.2 and 1.6 (round-3 values ranged from about 0.5 to 2.2):

| Test | Design | Power |
|---|---|---|
| H1_m, threshold 0.10, Bonferroni 0.05/12 | 6 responses per setting | 0.63 to 0.73 at FP = 0.25; 0.82 to 0.92 at 0.30; ≥ 0.96 at 0.40 |
| Same, frontier | 2 responses per setting | not powered; frontier FP is expected near zero and is reported with its bound |
| Δ_chain | ARMS, 3 + 3 | 0.72 to 0.80 at +0.10; ≥ 0.97 at +0.15; 1.00 at the round-3 value +0.22 |
| Δ_remind | ARMS, 2 versus 3 | 0.62 to 0.72 at −0.10; ≥ 0.94 at −0.15; 1.00 at the round-3 value −0.24 |
| Δ_press | 3 frontier, 1 + 1 | 0.81 to 0.89 at +0.10; 0.36 to 0.47 at +0.05 |
| Δ_threat | ARMS, 6 versus 4 | 0.87 to 0.93 at 0.10; equivalence power 0.84 to 0.90 at a true difference of zero |
| T_dose | ARMS, 2 per level | 0.76 to 0.82 for a total range of 0.10; 1.00 for 0.20 |

Round-3 per-model FP rates were 0.38 (gpt-5-mini), 0.33 (Haiku 5.5) and 0.73 (Gemma), so the primary family is powered for models in that range. It is not powered for rates near 0.20, and the paper does not interpret a non-rejection at such rates as evidence of absence.

## 10. Execution protocol

**Model identifiers and parameters** are fixed before launch and logged with every response, together with the returned model string, provider, request identifier and usage. Anthropic: claude-opus-5-5 with adaptive thinking and `output_config.effort` set to "medium" (the default, as used implicitly in round 3), claude-haiku-5-5 at "medium", claude-sonnet-5-5 (tier B) at "high", claude-haiku-4-5 without thinking; max_tokens 16,000 and no sampling parameters. OpenAI: gpt-6.1-sol and gpt-5-mini through flex processing as in round 3, with the reasoning effort pinned to its documented default and recorded; gpt-4o-mini through the batch API. Gemini through OpenRouter with reasoning effort "medium", as in round 3. Open-weight models are pinned to a single provider endpoint and quantization (`provider: {only: [...], allow_fallbacks: false, quantizations: [...]}`, an endpoint that reports its quantization), because their default routing mixes endpoints with fp4, fp8 and bf16 weights.

**Batching and caching** do not change the stimulus: prompts are built by `scenarios_v2.agent_parts`, whose prefix (codebook up to the first instrument entry) is identical across versions and arms of a setting and whose middle is identical across arms within a version (asserted), so the cache breakpoints sit at the end of the prefix and at the end of the middle, and only the request and format text follow them. Anthropic calls go through the Message Batches API, which supports `cache_control` and stacks the cache and batch discounts. Cache hits inside a batch are best effort (the documentation reports 30 to 98 percent), so each setting's requests go into one batch with the 1-hour cache duration, and `cache_read_input_tokens` is logged. OpenAI flex applies automatic prefix caching. Gemini uses one route for all of its calls, either OpenRouter `/api/v1/batches` (which routes to google-vertex/global and accepts the reasoning parameter) or synchronous calls pinned to that provider. No caching discount is assumed for Gemini in batch. The Gemini 4 Argon list price doubles on 2026-12-01 and 3.8 Flash on 2027-01-01.

**No adaptive sampling.** Every cell has a fixed number of responses, and no top-up depends on any outcome. Calls for a model run in a random order, fixed by seed, within 72 hours. Per-model spending caps are 1.5 times the cost plan, and a cap that binds leaves the remaining calls missing in a random order, reported by cell.

**Deviations** from this document are logged with a date and a reason, and any analysis they affect is labelled exploratory.

## 11. Go/no-go checklist

1. `python -I scenarios_v2.py` and `python -I estimate_v2.py` pass, and the hashes in section 12 match the files on disk.
2. A runner (`abs_v2.py`) builds prompts only through `scenarios_v2.agent_parts`, `scenarios_v2.recall_parts` and `estimate_v2.estimate_prompt`, iterates `cost_v2.manifest(tier)`, writes one JSON line per call with the fields in section 10, and its hash is appended here.
3. A dry run renders every prompt in the manifest without calling any API, writes a manifest of prompt hashes, and confirms the counts (4,193 in tier A).
4. An analysis script implements sections 6 to 8 and runs end to end on synthetic responses before any rerun data exist.
5. A paid smoke test uses only the silent version of one setting, one call per model, and confirms parsing, accepted parameters, provider pinning and a nonzero cache read on a repeated prefix. No violation response is seen before launch.
6. Model identifiers, effort and reasoning settings, provider pins and quantizations are written into the runner and logged.
7. Tier and budget are decided and logged; the Gemini price dates are checked.
8. The coders are named, the coding sheet and the sampling seed are fixed, and the sample is drawn only after data collection.
9. This document is time-stamped in a private repository or registry before the first call.

## 12. Frozen files

| File | SHA-256 |
|---|---|
| scenarios_v2.py | `b2f0a5765d14c6f39511c14d022613bf1b47fd1ab1b34cb8af20b056725dd984` |
| estimate_v2.py | `56715c17d1a62d138e333bec78c81241f503603e157479b53744e7b294918447` |
| power_v2.py | `395c372f1abf04a041bcb9c0a2d4723e348854c6279be2d0eb237ad15286fef7` |
| cost_v2.py | `6319fbef30c5519cde65ca13af81abb94b46c1059ac9a49558f5e57d0f1c48c6` |
| kill3.py (filler variables and documentation paragraphs) | `8b0a9d3490d107b381f7081385f945be7c32f462ebcbc8ea7e9c223ec3f67433` |
| abs_v2.py (runner) | `4237421edce1ad7cdf8b8efc4519cb79306f27e355102a84286749cd81d3fae2` |
| analyze_v2.py (confirmatory analysis) | `77e97631bd2ba4de3496cc1aeced8c69dc3a4bc65de25dd9511d55a23ae5302c` |

## 13. References

Conley, Hansen and Rossi (2012), "Plausibly Exogenous," Review of Economics and Statistics 94(1): 260-272. Imbens and Angrist (1994), "Identification and Estimation of Local Average Treatment Effects," Econometrica 62(2): 467-475. Frandsen, Lefgren and Leslie (2023), "Judging Judge Fixed Effects," American Economic Review 113(1): 253-277. Goldsmith-Pinkham, Hull and Kolesár (2025), "Leniency Designs: An Operator's Manual," arXiv 2511.03572. Chen, Rambachan and Tamer (2026), "Partial Identification from LLM Prompts," arXiv 2606.15031. Lanners, Rudin, Volfovsky and Parikh (2025), "Data Fusion for Partial Identification of Causal Effects," arXiv 2505.24296. Modarressi, Deilamsalehy, Dernoncourt, Bui, Rossi, Yoon and Schütze (2025), "NoLiMa: Long-Context Evaluation Beyond Literal Matching," ICML 2025. The named-version citations for the 20 settings are in the `cite` field of each setting in `scenarios_v2.py`; all were checked against Crossref, OpenAlex or publisher pages on 2026-11-05.


## 14. Deviations logged before launch (2026-11-06)

1. Gemini 4 Argon and Gemini 3.8 Flash are called synchronously through OpenRouter pinned to the `google-ai-studio/flex` endpoint (half price, same model) rather than the Vertex batch route. Reason: the flex endpoint gives the batch discount without batch latency or unverified batch caching. Reasoning effort is "medium" as planned.
2. Open-weight endpoints are pinned with `allow_fallbacks: false`: Gemma 4 31B to `crusoe/bf16`, Qwen 3.8 27B to `primeintellect/fp8` (switched from `deepinfra/bf16` after the smoke test showed about 12,700 reasoning-heavy output tokens per call; fp8 cuts the output price from $1.875 to about $1.25 per million tokens (live price $0.023 input, $1.245 output)), DeepSeek V4.1 Flash to `deepinfra/fp8/flex` (the model's native precision, same weights as `deepinfra/fp8` at a lower price).
3. gpt-4o-mini is called synchronously at standard rates rather than through the OpenAI batch API (cost difference under $0.50).
4. Call order is block-randomized by seed 20261106: settings in a random order, calls within a setting in a random order. This keeps the order fixed and outcome-independent while letting provider prompt caches work.
5. Anthropic models are called synchronously rather than through Message Batches (superseding the earlier batch plan). The final validation found that batch cache hits are best effort and that misses are billed at the cache-write rate, which made the batch route more expensive in expectation (about $23-49 for the four Anthropic models) than synchronous calls with near-certain cache hits (about $22). Cache breakpoints use the default 5-minute duration; within each setting one call per version runs first to write the cache, and the remaining calls of that setting then run in parallel. Each record logs its route.
6. The analysis script analyze_v2.py was validated on synthetic responses with planted rates (synth_test.py) before any real response was collected; it recovered the planted adoption rates, chain penalty, reminder effect, pressure effect, null threat effect and bounds rate.
7. For every provider, each setting's first agent call runs alone before the setting's remaining calls run in parallel, so provider prompt caches are written once per setting (cost only; the prompt and the outcome-independent order are unchanged). Gemini calls carry one `cache_control` breakpoint at the end of the shared codebook prefix.
8. Qwen 3.8 27B runs with max_tokens 32,768 (the endpoint maximum; its smoke-test completions reached 12.4k-13.0k tokens against the 16,000 default). All other models keep 16,000.
9. Spending caps are set explicitly per model near the worst case (`--cap MODEL=USD`), so they stop only runaway spending; cost accounting uses the provider-reported cost where available (OpenRouter `usage.cost`) and live prices for pinned endpoints otherwise.
10. Failure policy: empty text with a normal stop, provider errors and HTTP errors are logged to `fail_<model>.log` and retried on the next run of the same command; responses that stop on max_tokens, length, refusal or content filter are kept and counted, not retried. A 402 (out of credit) stops that model until the next run.
11. Estimate-step responses that cannot be parsed are excluded from B and C(r) and counted, rather than scored as not covering.
12. Tier B is the launch tier. In tier B the frontier models get two draws per implied and chain cell and the full estimate sweep. The confirmatory ARMS pool remains the five models named in section 2 (gpt-5-mini, haiku-5.5, gemma-4-31b, deepseek-v4.1-flash, gpt-4o-mini); the arms run on the other three non-frontier models (qwen-3.8-27b, haiku-4.5, gemini-3.8-flash) are exploratory.
13. Corrections found in final validation and fixed before launch: the H1 developer rule now uses an explicit developer map (Anthropic: opus, sonnet, haiku; Google: gemini, gemma; OpenAI: gpt; Alibaba: qwen; DeepSeek: deepseek), the seeded call order is now reproducible (sorted before shuffling), and pooled contrasts give equal weight to versions.
14. Launch (2026-11-06): tier B. The four Anthropic and three OpenAI models start first; the five OpenRouter models start after the OpenRouter account is topped up, using the same command (resume by key). The OSF registration of this document was not completed before the first call; until it is, the frozen state is evidenced by the SHA-256 hashes in section 12, the per-prompt hashes in out5/prompt_hashes_B.tsv, and run_log.log, all written before the first confirmatory call.
15. Qwen 3.8 27B reverted from `primeintellect/fp8` to `deepinfra/bf16` before any confirmatory Qwen call: the fp8 endpoint did not return two smoke-test calls within about 40 minutes, which would have made Qwen's 499 calls infeasible. Qwen therefore runs at its original bf16 precision; expected Qwen cost rises by about $3.5. The five OpenRouter models launched after the account was topped up to $23.25 of available credit.
16. Post-launch exploratory addendum (2026-11-07), not run. After the confirmatory run, two exploratory models were prepared in the runner to address two gaps: Claude Fable 5.1 (`fable-5.1`, `claude-fable-5-1`, adaptive thinking, effort "medium", the cells and draw indices of opus-5.5) for the missing top Anthropic tier, and Claude Haiku 4.5 with thinking (`haiku-4.5-think`, `claude-haiku-4-5`, `thinking: {type: "enabled", budget_tokens: 8000}`, no sampling parameters, the cells and draw indices of haiku-4.5) to separate model generation from the absence of thinking, since every model that failed ran without thinking. The prompts are identical to those of the source models (0 mismatches against out5/prompt_hashes_B.tsv). Only abs_v2.py changed (two MODELS entries, their prices, and a manifest wrapper that copies the source models' rows); its SHA-256 is now `fd20f8bb2c65f340858424a9d3ab3176baab19e7370ded8b85e02a3cf3c42b82`, and the frozen version is kept as abs_v2.py.bak_pre_addendum. The other frozen files are unchanged. Neither model was run, because each projected cost exceeded its budget. For fable-5.1 the projection is $27.5 against $20: opus-5.5's measured tokens at Fable prices, with the input side alone at $15.3. For haiku-4.5-think it is about $7.6 against $5: two smoke calls on the silent lottery prompt produced 2,282 and 1,938 output tokens, against 390 and 432 without thinking, and both parsed with the existing parser. The smoke test cost $0.05 and is kept in smoke.jsonl, which the analysis excludes. Any later run of these models is exploratory and outside the confirmatory families.

17. 2026-11-07: haiku-4.5-think run on primary cells only (agent step, neutral arm, threat request, silent/implied/chain; 140 calls, $2.96) via a new --primary flag in abs_v2.py. fable-5.1 primary violation cells (40 responses, one per setting and version) were collected in fresh sessions with no project context, scored with the frozen parser. Both exploratory, outside the confirmatory families.

18. 2026-11-07: first held-out natural-set run (out_nat_v1/, 8 models + Fable sessions) showed low silent-version decoy pull for frontier models. The set was recalibrated on silent versions only under the calibration amendment in natural_rules.md (alternative strength only; violation text and plant_re unchanged) and rerun. v1 outputs are retained and will be released with the materials.
