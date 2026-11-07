"""Job description, question bank, rubric and prepared-answer prompts.
Edit this file to change questions. Each JD responsibility has exactly 2 questions,
each with follow-up probes, strong signals and red flags.
"""

ROLE = "Petrophysicist (Senior, 15+ years) - technical support for sales and service delivery"

JD_TEXT = """Provide technical support in the area of expertise throughout the Sales and Product and Service Delivery process.
Assist as required with the development of technical job designs for Product Lines.
Assist with identifying areas where new and cost-effective techniques can be applied.
Explore opportunities for value-added products and services.
Consult with Design/Technical Engineer role as required to optimize the technical design.
Assist in real-time incident response, recovery, and investigation as related to the area of expertise.
Assist in evaluating technical viability and overall appraisal of tenders as related to the area of expertise.
Remain current on new technologies.
Maintain customer visibility through active participation in professional society activities and calls for papers.
Understand the competition's technical offering.
Participate in external technical societies and communities.
Contribute, write and review technical publications."""

# Shared 1-5 scoring rubric (behaviourally anchored). Applied ONLY to questions you actually asked.
SCALE = [
    (1, "No evidence", "No relevant example, incorrect technical content, or cannot answer the probes."),
    (2, "Weak", "Vague or purely hypothetical; credit shared with the team without own contribution; no outcome."),
    (3, "Competent", "Relevant, correct, first-person example, but generic or outcome not quantified; limited depth on probes."),
    (4, "Strong", "Specific example with own role clear, measurable outcome, handles probes with sound trade-offs."),
    (5, "Exceptional", "Senior-level judgement: quantified impact, explains alternatives and uncertainty, mentors/influences others, learning applied since."),
]

# (id, responsibility, [question dicts])
def _q(text, probes, strong, red):
    return {"text": text, "probes": probes, "strong": strong, "red": red}

RESPONSIBILITIES = [
 ("R01", "Technical support across the sales and service-delivery process", [
   _q("Take me through a recent opportunity where you gave technical input from first enquiry through job delivery. What changed because of your involvement?",
      ["Where did you push back on what the customer asked for?", "How did you hand over to operations?", "What did the post-job review show?"],
      ["Clear own role at each stage", "Matched service to the real problem", "Stayed involved through post-job evaluation"],
      ["Only engages after the sale", "Overpromises on capability"]),
   _q("A customer asks for a result our technology only partly delivers. How do you handle that conversation?",
      ["What do you say about limits and uncertainty?", "What alternative do you offer?", "How do you protect the relationship if they decline?"],
      ["Honest about limits with evidence", "Offers a workable alternative", "Aligns with sales without misleading"],
      ["Avoids the conflict", "Says yes to win the job"])]),
 ("R02", "Development of technical job designs for Product Lines", [
   _q("Describe how you build a technical job design for a product line: inputs, assumptions and acceptance criteria.",
      ["What well and fluid data do you insist on?", "How do you set success criteria up front?", "How do you build in contingencies?"],
      ["Well-specific inputs (hole, fluids, lithology)", "Explicit acceptance criteria", "Contingency and risk plan"],
      ["Generic template with no well-specific inputs"]),
   _q("Tell me about a job design that underdelivered. What in the design was the root cause?",
      ["What did you know at the time vs. later?", "What did you change in the standard design afterwards?", "How did you tell the customer?"],
      ["Owns the failure", "Root cause is technical and specific", "Changed the standard so it does not repeat"],
      ["Blames customer or tools only", "No lesson"])]),
 ("R03", "Identifying new, cost-effective techniques", [
   _q("Which technique have you introduced, or would you introduce, that cut cost or improved data quality? How did you prove it?",
      ["What was the baseline?", "How did you validate against known data?", "What was the cost-benefit?"],
      ["Named technique tied to a named problem", "Pilot or back-test with numbers", "Cost-benefit awareness"],
      ["Technology for its own sake"]),
   _q("How do you decide a new technique is mature enough to put in front of a customer?",
      ["What evidence do you require?", "Who signs off?", "What if sales is pushing to go early?"],
      ["Defined readiness criteria", "Separates pilot from product", "Willing to say 'not yet'"],
      ["Relies on vendor claims alone"])]),
 ("R04", "Value-added products and services", [
   _q("Where have you seen a value-added service grow out of core petrophysical work? How was it validated commercially?",
      ["Who was the buyer and what pain did it solve?", "What did it cost to deliver?", "What failed?"],
      ["Starts from customer pain point", "Evidence of uptake or pricing logic", "Realistic about delivery cost"],
      ["Ideas with no customer evidence"]),
   _q("If you owned our portfolio, what adjacent service would you pursue and what would stop you?",
      ["How would you test demand cheaply?", "What capability gap would you need to close?", "How does it differ from competitors?"],
      ["Specific, testable idea", "Names risks and gaps", "Links to differentiators"],
      ["Wish list with no prioritisation"])]),
 ("R05", "Consulting with Design / Technical Engineers to optimise design", [
   _q("Describe a disagreement with a design or technical engineer. How was it resolved and what did the design look like afterwards?",
      ["What data did each side rely on?", "What trade-off was made?", "What would you do differently?"],
      ["Evidence-led discussion", "Explicit cost/quality/risk trade-off", "Decision documented"],
      ["Wins by authority", "Avoids the disagreement"]),
   _q("Which petrophysical constraints do you make sure engineers understand before a design is frozen?",
      ["Give an example where this was missed.", "How do you communicate sensitivity to assumptions?", "How do you keep it from becoming a bottleneck?"],
      ["Names concrete constraints (hole conditions, resolution, calibration)", "Communicates sensitivities", "Early involvement"],
      ["Only reviews at the end"])]),
 ("R06", "Real-time incident response, recovery and investigation", [
   _q("Walk me through a real-time job where data or tool behaviour went wrong. What did you do in the first 30 minutes?",
      ["What did you check first and why?", "Who did you tell and when?", "What did you decide not to do?"],
      ["Safety first, then data QC", "Structured root-cause steps", "Early clear communication"],
      ["Panics or delays communication", "Guesses without checking"]),
   _q("After recovery, how do you run an investigation so the lesson is captured and does not repeat?",
      ["What is in your report?", "How do you separate cause from contributing factor?", "How do you check the fix worked?"],
      ["Blame-free structured method", "Corrective actions with owners", "Follow-up verification"],
      ["Report filed, nothing changes"])]),
 ("R07", "Evaluating technical viability and appraisal of tenders", [
   _q("How do you decide whether a tender is technically viable? What do you check first?",
      ["How do you spot hidden requirements?", "How do you estimate effort and risk?", "When have you recommended no-bid?"],
      ["Requirements vs capability gap analysis", "Assumptions and exclusions stated", "Willing to recommend no-bid"],
      ["Accepts all requirements unchecked"]),
   _q("A tender includes a requirement we cannot fully meet. What do you advise and what goes into the response?",
      ["How do you word a partial compliance?", "What alternatives or workarounds do you propose?", "Who needs to approve?"],
      ["Transparent partial compliance", "Credible workaround", "Escalates commercial risk"],
      ["Hides or glosses over the gap"])]),
 ("R08", "Staying current on new technologies", [
   _q("Which technology developments in the last 12 months changed how you work or advise? How did you assess them?",
      ["What did you read, test or attend?", "What did you reject and why?", "How did you share it with colleagues?"],
      ["Specific recent examples", "Evidence-based assessment", "Shares knowledge"],
      ["Outdated or only name-drops"]),
   _q("How do you separate hype from real capability, for example for machine-learning interpretation or new logging measurements?",
      ["What validation would you demand?", "What failure modes concern you?", "Where is the petrophysicist still needed?"],
      ["Physics-based validation", "Names bias/overfitting risks", "Keeps expert in the loop"],
      ["Treats ML as a black-box replacement"])]),
 ("R09", "Customer visibility via society activity and calls for papers", [
   _q("How have you used papers or talks to build customer visibility, and what business followed?",
      ["How did you choose the topic?", "How did you handle confidential customer data?", "What would you do differently?"],
      ["Link from talk to commercial result", "Respects confidentiality", "Targets the right audience"],
      ["Visibility with no follow-up"]),
   _q("How would you decide which conferences and calls for papers to target for us?",
      ["How do you measure return?", "How do you get internal approval?", "What do you do with limited budget?"],
      ["Prioritises by customer audience", "Measures return", "Plans abstracts early"],
      ["Chooses by personal interest only"])]),
 ("R10", "Understanding the competition's technical offering", [
   _q("How do you build a picture of a competitor's technical offering from public sources, and what do you do with it?",
      ["Which sources do you trust?", "How do you keep it current?", "How do you share it internally?"],
      ["Papers, specs, case histories", "Balanced strengths and weaknesses", "Turns it into positioning evidence"],
      ["Rumour or dismissal of competitors"]),
   _q("Give an example where knowing a competitor's limits changed your technical recommendation. How did you stay objective and ethical?",
      ["Where is your line on confidential information?", "How did you check your assumptions?", "What was the outcome?"],
      ["Clear ethical boundary", "Evidence-based", "Concrete outcome"],
      ["Uses confidential competitor information"])]),
 ("R11", "Participation in external technical societies and communities", [
   _q("Which societies or technical communities have you contributed to (for example SPWLA or SPE), and in what role?",
      ["What did you personally deliver?", "What did it bring back to your employer?", "How do you balance it with job demands?"],
      ["Active roles, not just membership", "Specific contributions", "Benefit to employer"],
      ["Name-only membership"]),
   _q("How do you turn community involvement into internal capability or customer opportunity?",
      ["Give a specific idea you brought back.", "How do you share it with the team?", "How do you measure benefit?"],
      ["Concrete knowledge transfer", "Network leads to action", "Measured value"],
      ["No link to the business"])]),
 ("R12", "Writing and reviewing technical publications", [
   _q("Tell me about a publication you wrote: your contribution, the review process and the impact.",
      ["What was the hardest reviewer comment?", "How did you handle data confidentiality?", "Who cited or used it?"],
      ["Own contribution is clear", "Handled peer review well", "Impact on customers or colleagues"],
      ["Cannot explain own role"]),
   _q("How do you review someone else's technical paper? What makes you request major changes or reject?",
      ["What is your checklist?", "How do you give feedback to a junior author?", "How do you handle a result you doubt?"],
      ["Structured criteria (method, data, claims)", "Constructive feedback", "Checks claims against evidence"],
      ["Superficial or purely editorial review"])]),
]

# Likely questions the CANDIDATE asks at the end + points for the interviewer to prepare
CANDIDATE_QS = [
    "What does success look like in the first 6-12 months?",
    "How closely will I work with sales, product lines and design engineers?",
    "How much travel or field/real-time support is expected?",
    "What support exists for publishing papers and society participation?",
    "Which new technologies or product lines are a priority?",
    "Who are the main competitors and where do we differentiate?",
    "What are the biggest challenges facing the team right now?",
    "How are incidents reviewed and how does the team learn from them?",
    "What does career progression look like for a senior technical expert?",
    "What are the next steps and timeline for the hiring process?",
]

# Guidance thresholds (a prompt for your judgement, not a hiring decision)
THRESHOLDS = {"strong_hire": 4.0, "hire": 3.3, "borderline": 2.5, "min_responsibilities": 8}


def all_questions():
    """Flat list of (qid, responsibility_id, responsibility, question dict)."""
    out = []
    for rid, title, qs in RESPONSIBILITIES:
        for i, q in enumerate(qs, 1):
            out.append((f"{rid}Q{i}", rid, title, q))
    return out


def guidance(avg, n_resp):
    if n_resp < THRESHOLDS["min_responsibilities"]:
        return f"Insufficient evidence (only {n_resp} of 12 responsibilities covered)"
    if avg >= THRESHOLDS["strong_hire"]: return "Strong hire signal"
    if avg >= THRESHOLDS["hire"]: return "Hire signal"
    if avg >= THRESHOLDS["borderline"]: return "Borderline"
    return "No-hire signal"


def builtin_plan():
    """Format A as JSON: the interview plan, built from this file (no AI)."""
    sections = []
    for rid, title, qs in RESPONSIBILITIES:
        sections.append({
            "responsibility_id": rid, "responsibility": title, "minutes": 5,
            "questions": [{"question": q["text"], "type": "behavioral" if i == 0 else "scenario",
                           "probes": q["probes"], "strong_signals": q["strong"], "red_flags": q["red"]}
                          for i, q in enumerate(qs)]})
    return {"role": ROLE, "seniority": "Senior (15+ years)", "total_minutes": 60, "sections": sections,
            "candidate_questions_prep": [{"likely_question": q, "answer_points": []} for q in CANDIDATE_QS]}


def builtin_rubric():
    """Format B as JSON: the scoring rubric, built from this file (no AI)."""
    scale = [{"score": s, "label": l, "description": d} for s, l, d in SCALE]
    crit = []
    for rid, title, qs in RESPONSIBILITIES:
        strong = [x for q in qs for x in q["strong"]]
        anchors = {f"score_{s}": d for s, _, d in SCALE}
        crit.append({"responsibility_id": rid, "responsibility": title, "weight": 1,
                     "evidence_needed": strong[:4], "anchors": anchors,
                     "disqualifiers": [x for q in qs for x in q["red"]]})
    return {"scale": scale, "criteria": crit,
            "decision_guidance": {"strong_hire_min": THRESHOLDS["strong_hire"], "hire_min": THRESHOLDS["hire"],
                                  "borderline_min": THRESHOLDS["borderline"],
                                  "min_responsibilities_covered": THRESHOLDS["min_responsibilities"],
                                  "notes": "Score only questions asked. Guidance supports, not replaces, panel judgement."}}
