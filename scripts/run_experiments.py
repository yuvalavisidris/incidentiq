#!/usr/bin/env python3
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
EVIDENCE = ROOT / "evidence"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

GUARD = (
    "You analyze a software production incident. Ground every statement in the provided input. "
    "If something is not directly in the input, label it an assumption or inference -- never "
    "present a guess as a fact. Prefer several competing explanations over one. Be concise and specific."
)


def current_model():
    html = INDEX.read_text(encoding="utf-8")
    model = re.search(r'let MODEL\s*=\s*"([^"]+)"', html)
    if not model:
        raise RuntimeError("Could not find MODEL in index.html")
    max_out = re.search(r'"' + re.escape(model.group(1)) + r'"\s*:\s*\{[^}]*maxOut\s*:\s*(\d+)', html)
    return model.group(1), int(max_out.group(1)) if max_out else 8192


def scenario_input(name, omit_reporting_line=False):
    scenario_dir = ROOT / "examples" / name
    logs = (scenario_dir / "logs.txt").read_text(encoding="utf-8").strip()
    if omit_reporting_line:
        logs = "\n".join(
            line for line in logs.splitlines()
            if line.strip() != "2024-11-18 14:12:10 WARN  reporting-svc opened 74 idle connections to orders-db"
        )
    desc = (scenario_dir / "description.txt").read_text(encoding="utf-8").strip()
    deploy = (scenario_dir / "deployment-notes.md").read_text(encoding="utf-8").strip()
    alerts = (scenario_dir / "alerts.txt").read_text(encoding="utf-8").strip()
    return (
        f"=== INCIDENT DESCRIPTION ===\n{desc or '(none)'}\n\n"
        f"=== LOGS / TRACES ===\n{logs or '(none)'}\n\n"
        f"=== DEPLOYMENT NOTES ===\n{deploy or '(none)'}\n\n"
        f"=== ALERTS / USER REPORTS ===\n{alerts or '(none)'}"
    )


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


class Runner:
    def __init__(self, pause_seconds):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.model, self.max_out = current_model()
        self.pause_seconds = pause_seconds
        self.counter = 0

    def call(self, experiment, stage, system, user, json_stage=False):
        self.counter += 1
        exp_dir = EVIDENCE / experiment
        exp_dir.mkdir(parents=True, exist_ok=True)
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": self.max_out},
        }
        if json_stage:
            body["generationConfig"]["responseMimeType"] = "application/json"

        url = f"{API_BASE}/{self.model}:generateContent"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )

        raw_http = None
        raw_text = ""
        status = None
        error = None
        for attempt in range(2):
            if self.counter > 1 or attempt > 0:
                time.sleep(self.pause_seconds if attempt == 0 else max(self.pause_seconds, 12))
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    status = response.status
                    raw_http = response.read().decode("utf-8")
                payload = json.loads(raw_http)
                raw_text = "".join(
                    part.get("text", "")
                    for part in payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                ).strip()
                break
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw_http = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt == 0:
                    continue
                error = f"HTTP {exc.code}"
                break
            except Exception as exc:
                error = repr(exc)
                break

        record = {
            "experiment": experiment,
            "stage": stage,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "model": self.model,
            "request": {
                "url": url,
                "system": system,
                "user": user,
                "generationConfig": body["generationConfig"],
            },
            "http_status": status,
            "raw_http_response": raw_http,
            "raw_response_text": raw_text,
            "error": error,
        }
        out = exp_dir / f"{stage}_{timestamp()}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(out.relative_to(ROOT))
        if error:
            raise RuntimeError(f"{stage} failed: {error}")
        return raw_text, out


def parse_json_text(raw):
    text = raw.replace("```json", "").replace("```", "").strip()
    if text.startswith("["):
        return json.loads(text)
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        text = text[a:b + 1]
    return json.loads(text)


def ensure_object(parsed, key):
    if isinstance(parsed, list):
        return {key: parsed}
    return parsed


def stage_summary(runner, experiment, inp, system_override=None, user_override=None):
    system = system_override or (GUARD + " Extract a short summary plus a fact/assumption ledger.")
    user = user_override or (
        f'{inp}\n\nReturn JSON: {{"summary":"3-4 sentence neutral summary of what is known, no speculation",'
        f'"facts":[{{"statement":"...","evidence":"the exact log line or note that supports it"}}],'
        f'"assumptions":[{{"statement":"belief the investigation relies on but the input does not prove",'
        f'"why":"why we\'d assume it"}}]}}. Max 6 facts, 4 assumptions.'
    )
    raw, file = runner.call(experiment, "summary", system, user, json_stage=True)
    return ensure_object(parse_json_text(raw), "facts"), file


def stage_timeline(runner, experiment, inp):
    raw, file = runner.call(
        experiment,
        "timeline",
        GUARD + " Reconstruct a timeline. Mark each event 'observed' (a timestamp/line exists) or 'inferred'.",
        f'{inp}\n\nReturn JSON: {{"timeline":[{{"time":"HH:MM or relative","event":"what happened",'
        f'"source":"which input line/section","kind":"observed|inferred"}}]}}. Chronological. Max 9 events.',
        json_stage=True,
    )
    return ensure_object(parse_json_text(raw), "timeline"), file


def stage_hypotheses(runner, experiment, inp, system_override=None, user_override=None):
    system = system_override or (
        GUARD + " Generate competing root-cause hypotheses. Include at least one that contradicts "
        "the obvious deploy-blame story, and remember that common causes usually beat exotic ones."
    )
    user = user_override or (
        f'{inp}\n\nReturn JSON: {{"hypotheses":[{{"title":"short root-cause claim","confidence":0-100,'
        f'"supporting":["evidence from input"],"contradicting":["evidence against, or \'none found in input\'"],'
        f'"test":"one concrete check that would confirm or kill this"}}]}}. Exactly 3 or 4, sorted by confidence '
        f'descending. Confidence must reflect real evidence strength, not neatness.'
    )
    raw, file = runner.call(experiment, "hypotheses", system, user, json_stage=True)
    return ensure_object(parse_json_text(raw), "hypotheses"), file


def stage_risks(runner, experiment, inp, hyps):
    top = hyps.get("hypotheses", [{}])[0].get("title", "")
    raw, file = runner.call(
        experiment,
        "risks",
        GUARD + " Identify cognitive biases and logical fallacies that could distort THIS investigation.",
        f'{inp}\n\nTop hypothesis under consideration: "{top}".\n\nReturn JSON: {{"risks":[{{"bias":"named bias or fallacy",'
        f'"where":"how it could show up here specifically","mitigation":"a concrete guard against it"}}]}}. 3 to 5 items. '
        f"Consider anchoring on the deploy, confirmation bias, post-hoc reasoning, automation bias, availability bias, base-rate neglect.",
        json_stage=True,
    )
    return ensure_object(parse_json_text(raw), "risks"), file


def stage_actions(runner, experiment, inp, hyps):
    titles = ";".join(" " + h.get("title", "") for h in hyps.get("hypotheses", []))
    raw, file = runner.call(
        experiment,
        "actions",
        GUARD + " Recommend next debugging steps tied to evidence, plus open questions.",
        f'{inp}\n\nHypotheses:{titles}.\n\nReturn JSON: {{"actions":[{{"action":"specific step",'
        f'"link":"which hypothesis or evidence it addresses","priority":"high|med|low"}}],'
        f'"questions":["what the input can\'t yet answer"]}}. 3-5 actions, 2-4 questions.',
        json_stage=True,
    )
    return ensure_object(parse_json_text(raw), "actions"), file


def stage_postmortem(runner, experiment, inp, system_override=None):
    system = system_override or (
        "Write a blameless incident postmortem in Markdown for engineers: technical, blameless, include specifics. "
        "Use only what the input supports; mark the root cause as a leading hypothesis, not a confirmed fact. "
        "Sections: Impact, Timeline, Leading hypothesis, Contributing factors, What we still need to verify, "
        "Follow-up actions. Output Markdown only, no preamble."
    )
    raw, file = runner.call(experiment, "postmortem", system, inp + "\n\nWrite the postmortem now.", json_stage=False)
    return raw, file


def tool_grounding(runner, experiment, inp, summary):
    claims = [f.get("statement", "") for f in summary.get("facts", [])] + [summary.get("summary", "")]
    raw, file = runner.call(
        experiment,
        "grounding",
        "Audit an AI incident summary for claims not supported by the source input. Be skeptical; arithmetic derived from the input is 'partly' supported at best.",
        f'SOURCE INPUT:\n{inp}\n\nCLAIMS TO AUDIT:\n' + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
        + '\n\nReturn JSON {"audit":[{"claim":"...","verdict":"supported|partly|unsupported","note":"which line supports it, or why it\'s ungrounded"}]}.',
        json_stage=True,
    )
    return ensure_object(parse_json_text(raw), "audit"), file


def tool_devil(runner, experiment, inp, hyps):
    top = hyps.get("hypotheses", [{}])[0].get("title", "")
    raw, file = runner.call(
        experiment,
        "devil",
        "Play devil's advocate. Argue AGAINST the leading hypothesis as hard as the evidence allows, so the team doesn't over-commit.",
        f'{inp}\n\nLEADING HYPOTHESIS: "{top}".\n\nReturn JSON: {{"counter":"one-sentence strongest reason this could be wrong",'
        f'"points":["specific objections or overlooked alternatives"],"blindspot":"what evidence we\'d be ignoring if we commit now"}}. 3-4 points.',
        json_stage=True,
    )
    return ensure_object(parse_json_text(raw), "points"), file


def full_pipeline(runner, experiment, scenario):
    inp = scenario_input(scenario)
    summary, _ = stage_summary(runner, experiment, inp)
    stage_timeline(runner, experiment, inp)
    hyps, _ = stage_hypotheses(runner, experiment, inp)
    stage_risks(runner, experiment, inp, hyps)
    stage_actions(runner, experiment, inp, hyps)
    stage_postmortem(runner, experiment, inp)
    tool_grounding(runner, experiment, inp, summary)
    tool_devil(runner, experiment, inp, hyps)


def run_all(pause_seconds):
    runner = Runner(pause_seconds)
    for i in range(1, 4):
        full_pipeline(runner, f"baseline_checkout_run_{i}", "checkout-v2.4.1")
    full_pipeline(runner, "baseline_registration_run_1", "course-registration")

    checkout = scenario_input("checkout-v2.4.1")
    checkout_no_reporting = scenario_input("checkout-v2.4.1", omit_reporting_line=True)
    stage_hypotheses(runner, "sensitivity_checkout_no_reporting_line", checkout_no_reporting)

    stage_hypotheses(
        runner,
        "ablation_hypotheses_no_counter_deploy",
        checkout,
        system_override=GUARD + " Generate competing root-cause hypotheses. Remember that common causes usually beat exotic ones.",
    )
    no_confidence_user = (
        f'{checkout}\n\nReturn JSON: {{"hypotheses":[{{"title":"short root-cause claim","confidence":0-100,'
        f'"supporting":["evidence from input"],"contradicting":["evidence against, or \'none found in input\'"],'
        f'"test":"one concrete check that would confirm or kill this"}}]}}. Exactly 3 or 4, sorted by confidence descending.'
    )
    for i in range(1, 3):
        stage_hypotheses(runner, f"ablation_hypotheses_no_confidence_guard_run_{i}", checkout, user_override=no_confidence_user)
    summary_no_evidence_user = (
        f'{checkout}\n\nReturn JSON: {{"summary":"3-4 sentence neutral summary of what is known, no speculation",'
        f'"facts":[{{"statement":"..."}}],"assumptions":[{{"statement":"belief the investigation relies on but the input does not prove",'
        f'"why":"why we\'d assume it"}}]}}. Max 6 facts, 4 assumptions.'
    )
    stage_summary(runner, "ablation_summary_no_fact_evidence", checkout, user_override=summary_no_evidence_user)
    postmortem_no_leading = (
        "Write a blameless incident postmortem in Markdown for engineers: technical, blameless, include specifics. "
        "Use only what the input supports. Sections: Impact, Timeline, Leading hypothesis, Contributing factors, "
        "What we still need to verify, Follow-up actions. Output Markdown only, no preamble."
    )
    stage_postmortem(runner, "ablation_postmortem_no_leading_hypothesis_guard", checkout, system_override=postmortem_no_leading)

    readme = EVIDENCE / "README.md"
    readme.write_text(
        "# Evidence log\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Model: `{runner.model}`\n\n"
        "Each subfolder contains raw Gemini responses for one experiment. Each `*.json` file stores the exact system prompt, "
        "user prompt, generation config, HTTP status, raw HTTP response, and extracted raw response text for one model call.\n\n"
        "Folders:\n"
        "- `baseline_checkout_run_1` to `baseline_checkout_run_3`: full checkout pipeline, independently repeated.\n"
        "- `baseline_registration_run_1`: full registration pipeline.\n"
        "- `sensitivity_checkout_no_reporting_line`: checkout hypotheses after deleting only the reporting-svc idle-connection log line.\n"
        "- `ablation_hypotheses_no_counter_deploy`: checkout hypotheses without the non-deploy/counter-deploy instruction.\n"
        "- `ablation_hypotheses_no_confidence_guard_run_1` and `_run_2`: checkout hypotheses without the confidence-calibration sentence.\n"
        "- `ablation_summary_no_fact_evidence`: checkout summary/facts without the exact-evidence requirement for facts.\n"
        "- `ablation_postmortem_no_leading_hypothesis_guard`: checkout postmortem without the instruction to mark the root cause as a leading hypothesis.\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=3.0, help="Seconds to pause between API calls")
    args = parser.parse_args()
    run_all(args.pause)


if __name__ == "__main__":
    main()
