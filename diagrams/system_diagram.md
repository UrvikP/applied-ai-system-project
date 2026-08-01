# System Diagram — Music Recommender (RAG + Content-Based Scorer)

This diagram shows the two entry paths (RAG mode and the profile demo), how a
request flows from input to output, and where testing / human review check the
AI's results.

```mermaid
flowchart TD
    %% ---------- Inputs ----------
    subgraph INPUT["Input"]
        Q["Free-text request<br/>(python src/main.py --ask ...)"]
        P["Hardcoded taste profiles<br/>(python src/main.py)"]
    end

    %% ---------- Knowledge base ----------
    CSV[("data/songs.csv<br/>song catalog / knowledge base")]

    %% ---------- RAG pipeline ----------
    subgraph RAG["RAG pipeline (src/rag_recommender.py)"]
        PARSE["1. Parse query -> user_prefs<br/>Local LLM via Ollama (schema-constrained)"]
        RETR["2. Retriever<br/>recommend_songs(): score + variety re-rank"]
        GEN["3. Generate grounded answer<br/>Local LLM (only from retrieved songs)"]
    end

    %% ---------- Deterministic core ----------
    subgraph CORE["Content-based core (src/recommender.py)"]
        SCORE["score_song() weighted closeness + mood bonus"]
    end

    %% ---------- Outputs ----------
    OUT_RAG["Grounded recommendation<br/>+ retrieved candidates"]
    OUT_DEMO["Ranked recommendations<br/>+ rule-based explanations"]

    %% ---------- Checking / guardrails ----------
    subgraph CHECK["Checking AI results"]
        GUARD{"Guardrails<br/>key/package check,<br/>neutral-profile fallback,<br/>grounding constraint,<br/>logging"}
        TESTS["Automated tests<br/>(tests/test_recommender.py, pytest)"]
        HUMAN["Human review<br/>edge-case profiles + reads grounded output"]
    end

    %% ---------- Flows ----------
    Q --> PARSE
    PARSE --> RETR
    CSV --> RETR
    RETR --> SCORE
    SCORE --> RETR
    RETR --> GEN
    GEN --> OUT_RAG

    P --> SCORE
    CSV --> SCORE
    SCORE --> OUT_DEMO

    PARSE -. validated by .-> GUARD
    GEN  -. validated by .-> GUARD
    GUARD --> OUT_RAG

    SCORE --- TESTS
    OUT_RAG --> HUMAN
    OUT_DEMO --> HUMAN
    HUMAN -. tunes weights / prompts .-> CORE
    HUMAN -. tunes prompts .-> RAG
```

## Legend

- **Input** — two entry points: a free-text request (RAG mode) or the built-in
  taste profiles (profile demo).
- **Retriever** — the existing `recommend_songs` scorer over `songs.csv`; it is
  reused as the RAG retriever so the AI feature is integrated, not bolted on.
- **Agent (LLM stages)** — a local LLM (via Ollama) parses the query (stage 1)
  and generates the final recommendation grounded only in retrieved songs
  (stage 3).
- **Evaluator / Tester** — `pytest` checks the deterministic scorer; guardrails
  validate the LLM stages at runtime (fallbacks, grounding, logging).
- **Human-in-the-loop** — a person runs adversarial edge-case profiles and reads
  the grounded output, then tunes feature weights and prompts.
