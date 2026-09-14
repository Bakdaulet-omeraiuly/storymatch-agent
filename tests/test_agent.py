"""
Structural checks that don't call a live model: the Agent builds with the
right tools wired in. Behavioral correctness (contradiction detection,
counterfactual queries, story mutation, adaptive retrieval) needs a real
LLM and was verified manually -- see README.md.
"""

from __future__ import annotations

import os

os.environ.setdefault("STORYMATCH_MODEL_PROVIDER", "bedrock")

from storymatch.agent import build_agent  # noqa: E402

EXPECTED_TOOLS = {"search_movies", "get_movie_details", "get_taste_memory", "update_taste_memory"}


def test_agent_builds_with_expected_tools():
    agent = build_agent()
    assert set(agent.tool_names) == EXPECTED_TOOLS


def test_agent_has_no_default_stdout_callback():
    """Regression test: Strands' default PrintingCallbackHandler double-
    prints every response (streamed once, then again from str(result)) in
    cli_demo.py -- build_agent() must opt out of it."""
    from strands.handlers.callback_handler import PrintingCallbackHandler

    agent = build_agent()
    assert not isinstance(agent.callback_handler, PrintingCallbackHandler)
