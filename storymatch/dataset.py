"""
Movie dataset + narrative scoring engine for StoryMatch.

This is the "derived narrative representation" layer described in the
research doc: every movie is pre-tagged with structured narrative attributes
(setting, threat, conflict, relationships, themes, tone, pacing, action
intensity, ending type). Retrieval + verification + ranking all operate on
these structured tags instead of raw embeddings, which keeps the pipeline
fast, explainable, and dependency-free for a hackathon demo.

Swap-in path for later: replace `_overlap_score` with a Bedrock Titan
embedding cosine-similarity stage for the broad-retrieval pass, and keep this
module's verification/ranking/evidence logic as Stage 3-4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "movies.json"

# Ordinal scales so "less action" / "slower pacing" requests can be scored
# gracefully instead of requiring an exact string match.
_ORDINAL = {"low": 0, "slow": 0, "medium": 1, "high": 2, "fast": 2}

# Dimension weights for the final narrative-fit score. Mirrors the
# `FinalScore` formula in the research doc, simplified to what the dataset
# actually carries. Renormalized at scoring time over dimensions the user
# actually specified, so an unspecified dimension never drags the score down.
_WEIGHTS = {
    "setting": 0.12,
    "threat": 0.10,
    "central_conflict": 0.18,
    "relationships": 0.10,
    "themes": 0.18,
    "tone": 0.14,
    "pacing": 0.09,
    "action_intensity": 0.09,
}

_LIST_FIELDS = ("setting", "threat", "central_conflict", "relationships", "themes", "tone")
_SCALAR_FIELDS = ("pacing", "action_intensity")

# Free-text fields we scan when checking hard "avoid" exclusions, since a
# user might say "avoid comedy" (a genre) or "avoid happy ending" (not a
# list field at all).
_AVOID_SCAN_FIELDS = ("genres", "setting", "threat", "central_conflict", "themes", "tone")

_HAPPY_ENDINGS = {"hopeful", "bittersweet_hopeful", "ambiguous_hopeful"}
_UNHAPPY_ENDING_TERMS = ("tragic", "bleak", "dark")


def load_movies() -> list[dict[str, Any]]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


_MOVIES_BY_ID: dict[str, dict[str, Any]] | None = None


def _index() -> dict[str, dict[str, Any]]:
    global _MOVIES_BY_ID
    if _MOVIES_BY_ID is None:
        _MOVIES_BY_ID = {m["id"]: m for m in load_movies()}
    return _MOVIES_BY_ID


def get_movie(movie_id: str) -> dict[str, Any] | None:
    return _index().get(movie_id)


def _norm_list(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {v.strip().lower().replace(" ", "_") for v in values if v and v.strip()}


def _list_overlap(requested: set[str], present: set[str]) -> tuple[float, set[str], set[str]]:
    """Returns (score 0..1, matched, missing) for one list-type dimension."""
    if not requested:
        return (None, set(), set())  # dimension not requested -> skip
    matched = requested & present
    missing = requested - present
    return (len(matched) / len(requested), matched, missing)


def _scalar_closeness(requested: str | None, present: str | None) -> float | None:
    if not requested:
        return None
    requested = requested.strip().lower()
    if requested not in _ORDINAL or not present:
        return None
    present = present.strip().lower()
    if present not in _ORDINAL:
        return None
    dist = abs(_ORDINAL[requested] - _ORDINAL[present])
    return max(0.0, 1.0 - dist / 2.0)


def _hits_avoid(movie: dict[str, Any], avoid_terms: set[str]) -> set[str]:
    """Hard-exclusion check: does the movie contain any avoided keyword?"""
    if not avoid_terms:
        return set()
    hits: set[str] = set()
    haystack: set[str] = set()
    for field in _AVOID_SCAN_FIELDS:
        haystack |= _norm_list(movie.get(field))
    for term in avoid_terms:
        t = term.strip().lower().replace(" ", "_")
        if t in haystack:
            hits.add(term)
        if "happy" in t and "ending" in t and movie.get("ending") in _HAPPY_ENDINGS:
            hits.add(term)
        if any(u in t for u in ("sad", "tragic", "bleak", "depressing")) and any(
            u in (movie.get("ending") or "") for u in _UNHAPPY_ENDING_TERMS
        ):
            hits.add(term)
    return hits


def score_movie(
    movie: dict[str, Any],
    *,
    setting: list[str] | None = None,
    threat: list[str] | None = None,
    central_conflict: list[str] | None = None,
    relationships: list[str] | None = None,
    themes: list[str] | None = None,
    tone: list[str] | None = None,
    pacing: str | None = None,
    action_intensity: str | None = None,
    required_elements: list[str] | None = None,
    avoid_elements: list[str] | None = None,
) -> dict[str, Any]:
    """
    Score one movie against a (partial) narrative fingerprint.

    Returns a dict with: overall_score (0-100), excluded (bool),
    excluded_reasons, per_dimension scores, matched evidence, and missing
    (mismatch) tags -- the raw material for the agent's "why it matches /
    why it may not" explanation.
    """
    avoid_hits = _hits_avoid(movie, _norm_list(avoid_elements))
    requested_dims = {
        "setting": setting,
        "threat": threat,
        "central_conflict": central_conflict,
        "relationships": relationships,
        "themes": themes,
        "tone": tone,
    }

    per_dimension: dict[str, float] = {}
    matched_evidence: dict[str, list[str]] = {}
    missing_evidence: dict[str, list[str]] = {}

    for dim in _LIST_FIELDS:
        req = _norm_list(requested_dims.get(dim))
        present = _norm_list(movie.get(dim))
        score, matched, missing = _list_overlap(req, present)
        if score is not None:
            per_dimension[dim] = round(score * 100)
            matched_evidence[dim] = sorted(matched)
            missing_evidence[dim] = sorted(missing)

    pacing_score = _scalar_closeness(pacing, movie.get("pacing"))
    if pacing_score is not None:
        per_dimension["pacing"] = round(pacing_score * 100)

    action_score = _scalar_closeness(action_intensity, movie.get("action_intensity"))
    if action_score is not None:
        per_dimension["action_intensity"] = round(action_score * 100)

    # required_elements are checked across ALL list fields at once (a
    # "required" tag like betrayal might live under relationships OR
    # central_conflict depending on the movie).
    required_norm = _norm_list(required_elements)
    required_matched, required_missing = set(), set()
    if required_norm:
        all_movie_tags = set()
        for f in _LIST_FIELDS:
            all_movie_tags |= _norm_list(movie.get(f))
        required_matched = required_norm & all_movie_tags
        required_missing = required_norm - all_movie_tags
        req_score = len(required_matched) / len(required_norm)
        per_dimension["required_elements"] = round(req_score * 100)
        matched_evidence["required_elements"] = sorted(required_matched)
        missing_evidence["required_elements"] = sorted(required_missing)

    # Weighted overall score, renormalized over dimensions actually present.
    weighted_sum = 0.0
    weight_total = 0.0
    for dim, weight in _WEIGHTS.items():
        if dim in per_dimension:
            weighted_sum += (per_dimension[dim] / 100.0) * weight
            weight_total += weight
    # required_elements counts extra-heavy when specified (it's a hard ask).
    if "required_elements" in per_dimension:
        req_weight = 0.25
        weighted_sum += (per_dimension["required_elements"] / 100.0) * req_weight
        weight_total += req_weight

    overall = round((weighted_sum / weight_total) * 100) if weight_total > 0 else 50

    excluded = bool(avoid_hits) or bool(required_norm and not required_matched and required_norm)
    if avoid_hits:
        overall = 0

    return {
        "movie_id": movie["id"],
        "title": movie["title"],
        "year": movie["year"],
        "overall_score": overall,
        "excluded": excluded,
        "excluded_reasons": sorted(avoid_hits),
        "per_dimension": per_dimension,
        "matched_evidence": matched_evidence,
        "missing_evidence": missing_evidence,
        "genres": movie.get("genres", []),
        "ending": movie.get("ending"),
        "popularity": movie.get("popularity"),
        "overview": movie.get("overview"),
    }


def search(
    *,
    top_n: int = 8,
    diversify: bool = True,
    **fingerprint_kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Stage 1-4 in one call: broad retrieval + hard-avoid filtering +
    narrative scoring + diversity-aware ranking.
    """
    scored = [score_movie(m, **fingerprint_kwargs) for m in load_movies()]
    candidates = [s for s in scored if not s["excluded"]]
    candidates.sort(key=lambda s: s["overall_score"], reverse=True)

    if not diversify or len(candidates) <= top_n:
        return candidates[:top_n]

    # Greedy diversity pass: after the top pick, penalize candidates that
    # share a genre with an already-selected movie so the result set spans
    # a spectrum instead of five near-clones (research doc, "Diversity
    # Matters").
    selected: list[dict[str, Any]] = []
    remaining = candidates[:]
    while remaining and len(selected) < top_n:
        if not selected:
            pick = remaining.pop(0)
            selected.append(pick)
            continue

        used_genres = {g for s in selected for g in s["genres"]}

        def adjusted(cand: dict[str, Any]) -> float:
            overlap_penalty = len(used_genres & set(cand["genres"])) * 6
            return cand["overall_score"] - overlap_penalty

        remaining.sort(key=adjusted, reverse=True)
        selected.append(remaining.pop(0))

    if len(selected) == top_n and len(candidates) > top_n:
        selected[-1] = {**selected[-1], "tag": "wildcard_pick"}

    return selected
