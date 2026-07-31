# Evidence log

Generated: 2026-07-31T12:40:33.008010+00:00

Model: `gemini-3.5-flash-lite`

Each subfolder contains raw Gemini responses for one experiment. Each `*.json` file stores the exact system prompt, user prompt, generation config, HTTP status, raw HTTP response, and extracted raw response text for one model call.

Folders:
- `baseline_checkout_run_1` to `baseline_checkout_run_3`: full checkout pipeline, independently repeated.
- `baseline_registration_run_1`: full registration pipeline.
- `sensitivity_checkout_no_reporting_line`: checkout hypotheses after deleting only the reporting-svc idle-connection log line.
- `ablation_hypotheses_no_counter_deploy`: checkout hypotheses without the non-deploy/counter-deploy instruction.
- `ablation_hypotheses_no_confidence_guard_run_1` and `_run_2`: checkout hypotheses without the confidence-calibration sentence.
- `ablation_summary_no_fact_evidence`: checkout summary/facts without the exact-evidence requirement for facts.
- `ablation_postmortem_no_leading_hypothesis_guard`: checkout postmortem without the instruction to mark the root cause as a leading hypothesis.
- `failed_parse_attempt_baseline_checkout_run_1_20260731T1236Z`: preserved partial first attempt where the hypotheses response returned a top-level JSON array instead of the requested object wrapper.
