"""
Command line runner for the Music Recommender Simulation.

Two modes:

  * Profile demo (default): runs the hardcoded taste profiles below through the
    content-based scorer and prints ranked recommendations.

        python src/main.py

  * RAG mode: takes a free-text request and answers it with the Retrieval-
    Augmented Generation pipeline in rag_recommender.py — the scorer retrieves
    candidate songs, then Claude writes a grounded recommendation over them.

        export ANTHROPIC_API_KEY=sk-ant-...
        python src/main.py --ask "something calm for late-night coding"
        python src/main.py --ask          # interactive prompt
"""

import logging
import sys

from recommender import load_songs, recommend_songs, score_song


# -- Realistic taste profiles -------------------------------------------------
# Each is a coherent listener whose numeric targets, mood, and genre agree.

LATE_NIGHT_FOCUS = {
    "genre": "lofi", "mood": "focused",
    "energy": 0.40, "valence": 0.55, "tempo_bpm": 82,
    "danceability": 0.55, "acousticness": 0.80, "likes_acoustic": True,
}

HIGH_ENERGY_POP = {
    "genre": "pop", "mood": "intense",
    "energy": 0.93, "valence": 0.80, "tempo_bpm": 134,
    "danceability": 0.88, "acousticness": 0.05, "likes_acoustic": False,
}

CHILL_LOFI = {
    "genre": "lofi", "mood": "chill",
    "energy": 0.35, "valence": 0.60, "tempo_bpm": 74,
    "danceability": 0.55, "acousticness": 0.85, "likes_acoustic": True,
}

DEEP_INTENSE_ROCK = {
    "genre": "rock", "mood": "intense",
    "energy": 0.92, "valence": 0.45, "tempo_bpm": 155,
    "danceability": 0.66, "acousticness": 0.08, "likes_acoustic": False,
}

# -- Adversarial / edge-case profiles -----------------------------------------
# Deliberately built to stress or "trick" the scoring logic. See the notes on
# each for the surprising behavior it's meant to expose.

# CONTRADICTORY: asks for an "intense" mood but calm, quiet numbers. The mood
# bonus rewards an intense-tagged song even though every numeric target points
# the opposite way -- exposes that the +0.10 mood bonus can override features.
CONTRADICTORY_MOOD = {
    "genre": "ambient", "mood": "intense",
    "energy": 0.15, "valence": 0.50, "tempo_bpm": 60,
    "danceability": 0.30, "acousticness": 0.95, "likes_acoustic": True,
}

# OUT-OF-RANGE: energy/valence pushed past 1.0 and tempo past the clamp ceiling.
# closeness = 1 - |user - song| can go NEGATIVE when user values exceed [0,1],
# and the tempo clamp saturates so every song looks equally far on tempo.
OUT_OF_RANGE = {
    "genre": "pop", "mood": "happy",
    "energy": 2.0, "valence": 1.8, "tempo_bpm": 400,
    "danceability": 0.5, "acousticness": 0.5, "likes_acoustic": True,
}

# SPARSE: only one feature specified. Missing features are skipped, so the
# weighted sum uses < 1.0 of total weight -- scores are capped low and the
# ranking is decided by a single dimension.
SPARSE_PROFILE = {
    "mood": "happy",
    "energy": 0.90,
}

# ALL-NEUTRAL: every numeric target at 0.5 and a mood no song has. Nothing
# stands out, so scores bunch together and ties are broken by catalog order --
# exposes ordering/tie-break bias.
ALL_NEUTRAL = {
    "genre": "none", "mood": "nonexistent",
    "energy": 0.5, "valence": 0.5, "tempo_bpm": 130,
    "danceability": 0.5, "acousticness": 0.5, "likes_acoustic": True,
}

# Name -> profile. Comment out any you don't want to run.
PROFILES = {
    "Late-Night Focus": LATE_NIGHT_FOCUS,
    "High-Energy Pop": HIGH_ENERGY_POP,
    "Chill Lofi": CHILL_LOFI,
    "Deep Intense Rock": DEEP_INTENSE_ROCK,
    "[edge] Contradictory Mood": CONTRADICTORY_MOOD,
    "[edge] Out-of-Range Values": OUT_OF_RANGE,
    "[edge] Sparse Profile": SPARSE_PROFILE,
    "[edge] All-Neutral": ALL_NEUTRAL,
}


def print_recommendations(name: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    """Run the recommender for one profile and print a formatted report."""
    recommendations = recommend_songs(user_prefs, songs, k=k)

    header = f"{name}  |  Top {len(recommendations)} recommendations"
    print("\n" + header)
    print("=" * len(header))

    for rank, (song, score, _explanation) in enumerate(recommendations, start=1):
        # Pull the specific reason phrases straight from the scoring function.
        _score, reasons = score_song(user_prefs, song)

        print(f"\n{rank}. {song['title']} - {song['artist']}")
        print(f"   Match score: {score:.2f}  ({score * 100:.0f}%)")
        print("   Why this song:")
        for reason in reasons:
            print(f"     - it {reason}")


def run_profile_demo() -> None:
    """Default mode: run every taste profile through the content-based scorer."""
    songs = load_songs("data/songs.csv")

    for name, prefs in PROFILES.items():
        print_recommendations(name, prefs, songs)

    print()


def run_rag(query: str) -> None:
    """
    RAG mode: retrieve candidates with the existing scorer, then have Claude
    generate a recommendation grounded in those retrieved songs.
    """
    # Imported lazily so the profile demo has no hard dependency on the LLM stack.
    from rag_recommender import recommend_from_query

    songs = load_songs("data/songs.csv")

    try:
        result = recommend_from_query(query, songs, k=5)
    except RuntimeError as exc:
        # Setup problems (missing key / package) — report cleanly, don't stack-trace.
        print(f"\n[RAG unavailable] {exc}")
        return

    print(f"\nRequest: {result['query']}")
    print("=" * (9 + len(result["query"])))

    print("\nRetrieved candidates (via the content-based scorer):")
    for rank, (song, score, _explanation) in enumerate(result["retrieved"], start=1):
        print(f"  {rank}. {song['title']} - {song['artist']}  ({score:.0%} match)")

    print("\nRecommendation (grounded in the retrieved songs):\n")
    print(result["answer"])
    print()


def main() -> None:
    # Emit progress/guardrail logs from the RAG pipeline to stderr.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    args = sys.argv[1:]
    if args and args[0] == "--ask":
        query = " ".join(args[1:]).strip()
        if not query:
            query = input("Describe what you want to listen to: ").strip()
        if not query:
            print("No request given.")
            return
        run_rag(query)
    else:
        run_profile_demo()


if __name__ == "__main__":
    main()
