"""
Terminal demo / presentation-day fallback for StoryMatch.

Two modes:
  python cli_demo.py            -> interactive chat loop
  python cli_demo.py --scripted -> runs the fixed demo conversation from the
                                    research doc's "5-Minute Demo Strategy",
                                    unattended. Good to have as a recorded
                                    backup in case venue wifi/Bedrock hiccups
                                    during the live presentation.
"""

from __future__ import annotations

import sys

from storymatch.agent import build_agent

SCRIPTED_TURNS = [
    "I want a movie about people surviving after a civilization collapse. "
    "Small group. Lots of distrust and betrayal. Dark and realistic. More "
    "psychological than action. I want the ending to be depressing.",
    "I liked #2. Give me something even darker, but not horror.",
]


def run_turn(agent, text: str) -> None:
    print(f"\n\033[1mYOU:\033[0m {text}\n")
    print("\033[1mSTORYMATCH:\033[0m")
    result = agent(text)
    print(str(result).strip())

    tool_calls = [
        block["toolUse"]["name"]
        for msg in agent.messages
        for block in msg.get("content", [])
        if isinstance(block, dict) and "toolUse" in block
    ]
    if tool_calls:
        print(f"\n\033[2m[tool calls this turn: {' -> '.join(tool_calls[-8:])}]\033[0m")


def main() -> None:
    agent = build_agent()

    if "--scripted" in sys.argv:
        for turn in SCRIPTED_TURNS:
            run_turn(agent, turn)
        return

    print("StoryMatch Agent -- describe the story you want to experience.")
    print("(Ctrl+C or 'quit' to exit)\n")
    while True:
        try:
            text = input("\033[1mYOU:\033[0m ")
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if text.strip().lower() in {"quit", "exit"}:
            break
        if not text.strip():
            continue
        print("\n\033[1mSTORYMATCH:\033[0m")
        result = agent(text)
        print(str(result).strip())
        print()


if __name__ == "__main__":
    main()
