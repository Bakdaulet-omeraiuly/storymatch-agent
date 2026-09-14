# Devpost submission draft -- StoryMatch Agent

Fill-in-ready draft for the "Agents for Humans" (Strands Agents) submission
form. Written from what was actually built and verified, not the doc's full
wishlist -- adjust only the AWS/Bedrock lines once verification clears.

## Tagline (one line)

Describe the story you want to experience -- StoryMatch turns it into a
narrative fingerprint, investigates a movie corpus, and tells you honestly
where each match holds up and where it doesn't.

## Inspiration

People don't think in genres, actors, or keywords. They think in stories:
"a small group turning on each other after civilization collapses,"
"someone slowly realizing their whole life is a lie." Every mainstream
search box -- streaming filters, a keyword field, even most "describe the
plot" tools -- makes you translate that back into database terms first.
Natural-language movie search already exists (AIMovieFinder, WhatFilmIs,
FindByVibe, and others); what we wanted to build was the part none of them
do: an agent that treats the description as a real investigation, not a
single embedding lookup.

## What it does

StoryMatch decomposes a free-form story request into a structured
**Narrative Fingerprint** -- setting, central conflict, relationships,
themes, tone, pacing, action intensity, required elements, things to
avoid -- then runs a Strands agent loop that:

- calls `search_movies`, a retrieve -> hard-filter -> verify -> rank ->
  diversify pipeline over an 82-film corpus tagged with derived narrative
  attributes (not raw plot embeddings);
- **adapts when the first pass comes back weak** -- relaxing constraints
  and re-searching on its own, rather than forcing a bad top-5;
- explains every result with a per-dimension evidence breakdown ("why it
  matches" / "why it may not"), never a bare percentage;
- **flags contradictory requests** ("slow psychological" + "nonstop
  action") and asks which should win, instead of averaging them into
  mush;
- answers **counterfactual questions** ("what if I remove the zombie
  requirement?") by dropping just that constraint and calling out which
  prior picks get weaker without it;
- remembers what a user likes and dislikes across turns via
  `get_taste_memory` / `update_taste_memory`, and folds it into later
  searches.

## How we built it

- **Strands Agents** drives the tool-use loop; the system prompt encodes
  the workflow (fingerprint extraction, contradiction/ambiguity checks,
  explanation format, feedback handling, memory hygiene) -- the LLM
  decides which of 4 tools to call and when, not a hardcoded pipeline.
- **`storymatch/dataset.py`** implements retrieval as structured-tag
  overlap + ordinal scoring (pacing/action intensity) instead of a vector
  DB, which keeps 82 movies fast, deterministic, and fully explainable --
  every match/mismatch traces to a literal tag, not a cosine similarity
  score no one can audit.
- **Model**: Amazon Bedrock (Claude, cross-region inference profile) as
  the primary path; a direct-Anthropic fallback (`STORYMATCH_MODEL_
  PROVIDER=anthropic`) let development and the transcript below happen
  while a brand-new AWS account's post-payment verification window was
  open.
- **Memory**: local JSON for the demo; a documented (unimplemented, by
  design) path to Bedrock AgentCore Memory is sketched in
  `storymatch/agentcore_memory.py` for anyone continuing this past the
  hackathon.

## Challenges we ran into

- A brand-new AWS account triggers a standard post-payment-method
  verification window during which every Bedrock model's daily token
  quota is held at zero (not visible or adjustable via Service Quotas) --
  cost real build time to diagnose across regions before the actual cause
  (not a permissions or code bug) became clear.
- Getting the ranking to renormalize sensibly when a user specifies only
  2-3 of the ~8 fingerprint dimensions, so an unmentioned dimension never
  silently drags the score down.
- Deciding the tool surface: more tools (one per retrieval stage) looked
  "more agentic" on paper but made function-calling less reliable in
  practice; collapsing retrieve/filter/verify/rank/diversify into one
  `search_movies` call, with a separate `get_movie_details` for deep
  dives, gave a genuine multi-tool loop without the model fumbling
  10+ parameters across 6 tools.

## Accomplishments we're proud of

The adaptive-retrieval transcript: given a narrow request the 82-film
corpus couldn't perfectly satisfy, the agent issued four `search_movies`
calls on its own -- relaxing the ending constraint, then group size --
before presenting results, and then said plainly *"the corpus doesn't have
a strong hit for this combination"* instead of overselling a mediocre
match. That honesty, not a lucky perfect match, is the actual product
differentiator.

## What we learned

Structured, agent-legible state (the Narrative Fingerprint, the per-tag
evidence) buys you more than a bigger model or a fancier vector store: it's
what lets the agent explain itself, detect its own contradictions, and
answer "what if" questions, none of which a single embedding-similarity
lookup can do.

## What's next

Wire the AgentCore Memory backend for real (sketch is in place, needs
Bedrock verified working), a Hidden-Gem popularity/narrative-fit slider,
and the 50-100 prompt evaluation benchmark from the design doc to turn
"looks good in a demo" into a measured retrieval/ranking system.

## Built with

`strands-agents`, `strands-agents-tools`, Amazon Bedrock, Anthropic Claude,
`boto3`, Streamlit, Python.
