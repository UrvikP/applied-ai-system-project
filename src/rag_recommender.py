"""
Retrieval-Augmented Generation (RAG) layer for the music recommender.

Uses a LOCAL LLM via Ollama (https://ollama.com) — free, no API key, runs
offline on your machine. The pipeline (all three stages are load-bearing — the
retrieved songs drive the final answer, they are not printed alongside a canned
response):

    1. RETRIEVE-PREP  A free-text request ("something calm for late-night
                      coding") is parsed by the LLM into a user_prefs dict whose
                      keys match the song dicts (genre, mood, energy, ...).
    2. RETRIEVE       The EXISTING content-based scorer (recommend_songs) ranks
                      the CSV catalog against those prefs and returns the top-k
                      candidates. The CSV is the knowledge base; the scorer is
                      the retriever. No LLM involvement here.
    3. GENERATE       The LLM writes the recommendation grounded ONLY in the
                      retrieved candidates. It is instructed to recommend nothing
                      outside that list and to say so when nothing fits.

Guardrails: a stopped Ollama server or missing model is reported clearly, a
failed parse falls back to a neutral profile (so retrieval still runs), the
generation prompt forbids inventing songs, and every stage is logged.
"""

import json
import logging
import os
from typing import Dict, List, Tuple

from recommender import recommend_songs

logger = logging.getLogger("rag_recommender")

# Local model served by Ollama. Override with the OLLAMA_MODEL env var.
# llama3.2 is small (~2GB) and runs on a typical laptop. Pull it once with:
#     ollama pull llama3.2
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# Where the Ollama server listens. The ollama client also reads OLLAMA_HOST.
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# The catalog fields the parser is allowed to fill. Kept in sync with the CSV
# columns that score_song actually reads. Passed to Ollama as a JSON schema so
# the model returns structured, parseable output.
_PREF_SCHEMA = {
    "type": "object",
    "properties": {
        "genre": {"type": "string", "description": "e.g. lofi, pop, rock, ambient; '' if unspecified"},
        "mood": {"type": "string", "description": "e.g. chill, happy, focused, intense; '' if unspecified"},
        "energy": {"type": "number", "description": "0.0 (calm) to 1.0 (high energy)"},
        "valence": {"type": "number", "description": "0.0 (sad) to 1.0 (positive)"},
        "tempo_bpm": {"type": "number", "description": "beats per minute, ~60-180"},
        "danceability": {"type": "number", "description": "0.0 to 1.0"},
        "acousticness": {"type": "number", "description": "0.0 (electronic) to 1.0 (acoustic)"},
    },
    "required": ["genre", "mood", "energy", "valence", "tempo_bpm", "danceability", "acousticness"],
    "additionalProperties": False,
}

# A safe, neutral profile used when query parsing fails, so retrieval can still
# run rather than crashing the whole request.
_NEUTRAL_PREFS = {
    "genre": "", "mood": "", "energy": 0.5, "valence": 0.5,
    "tempo_bpm": 110, "danceability": 0.5, "acousticness": 0.5,
}


def _get_client():
    """
    Build an Ollama client and verify the server is running and the model is
    available — surfacing a clear, actionable message instead of a deep SDK
    stack trace.
    """
    try:
        import ollama
    except ImportError as exc:  # dependency not installed
        raise RuntimeError(
            "The 'ollama' package is required for the RAG feature. "
            "Install it with: pip install -r requirements.txt"
        ) from exc

    client = ollama.Client(host=HOST)

    # Is the server up?
    try:
        listed = client.list()
    except Exception as exc:  # noqa: BLE001 - connection refused, etc.
        raise RuntimeError(
            f"Could not reach the Ollama server at {HOST}. "
            "Install Ollama from https://ollama.com, then start it with:\n"
            "    ollama serve"
        ) from exc

    # Is the model pulled? (names look like 'llama3.2:latest')
    available = [m.model for m in listed.models]
    if not any(m == MODEL or m.split(":")[0] == MODEL.split(":")[0] for m in available):
        raise RuntimeError(
            f"Model '{MODEL}' is not installed in Ollama. Pull it once with:\n"
            f"    ollama pull {MODEL}\n"
            f"(or set OLLAMA_MODEL to one you already have: {', '.join(available) or 'none'})"
        )

    return client


def parse_query_to_prefs(query: str, client=None) -> Dict:
    """
    Stage 1: turn a free-text request into a user_prefs dict via a small,
    schema-constrained LLM call. Falls back to a neutral profile on any failure
    so the pipeline can still retrieve.
    """
    client = client or _get_client()
    logger.info("Parsing query into preferences: %r", query)

    try:
        response = client.chat(
            model=MODEL,
            format=_PREF_SCHEMA,  # constrain output to the schema (returns JSON)
            options={"temperature": 0},  # deterministic parsing
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You translate a listener's free-text request into numeric "
                        "music preferences. Infer sensible values for every field "
                        "from the request; use '' for a genre/mood the user did not "
                        "imply, and 0.5 / mid-tempo for numeric fields you cannot "
                        "infer. Respond with JSON only."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        prefs = json.loads(response["message"]["content"])
        logger.info("Parsed preferences: %s", prefs)
        return prefs
    except Exception as exc:  # noqa: BLE001 - fall back, never crash retrieval
        logger.warning("Query parse failed (%s); using neutral profile.", exc)
        return dict(_NEUTRAL_PREFS)


def _format_candidates(retrieved: List[Tuple[Dict, float, str]]) -> str:
    """Render retrieved songs as a compact, grounded context block for the LLM."""
    lines = []
    for i, (song, score, explanation) in enumerate(retrieved, start=1):
        lines.append(
            f"{i}. \"{song['title']}\" by {song['artist']} "
            f"[genre={song['genre']}, mood={song['mood']}, energy={song['energy']}, "
            f"tempo={song['tempo_bpm']}bpm, acousticness={song['acousticness']}] "
            f"— match {score:.0%}. Why it matched: {explanation}"
        )
    return "\n".join(lines)


def generate_grounded_answer(
    query: str,
    retrieved: List[Tuple[Dict, float, str]],
    client=None,
) -> str:
    """
    Stage 3: write a recommendation grounded ONLY in the retrieved songs. The
    system prompt forbids recommending anything outside the candidate list,
    which is what makes this RAG rather than free generation.
    """
    client = client or _get_client()

    if not retrieved:
        return "No songs in the catalog matched that request."

    candidates = _format_candidates(retrieved)
    logger.info("Generating grounded answer from %d candidates.", len(retrieved))

    system = (
        "You are a music recommender. You will be given a listener's request and "
        "a numbered list of CANDIDATE songs retrieved from the catalog. "
        "Recommend only from these candidates — never invent songs, artists, or "
        "titles not in the list. Reference songs by their exact title and artist. "
        "Briefly explain, per pick, why it fits the request, using the provided "
        "attributes. If none of the candidates genuinely fit, say so plainly "
        "instead of forcing a recommendation."
    )
    user = f"Listener request: {query}\n\nCANDIDATE songs:\n{candidates}"

    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response["message"]["content"]


def recommend_from_query(
    query: str,
    songs: List[Dict],
    k: int = 5,
    client=None,
) -> Dict:
    """
    Full RAG pipeline for one free-text request.

    Returns a dict with the intermediate artifacts so callers (and tests) can
    inspect each stage:
        {
          "query":     the original request,
          "prefs":     parsed user_prefs dict (stage 1),
          "retrieved": list of (song, score, explanation) (stage 2),
          "answer":    grounded natural-language recommendation (stage 3),
        }
    """
    client = client or _get_client()

    prefs = parse_query_to_prefs(query, client=client)
    retrieved = recommend_songs(prefs, songs, k=k)
    answer = generate_grounded_answer(query, retrieved, client=client)

    return {"query": query, "prefs": prefs, "retrieved": retrieved, "answer": answer}
