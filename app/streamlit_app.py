"""Streamlit UI - entry point.

Run with:
    streamlit run app/streamlit_app.py

Sprint 2 status:
- Definer wired up (Sprint 1).
- Transformer: "Generate Metaphors" button runs 3 parallel Transformer instances.
  Results shown as cards; user picks one and can edit mappings inline.
- Mock mode works without API keys: METAPHOR_MOCK=1 streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
import streamlit as st  # noqa: E402

from metaphor_machine.core.pipeline import Pipeline  # noqa: E402
from metaphor_machine.core.schemas import Mapping, MetaphorSpec, ProblemSpec  # noqa: E402
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
# Sprint 2: which metaphor card is expanded for editing
if "editing_metaphor" not in st.session_state:
    st.session_state.editing_metaphor = None


# ---------------------------------------------------------------------------
# Header + sidebar
# ---------------------------------------------------------------------------

st.title("🎭 Metaphor Machine")
st.caption(
    "Describe your problem → the Definer extracts its structure → "
    "3 metaphor worlds are generated → explore one to brainstorm solutions."
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
    with st.expander("Per-agent temperatures"):
        st.slider("Definer", 0.0, 1.5, 0.2, 0.1, key="temp_definer")
        st.slider("Transformer", 0.0, 1.5, 0.9, 0.1, key="temp_transformer")
        st.slider("Explorer (Sprint 3)", 0.0, 1.5, 0.7, 0.1, key="temp_explorer", disabled=True)
        st.slider("Translator (Sprint 3)", 0.0, 1.5, 0.3, 0.1, key="temp_translator", disabled=True)

    if st.button("🔄 Reset session", use_container_width=True):
        st.session_state.pipeline = Pipeline()
        st.session_state.messages = []
        st.session_state.editing_metaphor = None
        st.rerun()


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

chat_col, structure_col, timeline_col = st.columns([3, 3, 2])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def render_structure_summary(p: ProblemSpec) -> str:
    """Short assistant message after Definer runs."""
    parts = [
        f"Extracted **{len(p.entities)} entities**, **{len(p.relations)} relations**, "
        f"**{len(p.constraints)} constraints**, **{len(p.goals)} goals**, "
        f"**{len(p.tensions)} tensions**.",
        "",
        f"_Summary:_ {p.summary}",
    ]
    if p.unknowns:
        parts += ["", "**Open questions I'd want to clarify:**"]
        parts += [f"- {u}" for u in p.unknowns]
    return "\n".join(parts)


def _fidelity_color(f: float) -> str:
    if f >= 0.8:
        return "🟢"
    if f >= 0.6:
        return "🟡"
    return "🔴"


def render_metaphor_card(m: MetaphorSpec, idx: int, chosen: bool) -> None:
    """Render one MetaphorSpec as an interactive card."""
    border = "border: 2px solid #4CAF50;" if chosen else "border: 1px solid #444;"
    header_emoji = "✅ " if chosen else ""

    with st.container(border=True):
        col_title, col_pick = st.columns([5, 1])
        with col_title:
            st.markdown(f"### {header_emoji}{m.domain.replace('_', ' ').title()}")
        with col_pick:
            label = "Selected" if chosen else "Select"
            if st.button(label, key=f"pick_{idx}", disabled=chosen, use_container_width=True):
                st.session_state.pipeline.session.chosen_metaphor = m
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        f"Metaphor **{m.domain.replace('_', ' ').title()}** selected. "
                        "The Explorer will play inside this world. (Sprint 3)"
                    ),
                })
                st.rerun()

        st.caption(m.domain_intro)

        with st.expander(f"Mappings ({len(m.mappings)})", expanded=chosen):
            for j, mp in enumerate(m.mappings):
                c1, c2, c3, c4 = st.columns([3, 3, 1, 3])
                c1.markdown(f"**{mp.original}**")
                c2.markdown(f"→ *{mp.metaphor}*")
                c3.markdown(f"{_fidelity_color(mp.fidelity)} `{mp.fidelity:.2f}`")
                if mp.leak:
                    c4.caption(f"⚠️ {mp.leak}")
                else:
                    c4.caption("_no leak identified_")

        if m.invariants_preserved:
            with st.expander("Preserved invariants"):
                for inv in m.invariants_preserved:
                    st.markdown(f"- ✔ {inv}")

        if m.invariants_broken:
            with st.expander("Broken invariants"):
                for inv in m.invariants_broken:
                    st.markdown(f"- ✖ {inv}")


# ---------------------------------------------------------------------------
# Left: chat
# ---------------------------------------------------------------------------

with chat_col:
    st.subheader("Conversation")

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
# Middle: live structure + metaphors
# ---------------------------------------------------------------------------

with structure_col:
    problem = st.session_state.pipeline.session.problem
    candidates = st.session_state.pipeline.session.metaphor_candidates
    chosen = st.session_state.pipeline.session.chosen_metaphor

    # --- ProblemSpec panel ---
    st.subheader("Problem structure")
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
                st.caption("_(none detected)_")
            for t in problem.tensions:
                st.markdown(f"- ⚡ {t}")

        with st.expander("Raw JSON", expanded=False):
            st.json(problem.model_dump())

        st.divider()

        # --- Transformer trigger ---
        st.subheader("Metaphor worlds")
        if not candidates:
            if st.button("🎲 Generate 3 metaphors", use_container_width=True, type="primary"):
                with st.spinner("Running 3 Transformers in parallel..."):
                    try:
                        candidates = st.session_state.pipeline.run_transformer(n=3)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": (
                                f"Generated **{len(candidates)} metaphor worlds**. "
                                "Pick one to explore — or re-roll for new options."
                            ),
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Transformer failed: `{type(e).__name__}: {e}`")

        else:
            if st.button("🔁 Re-roll metaphors", use_container_width=True):
                st.session_state.pipeline.session.metaphor_candidates = []
                st.session_state.pipeline.session.chosen_metaphor = None
                st.rerun()

            for i, m in enumerate(candidates):
                is_chosen = chosen is not None and chosen.domain == m.domain
                render_metaphor_card(m, i, is_chosen)


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

    if session.chosen_metaphor:
        st.success(f"Chosen: **{session.chosen_metaphor.domain.replace('_', ' ').title()}**")
        st.caption("Explorer (Sprint 3) will play inside this world.")
    elif session.metaphor_candidates:
        st.info("Pick a metaphor from the center panel to continue.")
    elif session.problem:
        st.info("Click 'Generate 3 metaphors' to continue.")
    else:
        st.caption("Describe your problem in the chat to begin.")
