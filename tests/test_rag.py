"""
Reliability tests for the RAG pipeline (src/rag_recommender.py).

These use a fake LLM client, so they run WITHOUT Ollama installed or running —
the tests exercise the pipeline wiring, the parse fallback guardrail, and the
grounding check that proves the model's output stays within retrieved data.
"""

import json

import rag_recommender as rag


# --- A tiny, self-contained catalog so tests don't depend on the CSV ---------
SONGS = [
    {"id": 1, "title": "Quiet Study", "artist": "LoRoom", "genre": "lofi",
     "mood": "focused", "energy": 0.30, "tempo_bpm": 72, "valence": 0.55,
     "danceability": 0.50, "acousticness": 0.85},
    {"id": 2, "title": "Night Sprint", "artist": "Voltline", "genre": "rock",
     "mood": "intense", "energy": 0.95, "tempo_bpm": 160, "valence": 0.45,
     "danceability": 0.65, "acousticness": 0.08},
    {"id": 3, "title": "Slow Tide", "artist": "Orbit Bloom", "genre": "ambient",
     "mood": "chill", "energy": 0.25, "tempo_bpm": 60, "valence": 0.60,
     "danceability": 0.40, "acousticness": 0.92},
]


class FakeClient:
    """Stands in for an ollama.Client. Returns canned parse/generate output."""

    def __init__(self, prefs_content: str, answer_content: str):
        self._prefs = prefs_content
        self._answer = answer_content

    def chat(self, model, messages, format=None, options=None):
        # The parse call passes a `format` schema; the generate call does not.
        content = self._prefs if format is not None else self._answer
        return {"message": {"content": content}}


# --- Stage 1: query parsing --------------------------------------------------

def test_parse_returns_prefs_from_valid_json():
    prefs = {"genre": "lofi", "mood": "focused", "energy": 0.3, "valence": 0.5,
             "tempo_bpm": 72, "danceability": 0.5, "acousticness": 0.85}
    client = FakeClient(json.dumps(prefs), "unused")
    assert rag.parse_query_to_prefs("calm study music", client=client) == prefs


def test_parse_falls_back_to_neutral_on_bad_json():
    # Guardrail: a malformed model response must not crash the pipeline.
    client = FakeClient("this is not json", "unused")
    prefs = rag.parse_query_to_prefs("whatever", client=client)
    assert prefs == rag._NEUTRAL_PREFS


# --- Stage 3: generation edge case -------------------------------------------

def test_generate_handles_no_candidates():
    client = FakeClient("unused", "unused")
    msg = rag.generate_grounded_answer("q", [], client=client)
    assert "No songs" in msg


# --- Grounding reliability check ---------------------------------------------

def test_grounding_flags_leaked_song():
    retrieved = [(SONGS[0], 0.9, "reason")]  # only "Quiet Study" was retrieved
    answer = 'I recommend "Night Sprint" by Voltline.'  # a NON-retrieved catalog song
    leaked = rag.check_grounding(answer, retrieved, SONGS)
    assert leaked == ["Night Sprint"]


def test_grounding_passes_when_answer_stays_in_retrieved():
    retrieved = [(SONGS[0], 0.9, "reason")]
    answer = 'I recommend "Quiet Study" by LoRoom.'
    assert rag.check_grounding(answer, retrieved, SONGS) == []


# --- Full pipeline wiring ----------------------------------------------------

def test_pipeline_returns_all_stages_and_is_grounded():
    prefs = {"genre": "lofi", "mood": "focused", "energy": 0.3, "valence": 0.55,
             "tempo_bpm": 72, "danceability": 0.5, "acousticness": 0.85}
    answer = 'Try "Quiet Study" by LoRoom and "Slow Tide" by Orbit Bloom.'
    client = FakeClient(json.dumps(prefs), answer)

    result = rag.recommend_from_query("calm focus music", SONGS, k=2, client=client)

    assert set(result) == {"query", "prefs", "retrieved", "answer", "ungrounded"}
    assert len(result["retrieved"]) == 2
    # Retrieved songs must be real catalog entries.
    titles = {s["title"] for s in SONGS}
    assert all(song["title"] in titles for song, _s, _r in result["retrieved"])
    # This answer only names retrieved songs, so grounding must pass.
    assert result["ungrounded"] == []
