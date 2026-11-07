"""Prompt lab: generate interview-prep JSON with Claude under different settings,
validate it, and grade it with an LLM-as-a-judge.

Two structured JSON output formats:
  A) interview_plan   - questions + probes + signals + red flags per JD responsibility
  B) scoring_rubric   - 1-5 behavioural anchors, evidence needed, weights, decision guidance

Settings that are tuned:
  effort       -> depth of reasoning ("low" | "medium" | "high")
  max_tokens   -> output cap (too low truncates the JSON)
  temperature  -> ONLY honoured by legacy models (e.g. claude-sonnet-4-6). Current models
                  (Opus/Sonnet 5.5) reject it, and the newest API version rejects it on every
                  model. The lab records that rejection instead of hiding it.

Command line:  python llm_lab.py --quick      (needs ANTHROPIC_API_KEY)
"""
import argparse, json, re, time
from datetime import datetime
from pathlib import Path

import jsonschema
import jd_content as jd

PROMPT_VERSION = "v1"
GEN_MODEL = "claude-opus-5-5"
JUDGE_MODEL = "claude-sonnet-5-5"       # a different model from the generator, to limit self-preference bias
LEGACY_TEMP_MODEL = "claude-sonnet-4-6"  # still accepts temperature

# ----------------------------------------------------------------------------- schemas
def _arr(item="string"):
    return {"type": "array", "items": {"type": item}}

_QUESTION = {"type": "object", "additionalProperties": False,
    "required": ["question", "type", "probes", "strong_signals", "red_flags"],
    "properties": {"question": {"type": "string"},
                   "type": {"type": "string", "enum": ["technical", "behavioral", "scenario"]},
                   "probes": _arr(), "strong_signals": _arr(), "red_flags": _arr()}}

SCHEMAS = {
 "interview_plan": {"type": "object", "additionalProperties": False,
   "required": ["role", "seniority", "total_minutes", "sections", "candidate_questions_prep"],
   "properties": {
     "role": {"type": "string"}, "seniority": {"type": "string"}, "total_minutes": {"type": "integer"},
     "sections": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["responsibility_id", "responsibility", "minutes", "questions"],
        "properties": {"responsibility_id": {"type": "string"}, "responsibility": {"type": "string"},
                       "minutes": {"type": "integer"}, "questions": {"type": "array", "items": _QUESTION}}}},
     "candidate_questions_prep": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["likely_question", "answer_points"],
        "properties": {"likely_question": {"type": "string"}, "answer_points": _arr()}}}}},
 "scoring_rubric": {"type": "object", "additionalProperties": False,
   "required": ["scale", "criteria", "decision_guidance"],
   "properties": {
     "scale": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["score", "label", "description"],
        "properties": {"score": {"type": "integer"}, "label": {"type": "string"}, "description": {"type": "string"}}}},
     "criteria": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["responsibility_id", "responsibility", "weight", "evidence_needed", "anchors", "disqualifiers"],
        "properties": {"responsibility_id": {"type": "string"}, "responsibility": {"type": "string"},
                       "weight": {"type": "integer"}, "evidence_needed": _arr(),
                       "anchors": {"type": "object", "additionalProperties": False,
                                   "required": [f"score_{i}" for i in range(1, 6)],
                                   "properties": {f"score_{i}": {"type": "string"} for i in range(1, 6)}},
                       "disqualifiers": _arr()}}},
     "decision_guidance": {"type": "object", "additionalProperties": False,
        "required": ["strong_hire_min", "hire_min", "borderline_min", "min_responsibilities_covered", "notes"],
        "properties": {"strong_hire_min": {"type": "number"}, "hire_min": {"type": "number"},
                       "borderline_min": {"type": "number"}, "min_responsibilities_covered": {"type": "integer"},
                       "notes": {"type": "string"}}}}},
}
FORMATS = {"interview_plan": "A - Interview plan", "scoring_rubric": "B - Scoring rubric"}

# ----------------------------------------------------------------------------- prompts
SYSTEM = ("You are a senior petrophysics hiring advisor for an oilfield services company. "
          "You write interview material for INTERVIEWERS who are petrophysicists. "
          "Be specific and technically accurate; avoid generic corporate wording; never invent company facts.")

_IDS = "\n".join(f"{rid}: {title}" for rid, title, _ in jd.RESPONSIBILITIES)

PROMPTS = {
 "interview_plan": f"""Role: {jd.ROLE}.
Job description responsibilities (use these exact ids):
{_IDS}

Task: produce a 60-minute INTERVIEW PLAN as JSON.
Requirements:
- One section per responsibility id (all 12), minutes summing to about 55, leaving 5 for candidate questions.
- Exactly 2 questions per section: one past-behaviour question and one scenario/technical question.
- Each question: open, single-issue, non-leading, answerable by someone with 15+ years' experience.
- 3 probes per question that test depth (own role, trade-offs, measured outcome).
- 2-3 strong_signals and 1-2 red_flags per question, concrete and observable.
- candidate_questions_prep: 8 questions a senior candidate is likely to ask at the end, with 2-3 answer_points each.
Return only the JSON object.""",
 "scoring_rubric": f"""Role: {jd.ROLE}.
Job description responsibilities (use these exact ids):
{_IDS}

Task: produce a SCORING RUBRIC as JSON for a 1-5 scale.
Requirements:
- scale: five levels 1..5 with a label and a behavioural description.
- criteria: one per responsibility id (all 12) with weight 1-5 reflecting importance to this role.
- anchors score_1..score_5 must describe observable, DIFFERENT behaviours specific to that responsibility
  (not the same sentence reworded); score_5 must reflect senior-level judgement.
- evidence_needed: 3-4 items an interviewer should hear; disqualifiers: 1-3 items.
- decision_guidance: thresholds for strong hire / hire / borderline, the minimum number of responsibilities
  that must be covered before scoring, and notes that remind interviewers to score only questions asked.
Return only the JSON object.""",
}

# ----------------------------------------------------------------------------- generation
def _text(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def generate(client, fmt, model=GEN_MODEL, max_tokens=12000, effort="medium", temperature=None):
    """One generation. Never raises for API problems: returns an error entry instead."""
    import anthropic
    kwargs = dict(model=model, max_tokens=max_tokens, system=SYSTEM,
                  messages=[{"role": "user", "content": PROMPTS[fmt]}],
                  output_config={"format": {"type": "json_schema", "schema": SCHEMAS[fmt]}, "effort": effort})
    if temperature is not None:
        kwargs["extra_body"] = {"temperature": temperature}
    out = {"format": fmt, "model": model, "max_tokens": max_tokens, "effort": effort, "temperature": temperature,
           "ok": False, "parsed": None, "error": None, "stop_reason": None,
           "input_tokens": None, "output_tokens": None, "seconds": None}
    t0 = time.time()
    try:
        resp = client.messages.create(**kwargs)
    except anthropic.APIStatusError as e:
        out["error"] = f"{e.status_code}: {getattr(e, 'message', str(e))}"[:300]
        out["seconds"] = round(time.time() - t0, 1)
        return out
    except anthropic.APIConnectionError as e:
        out["error"] = f"connection: {e}"[:300]
        return out
    out["seconds"] = round(time.time() - t0, 1)
    out["stop_reason"] = resp.stop_reason
    out["input_tokens"], out["output_tokens"] = resp.usage.input_tokens, resp.usage.output_tokens
    if resp.stop_reason == "refusal":
        out["error"] = "model refused"
        return out
    if resp.stop_reason == "max_tokens":
        out["error"] = "truncated: output hit max_tokens before the JSON was complete"
        return out
    try:
        out["parsed"] = json.loads(_text(resp))
        out["ok"] = True
    except json.JSONDecodeError as e:
        out["error"] = f"invalid JSON: {e}"
    return out

# ----------------------------------------------------------------------------- deterministic checks
def checks(fmt, parsed):
    """Objective checks, independent of any LLM. Returns metrics and a 0-1 score."""
    if parsed is None:
        return {"schema_valid": False, "score": 0.0}
    m = {}
    try:
        jsonschema.validate(parsed, SCHEMAS[fmt]); m["schema_valid"] = True
    except jsonschema.ValidationError as e:
        m["schema_valid"] = False; m["schema_error"] = e.message[:120]
    expected = {rid for rid, _, _ in jd.RESPONSIBILITIES}
    if fmt == "interview_plan":
        secs = parsed.get("sections", [])
        ids = {s.get("responsibility_id") for s in secs}
        qs = [s.get("questions", []) for s in secs]
        m["responsibilities_covered"] = len(ids & expected)
        m["two_questions_each"] = all(len(q) == 2 for q in qs) and len(secs) == 12
        m["probes_ge_2_each"] = all(len(q.get("probes", [])) >= 2 for ql in qs for q in ql) if qs else False
        m["signals_and_flags_present"] = all(q.get("strong_signals") and q.get("red_flags") for ql in qs for q in ql) if qs else False
        m["minutes_total"] = sum(s.get("minutes", 0) for s in secs)
        m["minutes_ok"] = 45 <= m["minutes_total"] <= 60
        texts = [q.get("question", "").strip().lower() for ql in qs for q in ql]
        m["no_duplicate_questions"] = len(texts) == len(set(texts))
        flags = [m["schema_valid"], m["responsibilities_covered"] == 12, m["two_questions_each"],
                 m["probes_ge_2_each"], m["signals_and_flags_present"], m["minutes_ok"], m["no_duplicate_questions"]]
    else:
        crit = parsed.get("criteria", [])
        ids = {c.get("responsibility_id") for c in crit}
        m["responsibilities_covered"] = len(ids & expected)
        anchors_ok = all(all(c.get("anchors", {}).get(f"score_{i}", "").strip() for i in range(1, 6)) for c in crit) if crit else False
        m["all_anchors_present"] = anchors_ok
        distinct = all(len({c["anchors"].get(f"score_{i}", "") for i in range(1, 6)}) == 5 for c in crit if "anchors" in c) if crit else False
        m["anchors_distinct_within_criterion"] = distinct
        m["anchors_differ_across_criteria"] = len({tuple(c.get("anchors", {}).values()) for c in crit}) > 1
        m["scale_has_5_levels"] = sorted(s.get("score") for s in parsed.get("scale", [])) == [1, 2, 3, 4, 5]
        w = [c.get("weight", 0) for c in crit]
        m["weights_in_1_5"] = bool(w) and all(1 <= x <= 5 for x in w)
        m["weights_vary"] = len(set(w)) > 1
        flags = [m["schema_valid"], m["responsibilities_covered"] == 12, anchors_ok, distinct,
                 m["anchors_differ_across_criteria"], m["scale_has_5_levels"], m["weights_in_1_5"], m["weights_vary"]]
    m["score"] = round(sum(bool(f) for f in flags) / len(flags), 2)
    return m

# ----------------------------------------------------------------------------- LLM-as-a-judge
DIMENSIONS = {
 "jd_alignment": "Every JD responsibility is addressed with content specific to THAT responsibility.",
 "specificity": "Content is concrete and specific to petrophysics / oilfield services, not generic HR boilerplate.",
 "discriminating_power": "Plan: probes separate strong from weak candidates. Rubric: anchors describe clearly different observable behaviours per level.",
 "seniority_fit": "Suited to a candidate with 15+ years: judgement, trade-offs, mentoring, influence.",
 "technical_accuracy": "Petrophysical and commercial/technical-support content is correct and realistic.",
 "usability": "An interviewer could use it as-is in a live interview: clear, concise, well organised.",
 "fairness": "Questions are open, non-leading and free of bias; criteria are job-related and observable.",
}
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["assessments", "top_issues", "verdict"],
  "properties": {
   "assessments": {"type": "array", "items": {"type": "object", "additionalProperties": False,
       "required": ["dimension", "evidence", "score"],
       "properties": {"dimension": {"type": "string", "enum": list(DIMENSIONS)},
                      "evidence": {"type": "string"}, "score": {"type": "integer"}}}},
   "top_issues": {"type": "array", "items": {"type": "string"}},
   "verdict": {"type": "string", "enum": ["usable_as_is", "needs_minor_edits", "needs_major_rework"]}}}

JUDGE_SYSTEM = ("You are a strict, impartial evaluator of interview-preparation material for senior petrophysicists. "
                "Score only what is in the material. Cite specific evidence before giving each score. "
                "Use the full 1-5 range; 3 means acceptable, 5 is rare. Do not reward length. "
                "You are not told how the material was produced and must not guess.")


def judge(client, fmt, parsed, model=JUDGE_MODEL):
    """Score one output on 7 dimensions (1-5). Evidence is written BEFORE each score."""
    import anthropic
    dims = "\n".join(f"- {k}: {v}" for k, v in DIMENSIONS.items())
    prompt = (f"Job description:\n{jd.JD_TEXT}\n\nFormat evaluated: {FORMATS[fmt]}\n\n"
              f"Material to evaluate (JSON):\n{json.dumps(parsed, ensure_ascii=False)}\n\n"
              f"Score each dimension from 1 to 5:\n{dims}\n\n"
              "For each dimension give brief evidence quoting the material, then the score. "
              "List up to 5 top_issues and a verdict.")
    try:
        r = client.messages.create(model=model, max_tokens=6000, system=JUDGE_SYSTEM,
              messages=[{"role": "user", "content": prompt}],
              output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}, "effort": "medium"})
        if r.stop_reason in ("max_tokens", "refusal"):
            return {"error": f"judge stopped: {r.stop_reason}"}
        j = json.loads(_text(r))
    except (anthropic.APIError, json.JSONDecodeError) as e:
        return {"error": str(e)[:200]}
    scores = {a["dimension"]: max(1, min(5, a["score"])) for a in j["assessments"]}
    j["scores"] = scores
    j["mean"] = round(sum(scores.values()) / len(scores), 2) if scores else None
    return j

# ----------------------------------------------------------------------------- experiment
def grid(quick=False):
    """Settings to compare. Each entry: label + kwargs for generate()."""
    g = [("effort=low", dict(effort="low")), ("effort=medium", dict(effort="medium")), ("effort=high", dict(effort="high")),
         ("max_tokens=1500", dict(max_tokens=1500)), ("max_tokens=4000", dict(max_tokens=4000))]
    if not quick:
        g += [("legacy temp=0.0", dict(model=LEGACY_TEMP_MODEL, temperature=0.0)),
              ("legacy temp=0.7", dict(model=LEGACY_TEMP_MODEL, temperature=0.7)),
              ("legacy temp=1.0", dict(model=LEGACY_TEMP_MODEL, temperature=1.0)),
              ("current model + temp=0.2", dict(temperature=0.2))]  # expected to be rejected: documents the limit
    return g


def run_experiment(client, formats=("interview_plan", "scoring_rubric"), quick=False, gen_model=GEN_MODEL,
                   judge_model=JUDGE_MODEL, include_baseline=True, progress=lambda done, total, msg: None):
    configs = grid(quick)
    total = len(configs) * len(formats) + (len(formats) if include_baseline else 0)
    rows, n = [], 0
    for fmt in formats:
        if include_baseline:
            parsed = jd.builtin_plan() if fmt == "interview_plan" else jd.builtin_rubric()
            ch = checks(fmt, parsed)
            jg = judge(client, fmt, parsed, judge_model)
            rows.append({"format": fmt, "label": "built-in baseline (no AI)", "settings": {}, "ok": True, "error": None,
                         "stop_reason": None, "output_tokens": None, "seconds": None, "checks": ch, "judge": jg,
                         "parsed": parsed})
            n += 1; progress(n, total, f"{fmt}: baseline")
        for label, kw in configs:
            kw = dict(kw); kw.setdefault("model", gen_model)
            res = generate(client, fmt, **kw)
            ch = checks(fmt, res["parsed"]); jg = judge(client, fmt, res["parsed"], judge_model) if res["ok"] else None
            rows.append({"format": fmt, "label": label, "settings": {k: res[k] for k in ("model", "max_tokens", "effort", "temperature")},
                         "ok": res["ok"], "error": res["error"], "stop_reason": res["stop_reason"],
                         "output_tokens": res["output_tokens"], "seconds": res["seconds"], "checks": ch, "judge": jg,
                         "parsed": res["parsed"]})
            n += 1; progress(n, total, f"{fmt}: {label}")
    return {"prompt_version": PROMPT_VERSION, "created": datetime.now().isoformat(timespec="seconds"),
            "gen_model": gen_model, "judge_model": judge_model, "rows": rows}


def summary_rows(result):
    out = []
    for r in result["rows"]:
        jm = (r["judge"] or {}).get("mean") if r.get("judge") else None
        out.append({"Format": FORMATS[r["format"]][:1], "Setting": r["label"],
                    "Valid JSON": "yes" if r["ok"] else "no", "Auto-check": r["checks"].get("score"),
                    "Judge mean (1-5)": jm, "Verdict": (r["judge"] or {}).get("verdict", "") if r.get("judge") else "",
                    "Out tokens": r["output_tokens"], "Seconds": r["seconds"], "Problem": r["error"] or ""})
    return out


def report_markdown(result):
    lines = [f"# Prompt lab report ({result['created']})", "",
             f"Prompt version {result['prompt_version']} | generator `{result['gen_model']}` | judge `{result['judge_model']}`", "",
             "| Fmt | Setting | Valid | Auto | Judge | Verdict | Out tok | Sec | Problem |", "|---|---|---|---|---|---|---|---|---|"]
    for s in summary_rows(result):
        lines.append("| " + " | ".join(str(s[k]) if s[k] not in (None, "") else "-" for k in
                     ["Format", "Setting", "Valid JSON", "Auto-check", "Judge mean (1-5)", "Verdict", "Out tokens", "Seconds", "Problem"]) + " |")
    lines += ["", "Judge dimensions: " + ", ".join(DIMENSIONS), "",
              "Caveats: one run per setting (LLM output varies run to run); judge is itself an LLM and can be biased "
              "(length, style, self-preference). Treat differences under ~0.3 judge points as noise and confirm with repeats "
              "and your own expert review."]
    return "\n".join(lines)


def main():
    import anthropic
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="effort and max_tokens sweeps only")
    ap.add_argument("--out", default="prompt_lab_results")
    a = ap.parse_args()
    res = run_experiment(anthropic.Anthropic(), quick=a.quick, progress=lambda d, t, m: print(f"[{d}/{t}] {m}", flush=True))
    Path(a.out + ".json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(a.out + ".md").write_text(report_markdown(res), encoding="utf-8")
    print("saved", a.out + ".json", a.out + ".md")


if __name__ == "__main__":
    main()
