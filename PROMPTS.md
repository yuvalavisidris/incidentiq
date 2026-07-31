# System prompts & prompt engineering notes

Every analysis stage is a separate, grounded prompt to Gemini
(`gemini-3.5-flash-lite` by default). They share a common guard clause and each requests a
small JSON object. This document lists the prompts the system uses and the iterations
that got them there — the brief asks us to show *prompt iterations*, not just final prompts.

## Shared guard (prepended to every analysis stage)

> You analyze a software production incident. Ground every statement in the provided
> input. If something is not directly in the input, label it an assumption or inference —
> never present a guess as a fact. Prefer several competing explanations over one. Be
> concise and specific.

## Structured output

JSON stages set `generationConfig.responseMimeType = "application/json"`, which makes the
API return valid JSON rather than relying on the prompt to ask nicely. A parse-failure
retry and a brace-slice fallback remain as a safety net.

## Gemini API constraints we had to respect

- `temperature`, `top_p` and `top_k` are omitted for compatibility with current Gemini
  APIs. We rely on system instructions and staged prompts for consistency instead.
- `gemini-3.6-flash` was removed from the app after API-key runs returned temporary
  high-demand 503 errors. The live app now uses `gemini-3.5-flash-lite`.
- Requests may not end on a `model` role turn, so every call ends with the user turn.

## Stage prompts (summarized)

1. **Summary + ledger** — neutral 3–4 sentence summary, up to 6 `facts` (each with the
   exact evidence line) and up to 4 `assumptions` (each with *why*).
2. **Timeline** — chronological events, each tagged `observed` (a line/timestamp exists)
   or `inferred`, with its `source`.
3. **Hypotheses** — 3–4 competing root causes, each with `confidence` 0–100,
   `supporting`, `contradicting`, and a falsifying `test`; *"include at least one that
   contradicts the obvious deploy-blame story"* and *"common causes usually beat exotic ones."*
4. **Reasoning risks** — 3–5 biases/fallacies specific to this incident, each with *where*
   it shows up and a concrete *mitigation*.
5. **Actions + questions** — 3–5 evidence-linked next steps with priority, plus open questions.
6. **Postmortem** — blameless Markdown, audience-tuned (engineer / manager / support); root
   cause stated as a *leading hypothesis*, not confirmed fact.

On-demand:
- **Devil's advocate** — argue *against* the leading hypothesis; return the strongest
  counter, specific objections, and the blind spot we'd have if we committed now.
- **Grounding check** — audit the summary's own claims against the raw input; verdict
  `supported | partly | unsupported`, with arithmetic derived from the input rated
  `partly` at best.

## Iteration log (what we changed and why)

| # | Problem we saw | Change we made |
|---|---|---|
| 1 | First version blamed the deploy every time (**anchoring / post-hoc**). | Added *"include at least one hypothesis that contradicts the obvious deploy-blame story"* plus a base-rate reminder. |
| 2 | Confidence numbers clustered at 85–95% (**overconfidence**). | Added *"confidence must reflect real evidence strength, not neatness"* and forced a `contradicting` field so weak theories can't look strong. |
| 3 | "Facts" included invented specifics not in the logs. | Required an `evidence` string per fact = the exact source line; anything else must go under `assumptions`. |
| 4 | Model wrapped prose around the JSON, breaking the parser. | Switched to `responseMimeType: "application/json"`; kept the retry and brace-slice fallback. |
| 5 | Single giant prompt sometimes truncated. | Split into six small staged prompts so each response stays small and reliable. |
| 6 | Postmortem sometimes declared a confirmed root cause. | Instructed it to label the cause a *leading hypothesis* and add a "what we still need to verify" section. |
| 7 | Grounding check passed arithmetic (e.g. "6 pods × 20 = 120 connections") as a supported fact. | Told the auditor to rate derived arithmetic `partly` at best, since the product is inference, not evidence. |

## Reproducing our tests
- **Logged evidence:** run `python scripts/run_experiments.py` with `GEMINI_API_KEY` set in
  the environment. The runner writes raw responses and exact prompts under `evidence/`.
- **Baseline repeatability:** run the full checkout pipeline three times and compare the
  leading hypothesis, confidence, grounding verdicts, and devil's-advocate objections.
- **Evidence sensitivity:** delete only the `reporting-svc opened 74 idle connections`
  log line from the checkout input and re-run the hypotheses stage. Compare the result with
  the baseline files in `evidence/baseline_checkout_run_*/`.
- **Prompt ablations:** re-run the affected stage after removing one prompt guard at a time:
  the non-deploy/counter-deploy instruction, the confidence-calibration sentence, the exact
  evidence requirement for facts, and the postmortem "leading hypothesis" instruction. The
  saved ablation outputs live in `evidence/ablation_*`.
