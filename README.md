# IncidentIQ

**An AI-assisted incident-response and root-cause analysis tool that reasons under uncertainty.**

IncidentIQ takes messy incident data — logs, error traces, deployment notes, alerts —
and produces a *structured, evidence-linked investigation* instead of a single confident
answer. It reconstructs a timeline, ranks competing root-cause hypotheses with evidence
**for and against** each, flags the cognitive biases threatening the investigation, and
drafts a blameless postmortem. Throughout, it keeps **facts, assumptions, hypotheses, and
actions visibly separate** and never claims a verified root cause.

> Built for the *Critical Thinking, Problem Solving & 21st-Century Skills* final project.
> The point is not to let AI decide the answer — it is to use AI critically when the
> information is incomplete, noisy, or misleading.

---

## Submission links

- **Demo video URL: https://drive.google.com/file/d/1rbpqdvLSWR67wCVVJlEx7JaQdtpLtTqI/view?usp=sharing
- **GitHub repository URL: https://github.com/yuvalavisidris/incidentiq
---

## Try it in 5 seconds — no setup, no API key

Open `index.html` in any browser and click **"See a saved run — no key needed."**

That loads a stored analysis of a sample incident so the entire tool can be reviewed
immediately. It is clearly labelled as a saved run and makes no network call. To analyse
your own data live, add a free Gemini key (below).

---

## Why it's built this way

Modern systems fail in messy ways: logs are incomplete, the first alert is often
misleading, and the first explanation is usually wrong. An AI that sounds confident can
make this worse. So IncidentIQ is designed around three rules:

1. **No claim without a source.** Every "fact" points back to a specific line of input.
   Anything not in the input is labelled an *assumption* or *inference*, never a fact.
2. **Several explanations, not one.** The hypothesis generator is forced to produce
   competing theories — including at least one that contradicts the obvious "blame the
   deploy" story — each with a concrete test that could *kill* it.
3. **Watch the reasoning, not just the bug.** A dedicated pass names the biases
   (anchoring, confirmation, post-hoc, automation bias, base-rate neglect) that could
   distort *this specific* investigation, and how to guard against each.

Two built-in "distrust the machine" tools make this concrete:
- **Challenge the leading hypothesis** — asks the model to argue *against* its own top answer.
- **Grounding check** — re-audits the summary's claims against the raw input and flags
  anything unsupported.

---

## Features (mapped to the brief)

| Brief requirement | Where it lives |
|---|---|
| Input interface — paste **or upload** logs, errors, description, deploy notes | Left rail |
| AI-powered incident summary | Section 01 |
| Facts / Assumptions / Hypotheses / Actions ledger | Section 02 |
| Timeline reconstruction with evidence source per event | Section 03 (+ signal chart) |
| Root-cause hypotheses: confidence, evidence for/against, recommended test | Section 04 (+ chart) |
| Bias & fallacy detector | Section 05 |
| Suggested next actions linked to evidence + open questions | Section 06 |
| Unsupported-claim detection | Section 07 (Grounding check) |
| Draft postmortem, role-based (engineer / manager / support) | Section 08 |
| Charts | Timeline signal + hypothesis-confidence charts |
| Export | Copy Markdown, download `.md`, download analysis JSON |

---

## Architecture

A single self-contained `index.html` — no build step, no dependencies to install.
Vanilla JS + [Chart.js]. The analysis is a **staged pipeline** of six small, focused
prompts rather than one giant call: each stage is grounded in the same input block and
returns compact JSON that the UI renders. Staging keeps every response small and reliable,
and it mirrors how a real investigator works — establish facts, then a timeline, then
hypotheses, then examine the reasoning itself.

```
Input (desc + logs + deploy + alerts)
        │
        ▼
[1] Summary + Facts/Assumptions   ─┐
[2] Timeline (observed vs inferred)│  each stage = one grounded
[3] Competing hypotheses           │  JSON prompt to Gemini
[4] Reasoning-risk scan            │  (see PROMPTS.md)
[5] Actions + open questions       │
[6] Postmortem (role-aware)       ─┘
        │
        ├── on demand: Devil's-advocate counter-argument
        └── on demand: Grounding audit of the summary's claims
```

See **[PROMPTS.md](PROMPTS.md)** for prompt summaries and iteration notes. The full
prompt strings live in the `stage*` functions in `index.html`.

---

## Running a live analysis

1. Get a **free** API key at <https://aistudio.google.com/apikey>. The Gemini free tier
   requires no credit card.
2. Open `index.html` in a browser (or serve it: `python3 -m http.server`).
3. Click the button in the header and paste the key.
4. Load a sample or paste your own incident, then **Analyze incident**.

### Models

| Model | Notes |
|---|---|
| `gemini-3.5-flash-lite` *(default)* | The live-analysis model used by the app. It is the stable option for this project when using a Gemini API key. |

`gemini-3.6-flash` was removed from the app because API-key runs can fail with temporary
high-demand 503 errors. Free-tier quotas change; if the remaining model returns 429, wait
a moment and try again. Current limits are shown in Google AI Studio.

### Key handling

The key lives in the browser tab's memory only. It is never written to disk, never placed
in a URL, and never committed — `.gitignore` blocks `.env` and key files. Reloading the
page clears it.

Because this is still a browser-held key, restrict it in Google AI Studio to the minimum
API/project access needed for this demo, and rotate it after recording if necessary.

> ⚠️ **Do not paste real production logs** containing customer data, secrets, or internal
> hostnames. On the Gemini free tier, Google may use submitted prompts to improve their
> models. Use the sanitized samples, or redact first.

---

## Repository layout

```
incidentiq/
├── index.html                     # the entire app, including the saved demo run
├── README.md
├── PROMPTS.md                     # system prompts + iteration notes
├── LICENSE
├── .gitignore
├── docs/
│   └── IncidentIQ_Reflective_Report.docx
├── evidence/
│   ├── README.md
│   ├── baseline_checkout_run_1/
│   ├── baseline_checkout_run_2/
│   ├── baseline_checkout_run_3/
│   ├── baseline_registration_run_1/
│   ├── sensitivity_checkout_no_reporting_line/
│   ├── ablation_hypotheses_no_counter_deploy/
│   ├── ablation_hypotheses_no_confidence_guard_run_1/
│   ├── ablation_hypotheses_no_confidence_guard_run_2/
│   ├── ablation_summary_no_fact_evidence/
│   ├── ablation_postmortem_no_leading_hypothesis_guard/
│   └── failed_parse_attempt_baseline_checkout_run_1_20260731T1236Z/
├── scripts/
│   └── run_experiments.py
└── examples/
    ├── checkout-v2.4.1/           # deploy + hidden connection pressure
    │   ├── description.txt
    │   ├── logs.txt
    │   ├── deployment-notes.md
    │   ├── alerts.txt
    │   ├── example-output.json
    │   ├── example-postmortem.md
    │   └── README.md
    └── course-registration/       # cold cache + missing index at peak
        ├── description.txt
        ├── logs.txt
        ├── deployment-notes.md
        ├── alerts.txt
        ├── example-output.json
        ├── example-postmortem.md
        └── README.md
```

Each example folder has `description.txt`, `logs.txt`, `deployment-notes.md`,
`alerts.txt`, saved example outputs, and a `README.md` explaining the "trap" the scenario
is designed to test. You can drag the input files straight into the upload control.

The `evidence/` folder is the logged record of model runs used to support the observations
in the reflective report.

---

## Honest limitations

- IncidentIQ can be **confidently wrong**. Its hypotheses are starting points; the
  recommended tests exist because a human must confirm them before acting.
- It only sees what you paste. Missing logs = blind spots it cannot know about.
- The grounding check reduces but does not eliminate hallucination.
- The saved demo run is a stored response, not a live one — it demonstrates the interface
  and a representative analysis, not the model's behaviour on your data.
- It is a reasoning aid, **not** an autonomous root-cause decider, and should never be
  the sole basis for external communication or a risky remediation.

## AI tools used
- **Google Gemini** (`gemini-3.5-flash-lite`) via the Generative
  Language `generateContent` REST API, for every analysis stage.

## License
MIT — see [LICENSE](LICENSE).

[Chart.js]: https://www.chartjs.org/
