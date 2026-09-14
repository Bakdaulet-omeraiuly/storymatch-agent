"""
Bedrock AgentCore Memory backend -- SKETCH, NOT WIRED IN, NOT VERIFIED.

Written while Bedrock model access was blocked by AWS account verification,
so this has not been run against a live AgentCore Memory resource. Treat it
as a documented starting point, not a working feature.

Why this exists: the research doc positions persistent, cross-session
narrative taste memory as a real product differentiator, and Amazon Bedrock
AgentCore Memory is the "do it properly on AWS" version of what
storymatch/memory.py currently does with a local JSON file. This module
sketches that swap without touching the proven-working local-JSON path.

What's needed to actually turn this on (do this AFTER Bedrock access is
confirmed working -- see README's status section):

1. `pip install bedrock-agentcore` (the AgentCore Python SDK -- confirm the
   exact package name in current AWS docs, it has moved before).
2. Create a Memory resource once, e.g.:
     aws bedrock-agentcore-control create-memory \
       --name storymatch-taste-memory \
       --event-expiry-duration "P90D" \
       --memory-strategies '[{"userPreferenceMemoryStrategy": {"name": "narrative-taste"}}]'
   and note the returned memory ID (put it in .env as
   STORYMATCH_AGENTCORE_MEMORY_ID).
3. Implement get_profile/update_profile below for real using the SDK's
   MemoryClient (create_event to record a turn, retrieve_memories or
   list_events to read back extracted preferences for a given actor/session
   ID). The exact method names are the part most likely to have drifted --
   check https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ at
   build time rather than trusting this comment.
4. In storymatch/tools.py, swap the `from storymatch import memory` import
   for `from storymatch import agentcore_memory as memory` -- the two
   modules are meant to expose the same get_profile/update_profile/
   reset_profile function signatures so nothing else has to change.
5. Test standalone (write a profile, read it back in a fresh process)
   BEFORE wiring it into a live demo. A memory backend that silently no-ops
   is worse than the local JSON file it replaced.

Until all five steps are done and verified, storymatch/memory.py (local
JSON) remains the default and is what's actually running the demo.
"""

from __future__ import annotations

import os


class AgentCoreMemoryNotConfigured(RuntimeError):
    """Raised when this backend is used before the setup steps above are done."""


def _require_memory_id() -> str:
    memory_id = os.environ.get("STORYMATCH_AGENTCORE_MEMORY_ID")
    if not memory_id:
        raise AgentCoreMemoryNotConfigured(
            "STORYMATCH_AGENTCORE_MEMORY_ID is not set -- this backend is a sketch, "
            "not wired up. See the module docstring for the setup steps, or use "
            "storymatch.memory (local JSON) instead."
        )
    return memory_id


def get_profile(user_id: str) -> dict[str, list[str]]:
    """Mirrors storymatch.memory.get_profile's signature -- NOT implemented."""
    _require_memory_id()
    raise NotImplementedError(
        "AgentCore Memory read path is sketched but not implemented/verified. "
        "See storymatch/agentcore_memory.py docstring, step 3."
    )


def update_profile(user_id: str, likes: list[str], dislikes: list[str]) -> dict[str, list[str]]:
    """Mirrors storymatch.memory.update_profile's signature -- NOT implemented."""
    _require_memory_id()
    raise NotImplementedError(
        "AgentCore Memory write path is sketched but not implemented/verified. "
        "See storymatch/agentcore_memory.py docstring, step 3."
    )


def reset_profile(user_id: str) -> None:
    _require_memory_id()
    raise NotImplementedError("Not implemented -- see module docstring.")
