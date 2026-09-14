"""
StoryMatch demo UI (Streamlit).

Run with:  streamlit run app.py

This is intentionally thin: the agent's own markdown response (match
percentages, ASCII evidence bars, why-it-matches / why-it-may-not) IS the
UI. Streamlit just renders it and keeps the conversation + a visible tool
trace so judges can see the agent actually calling search_movies /
get_movie_details / update_taste_memory rather than just chatting.
"""

from __future__ import annotations

import streamlit as st

from storymatch.agent import build_agent

st.set_page_config(page_title="StoryMatch Agent", page_icon="\U0001f3ac", layout="centered")

st.title("\U0001f3ac StoryMatch Agent")
st.caption(
    "Don't search for a movie. Describe the story you want to experience."
)

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
    st.session_state.history = []  # list of (role, text)

with st.sidebar:
    st.subheader("Session")
    if st.button("Reset conversation"):
        st.session_state.agent = build_agent()
        st.session_state.history = []
        st.rerun()

    st.subheader("Why this is an agent, not a chatbot")
    st.markdown(
        "- Builds a structured **Narrative Fingerprint** from free text\n"
        "- Calls `search_movies` (retrieve → filter → verify → rank → diversify)\n"
        "- Calls `get_movie_details` to ground explanations in evidence\n"
        "- Calls `get_taste_memory` / `update_taste_memory` across turns\n"
        "- Re-plans the search when you give feedback"
    )

    st.subheader("Try")
    st.code(
        "I want a dark movie about survivors after a\n"
        "zombie apocalypse. Small group, lots of betrayal\n"
        "and distrust, more psychological than action,\n"
        "and I don't want a happy ending.",
        language=None,
    )

for role, text in st.session_state.history:
    with st.chat_message(role):
        st.markdown(text)

user_text = st.chat_input("Describe the story you want to experience...")

if user_text:
    st.session_state.history.append(("user", user_text))
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking through your story..."):
            result = st.session_state.agent(user_text)
            response_text = str(result)
        st.markdown(response_text)

        tool_calls = [
            block["toolUse"]["name"]
            for msg in st.session_state.agent.messages
            for block in msg.get("content", [])
            if isinstance(block, dict) and "toolUse" in block
        ]
        if tool_calls:
            st.caption("Tool calls this turn: " + " → ".join(tool_calls[-8:]))

    st.session_state.history.append(("assistant", response_text))
