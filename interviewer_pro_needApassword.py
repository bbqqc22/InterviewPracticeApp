"""Senior Petrophysicist Interviewer Pro – strict single-page Streamlit app.
Start with: Start_Interview_App.bat  (double-click on Windows)
Or:  python -m streamlit run interviewer_pro_needApassword.py
Data is auto-saved encrypted in 'interview_vault.enc' next to this file.
"""
import csv, hashlib, io, json, os, time
from datetime import datetime

import streamlit as st

import jd_content as jd
import llm_lab as lab
import vault as vl

IDLE_SECONDS = 15 * 60
st.set_page_config(page_title="Petrophysicist Interviewer Pro", page_icon="🛢️", layout="wide")
ss = st.session_state


# ── security gate ─────────────────────────────────────────────────────────────
def lock(message=None):
    for k in list(ss.keys()):
        del ss[k]
    if message:
        ss["lock_msg"] = message


def gate():
    if ss.get("vault") is not None:
        ss["last_active"] = time.time()
        return
    st.title("🛢️ Petrophysicist Interviewer Pro")
    if ss.get("lock_msg"):
        st.info(ss["lock_msg"])
    st.subheader("🔒 Interviewer access")
    if not vl.exists():
        st.info("First time: create a password. It encrypts all candidate data on this computer.")
        st.warning("There is NO password recovery. If you forget it, the data cannot be opened. Write it down somewhere safe.")
        with st.form("create"):
            p1 = st.text_input(f"New password (at least {vl.MIN_PASSWORD} characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            ok = st.checkbox("I understand there is no password recovery")
            go = st.form_submit_button("Create encrypted vault", type="primary")
        if go:
            if not ok:
                st.error("Please tick the box to continue.")
            elif p1 != p2:
                st.error("Passwords do not match.")
            elif len(p1) < vl.MIN_PASSWORD:
                st.error(f"Password must be at least {vl.MIN_PASSWORD} characters.")
            else:
                v = vl.Vault.create(p1)
                ss.update(vault=v, data=vl.empty_data(), last_active=time.time())
                st.rerun()
        st.stop()
    wait = vl.lock_seconds_left()
    if wait:
        st.error(f"Too many wrong attempts. Try again in {wait // 60 + 1} minute(s).")
        st.stop()
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        go = st.form_submit_button("Unlock", type="primary")
    if go:
        try:
            v, data = vl.Vault.open(pw)
        except vl.WrongPassword:
            left = vl.register_failure()
            st.error("Wrong password." + (f" {left} attempt(s) left." if left else " Locked for 5 minutes."))
        except (OSError, ValueError, KeyError) as e:
            st.error(f"Vault file could not be read ({e}). A backup may exist: interview_vault.bak")
        else:
            vl.register_success()
            ss.update(vault=v, data=data, last_active=time.time())
            st.rerun()
    st.stop()


@st.fragment(run_every="60s")
def idle_watch():
    if ss.get("vault") is not None and time.time() - ss.get("last_active", 0) > IDLE_SECONDS:
        lock("Locked after 15 minutes of inactivity.")
        st.rerun()


def autosave(data):
    h = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if h != ss.get("saved_hash"):
        ss["vault"].save(data)
        ss["saved_hash"], ss["saved_at"] = h, datetime.now().strftime("%H:%M:%S")


# ── scoring helpers ────────────────────────────────────────────────────────────
def candidate_stats(c):
    asked = [q for q, v in c.get("asked", {}).items() if v and q in c.get("ratings", {})]
    scores = [c["ratings"][q] for q in asked]
    rids = {q[:3] for q in asked}
    avg = sum(scores) / len(scores) if scores else None
    return {"asked": len(asked), "avg": avg, "resp": len(rids),
            "guidance": jd.guidance(avg, len(rids)) if avg is not None else "No questions scored yet"}


def add_candidate():
    name = ss.get("newc", "").strip()
    data = ss["data"]
    if not name:
        ss["cand_msg"] = "Enter a name first."
    elif name.lower() in {n.lower() for n in data["candidates"]}:
        ss["cand_msg"] = "That name already exists – add a middle initial or date."
    else:
        data["candidates"][name] = {"created": datetime.now().strftime("%Y-%m-%d"),
                                    "asked": {}, "ratings": {}, "notes": {}, "overall": ""}
        ss["cand_sel"], ss["newc"], ss["cand_msg"] = name, "", ""


# ── A · interview questions ────────────────────────────────────────────────────
def section_interview(data, name):
    c = data["candidates"][name]
    for k, d in (("asked", {}), ("ratings", {}), ("notes", {}), ("overall", "")):
        c.setdefault(k, d)

    with st.expander("📋 Scoring rubric reference (1–5 scale — only Asked questions are scored)", expanded=False):
        st.table([{"Score": s, "Level": l, "What it looks like": d} for s, l, d in jd.SCALE])

    colL, colR = st.columns(2)
    for i, (rid, title, qs) in enumerate(jd.RESPONSIBILITIES):
        col = colL if i < 6 else colR
        with col:
            with st.expander(f"{rid} · {title}"):
                for n_q, q in enumerate(qs, 1):
                    qid = f"{rid}Q{n_q}"
                    st.markdown(f"**{q['text']}**")
                    st.caption("Probes: " + "  |  ".join(q["probes"]))
                    st.caption("✅ Listen for: " + "; ".join(q["strong"]))
                    st.caption("🚩 Red flags: " + "; ".join(q["red"]))
                    a, b = st.columns([1, 3])
                    asked = a.toggle("Asked", value=c["asked"].get(qid, False), key=f"as_{name}_{qid}")
                    c["asked"][qid] = asked
                    score = b.slider("Score", 1, 5, value=c["ratings"].get(qid, 3),
                                     key=f"sc_{name}_{qid}", disabled=not asked)
                    if asked:
                        c["ratings"][qid] = score
                    c["notes"][qid] = st.text_area(
                        "Notes", value=c["notes"].get(qid, ""), key=f"nt_{name}_{qid}",
                        height=68, label_visibility="collapsed", placeholder="Notes / evidence heard")
                    st.divider()
    c["overall"] = st.text_area("Overall impression / recommendation",
                                value=c["overall"], key=f"ov_{name}")


# ── B · candidate's questions ──────────────────────────────────────────────────
def section_candidate_qs(data):
    st.caption("Questions the candidate is likely to ask at the end of the interview. "
               "Prepare your answers here — they are saved with everything else.")
    allq = jd.CANDIDATE_QS + data["custom_candidate_qs"]
    for i, q in enumerate(allq):
        data["prepared_answers"][q] = st.text_area(
            q, value=data["prepared_answers"].get(q, ""), key=f"cq_{i}", height=80)
    new = st.text_input("Add a question the candidate hasn't asked yet", key="extra_cq")
    if st.button("Add question") and new.strip() and new.strip() not in allq:
        data["custom_candidate_qs"].append(new.strip())
        st.rerun()


# ── C · summary & export ──────────────────────────────────────────────────────
def section_summary(data):
    if not data["candidates"]:
        st.info("No candidates yet.")
        return
    rows, per = [], []
    for n, c in data["candidates"].items():
        s = candidate_stats(c)
        rows.append({"Candidate": n, "Asked & scored": s["asked"], "Responsibilities": f"{s['resp']}/12",
                     "Average": round(s["avg"], 2) if s["avg"] is not None else None,
                     "Guidance": s["guidance"]})
        r = {"Candidate": n}
        for rid, title, _ in jd.RESPONSIBILITIES:
            v = [c["ratings"][q] for q, a in c.get("asked", {}).items()
                 if a and q.startswith(rid) and q in c.get("ratings", {})]
            r[rid] = round(sum(v) / len(v), 1) if v else None
        per.append(r)
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption("Score by responsibility (blank = not asked)")
    st.dataframe(per, width="stretch", hide_index=True)
    st.caption("Guidance supports your judgement; it is not a hiring decision. "
               "Averages use only questions marked Asked.")

    sel = st.selectbox("Export / manage candidate", list(data["candidates"]), key="sum_sel")
    c = data["candidates"][sel]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["question_id", "responsibility", "question", "asked", "score", "notes"])
    for qid, rid, title, q in jd.all_questions():
        w.writerow([qid, title, q["text"], c["asked"].get(qid, False),
                    c["ratings"].get(qid, "") if c["asked"].get(qid) else "",
                    c["notes"].get(qid, "")])
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Scorecard CSV", buf.getvalue(), f"{sel}_scorecard.csv", "text/csv")
    d2.download_button("⬇ Scorecard JSON",
                       json.dumps({sel: c}, indent=2, ensure_ascii=False),
                       f"{sel}_scorecard.json", "application/json")
    with st.popover("🗑 Delete this candidate"):
        st.warning(f"Permanently delete {sel} and all notes?")
        if st.button("Yes, delete", key="del_yes"):
            del data["candidates"][sel]
            for k in [k for k in list(ss.keys())
                      if isinstance(k, str) and (f"_{sel}_" in k or k == f"ov_{sel}")]:
                del ss[k]
            ss.pop("cand_sel", None)
            st.rerun()


# ── D · JSON formats ───────────────────────────────────────────────────────────
def section_json_formats():
    st.caption("Format A = interview plan (questions, probes, strong signals, red flags).  "
               "Format B = scoring rubric (1–5 anchors, weights, guidance thresholds).  "
               "Both are built directly from the question bank — no AI or API key needed.")
    o1, o2 = st.columns(2)
    o1.download_button("⬇ Format A – interview plan JSON (offline)",
                       json.dumps(jd.builtin_plan(), indent=2, ensure_ascii=False),
                       "interview_plan.json", "application/json")
    o2.download_button("⬇ Format B – scoring rubric JSON (offline)",
                       json.dumps(jd.builtin_rubric(), indent=2, ensure_ascii=False),
                       "scoring_rubric.json", "application/json")


# ── helpers shared by AI sections ─────────────────────────────────────────────
def get_client(data):
    try:
        import anthropic
    except ImportError:
        st.error("The 'anthropic' package is missing. Run the launcher again to install it.")
        return None
    key = os.environ.get("ANTHROPIC_API_KEY") or data["settings"].get("api_key", "")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


# ── E · AI generation & settings test ─────────────────────────────────────────
def section_ai_gen(data):
    env_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    with st.expander("🔑 Anthropic API key" +
                     (" (using ANTHROPIC_API_KEY from environment)" if env_key else ""),
                     expanded=not (env_key or data["settings"].get("api_key"))):
        k = st.text_input("API key (stored encrypted inside your vault — never stored in plain text)",
                          value=data["settings"].get("api_key", ""), type="password", key="apikey")
        data["settings"]["api_key"] = k.strip()
        st.caption("⚠️ Every AI call sends the job description and prompt to Anthropic.  "
                   "Do NOT put candidate names, scores, or personal notes into this section.")

    client = get_client(data)
    if client is None:
        st.info("Add an API key above to enable AI features.  "
                "The offline JSON downloads in Section D work without one.")
        return

    st.markdown("**Generate once with your chosen settings**")
    st.caption(
        f"Default model: `{lab.GEN_MODEL}`.  "
        "**Temperature** is rejected (HTTP 400) by current Claude models "
        "(Opus 5.5 / Sonnet 5.5) and by API version 2026-10-21 for every model.  "
        f"To test temperature, tick the legacy-model box — it uses `{lab.LEGACY_TEMP_MODEL}` "
        "on an older API version that still accepts it."
    )
    with st.form("gen"):
        a, b, c_, d = st.columns(4)
        fmt = a.selectbox("Format", list(lab.FORMATS), format_func=lambda f: lab.FORMATS[f])
        effort = b.selectbox("Reasoning effort", ["low", "medium", "high"], index=1)
        max_tok = c_.select_slider("Max tokens", [1500, 4000, 8000, 12000, 16000], value=12000)
        temp_choice = d.selectbox(
            "Temperature",
            ["not sent (default)", 0.0, 0.7, 1.0],
            help="Current models reject non-default temperature. "
                 "Pick a value only when using the legacy model below.")
        legacy = st.checkbox(
            f"Use legacy model  {lab.LEGACY_TEMP_MODEL}  (required to test temperature; "
            "if unticked, the temperature choice is ignored and nothing is sent)")
        go = st.form_submit_button("Generate", type="primary")

    if go:
        temperature = None if isinstance(temp_choice, str) else temp_choice
        model = lab.LEGACY_TEMP_MODEL if legacy else lab.GEN_MODEL
        if temperature is not None and not legacy:
            st.warning(
                f"Temperature={temperature} was NOT sent — current model `{model}` rejects it.  "
                "Tick the legacy-model box to actually test temperature.")
            temperature = None
        with st.spinner("Generating…"):
            res = lab.generate(client, fmt, model=model, max_tokens=max_tok,
                               effort=effort, temperature=temperature)
            res["checks"] = lab.checks(fmt, res["parsed"])
        ss["lab_single"] = res

    r = ss.get("lab_single")
    if r:
        if r["ok"]:
            temp_note = (f"temperature={r.get('temperature')} (legacy model `{r['model']}`)"
                         if r.get("temperature") is not None
                         else f"temperature not sent — model `{r['model']}`")
            st.success(f"Valid JSON · auto-check {r['checks']['score']} · "
                       f"{r['output_tokens']} output tokens · {r['seconds']}s · {temp_note}")
            st.download_button("⬇ Download JSON",
                               json.dumps(r["parsed"], indent=2, ensure_ascii=False),
                               f"{r['format']}_ai.json", "application/json")
            with st.expander("Show JSON / auto-checks"):
                st.json(r["checks"])
                st.json(r["parsed"], expanded=False)
        else:
            st.error(r["error"])


# ── F · LLM-as-a-judge and comparison ─────────────────────────────────────────
def section_judge(data):
    client = get_client(data)
    if client is None:
        st.info("Add an API key in Section E above to enable the judge.")
        return

    st.markdown(f"**Settings comparison — generator `{lab.GEN_MODEL}` · judge `{lab.JUDGE_MODEL}` (different model, deliberate)**")
    st.caption(
        "Quick sweep: reasoning effort (low / medium / high) × max tokens (1 500 / 4 000).  "
        "Full sweep adds temperature on the legacy model AND a 'current model + temp=0.2' row "
        "to document the HTTP 400 rejection.  "
        "Treat judge score differences under ~0.3 as noise — single run per configuration.  "
        "Judges can favour length or their own writing style; confirm with your own expert reading.  "
        "No live results are pre-loaded here: results exist only once you click Run."
    )

    p1, p2, p3 = st.columns(3)
    quick = p1.radio(
        "Sweep size",
        ["Quick (effort + max tokens)", "Full (adds temperature + rejection row)"]
    ).startswith("Quick")
    fmts = p2.multiselect("Formats", list(lab.FORMATS), default=list(lab.FORMATS),
                          format_func=lambda f: lab.FORMATS[f])
    base = p3.checkbox("Include built-in baseline", value=True)

    n_gen = len(lab.grid(quick)) * len(fmts)
    n_judge = n_gen + (len(fmts) if base else 0)
    st.caption(f"≈{n_gen} generation call(s) + up to {n_judge} judge call(s).  Can take several minutes.")

    if st.button("Run comparison", disabled=not fmts, key="run_cmp"):
        bar = st.progress(0.0, "Starting")
        result = lab.run_experiment(
            client, formats=tuple(fmts), quick=quick, include_baseline=base,
            progress=lambda d_, t_, m_: bar.progress(d_ / t_, f"{d_}/{t_}  {m_}"))
        bar.empty()
        data["lab_runs"] = (data["lab_runs"] + [result])[-5:]
        ss["lab_result"] = result

    res = ss.get("lab_result") or (data["lab_runs"][-1] if data["lab_runs"] else None)
    if res:
        st.caption(f"Showing run from {res['created']}")
        st.dataframe(lab.summary_rows(res), width="stretch", hide_index=True)
        st.download_button("⬇ Report (Markdown)", lab.report_markdown(res),
                           "prompt_lab_report.md", "text/markdown")
        st.download_button("⬇ Full results (JSON)",
                           json.dumps(res, indent=2, ensure_ascii=False),
                           "prompt_lab_results.json", "application/json")


# ── G · security & settings ───────────────────────────────────────────────────
def section_settings(data):
    st.subheader("Change password")
    st.caption(f"Minimum {vl.MIN_PASSWORD} characters.  "
               "There is NO password recovery — write your password down somewhere safe.")
    with st.form("chpw"):
        p1 = st.text_input("New password", type="password")
        p2 = st.text_input("Confirm new password", type="password")
        go = st.form_submit_button("Change password")
    if go:
        if p1 != p2:
            st.error("Passwords do not match.")
        elif len(p1) < vl.MIN_PASSWORD:
            st.error(f"At least {vl.MIN_PASSWORD} characters required.")
        else:
            ss["vault"].change_password(p1, data)
            ss["saved_hash"] = None
            st.success("Password changed. Use the new one next time.")

    st.subheader("Data file")
    st.write(f"Encrypted file: `{vl.VAULT_FILE}`")
    st.write("The previous version is kept as `interview_vault.bak` automatically.  "
             "Copy the `.enc` file to back it up — it stays encrypted, unreadable without your password.")
    st.caption(f"Auto-lock: {IDLE_SECONDS // 60} minutes of inactivity.  "
               "Lockout: 5 wrong passwords → 5-minute wait.  "
               "Deleting `vault_guard.json` resets only the lockout counter, not the encryption.")

    with st.popover("Export UNENCRYPTED copy"):
        st.warning("This file is readable by anyone. Store it safely and delete it when done.")
        st.download_button("⬇ Download plain JSON",
                           json.dumps(data, indent=2, ensure_ascii=False),
                           "interview_data_PLAINTEXT.json", "application/json")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    gate()
    data = ss["data"]
    data.setdefault("settings", {"api_key": ""})
    data["settings"].setdefault("api_key", "")
    data.setdefault("lab_runs", [])
    data.setdefault("custom_candidate_qs", [])
    data.setdefault("prepared_answers", {})
    idle_watch()

    # ── header (always visible) ────────────────────────────────────────────────
    hdr_title, hdr_lock = st.columns([9, 1])
    with hdr_title:
        st.markdown("### 🛢️ Petrophysicist Interviewer Pro")
        st.caption(jd.ROLE)
    if hdr_lock.button("🔒 Lock", use_container_width=True):
        lock("Locked.")
        st.rerun()

    # candidate bar
    names = list(data["candidates"])
    cc1, cc2, cc3 = st.columns([3, 3, 1])
    if names:
        cc1.selectbox("Candidate", names, key="cand_sel", label_visibility="collapsed")
    cc2.text_input("New candidate", key="newc", placeholder="New candidate name",
                   label_visibility="collapsed")
    cc3.button("Add", on_click=add_candidate, use_container_width=True)
    if ss.get("cand_msg"):
        st.warning(ss["cand_msg"])

    # reserve metric slot – filled AFTER section A processes widget values
    metrics_slot = st.empty()

    autosave(data)
    st.caption(f"💾 Auto-saved {ss.get('saved_at', '—')} (encrypted) · {vl.VAULT_FILE}")
    st.divider()

    # ── sections A–G ──────────────────────────────────────────────────────────
    with st.expander("🎤 A · Interview questions", expanded=bool(names)):
        if names:
            name = ss.get("cand_sel") or names[0]
            section_interview(data, name)  # reads toggles/sliders from ss, updates data in place
        else:
            st.info("Add a candidate above to begin.  "
                    "Mark each question 'Asked' only when you actually ask it — "
                    "unasked questions are never scored.")

    with st.expander("❓ B · Candidate's questions — your prepared answers"):
        section_candidate_qs(data)

    with st.expander("📊 C · Summary and export"):
        section_summary(data)

    with st.expander("📄 D · Interview-prep JSON (two formats — no AI needed)"):
        section_json_formats()

    with st.expander("🤖 E · AI generation and settings test (temperature · effort · max tokens)"):
        section_ai_gen(data)

    with st.expander("⚖️ F · LLM-as-a-judge and settings comparison"):
        section_judge(data)

    with st.expander("⚙️ G · Security and settings"):
        section_settings(data)

    # fill metrics slot now that section A has updated data["candidates"]
    if names:
        name = ss.get("cand_sel") or names[0]
        c = data["candidates"].get(name, {})
        s = candidate_stats(c)
        with metrics_slot.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Asked & scored", f"{s['asked']} / 24")
            m2.metric("Responsibilities", f"{s['resp']} / 12")
            m3.metric("Average (asked only)", f"{s['avg']:.2f}" if s["avg"] is not None else "—")
            m4.metric("Guidance", s["guidance"])


main()
