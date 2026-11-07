PETROPHYSICIST INTERVIEWER PRO
==============================
START:   double-click  Start_Interview_App.bat   (first run needs internet and Python)
STOP:    close the black window.

YOUR DATA
  interview_vault.enc   <- all candidates, notes, scores (ENCRYPTED, auto-saved)
  interview_vault.bak   <- previous version (automatic)
  There is NO password recovery. Back up interview_vault.enc by copying it.

FILES
  interviewer_pro_needApassword.py  the app
  jd_content.py                     questions, probes, rubric (edit here)
  vault.py                          encryption
  llm_lab.py                        AI generation, settings test, LLM judge
  Start_Interview_App.bat           launcher

AI FEATURES (optional): open section E (AI generation) on the app page -> paste an Anthropic API key
  (stored encrypted in your vault). Do not enter candidate names or notes in that section.
  Temperature testing requires the legacy-model checkbox; current Claude models reject it (HTTP 400).
If something breaks: copy the full error text and paste it to Claude.
