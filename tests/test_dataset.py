"""
Formalizes the manual sanity checks run during development into pytest.

Covers the parts of storymatch that don't need a live model: the dataset
schema and the retrieve/filter/verify/rank/diversify/hidden-gem pipeline in
dataset.py. Agent behavior (contradiction detection, counterfactual
queries, story mutation) needs a live LLM and was verified manually against
both Bedrock and the Anthropic API -- see README.md's "Verified beyond the
base loop" section for those transcripts.
"""

from __future__ import annotations

from storymatch import dataset

REQUIRED_FIELDS = [
    "id",
    "title",
    "year",
    "genres",
    "setting",
    "threat",
    "central_conflict",
    "relationships",
    "themes",
    "tone",
    "pacing",
    "action_intensity",
    "ending",
    "popularity",
    "overview",
]


def test_movies_load():
    movies = dataset.load_movies()
    assert len(movies) >= 40


def test_no_duplicate_ids():
    movies = dataset.load_movies()
    ids = [m["id"] for m in movies]
    assert len(ids) == len(set(ids))


def test_every_movie_has_the_full_schema():
    for movie in dataset.load_movies():
        for field in REQUIRED_FIELDS:
            assert field in movie, f"{movie.get('id')} is missing '{field}'"


def test_get_movie_by_id_round_trips():
    movies = dataset.load_movies()
    sample = movies[0]
    assert dataset.get_movie(sample["id"])["title"] == sample["title"]


def test_get_movie_missing_id_returns_none():
    assert dataset.get_movie("does_not_exist") is None


def test_avoid_elements_excludes_matching_genre():
    """A comedy explicitly avoided must be excluded, not just down-ranked."""
    hangover = dataset.get_movie("the_hangover")
    scored = dataset.score_movie(hangover, avoid_elements=["comedy"])
    assert scored["excluded"] is True
    assert scored["overall_score"] == 0


def test_avoid_happy_ending_excludes_hopeful_films():
    avengers = dataset.get_movie("the_avengers")
    scored = dataset.score_movie(avengers, avoid_elements=["happy ending"])
    assert scored["excluded"] is True


def test_search_respects_required_elements_and_ranks_by_fit():
    results = dataset.search(
        setting=["post-apocalyptic"],
        central_conflict=["survival", "betrayal"],
        tone=["dark", "psychological"],
        pacing="slow",
        action_intensity="low",
        required_elements=["betrayal"],
        avoid_elements=["happy ending", "comedy"],
        top_n=5,
    )
    assert 1 <= len(results) <= 5
    scores = [r["overall_score"] for r in results]
    assert scores == sorted(scores, reverse=True), "results must be ranked highest-first"
    for r in results:
        assert r["excluded"] is False


def test_search_returns_evidence_for_explanations():
    results = dataset.search(themes=["human nature"], tone=["dark"], top_n=3)
    for r in results:
        assert "matched_evidence" in r
        assert "missing_evidence" in r


def test_diversity_pass_avoids_five_genre_clones():
    """Doc's 'Diversity Matters': top results shouldn't all share one genre."""
    results = dataset.search(tone=["dark"], top_n=5, diversify=True)
    all_genres = [g for r in results for g in r["genres"]]
    most_common_count = max(all_genres.count(g) for g in set(all_genres))
    assert most_common_count < len(results), "diversity pass should break up genre monoculture"


def test_hidden_gem_mode_favors_low_popularity_titles():
    balanced = dataset.search(themes=["identity"], tone=["dark"], top_n=5)
    gems = dataset.search(
        themes=["identity"], tone=["dark"], top_n=5, prioritize_hidden_gems=True
    )
    balanced_pop = [r["popularity"] for r in balanced]
    gems_pop = [r["popularity"] for r in gems]

    def score(pops):
        weight = {"low": 2, "medium": 1, "high": 0}
        return sum(weight.get(p, 0) for p in pops)

    assert score(gems_pop) >= score(balanced_pop)
    assert any(r.get("hidden_gem") for r in gems if r["popularity"] == "low") or not any(
        p == "low" for p in gems_pop
    )
