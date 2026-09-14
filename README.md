# StoryMatch Agent

> Don't search for a movie. Describe the story you want to experience.

An agentic narrative-discovery system built on **Strands Agents** + **Amazon
Bedrock**. Converts a free-form story description into a structured
**Narrative Fingerprint**, searches a curated movie corpus, verifies
evidence, ranks candidates, explains matches/mismatches, and refines on
feedback. Built for the "Agents for Humans" (Strands Agents) hackathon --
see `../StoryMatch_Agent_Research.md` on the Desktop for the full product
research doc this scaffold implements.

## ⚠️ Status: AWS Bedrock pending account verification

Timeline so far (account `034456343698`, `us-east-1`):

1. Bedrock initially denied every model (Claude, Nova) with
   `INVALID_PAYMENT_INSTRUMENT` -- no valid card on the account. Fixed by
   adding a payment method in Billing -> Payment preferences.
2. After that, Bedrock switched to `ThrottlingException: Too many tokens
   per day`. Root cause (confirmed via Service Quotas API): adding/changing
   a payment method triggers a standard **AWS account verification** step
   (a `us-east-2` call surfaced the explicit message: *"Your account is
   currently being verified. Verification normally takes less than 2
   hours."*). During verification, Bedrock's daily token quota for every
   model sits at a hard **0** and cannot be raised manually (`Service
   Quotas` confirms these particular quotas are not adjustable) -- it lifts
   automatically once verification finishes.
3. **Nothing to do but wait it out** (typically <2h, occasionally longer
   for brand-new accounts). Re-check with:

```bash
source .venv/bin/activate
python -c "
import boto3
c = boto3.client('bedrock-runtime', region_name='us-east-1')
r = c.converse(modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                messages=[{'role':'user','content':[{'text':'Reply with exactly: OK'}]}])
print(r['output']['message']['content'])
"
```

**This did not block the build.** The whole agent is verified working
end-to-end right now via `STORYMATCH_MODEL_PROVIDER=anthropic` (direct
Anthropic API) -- ran the full two-turn scripted demo successfully,
including the agent adaptively relaxing search constraints across multiple
`search_movies` calls when the first attempt came back empty, and honestly
reporting when the 82-movie corpus has no great match instead of
overselling a mediocre one. Switch back to `bedrock` (or unset the env var)
once verification clears -- that's what the hackathon rubric rewards.

## What's actually built (MVP)

- **`data/movies.json`** -- 82 hand-curated films (including superhero,
  rom-com, and straight-comedy titles specifically so `avoid_elements`
  exclusions have something real to filter out), each pre-tagged with a
  derived narrative representation: setting, threat, protagonist,
  central_conflict, relationships, themes, tone, pacing, action_intensity,
  ending type. This is the "Derived Narrative Representation" layer from
  the research doc (section 16) -- the actual product differentiation.
- **`storymatch/dataset.py`** -- the retrieve -> hard-filter (avoid
  exclusions) -> verify (per-dimension evidence) -> rank -> diversify
  pipeline (sections 17-19 of the doc), pure Python, no vector DB needed
  for 40 movies.
- **`storymatch/memory.py`** -- local JSON taste memory (likes/dislikes per
  user). Upgrade path to Bedrock AgentCore Memory documented inline.
- **`storymatch/tools.py`** -- 4 Strands `@tool` functions: `search_movies`,
  `get_movie_details`, `get_taste_memory`, `update_taste_memory`.
- **`storymatch/agent.py`** -- the Strands `Agent`, wired to Bedrock (or
  Anthropic as a fallback), with a system prompt that encodes the full
  workflow: fingerprint extraction, contradiction detection, ambiguity
  clarification, evidence-grounded explanation, feedback-driven
  refinement, and quiet taste-memory updates.
- **`app.py`** -- Streamlit chat UI. The agent's own markdown response
  (match %, ASCII evidence bars, why-it-matches/why-it-may-not) *is* the
  UI; Streamlit just renders it and shows the tool-call trace so judges can
  see the agent actually doing multi-step work.
- **`cli_demo.py`** -- terminal fallback, including a `--scripted` mode
  that replays the doc's example conversation unattended (recorded backup
  in case venue wifi or Bedrock hiccups during the live demo).

## Verified beyond the base loop

These aren't just in the system prompt -- each was run against a live model
(Anthropic API, while Bedrock was blocked) and behaved correctly with no
extra tool code, because Claude's own reasoning plus the workflow
instructions in `agent.py`'s `SYSTEM_PROMPT` cover them:

- **Contradiction detection** (doc's killer feature #6) -- asked for "a
  slow, quiet psychological drama, but also nonstop explosive action the
  whole time" and the agent stopped and asked which should take priority
  *before* searching, instead of averaging the two into a mediocre query.
- **Counterfactual search** (doc's killer feature #8) -- after getting
  zombie-survival results, asked "what if I remove the zombie requirement
  entirely?" and the agent re-ran the search with only that constraint
  dropped, and explicitly called out which prior picks got weaker without
  it (e.g. "Train to Busan -- zombies, you just dropped that").
- **Adaptive retrieval** -- when the first `search_movies` call for a
  narrow request came back with poor matches, the agent relaxed
  constraints (ending type, then group size) across several more
  `search_movies` calls on its own before presenting results, rather than
  forcing a bad top-5. This is the strongest "this is actually an agent,
  not a wrapper" evidence -- see the case-file artifact's Exhibit C/D.

## What's deliberately NOT built yet (stretch, section 27 of the doc)

Cut for time -- add only if the MVP demo is solid and there are hours left:

- Hidden Gem / popularity-vs-narrative-fit slider -- `popularity` is on
  every movie record but not yet used in ranking.
- **Bedrock AgentCore Memory** -- `storymatch/agentcore_memory.py` has a
  documented sketch (setup steps, what to implement) but it's
  `NotImplementedError` by design: it was written while Bedrock access was
  blocked, so it's unverified and NOT wired into `tools.py`. The proven
  local-JSON `storymatch/memory.py` is what the demo actually runs on. Only
  flip the switch (see that file's docstring) after testing the AgentCore
  path standalone -- a silently-broken memory backend is worse than the
  file it replaced.
- AgentCore Runtime deployment -- running locally only. Doc section 22 has
  the target architecture if there's time to deploy.
- The 50-100 prompt evaluation benchmark (doc section 30).

## Setup

```bash
cd StoryMatch-Agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit if needed
```

AWS credentials are read from `~/.aws/credentials` (`default` profile is
already configured, region `us-east-1`) -- nothing else to set up for
Bedrock once the payment-instrument issue above is fixed.

## Run

```bash
source .venv/bin/activate

# Web demo
streamlit run app.py

# Terminal demo
python cli_demo.py                # interactive
python cli_demo.py --scripted     # unattended, matches the doc's demo script

# Local dev without waiting on AWS billing:
STORYMATCH_MODEL_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... streamlit run app.py
```

Reset taste memory between demo runs: `rm data/taste_memory.json`.

## Try this in the demo

```
I want a dark movie about survivors after a zombie apocalypse. Small
group, lots of betrayal and distrust, more psychological than action,
and I don't want a happy ending.
```

Then: `"I liked #2. Give me something even darker, but not horror."`

This exercises the full loop: fingerprint extraction -> `search_movies` ->
ranked results with evidence -> feedback -> refined `search_movies` call ->
`update_taste_memory`. That two-turn loop is the core "agency" proof point
for judges -- see doc section 21, "Why This Is Actually an Agent."

## Architecture

```
User story (free text)
       |
       v
Strands Agent (Bedrock Claude)  <-- system_prompt encodes the whole
       |                             workflow: fingerprint, contradiction/
       |  tool calls                 ambiguity checks, explanation style,
       v                             feedback handling, memory hygiene
 get_taste_memory
 search_movies  --> storymatch/dataset.py: retrieve -> hard filter
                     (avoid_elements) -> per-dimension verify -> weighted
                     rank -> greedy diversity pass
 get_movie_details
 update_taste_memory --> storymatch/memory.py: local JSON, per user_id
       |
       v
Markdown response: match %, ASCII evidence bars, why/why-not, ask for
feedback
```

## Extending the dataset

82 movies is enough for a convincing demo across the query types in the
doc (post-apocalyptic survival, psychological thrillers, simulated-reality
sci-fi, tragic romance, folk horror, dystopian survival games, war drama,
heist/crime, superhero/comedy for exclusion testing). To grow it further:
add entries to `data/movies.json` following the existing schema, or write a
`data/prep_dataset.py` that pulls from TMDb (metadata + overview) and asks
a Bedrock model to derive the narrative tags in batch -- the doc's
recommended data strategy (section 16). Not built here to avoid needing a
TMDb API key as a hard dependency for the MVP demo.

## Pitch (for the submission form)

> People don't think in genres. They think in stories. StoryMatch is an
> agent that turns an imagined story into a searchable narrative
> fingerprint, investigates a movie corpus, verifies the story fit, and
> learns what kinds of stories you actually like.
