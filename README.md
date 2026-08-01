# 🎵 Music Recommender Simulation

**Repository:** https://github.com/UrvikP/applied-ai-system-project

## Summary

The **Music Recommender Simulation** is a command-line music recommender that turns
songs and a listener's taste profile into ranked recommendations, each with a
plain-language explanation of *why* it was picked. This phase adds a
**Retrieval-Augmented Generation (RAG)** mode: you can now describe what you want in
plain English ("something calm for late-night coding") and a local LLM answers using
songs retrieved by the original scoring engine. This matters because it shows how a
small, transparent, rule-based system can be paired with an LLM so the model stays
**grounded in real catalog data** instead of inventing recommendations.

### Original Project (Modules 3)

This builds directly on my original **Music Recommender Simulation** from Module
3. That project represented each song and a user "taste profile" as numeric data
(energy, valence, tempo, danceability, acousticness, plus mood and genre), designed a
content-based scoring rule that measured how closely each song matched the profile,
and ranked the catalog into a top-K list using a variety re-rank and human-readable
reasons. Its goal was to show, end to end, how raw preference data becomes explainable
recommendations — and where bias can creep in.

---

## Architecture Overview

The full system diagram is in
[`diagrams/system_diagram.mmd`](diagrams/system_diagram.mmd) (Mermaid source; also
rendered in [`diagrams/system_diagram.md`](diagrams/system_diagram.md)).

Data flows **input → process → output** along two paths:

- **Profile demo (no LLM):** a hardcoded taste profile → the content-based **scorer**
  (`score_song` + variety re-rank in `recommend_songs`) over `data/songs.csv` →
  ranked recommendations with reasons.
- **RAG mode (LLM):** a free-text request → **(1) parse** it into a numeric profile
  with the local LLM → **(2) retrieve** the top-K candidates using the *same* scorer
  (the CSV is the knowledge base, the scorer is the retriever) → **(3) generate** a
  recommendation grounded only in those retrieved songs.

Checking happens in two places: **automated tests** (`pytest`) verify the
deterministic scorer, and **runtime guardrails** (server/model checks, a
neutral-profile fallback, a grounding constraint, and per-stage logging) validate the
LLM stages. A human reviews the grounded output and the adversarial edge-case
profiles, and tunes weights/prompts from there.

---

## How The System Works

Explain your design in plain language.

Some prompts to answer:

- What features does each `Song` use in your system
  - For example: genre, mood, energy, tempo
- What information does your `UserProfile` store
- How does your `Recommender` compute a score for each song
- How do you choose which songs to recommend

You can include a simple diagram or bullet list if helpful.
In the real world, content platforms like Youtube and Spotify use a mixture of content-based filtering (which is what this recommendation project is using) and collabrative filitering (which ignores content and instead relies on pattern recognition for a large user base, for example: users who clicked on this video also enjoyed the following video - so the following video is recommended). So they take into account the users preference (what they watch) and show similar videos and also occasionally show content based on other users interests that the user might enjoy.

  -  My simulator is a content-based recommender. The scoring rule measures, feature by feature, how close each song's numeric attributes (energy, valence, danceability, acousticness, normalized tempo) are to the user's preferences, combined as a weighted sum where the weights encode how much each feature matters — producing one match score in [0,1] plus human-readable reasons. The ranking rule then sorts all scored songs and applies a variety penalty so the final top-K isn't five near-identical tracks. Variety is enforced at ranking, not by discarding features, so I keep full matching accuracy and a diverse list.
        ┌──────────────────┐        ┌──────────────────────┐
        │  Song catalog    │        │   User taste profile │
        │  (load_songs)    │        │   (UserProfile)      │
        │ energy, valence, │        │ target energy,       │
        │ tempo, dance...  │        │ mood, likes_acoustic │
        └────────┬─────────┘        └──────────┬───────────┘
                 │                             │
                 └──────────────┬──────────────┘
                                │
                                ▼
        ╔═══════════════════════════════════════════════╗
        ║   SCORING RULE   ·   score_song(user, song)    ║
        ║   "How well does THIS ONE song match?"         ║
        ╠═══════════════════════════════════════════════╣
        ║  1. Normalize features → all on 0–1 scale      ║
        ║       (tempo_bpm rescaled!)                    ║
        ║  2. Per-feature closeness = 1 - |user - song|  ║
        ║  3. Weighted sum  Σ (weight × closeness)       ║
        ║       energy .30  valence .25  dance .20 ...   ║
        ║       (weights sum to 1)                       ║
        ╚═══════════════════════════════════════════════╝
                                │
                                ▼
              one score in [0,1]  +  reasons
              (repeat for every song)
                                │
                                ▼
        ╔═══════════════════════════════════════════════╗
        ║   RANKING RULE   ·   recommend_songs(...)      ║
        ║   "What LIST do I actually show?"              ║
        ╠═══════════════════════════════════════════════╣
        ║  1. Sort all songs by score (descending)       ║
        ║  2. Variety re-rank: penalize a candidate      ║
        ║     too similar to ones already picked         ║
        ║       ← variety lives HERE, not by dropping    ║
        ║         features in scoring                    ║
        ╚═══════════════════════════════════════════════╝
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Top-K recommendations│
                    │   (song, score, why)   │
                    └───────────────────────┘


Phase 2:

My algortihm does not care about Genre when it comes to recomendations, atleast its not factored into my algorithm. I did not remove it as songs still need to be classified into genre. I want to avoid giving more weight to one particular preference than the others.

Finalized Algorithm:
    Stage 1 — score_song(user_prefs, song) → (score, reasons)
    Judges one song against the taste profile.

    Normalize every feature to a 0–1 scale. Most already are; tempo_bpm is rescaled with (bpm - 60) / (200 - 60), clamped — otherwise its large raw numbers would dominate.

    Per-feature closeness for each numeric feature: closeness = 1 - abs(user_target - song_value) → 1.0 = perfect match, 0.0 = opposite.

    Weighted sum — multiply each closeness by its weight and add them up. Weights sum to 1, so the score lands in [0, 1] (a "percent match"):

    Feature	Weight	Why
    acousticness	0.25	most disqualifying if wrong for focus
    energy	0.25	must stay calm/low-arousal
    tempo_bpm	0.20	pace = intensity (trimmed; correlates w/ energy)
    valence	0.15	persona tolerant on mood
    danceability	0.15	least relevant for background listening
    Categoricals handled separately (can't use abs()): mood adds a small match bonus; genre is carried for display only, weight 0 (variety decision).

    Collect reasons — for each feature that scores high, append a human-readable string ("matches your energy preference") to power explain_recommendation.

    Stage 2 — recommend_songs(user_prefs, songs, k) → list of (song, score, explanation)
    Turns scores into the final list.

    Score every song via score_song.
    Sort by score, descending.
    Variety re-rank — when picking each next song, penalize candidates too similar to ones already chosen (e.g. same artist / near-identical feature vector), so the top-K isn't five clones. Variety lives here, not in scoring.
    Return top-K with their scores and explanations.
    The core design principle
    Scoring judges a song in isolation (stays blind to variety on purpose, protecting match accuracy). Ranking looks at the whole set and injects variety. Keeping them separate is why you don't drop features to force variety.

Some biases:
- Weights are opinions — the hand-picked weights (acousticness/energy high, valence/danceability low) encode the designer's belief about what matters; the user never chose them, so the scoring favors that bias by design.
- Correlated features double-count — tempo and energy both measure "calmness," so the mellow-ness axis carries ~0.45 combined and quietly outweighs valence and danceability, even though the weights look balanced.
- Variety over-rides best match — the ranking's diversity re-rank intentionally demotes some closest-matching songs, so the top result isn't always the true highest score.


---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app (profile demo — no LLM or internet needed):

```bash
python src/main.py
```

   For the RAG mode (free-text requests), see **Running RAG mode** below.

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## AI Feature: Retrieval-Augmented Generation (RAG)

On top of the deterministic content-based recommender, the system includes a
**RAG** mode that answers free-text listening requests. It runs on a **local LLM
via [Ollama](https://ollama.com)** — free, no API key, works offline. The
retrieval step is the existing scorer, so the AI feature is fully integrated
rather than bolted on.

**Pipeline** (`src/rag_recommender.py`):

1. **Parse** — the local LLM turns a request like *"something calm for late-night
   coding"* into a numeric `user_prefs` profile (schema-constrained call).
2. **Retrieve** — the existing `recommend_songs` scorer ranks `data/songs.csv`
   against that profile and returns the top-k candidates. The CSV is the
   knowledge base; the scorer is the retriever.
3. **Generate** — the LLM writes the recommendation **grounded only in the
   retrieved candidates**, and is instructed to recommend nothing outside that
   list (and to say so when nothing fits).

The retrieved songs actively determine the answer — the model is not allowed to
recommend songs it wasn't given.

### Setup for RAG

RAG runs a local model through Ollama — no API key, no account, no cost.

1. Install Ollama from https://ollama.com and start the server:

   ```bash
   ollama serve
   ```

2. Download the model once (~2 GB, runs on a typical laptop):

   ```bash
   ollama pull llama3.2
   ```

The `ollama` Python package is already in `requirements.txt`. To use a different
local model, set `OLLAMA_MODEL` (e.g. `export OLLAMA_MODEL=mistral`).

### Running RAG mode

```bash
python src/main.py --ask "something calm for late-night coding"
python src/main.py --ask                    # interactive prompt
```

Without `--ask`, the app runs the original profile demo. **Guardrails**: a
stopped Ollama server, missing model, or missing package is reported cleanly
(no stack trace), a failed query parse falls back to a neutral profile so
retrieval still runs, and every stage is logged to stderr.

---

## Sample Interactions

Three real, reproducible runs against the 50-song catalog.

### Example 1 — RAG mode (free-text → grounded AI recommendation)

**Input:**

```bash
python src/main.py --ask "something calm for late-night coding"
```

**Output** (local `llama3.2` via Ollama; logs show each stage):

```
Parsing query into preferences: 'something calm for late-night coding'
Parsed preferences: {'genre': 'Instrumental', 'mood': 'Relaxing', 'energy': 0.5,
                     'valence': 0.5, 'tempo_bpm': 60, 'danceability': 0.5, 'acousticness': 0.8}
Generating grounded answer from 5 candidates.

Request: something calm for late-night coding
=============================================

Retrieved candidates (via the content-based scorer):
  1. City Lights Fade - LoRoom  (92% match)
  2. Spacewalk Thoughts - Orbit Bloom  (88% match)
  3. Library Rain - Paper Lanterns  (90% match)
  4. Deep Focus - LoRoom  (91% match)
  5. Focus Flow - LoRoom  (91% match)

Recommendation (grounded in the retrieved songs):

Based on the listener's request for something calm for late-night coding, I recommend:

1. "Spacewalk Thoughts" by Orbit Bloom
2. "Library Rain" by Paper Lanterns
3. "Deep Focus" by LoRoom

All three songs have a calming effect due to their low energy levels (0.28-0.35) and
slow tempos (60.0bpm-72.0bpm), which should help create a focus-enhancing atmosphere
for late-night coding.

[grounding OK] all recommended songs came from the retrieved set
```

Note that **every song the LLM recommends comes from the retrieved list** — it invents
nothing and even cites the real energy/tempo values from the retrieved data. That
grounding is what makes this RAG rather than a plain LLM answer.

### Example 2 — Profile demo, "Late-Night Focus" listener (deterministic scorer)

**Input:** `python src/main.py`  (excerpt for the Late-Night Focus profile)

```
Late-Night Focus  |  Top 5 recommendations
==========================================

1. Focus Flow - LoRoom
   Match score: 1.00  (100%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference
     - it has the mood you like (focused)

2. Deep Focus - LoRoom            Match score: 1.00  (100%)
3. Slow Morning - Slow Stereo     Match score: 0.96  (96%)
4. Rainy Window Seat - Paper Lanterns   Match score: 0.95  (95%)
5. Late Bus Home - Mellow Kanto   Match score: 0.95  (95%)
```

### Example 3 — Profile demo, "High-Energy Pop" listener (deterministic scorer)

**Input:** `python src/main.py`  (excerpt for the High-Energy Pop profile)

```
High-Energy Pop  |  Top 5 recommendations
=========================================

1. Gym Hero - Max Pulse
   Match score: 1.00  (100%)
   Why this song:
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your danceability preference
     - it has the mood you like (intense)

2. Circuit Breaker - Bassline Theory   Match score: 0.99  (99%)
3. Redline Fever - Steel Mirage        Match score: 0.98  (98%)
```

The two deterministic profiles pull completely different, coherent lists (mellow lofi
vs. high-tempo pop/electronic), and the expanded 50-song catalog surfaces the newer
tracks (Late Bus Home, Circuit Breaker, Redline Fever).

---

## Reproducible Execution Evidence

Everything below is real, captured output so the system can be graded without watching
a demo. (RAG logs stream to stderr; the recommendation and grounding result to stdout.)

### A. RAG command execution — input, output, and guardrail result in one run

**Command / input:**

```bash
python src/main.py --ask "upbeat music for a workout"
```

**Output (real run, local llama3.2 via Ollama):**

```
rag_recommender INFO: Parsing query into preferences: 'upbeat music for a workout'
rag_recommender INFO: Parsed preferences: {'genre': 'Pop', 'mood': 'Energizing',
                      'energy': 1, 'valence': 0.5, 'tempo_bpm': 120,
                      'danceability': 0.8, 'acousticness': 0}
rag_recommender INFO: Generating grounded answer from 5 candidates.
rag_recommender INFO: Grounding check passed: answer stays within retrieved songs.

Request: upbeat music for a workout
===================================

Retrieved candidates (via the content-based scorer):
  1. Concrete Pulse - Null Sector  (91% match)
  2. Power Hour - Max Pulse  (90% match)
  3. Redline Fever - Steel Mirage  (89% match)
  4. Circuit Breaker - Bassline Theory  (88% match)
  5. Deep End - Marlow House  (89% match)

Recommendation (grounded in the retrieved songs):

Based on the listener's request for upbeat music for a workout, I recommend:

1. "Power Hour" by Max Pulse - intense mood, tempo 136bpm.
2. "Circuit Breaker" by Bassline Theory - drum and bass, fast tempo 174bpm.
3. "Deep End" by Marlow House - house track, energetic, 124bpm.

[grounding OK] all recommended songs came from the retrieved set
```

Every recommended song is one of the five retrieved candidates — the **guardrail
result** (`[grounding OK]`) confirms the model did not invent or leak any song.

### B. Reliability check — automated tests

**Command:**

```bash
pytest -q
```

**Output:**

```
........                                                                 [100%]
8 passed in 0.02s
```

### C. Reliability check — grounding detector (proves the guardrail actually works)

Run the grounding check on a grounded answer (returns `[]`) and on one that leaks a
non-retrieved song (flags it):

```
ungrounded (grounded answer):  []
ungrounded (leak of "Storm Runner"):  ['Storm Runner']
```

### D. Guardrail — RAG when Ollama is unavailable (no crash)

When the model server, model, or package is missing, RAG mode reports it cleanly and
the program still exits 0:

```
[RAG unavailable] The 'ollama' package is required for the RAG feature.
Install it with: pip install -r requirements.txt
```

(An empty request behaves the same way: `python src/main.py --ask ""` prints
`No request given.` and exits 0.)

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

EDGE CASES OUTPUT

[edge] Contradictory Mood  |  Top 5 recommendations
===================================================

1. Starlit Drift - Orbit Bloom
   Match score: 0.94  (94%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference

2. Spacewalk Thoughts - Orbit Bloom
   Match score: 0.92  (92%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference

3. Rainy Window Seat - Paper Lanterns
   Match score: 0.87  (87%)
   Why this song:
     - it closely matches your acousticness preference
     - it is a good fit for your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it is a good fit for your danceability preference

4. Library Rain - Paper Lanterns
   Match score: 0.85  (85%)
   Why this song:
     - it closely matches your acousticness preference
     - it is a good fit for your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it is a good fit for your danceability preference

5. Coffee Shop Stories - Slow Stereo
   Match score: 0.82  (82%)
   Why this song:
     - it closely matches your acousticness preference
     - it is a good fit for your energy preference
     - it is a good fit for your tempo_bpm preference
     - it is a good fit for your valence preference
     - it is a good fit for your danceability preference

[edge] Out-of-Range Values  |  Top 5 recommendations
====================================================

1. Golden Parade - Indigo Parade
   Match score: 0.45  (45%)
   Why this song:
     - it closely matches your acousticness preference
     - it is a good fit for your danceability preference
     - it has the mood you like (happy)

2. Rooftop Lights - Indigo Parade
   Match score: 0.45  (45%)
   Why this song:
     - it closely matches your acousticness preference
     - it has the mood you like (happy)

3. Sunrise City - Neon Echo
   Match score: 0.42  (42%)
   Why this song:
     - it is a good fit for your danceability preference
     - it has the mood you like (happy)


[edge] Sparse Profile  |  Top 5 recommendations
===============================================

1. Sunrise City - Neon Echo
   Match score: 0.33  (33%)
   Why this song:
     - it closely matches your energy preference
     - it has the mood you like (happy)

2. Rooftop Lights - Indigo Parade
   Match score: 0.32  (32%)
   Why this song:
     - it closely matches your energy preference
     - it has the mood you like (happy)

3. Electric Sunset - Neon Echo
   Match score: 0.33  (32%)
   Why this song:
     - it closely matches your energy preference
     - it has the mood you like (happy)

4. Golden Parade - Indigo Parade
   Match score: 0.31  (31%)
   Why this song:
     - it is a good fit for your energy preference
     - it has the mood you like (happy)

5. Storm Runner - Voltline
   Match score: 0.25  (25%)
   Why this song:
     - it closely matches your energy preference

[edge] All-Neutral  |  Top 5 recommendations
============================================

1. City Lights Fade - LoRoom
   Match score: 0.83  (83%)
   Why this song:
     - it is a good fit for your acousticness preference
     - it closely matches your energy preference
     - it closely matches your valence preference
     - it closely matches your danceability preference

2. Golden Parade - Indigo Parade
   Match score: 0.80  (80%)

---

## Design Decisions

Key choices and the trade-offs behind them:

- **Separate scoring from ranking.** `score_song` judges one song in isolation;
  `recommend_songs` handles variety across the whole set. *Trade-off:* slightly more
  code and two passes, but variety never corrupts match accuracy — I don't have to
  drop features to avoid five near-identical results.
- **Genre carried but weighted 0.** Genre is kept for display/classification but not
  scored, so no single preference dominates. *Trade-off:* loses an obvious signal a
  real service would use, in exchange for a more balanced weighted sum.
- **Reuse the scorer as the RAG retriever.** The LLM does not choose songs — the
  existing scorer retrieves candidates and the model may only recommend from them.
  *Trade-off:* the model can't surface anything outside the catalog, but in return it
  can't hallucinate songs, which is the whole point of adding RAG.
- **Local LLM (Ollama) instead of a paid API.** Runs offline, free, no API key.
  *Trade-off:* the reviewer must install Ollama and pull a model, and a small local
  model (llama3.2) writes weaker prose and is slower (~15–25s/stage) than a large
  cloud model — but the project stays free and reproducible.
- **Guardrails over crashes.** Missing server/model/package is reported cleanly, and a
  failed query-parse falls back to a neutral profile so retrieval still runs.
  *Trade-off:* a neutral fallback can produce a generic result instead of an error,
  but the app never dies mid-request.

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

The realistic 3 (added)
High-Energy Pop, Chill Lofi, Deep Intense Rock — coherent profiles where numbers, mood, and genre agree. These just confirm the scorer ranks sensibly.
The adversarial 4 — and the bug/quirk each reveals
1. Contradictory Mood (mood: intense but energy 0.15, tempo 60)

Result: top picks are all calm ambient tracks (Starlit Drift, 0.94) and none got the mood bonus.
What it reveals: the numeric targets won here — but only because your catalog has no calm song tagged "intense." If one existed, the +0.10 mood bonus could vault a jarring track above better numeric matches. The design lets mood and features pull in opposite directions with no consistency check.
2. Out-of-Range Values (energy: 2.0, valence: 1.8, tempo: 400) — the real bug

Result: scores collapse to ~0.45 and the "percent match" label becomes meaningless.
What it reveals: closeness = 1 - abs(2.0 - 0.9) = -0.1 goes negative — a song can now subtract from its own score. And tempo 400 saturates the clamp at 1.0, so every song looks identically far on tempo. Nothing validates that inputs are in [0,1].
3. Sparse Profile (only mood + energy)

Result: max score caps at 0.33, even for a perfect energy match.
What it reveals: missing features are silently skipped, so only 0.25 (energy weight) + 0.10 (mood) = 0.35 of weight is ever in play. Scores across profiles aren't comparable because the denominator silently changes.
4. All-Neutral (0.5 everything, mood: nonexistent)

Result: scores bunch tightly (0.80–0.83) and ties break by catalog order.
What it reveals: the ordering/tie-break bias I flagged earlier — with no distinguishing signal, whichever song appears first in the CSV wins.

---

## Testing Summary

**One-line summary:** 8/8 automated tests pass, and the grounding check reports 0
ungrounded songs across real RAG runs — the AI never recommends a song outside its
retrieved context. Full detail and a human-evaluation table are in
[`tests/human_eval.md`](tests/human_eval.md).

**What I tested**

- **Automated tests** (`pytest`): `tests/test_recommender.py` covers the scorer (sorted
  results, non-empty explanations); `tests/test_rag.py` covers the RAG pipeline using a
  **mocked LLM client** so it runs without Ollama — parse output, the neutral-profile
  fallback on bad model output, the empty-retrieval case, and the grounding check.
  **All 8 pass.**
- **Grounding check** (`check_grounding`): a reliability metric run on every RAG
  request — it flags any catalog song the answer names that wasn't retrieved. `main.py`
  prints `[grounding OK]` / `[grounding WARNING]`. Real runs so far: 0 ungrounded.
- **Adversarial profiles** (the four `[edge]` profiles in `main.py`): contradictory
  mood, out-of-range values, sparse profile, and all-neutral — run through the scorer
  to probe failure modes (see *Experiments* and *Limitations* above).
- **RAG end-to-end**: ran real free-text queries against the local model and confirmed
  the recommendations only ever come from the retrieved candidate list.

**What worked**

- The scorer ranks coherent profiles sensibly, and the variety re-rank keeps the top-K
  from being five clones.
- RAG grounding held up: in the "late-night coding" run, every recommended song was
  from the retrieved set and the model cited the real feature values.
- Guardrails behaved — with Ollama not installed, RAG mode reports a clean message
  instead of a stack trace, and the profile demo runs with zero setup.

**What didn't / what's rough**

- The out-of-range profile exposed a real bug: `closeness = 1 - |user - song|` can go
  **negative** when inputs exceed [0, 1], and tempo saturates the clamp — so the
  "percent match" label becomes meaningless. Inputs are not validated to [0, 1].
- Sparse profiles silently skip missing features, so scores aren't comparable across
  profiles (the weight denominator changes).
- The local LLM is slow and its prose quality is modest; occasionally it returns a
  loosely-worded profile, which the neutral fallback and grounding constraint absorb.

**What I learned**

- Scoring and ranking are genuinely separate jobs; conflating them quietly trades away
  accuracy.
- Correlated features (energy and tempo) double-count and skew results even when the
  weights look balanced.
- RAG is only as trustworthy as its grounding constraint — the retrieval step, not the
  model, is what keeps the recommendations honest.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this

I learned about all the preferences/metrics that have to be taken into consideration before predicting the best possible recommendation. Assigning weights to preferences is very important, aslo certain preferances can be very similiar, in this project energy and tempo_bpm basically the same type of metric and this can skew the ratings of the songs. I learned that scoring and ranking are seprate jobs. My intial idea was to score how good a single song is for a user and decide if it should be included in the list all within the same function (I didn't realize I was doing this at first). After asking CLaude.ai for input, it rectified and explained my logic. By seperatign the process, it allowed me to rate the song and then curate a recommendation without sacrificing accuracy.

Bias can show up in any program. My program has only 20 songs, limited data to work with, and as I've learned from AI, I haven't in taken into consideration the full scope of user "Tastes" like lyrics and culture. I guess this could also be a problem for real world companies like Spotify and Youtube where skewed datasets or weights tuned for engagement can shape what millions of people are exposed to.

---

## Portfolio Artifact

**Code:** https://github.com/UrvikP/applied-ai-system-project

**What this project says about me as an AI engineer.** This project shows that I treat
an LLM as one component in a system, not as the whole system. Rather than letting a
model free-associate recommendations, I made a deterministic, testable scorer do the
retrieval and constrained the model to answer only from what it retrieved — then I
proved that constraint held with an automatic grounding check and unit tests instead
of trusting a good-looking demo. I also chose a free, local model so the project stays
reproducible for anyone, and I built guardrails (clear error handling, a neutral-profile
fallback, per-stage logging) so it fails safely. In short, I care about grounding,
reliability, and reproducibility — making AI that can *prove* it works, and being honest
about where it still falls short (input validation, catalog bias, a small local model).

