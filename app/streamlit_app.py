"""Streamlit UI — entry point.

Run with:
    streamlit run app/streamlit_app.py

This is the Sprint-1 skeleton: it loads env, shows the three-column layout,
and renders placeholders. Each sprint fills in one column.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable without installing the package — convenient during dev.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
import streamlit as st  # noqa: E402

load_dotenv()

st.set_page_config(page_title="Metaphor Machine", layout="wide", page_icon="🎭")

st.title("🎭 Metaphor Machine")
st.caption(
    "Map your problem into a metaphor → explore solutions there → translate back. "
    "Course project, Applied Generative AI SS26."
)

with st.sidebar:
    st.header("Model")
    st.text_input("Model", value="anthropic/claude-sonnet-4-6", key="model")
    st.slider("Temperature (default)", 0.0, 1.5, 0.7, 0.1, key="temperature")
    st.divider()
    st.caption("Per-agent overrides will appear here in Sprint 2.")

chat_col, structure_col, timeline_col = st.columns([3, 3, 2])

with chat_col:
    st.subheader("Conversation")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Describe your problem..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.info(
                "🚧 Skeleton only — the Definer agent runs here in Sprint 1.\n\n"
                "See `PLAN.md` for the full plan."
            )

with structure_col:
    st.subheader("Problem structure")
    st.caption("Editable ProblemSpec / MetaphorSpec appears here.")
    st.code(
        "{\n  'entities': [],\n  'relations': [],\n  'constraints': [],\n  'goals': []\n}",
        language="json",
    )

with timeline_col:
    st.subheader("Session")
    st.caption("Pipeline progress + 🎲 'try another metaphor'.")
    st.progress(0, text="Waiting for input")
