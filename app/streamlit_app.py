"""Streamlit UI - entry point.

Run with:
    streamlit run app/streamlit_app.py

Sprint 1 status: Definer wired up end-to-end. Chat input -> Pipeline.run_definer
-> ProblemSpec rendered live in the structure panel. Mock mode supported via
METAPHOR_MOCK=1 (so the UI is usable without API keys).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `src/` importable without installing the package - convenient during dev.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
import streamlit as st  # noqa: E402

from metaphor_machine.core.pipeline import Pipeline  # noqa: E402
from metaphor_machine.core.schemas import ProblemSpec  # noqa: E402
from metaphor_machine.llm.mock import mock_enabled  # noqa: E402

load_dotenv()

st.set_page_config(page_title="Metaphor Machine", layout="wide", page_icon="🎭")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "pipeline" not in st.session_state:
    st.session_state.pipeline = Pipeline()
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Header + sidebar
# ---------------------------------------------------------------------------

st.title("🎭 Metaphor Machine")
st.caption(
    "Describe your problem → the Definer extracts its structure → "
    "(soon) it gets mapped into a metaphor world to brainstorm in."
)

with st.sidebar:
    st.header("Settings")
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    if mock_enabled():
        st.warning("**Mock mode active** — set `METAPHOR_MOCK=0` and add a key to use real LLMs.")
    elif not (has_anthropic or has_openai):
        st.error(
            "No API key found. Either set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `.env`, "
            "or run with `METAPHOR_MOCK=1 streamlit run app/streamlit_app.py`."
        )
    else:
        providers = []
        if has_anthropic:
            providers.append("Anthropic")
        if has_openai:
            providers.append("OpenAI")
        st.success(f"Connected: {', '.join(providers)}")

    st.text_input(
        "Model",
        value=os.getenv("METAPHOR_DEFAULT_MODEL", "anthropic/claude-sonnet-4-6"),
        key="model",
        help="Any LiteLLM model string. e.g. anthropic/claude-haiku-4-5, openai/gpt-4o",
    )
    st.slider("Default temperature", 0.0, 1.5, 0.7, 0.1, key="temperature")
    st.divider()
    st.caption("Per-agent temperature overrides will appear here in Sprint 2.")

    if st.button("🔄 Reset session", use_container_width=True):
        st.session_state.pipeline = Pipeline()
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

chat_col, structure_col, timeline_col = st.columns([3, 3, 2])


# ---------------------------------------------------------------------------
# Left: chat
# ---------------------------------------------------------------------------

def render_structure_summary(p: ProblemSpec) -> str:
    """Short assistant message after Definer runs, so the chat stays informative."""
    n_entities = len(p.entities)
    n_relations = len(p.relations)
    n_tensions = len(p.tensions)
    parts = [
        f"Extracted **{n_entities} entities**, **{n_relations} relations**, "
        f"**{len(p.constraints)} constraints**, **{len(p.goals)} goals**, "
        f"**{n_tensions} tensions**.",
        "",
        f"_Summary:_ {p.summary}",
    ]
    if p.unknowns:
        parts.append("")
        parts.append("**Open questions I'd want to clarify:**")
        for u in p.unknowns:
            parts.append(f"- {u}")
    return "\n".join(parts)


with chat_col:
    st.subheader("Conversation")

    # Replay chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Describe your problem...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Definer is extracting structure..."):
                    problem = st.session_state.pipeline.run_definer(prompt)
                response = render_structure_summary(problem)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                err = f"⚠️ Definer failed: `{type(e).__name__}: {e}`"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})


# ---------------------------------------------------------------------------
# Middle: live ProblemSpec
# ---------------------------------------------------------------------------

with structure_col:
    st.subheader("Problem structure")
    problem = st.session_state.pipeline.session.problem
    if problem is None:
        st.caption("The ProblemSpec extracted by the Definer will appear here.")
        st.code(
            "{\n  'entities': [],\n  'relations': [],\n  'constraints': [],\n  'goals': []\n}",
            language="json",
        )
    else:
        st.markdown(f"**Summary:** {problem.summary}")

        with st.expander(f"Entities ({len(problem.entities)})", expanded=True):
            for e in problem.entities:
                st.markdown(f"- **{e.name}** _({e.role})_ — {', '.join(e.attributes) or '_no attrs_'}")

        with st.expander(f"Relations ({len(problem.relations)})", expanded=False):
            for r in problem.relations:
                st.markdown(f"- `{r.source}` --{r.kind}--> `{r.target}` _(strength {r.strength:.1f})_")

        with st.expander(f"Constraints ({len(problem.constraints)})", expanded=False):
            for c in problem.constraints:
                st.markdown(f"- {c}")

        with st.expander(f"Goals ({len(problem.goals)})", expanded=False):
            for g in problem.goals:
                st.markdown(f"- {g}")

        with st.expander(f"Tensions ({len(problem.tensions)})", expanded=True):
            if not problem.tensions:
                st.caption("_(none detected — Definer thinks the problem is internally consistent)_")
            for t in problem.tensions:
                st.markdown(f"- ⚡ {t}")

        with st.expander(f"Unknowns ({len(problem.unknowns)})", expanded=False):
            for u in problem.unknowns:
                st.markdown(f"- ❓ {u}")

        with st.expander("Raw JSON", expanded=False):
            st.json(problem.model_dump())


# ---------------------------------------------------------------------------
# Right: timeline
# ---------------------------------------------------------------------------

with timeline_col:
    st.subheader("Session")
    session = st.session_state.pipeline.session

    steps = [
        ("1. Definer", session.problem is not None),
        ("2. Transformer", bool(session.metaphor_candidates)),
        ("3. Explorer", bool(session.moves)),
        ("4. Translator", bool(session.solutions)),
    ]
    done = sum(1 for _, ok in steps if ok)
    st.progress(done / len(steps), text=f"{done}/{len(steps)} stages complete")

    for name, ok in steps:
        st.markdown(f"{'✅' if ok else '⏳'} {name}")

    st.divider()
    st.caption(
        "Sprint 1 ships the Definer. The Transformer + Explorer + Translator "
        "land in Sprints 2 & 3."
    )
