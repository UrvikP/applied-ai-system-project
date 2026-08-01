# Presentation Outline (5–7 minutes)

A slide-by-slide script for the final demo. Timings are targets.

## Slide 1 — Title (0:20)
- **Music Recommender Simulation** — from a rule-based recommender to a RAG system.
- Repo: https://github.com/UrvikP/applied-ai-system-project
- One line: "A content-based music recommender that now answers plain-English requests with a local LLM — grounded in real catalog data."

## Slide 2 — The original project (0:40)
- Built in Module 3: songs + a user taste profile as numeric data (energy, valence, tempo, danceability, acousticness, mood).
- A content-based scorer measures how closely each song matches, ranks the catalog, and explains each pick.
- Goal: turn raw preference data into *explainable* recommendations.

## Slide 3 — What I added: RAG (0:50)
- Problem: the original only took hardcoded numeric profiles, not real language.
- Added a **Retrieval-Augmented Generation** mode: describe what you want in plain English.
- Key idea (say this clearly): **the LLM does not pick songs.** My scorer retrieves candidates; the model may only recommend from them.
- Three stages: parse query → **retrieve with the existing scorer** → generate grounded answer.

## Slide 4 — Architecture diagram (0:50)
- Show `diagrams/system_diagram.mmd`.
- Trace the flow: input → parse → retrieve (CSV = knowledge base, scorer = retriever) → generate → output.
- Point out the two check points: automated tests on the scorer, runtime guardrails on the LLM.

## Slide 5 — Live demo (1:30)
- Run: `python src/main.py --ask "upbeat music for a workout"`
- Narrate: parsed preferences → retrieved candidates → grounded recommendation → `[grounding OK]`.
- (Backup if offline: show the captured run in README → *Reproducible Execution Evidence*.)
- Optional second run: `python src/main.py` (profile demo, no LLM) to show the deterministic core.

## Slide 6 — Proving it works: reliability (1:00)
- `pytest -q` → **8/8 pass** (scorer + RAG pipeline, RAG tests mock the LLM so they run without Ollama).
- **Grounding check** on every run: flags any recommended song not in the retrieved set. Real runs: 0 ungrounded.
- Guardrails: missing server/model/package and empty input are handled cleanly, no crash.
- Point to `tests/human_eval.md` for the full table.

## Slide 7 — What I learned / responsible AI (0:50)
- Scoring vs. ranking are separate jobs (a helpful AI suggestion I acted on).
- One flawed AI suggestion: the first auto-generated songs stayed skewed — AI output can be confidently wrong.
- Limitations: input validation bug (out-of-range → negative scores), catalog bias, a small local model.
- Misuse & prevention: prompt injection is contained by the grounding check; weights are transparent.

## Slide 8 — Close (0:20)
- Takeaway: "I build AI that can prove it works — grounded, tested, reproducible — and I'm honest about where it still falls short."
- Repo link again.

---

### Quick demo commands
```bash
python src/main.py                                  # profile demo (no LLM)
python src/main.py --ask "upbeat music for a workout"   # RAG mode
pytest -q                                           # 8/8 tests
```
