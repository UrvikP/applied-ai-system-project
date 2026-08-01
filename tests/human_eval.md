# Reliability & Human Evaluation

How the system's reliability is measured, in a parseable format (no demo needed).

## 1. Automated tests (`pytest`)

Run with `pytest` from the project root.

| Test | What it checks | Result |
|------|----------------|--------|
| `test_recommend_returns_songs_sorted_by_score` | Scorer ranks the right song first | Pass |
| `test_explain_recommendation_returns_non_empty_string` | Explanations are produced | Pass |
| `test_parse_returns_prefs_from_valid_json` | RAG parses a query into a prefs dict | Pass |
| `test_parse_falls_back_to_neutral_on_bad_json` | Bad LLM output → neutral fallback, no crash | Pass |
| `test_generate_handles_no_candidates` | Empty retrieval → safe message | Pass |
| `test_grounding_flags_leaked_song` | Detects a recommended song that wasn't retrieved | Pass |
| `test_grounding_passes_when_answer_stays_in_retrieved` | No false alarm when grounded | Pass |
| `test_pipeline_returns_all_stages_and_is_grounded` | End-to-end wiring + grounding | Pass |

**Summary: 8 / 8 automated tests pass.** The RAG tests use a fake LLM client, so
they run without Ollama installed.

## 2. Grounding check (automatic reliability metric)

Every RAG run calls `check_grounding()`, which flags any catalog song the answer
mentions that was **not** in the retrieved set. `main.py` prints the result as
`[grounding OK]` or `[grounding WARNING]`, and it is logged. Metric on real runs
so far: **0 ungrounded songs** — the model never recommended a song outside the
retrieved candidates.

## 3. Human evaluation of real runs

| Test Input | Evaluation Criteria | Result |
|------------|---------------------|--------|
| `--ask "something calm for late-night coding"` | Recommends only retrieved songs; explanation matches the calm request | Pass — 3 picks, all from the retrieved 5, cited real energy/tempo values |
| `python src/main.py` (Late-Night Focus profile) | Calm lofi tracks rank at the top | Pass — Focus Flow / Deep Focus at 100% |
| `python src/main.py` (High-Energy Pop profile) | Loud, fast, danceable tracks rank at the top | Pass — Gym Hero / Circuit Breaker / Redline Fever |
| `[edge] Out-of-Range Values` (energy 2.0, tempo 400) | Stays within [0,1]; percent match meaningful | Fail — closeness goes negative, "percent match" becomes meaningless (documented bug) |
| `[edge] Sparse Profile` (one trait only) | Scores comparable across profiles | Partial — max score caps low; scores not comparable when features are missing |
| `--ask ""` (empty request) | Handles gracefully | Pass — prints "No request given", exits 0 |
| RAG with Ollama not installed / server down | Reports cleanly, no stack trace | Pass — "[RAG unavailable] ..." message |

## Testing summary

8/8 automated tests pass and the grounding check reports 0 ungrounded songs across
real RAG runs, so the AI stays within its retrieved context. The system handles
missing input, a stopped model server, and malformed LLM output gracefully. The main
reliability gap is input validation: out-of-range or sparse profiles produce
negative or non-comparable scores — a known bug documented in the model card, and the
clearest next fix.
