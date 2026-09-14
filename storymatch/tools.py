"""
Strands tools for the StoryMatch agent.

Kept to four tools on purpose: enough to force a genuine multi-step,
tool-using agent loop (search -> inspect -> remember) without an oversized
tool surface that's harder for the model to call reliably in a live demo.

  1. search_movies      -- Stage 1-4 retrieval/verify/rank pipeline
  2. get_movie_details   -- metadata lookup for one candidate
  3. get_taste_memory     -- read what this user has liked/disliked before
  4. update_taste_memory  -- persist newly learned likes/dislikes

The LLM is responsible for building the Narrative Fingerprint from the
user's free text and deciding which tools to call and when -- that
reasoning happens in the agent's system prompt (see agent.py), not in this
file.
"""

from __future__ import annotations

from typing import List, Optional

from strands import tool

from storymatch import dataset, memory


@tool
def search_movies(
    setting: Optional[List[str]] = None,
    threat: Optional[List[str]] = None,
    central_conflict: Optional[List[str]] = None,
    relationships: Optional[List[str]] = None,
    themes: Optional[List[str]] = None,
    tone: Optional[List[str]] = None,
    pacing: Optional[str] = None,
    action_intensity: Optional[str] = None,
    required_elements: Optional[List[str]] = None,
    avoid_elements: Optional[List[str]] = None,
    top_n: int = 5,
    prioritize_hidden_gems: bool = False,
) -> dict:
    """Search the movie corpus using a structured Narrative Fingerprint.

    This runs the full retrieve -> hard-filter -> verify -> rank ->
    diversify pipeline in one call and returns ranked candidates with a
    per-dimension score breakdown and matched/missing evidence tags, so you
    can explain *why* each result matches or doesn't.

    Use short, lowercase, snake_case tags for every list argument (e.g.
    "post-apocalyptic", "betrayal", "psychological", "slow_burn") drawn
    from how the user actually described the story -- do not invent movie
    titles or genres that weren't implied by the request.

    Args:
        setting: Where/when the story takes place (e.g. ["post-apocalyptic", "urban"]).
        threat: The antagonistic force (e.g. ["zombies", "societal collapse"]).
        central_conflict: The core dramatic conflict (e.g. ["survival", "betrayal"]).
        relationships: Key relationship dynamics (e.g. ["group tension", "father-daughter"]).
        themes: Underlying themes (e.g. ["human nature", "trust"]).
        tone: Emotional/stylistic tone (e.g. ["dark", "psychological"]).
        pacing: One of "slow", "medium", "fast".
        action_intensity: One of "low", "medium", "high".
        required_elements: Tags that MUST be present (hard requirement, heavily weighted).
        avoid_elements: Tags that MUST NOT be present (e.g. ["happy ending", "comedy"]) -- movies hitting these are excluded entirely, not just down-ranked.
        top_n: How many ranked results to return (default 5).
        prioritize_hidden_gems: Set True only when the user asks to ignore popularity or explicitly wants an obscure/underrated pick -- nudges ranking toward narrative fit over fame instead of the default balance.
    """
    results = dataset.search(
        setting=setting,
        threat=threat,
        central_conflict=central_conflict,
        relationships=relationships,
        themes=themes,
        tone=tone,
        pacing=pacing,
        action_intensity=action_intensity,
        required_elements=required_elements,
        avoid_elements=avoid_elements,
        top_n=top_n,
        prioritize_hidden_gems=prioritize_hidden_gems,
    )
    return {"count": len(results), "candidates": results}


@tool
def get_movie_details(movie_id: str) -> dict:
    """Look up full metadata for one movie by its id (as returned by search_movies).

    Args:
        movie_id: The movie's id, e.g. "train_to_busan".
    """
    movie = dataset.get_movie(movie_id)
    if not movie:
        return {"status": "error", "content": [{"text": f"No movie found with id '{movie_id}'."}]}
    return movie


@tool
def get_taste_memory(user_id: str = "demo_user") -> dict:
    """Read this user's previously learned narrative taste (likes/dislikes).

    Call this near the start of a conversation so results can already be
    steered by what this person has liked or rejected before.

    Args:
        user_id: Identifier for the user/session (default "demo_user").
    """
    return memory.get_profile(user_id)


@tool
def update_taste_memory(
    likes: Optional[List[str]] = None,
    dislikes: Optional[List[str]] = None,
    user_id: str = "demo_user",
) -> dict:
    """Persist newly learned narrative preferences for this user.

    Call this after the user reacts to results or gives feedback (e.g.
    "I liked #2", "too much action", "no more horror") so future
    conversations -- and later turns in this one -- benefit from it.

    Args:
        likes: Narrative tags the user showed a preference for (e.g. ["psychological tension", "dark ending"]).
        dislikes: Narrative tags the user showed dislike for (e.g. ["superhero action", "happy ending"]).
        user_id: Identifier for the user/session (default "demo_user").
    """
    return memory.update_profile(user_id, likes or [], dislikes or [])
