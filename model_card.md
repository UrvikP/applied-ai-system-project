# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name   
**PathToMusic 1.0**

---

## 2. Intended Use  

My recommender is for people who want to look ofr similar song to the ones they already listen ton to. However they should expect the music to match the exact genre. Perhaps they'll be in for a surprise.

---

## 3. How the Model Works  

Think of the program as a matchmaker for songs. The listener describes the music they're in the mood for, and the program measures how closely each song fits — then returns the best matches with a reason for each.

What we look at in each song: measurable traits like energy (calm vs. hyped), tempo (fast vs. slow), valence (upbeat vs. moody), danceability, acousticness (unplugged vs. electronic), and a mood label like "chill" or "focused."

What the listener gives us: their ideal version of those same traits — how much energy, what tempo, what mood, and so on.

How we turn that into a score: for each trait we ask "how close is the song to what the listener wanted?" — a perfect match is 100%, further off scores lower. We blend all the traits into one score from 0 to 100%. The key twist: traits aren't weighted equally — energy and acousticness matter most for our focus listener, danceability barely matters — and a matching mood earns a small bonus. Each recommendation comes with plain-English reasons, like "closely matches your energy preference."

What we changed from the starter: the starter just returned the first few songs without looking at them. We made it actually compare each song's traits to the listener's wishes, added weights so important traits count more, made it explain itself, and left genre out of scoring (plus a step that avoids five near-identical picks) so results have some variety.


---

## 4. Data  


The datset holds 20 songs, seven genres: lofi (6), pop (3), synthwave (3), indie pop (2), rock (2), ambient (2), and jazz (2). No hip-hop, classical, country, metal, electronic/EDM, R&B, or world music.
I had Claude.ai add 10 additional songs.
The sample is too small and lofi-skewed to represent a realistic library, so some tastes (e.g. an intense-rock listener) have very few songs to match against.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  
    Late-Night Focus — the two focused lofi tracks (Focus Flow, Deep Focus) top the list at 100%, exactly the calm, acoustic, low-energy songs a focus listener wants.
    High-Energy Pop and Deep Intense Rock — the loud, fast, danceable tracks rise to the top and the mellow ones sink, matching intuition.
    Chill Lofi — surfaces the quiet, acoustic, slow songs and pushes intense tracks to the bottom.
---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

**Features it does not consider.** The scorer sees only five numeric traits (energy,
tempo, valence, danceability, acousticness) plus a mood label, so it is blind to
lyrics, vocals, era, production quality, and cultural context. It also ignores genre
by design, which means a listener can be handed a song from a genre they dislike as
long as the numbers line up.

**Genres or moods that are underrepresented.** The catalog is small and was skewed
toward lofi and pop, so listeners wanting under-represented styles (originally rock,
jazz, and anything outside the starter genres) got thinner, lower-quality results
purely because of what's in the data. Expanding the catalog to 50 songs across many
more genres reduced this, but any fixed catalog still biases results toward whatever
is over-represented in it.

**Cases where the system overfits to one preference.** Because the score is a weighted
blend, a song that nails the two heaviest traits (energy and acousticness) can rank
highly while missing everything else. A sparse profile is worse: with only one or two
traits specified, a single trait can decide the entire ranking, and scores stop being
comparable across profiles because the weight denominator silently changes.

**Ways the scoring might unintentionally favor some users.** The weights were
hand-tuned for a calm, focus-style listener, so users who care most about
low-weighted traits like danceability — or who sit at a bland "all-neutral" middle —
get less accurate or undifferentiated results. Energy and tempo are also correlated,
so the "calmness" axis is effectively double-counted and quietly outweighs valence
and danceability even though the weights look balanced. Finally, valid but extreme
inputs (values outside 0–1) can produce negative trait scores and a broken "percent
match," so the system misbehaves silently instead of warning the user.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

**Profiles I tested.** Four realistic profiles (Late-Night Focus, High-Energy Pop,
Chill Lofi, Deep Intense Rock) to confirm sensible ranking, plus four adversarial
"edge" profiles built to break the scorer: Contradictory Mood (intense mood but calm
numbers), Out-of-Range Values (energy 2.0, tempo 400), Sparse Profile (one trait
only), and All-Neutral (0.5 everything).

**What I looked for.** Whether coherent profiles surfaced the obviously-right songs at
the top, whether the variety re-rank prevented five near-identical picks, and whether
the edge profiles exposed hidden assumptions in the scoring math.

**Simple tests I ran.** Automated `pytest` tests (`tests/test_recommender.py`) verify
that `recommend` returns songs sorted by score and that `explain_recommendation`
returns a non-empty string — both pass. For the RAG feature, I ran real free-text
queries and confirmed the model only ever recommends songs from the retrieved
candidate list (grounding held).

**What surprised me.** The Out-of-Range profile revealed a genuine bug: closeness
`1 - |user - song|` goes **negative** when inputs exceed [0, 1], so a song can subtract
from its own score and the "percent match" label becomes meaningless. I also didn't
expect how tightly the All-Neutral scores bunched together, leaving ties to be broken
by catalog order — a subtle ordering bias.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  


Add more features — include era, vocals, and language, let users set their own weights, and validate inputs to 0–1.
Explain better — show each trait's contribution and score breakdown, not just which preferences matched.
Improve diversity — tune the variety penalty and spread genres/moods so one style doesn't dominate.
Handle complex tastes — support multiple moods, learn from skips/likes, and add a collaborative-filtering signal.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

I learned about weights and how emphasizing one preference/metric can change the results.
I thought my application took into consideration everything necessary, but it turns out its not enough. I didn't bother adjusting my application to consider all those additional preferences/metrics because I don't want to burn through all my Claude.ai tokens.
I have a much deeper understanding of just how many considerations music apps make before recommending music to users. All that processing power for a few recommendations. I've only implemented a simple solution, there is so much more to consider when recommending something to someone.

### Responsible-AI Reflection

**How I collaborated with AI.** I used Claude.ai as a coding partner throughout:
to review my logic, expand the song catalog, and build the RAG feature that lets a
user ask for music in plain English. I also used a local LLM (llama3.2 via Ollama)
as the runtime model for the RAG mode, so the recommender itself now leans on AI —
but only within guardrails I set (the model may recommend *only* from songs my
scorer retrieves).

**One helpful AI suggestion.** Early on I was scoring a song and deciding whether to
include it in the final list inside the *same* function without realizing it. Claude
pointed out that I was conflating two jobs and suggested splitting **scoring** (judge
one song in isolation) from **ranking** (build a varied list). Separating them let me
add a variety re-rank without sacrificing match accuracy — this became the core design
of the whole project.

**One flawed AI suggestion.** When I asked Claude to add songs to the catalog, its
first batch of 10 stayed skewed toward the same lofi/pop styles the catalog already
had, instead of adding real variety — so under-represented tastes (rock, jazz, and
anything outside the existing genres) still had almost nothing to match against. The
suggestion looked reasonable but didn't actually fix the bias I was trying to address;
I had to explicitly ask for songs spanning new genres, moods, and the full range of
feature values before the catalog was genuinely diverse. It was a good reminder that
AI output can be confidently plausible while quietly failing the real goal, so I need
to check it against what I actually asked for.

**System limitations.** The recommender sees only five numeric traits plus a mood
label, so it is blind to lyrics, vocals, era, and culture; it ignores genre by design;
the catalog is small and skewed; extreme inputs outside [0, 1] can produce negative
scores and a meaningless "percent match"; and the RAG layer depends on a small local
model whose query-parsing can be imprecise. (Full detail in sections 6 and 7.)

### Could This AI Be Misused, and How I Prevent It

Yes — a few ways, each with a mitigation already in the system:

- **Prompt injection through the free-text request.** Because the query is sent to
  an LLM, a user could try to make it ignore its instructions and output arbitrary
  text or "recommend" songs that don't exist. *Prevention:* the LLM never chooses
  songs — my deterministic scorer retrieves the candidates, and the model may only
  recommend from that list. The `check_grounding()` function runs on every response
  and flags any song mentioned that wasn't retrieved, so a hijacked answer is caught
  and reported rather than trusted.
- **Manipulating what people hear (filter bubbles / promotion).** If someone
  controlled the catalog or tuned the weights for engagement rather than fit, the
  system could quietly push particular songs or trap listeners in one narrow style.
  *Prevention:* the weights are transparent and documented, genre is deliberately
  unweighted so no single preference dominates, and the variety re-rank actively
  spreads the results. At this scale it's a simulation, but the risk is exactly what
  real platforms face.
- **Silent wrong output presented as confident.** The parser can return plausible but
  unusable values, and out-of-range inputs break the score. *Prevention:* every stage
  is logged, a bad parse falls back to a neutral profile instead of crashing, and the
  known input-validation gap is documented here as the top future fix.

### What Surprised Me While Testing the AI's Reliability

I expected the local model to occasionally recommend a song that wasn't in the
retrieved list, so I built the grounding check specifically to catch it — and was
surprised that across my real runs it reported **zero** ungrounded songs. The prompt
constraint plus the retrieval step were enough to keep the model honest, and the
automatic check let me *prove* that rather than just assume it. The other surprise
was the opposite direction: the parsing step confidently produced labels like genre
"Instrumental" and mood "Relaxing" that don't exist in my catalog's vocabulary, so
they silently contributed nothing to retrieval — a reliability risk hidden behind
plausible-looking output, which is exactly why the guardrails and logging matter.