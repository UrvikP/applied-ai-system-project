# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

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

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## AI Feature: Retrieval-Augmented Generation (RAG)

On top of the deterministic content-based recommender, the system includes a
**RAG** mode that answers free-text listening requests. The retrieval step is
the existing scorer, so the AI feature is fully integrated rather than bolted on.

**Pipeline** (`src/rag_recommender.py`):

1. **Parse** — Claude turns a request like *"something calm for late-night
   coding"* into a numeric `user_prefs` profile (schema-constrained call).
2. **Retrieve** — the existing `recommend_songs` scorer ranks `data/songs.csv`
   against that profile and returns the top-k candidates. The CSV is the
   knowledge base; the scorer is the retriever.
3. **Generate** — Claude writes the recommendation **grounded only in the
   retrieved candidates**, and is instructed to recommend nothing outside that
   list (and to say so when nothing fits).

The retrieved songs actively determine the answer — the model is not allowed to
recommend songs it wasn't given.

### Setup for RAG

RAG needs an Anthropic API key (the `anthropic` package is already in
`requirements.txt`):

```bash
export ANTHROPIC_API_KEY=sk-ant-...        # Mac or Linux
setx ANTHROPIC_API_KEY "sk-ant-..."        # Windows
```

### Running RAG mode

```bash
python src/main.py --ask "something calm for late-night coding"
python src/main.py --ask                    # interactive prompt
```

Without `--ask`, the app runs the original profile demo. **Guardrails**: a
missing key or package is reported cleanly (no stack trace), a failed query
parse falls back to a neutral profile so retrieval still runs, and every stage
is logged to stderr.

---

## Sample Recommendation Output

Paste a sample of your recommender's output here as a text block so a reader can see what it produces:

```
Loaded 20 songs from /Users/urvikpatel/Desktop/ai110-module3show-musicrecommendersimulation-starter/data/songs.csv

Top 5 recommendations for a focused / lofi listener
===================================================

1. Focus Flow - LoRoom
   Match score: 1.00  (100%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference
     - it has the mood you like (focused)

2. Deep Focus - LoRoom
   Match score: 1.00  (100%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference
     - it has the mood you like (focused)

3. Slow Morning - Slow Stereo
   Match score: 0.96  (96%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference

4. Rainy Window Seat - Paper Lanterns
   Match score: 0.95  (95%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference

5. City Lights Fade - LoRoom
   Match score: 0.96  (96%)
   Why this song:
     - it closely matches your acousticness preference
     - it closely matches your energy preference
     - it closely matches your tempo_bpm preference
     - it closely matches your valence preference
     - it closely matches your danceability preference
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

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

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this

I learned about all the preferences/metrics that have to be taken into consideration before predicting the best possible recommendation. Assigning weights to preferences is very important, aslo certain preferances can be very similiar, in this project energy and tempo_bpm basically the same type of metric and this can skew the ratings of the songs. I learned that scoring and ranking are seprate jobs. My intial idea was to score how good a single song is for a user and decide if it should be included in the list all within the same function (I didn't realize I was doing this at first). After asking CLaude.ai for input, it rectified and explained my logic. By seperatign the process, it allowed me to rate the song and then curate a recommendation without sacrificing accuracy.

Bias can show up in any program. My program has only 20 songs, limited data to work with, and as I've learned from AI, I haven't in taken into consideration the full scope of user "Tastes" like lyrics and culture. I guess this could also be a problem for real world companies like Spotify and Youtube where skewed datasets or weights tuned for engagement can shape what millions of people are exposed to.

