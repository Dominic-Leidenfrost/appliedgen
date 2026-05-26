"""Streamlit UI - entry point.

Run with:
    streamlit run app/streamlit_app.py

Sprint 3 status (full pipeline):
- Definer: chat → ProblemSpec panel.
- Transformer: parallel runs → 3 metaphor cards, user picks one.
- Explorer: interactive chat inside the chosen metaphor → Move history.
- Translator: "Translate to solutions" → Solution panel + optional baseline.
- Storage: "Save session" persists markdown + JSON to data/runs/.
- Mock mode: METAPHOR_MOCK=1 works for the entire pipeline.
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
from metaphor_machine.core.schemas import MetaphorSpec, Move, ProblemSpec, Solution  # noqa: E402
from metaphor_machine.llm.mock import mock_enabled  # noqa: E402
from metaphor_machine.llm.providers import PROVIDERS  # noqa: E402
from metaphor_machine.storage.markdown_store import MarkdownStore  # noqa: E402

load_dotenv()

st.set_page_config(page_title="Metaphor Machine", layout="wide", page_icon="🎭")


# ---------------------------------------------------------------------------
# OpenRouter live catalog (cached per Streamlit process for 1 hour)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_openrouter_models() -> list[tuple[str, str]]:
    """Fetch OpenRouter's public model catalog.

    Endpoint is public (no auth needed for listing). Returns
    [(display_name, litellm_model_id), …] sorted by display name.
    Returns [] on any failure — caller falls back to curated list.
    """
    import json as _json
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    try:
        req = Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "metaphor-machine/0.1"},
        )
        with urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
    except (URLError, TimeoutError, _json.JSONDecodeError, OSError):
        return []

    out: list[tuple[str, str]] = []
    for m in data.get("data", []):
        model_id = m.get("id")
        if not model_id:
            continue
        name = m.get("name") or model_id
        pricing = m.get("pricing") or {}
        # Heuristic free-tier marker: prompt cost == "0"
        is_free = str(pricing.get("prompt", "0")) in ("0", "0.0", "0.00")
        marker = " (free)" if is_free else ""
        out.append((f"{name}{marker}  ·  {model_id}", f"openrouter/{model_id}"))
    out.sort(key=lambda x: x[0].lower())
    return out


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "pipeline" not in st.session_state:
    st.session_state.pipeline = Pipeline()
if "messages" not in st.session_state:
    st.session_state.messages = []
# Phase: "definer" | "transformer" | "explorer" | "translator"
if "phase" not in st.session_state:
    st.session_state.phase = "definer"
if "baseline_text" not in st.session_state:
    st.session_state.baseline_text = None
if "saved_path" not in st.session_state:
    st.session_state.saved_path = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🎭 Metaphor Machine")

    # Detect every provider supported in .env.example. Order matters only for
    # the success message - any one of these is enough to run the pipeline.
    provider_keys = {
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Gemini": "GEMINI_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
    }
    connected = [name for name, env in provider_keys.items() if os.getenv(env)]

    if mock_enabled():
        st.warning("**Mock mode** — no LLM calls.")
    elif not connected:
        st.error(
            "No API key found. Set one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, "
            "`GEMINI_API_KEY` or `OPENROUTER_API_KEY` in `.env`, then restart "
            "`streamlit run` (the .env is only read at startup). "
            "Or run with `METAPHOR_MOCK=1`."
        )
    else:
        st.success(f"Connected: {', '.join(connected)}")

    # ---- Two-step model picker: Provider → Model ----
    # Curated list for Anthropic/OpenAI/Gemini (their catalogs are small and
    # we want sensible defaults). For OpenRouter we fetch the live catalog —
    # 300+ models — and add a text-filter so it stays usable.
    current_model = st.session_state.pipeline.model

    available_provs = [p for p in PROVIDERS if p.is_available()]

    if mock_enabled():
        st.info("**Active model:** _mock fixtures_ (no LLM calls)")
    elif not available_provs:
        st.warning(
            "No provider has a key set. Add a key to `.env` and restart, "
            "or run with `METAPHOR_MOCK=1`."
        )
    else:
        # --- Step 1: Provider --------------------------------------------
        # Default to whatever provider matches the currently-active model.
        active_prefix = current_model.split("/")[0]
        prov_default_idx = next(
            (i for i, p in enumerate(available_provs) if p.key == active_prefix),
            0,
        )
        prov_label = st.selectbox(
            "Provider",
            options=[p.display for p in available_provs],
            index=prov_default_idx,
            key="provider_choice",
        )
        provider = next(p for p in available_provs if p.display == prov_label)

        # --- Step 2: Model (different UX for OpenRouter vs others) -------
        chosen_id: str | None = None

        if provider.key == "openrouter":
            # Live catalog: fetch once per hour, cached across reruns.
            with st.spinner("Fetching OpenRouter catalog…"):
                catalog = _fetch_openrouter_models()
            if not catalog:
                st.warning(
                    "Could not fetch OpenRouter catalog (offline?). "
                    "Falling back to curated list."
                )
                catalog = [(m.display, m.model_id) for m in provider.models]

            search = st.text_input(
                "🔍 Filter",
                value="",
                key="or_filter",
                placeholder="e.g. 'claude', 'gemini', 'mistral', 'free'…",
            )
            filtered = (
                [(n, mid) for n, mid in catalog if search.lower() in n.lower()]
                if search
                else catalog
            )
            if not filtered:
                st.caption("_No matches — type a different filter._")
                chosen_id = current_model
            else:
                # Try to keep the user's current model selected if it survives the filter
                default_model_idx = next(
                    (i for i, (_, mid) in enumerate(filtered) if mid == current_model),
                    0,
                )
                model_label = st.selectbox(
                    f"Model ({len(filtered)} of {len(catalog)})",
                    options=[n for n, _ in filtered],
                    index=default_model_idx,
                    key="or_model_choice",
                )
                chosen_id = next(mid for n, mid in filtered if n == model_label)
        else:
            # Curated list for Anthropic/OpenAI/Gemini
            default_model_idx = next(
                (i for i, m in enumerate(provider.models) if m.model_id == current_model),
                0,
            )
            model_label = st.selectbox(
                "Model",
                options=[m.display for m in provider.models],
                index=default_model_idx,
                key=f"{provider.key}_model_choice",
            )
            chosen_id = next(
                m.model_id for m in provider.models if m.display == model_label
            )

        # --- Custom override (always available, hidden by default) -------
        with st.expander("✏️ Custom model string (advanced)"):
            custom = st.text_input(
                "LiteLLM model string",
                value="",
                placeholder=f"e.g. {provider.default_model()} or any other",
                key="custom_model",
                help="Leave blank to use the dropdown choice above. "
                "Useful for brand-new models not in our registry.",
            )
            if custom.strip():
                chosen_id = custom.strip()

        # --- Apply choice ------------------------------------------------
        if chosen_id and chosen_id != st.session_state.pipeline.model:
            st.session_state.pipeline.set_model(chosen_id)
            st.toast(f"Switched to {chosen_id}", icon="🔄")

        # --- Status row --------------------------------------------------
        active = st.session_state.pipeline.model
        active_prefix = active.split("/")[0].lower()
        provider_env = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(active_prefix, "")
        key_ok = bool(provider_env) and bool(os.getenv(provider_env))
        st.caption(
            f"{'🟢' if key_ok else '🔴'} Active: `{active}`"
            + ("" if key_ok else f" — no key for `{provider_env or 'this provider'}`")
        )

    with st.expander("Per-agent temperatures"):
        st.slider("Definer", 0.0, 1.5, 0.2, 0.1, key="temp_definer")
        st.slider("Transformer", 0.0, 1.5, 0.9, 0.1, key="temp_transformer")
        st.slider("Explorer", 0.0, 1.5, 0.7, 0.1, key="temp_explorer")
        st.slider("Translator", 0.0, 1.5, 0.3, 0.1, key="temp_translator")

    st.divider()

    # Phase progress
    session = st.session_state.pipeline.session
    steps = [
        ("1. Definer", session.problem is not None),
        ("2. Transformer", bool(session.metaphor_candidates)),
        ("3. Explorer", bool(session.moves)),
        ("4. Translator", bool(session.solutions)),
    ]
    done = sum(1 for _, ok in steps if ok)
    st.progress(done / len(steps), text=f"{done}/{len(steps)} stages")
    for name, ok in steps:
        st.markdown(f"{'✅' if ok else '⏳'} {name}")

    st.divider()

    # Save session
    if session.problem is not None:
        if st.button("💾 Save session", use_container_width=True):
            store = MarkdownStore(ROOT / "data" / "runs")
            slug = (session.problem.summary[:30].replace(" ", "_").lower() or "session")
            saved = store.save(session, slug=slug)
            st.session_state.saved_path = str(saved)
            st.success(f"Saved to `{saved.name}`")
    if st.session_state.saved_path:
        st.caption(f"Last saved: `{Path(st.session_state.saved_path).name}`")

    if st.button("🔄 Reset session", use_container_width=True):
        st.session_state.pipeline = Pipeline()
        st.session_state.messages = []
        st.session_state.phase = "definer"
        st.session_state.baseline_text = None
        st.session_state.saved_path = None
        st.rerun()


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

chat_col, structure_col = st.columns([4, 4])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fidelity_color(f: float) -> str:
    return "🟢" if f >= 0.8 else ("🟡" if f >= 0.6 else "🔴")


def _push_msg(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def _format_error(e: BaseException) -> str:
    """Unwrap RetryError/ExceptionGroup so the user sees the real cause.

    tenacity wraps the last failed call in a RetryError; ExceptionGroups
    (Python 3.11+) hide useful messages inside .exceptions. Drill down to
    the innermost exception that actually carries a message.
    """
    inner: BaseException = e
    seen: set[int] = set()
    while id(inner) not in seen:
        seen.add(id(inner))
        # tenacity.RetryError exposes .last_attempt — extract its exception
        last = getattr(inner, "last_attempt", None)
        if last is not None:
            try:
                inner = last.exception() or inner
                continue
            except Exception:
                pass
        # Python 3.11+ ExceptionGroup
        excs = getattr(inner, "exceptions", None)
        if excs:
            inner = excs[0]
            continue
        # __cause__ from `raise X from Y`
        if inner.__cause__ is not None:
            inner = inner.__cause__
            continue
        break
    return f"{type(inner).__name__}: {inner}"


def render_problem_panel(problem: ProblemSpec) -> None:
    st.markdown(f"**Summary:** {problem.summary}")
    with st.expander(f"Entities ({len(problem.entities)})", expanded=True):
        for e in problem.entities:
            attrs = ", ".join(e.attributes) or "_none_"
            st.markdown(f"- **{e.name}** _({e.role})_ — {attrs}")
    with st.expander(f"Relations ({len(problem.relations)})", expanded=False):
        for r in problem.relations:
            st.markdown(f"- `{r.source}` --{r.kind}--> `{r.target}` _(str {r.strength:.1f})_")
    with st.expander(f"Tensions ({len(problem.tensions)})", expanded=True):
        for t in problem.tensions:
            st.markdown(f"- ⚡ {t}")
        if not problem.tensions:
            st.caption("_(none detected)_")
    with st.expander("Constraints / Goals", expanded=False):
        for c in problem.constraints:
            st.markdown(f"- ⛔ {c}")
        for g in problem.goals:
            st.markdown(f"- 🎯 {g}")
    with st.expander("Raw JSON", expanded=False):
        st.json(problem.model_dump())


def render_metaphor_card(m: MetaphorSpec, idx: int, chosen: bool) -> None:
    with st.container(border=True):
        col_title, col_pick = st.columns([5, 1])
        with col_title:
            prefix = "✅ " if chosen else ""
            st.markdown(f"#### {prefix}{m.domain.replace('_', ' ').title()}")
        with col_pick:
            if not chosen and st.button("Select", key=f"pick_{idx}", use_container_width=True):
                st.session_state.pipeline.session.chosen_metaphor = m
                st.session_state.phase = "explorer"
                _push_msg(
                    "assistant",
                    f"Metaphor **{m.domain.replace('_', ' ').title()}** selected. "
                    "Click **🎲 Generate first move** below — the Explorer will "
                    "propose moves and you curate (steer, redo, or accept).",
                )
                st.rerun()
        st.caption(m.domain_intro)
        with st.expander(f"Mappings ({len(m.mappings)})", expanded=chosen):
            for mp in m.mappings:
                c1, c2, c3, c4 = st.columns([3, 3, 1, 3])
                c1.markdown(f"**{mp.original}**")
                c2.markdown(f"→ *{mp.metaphor}*")
                c3.markdown(f"{_fidelity_color(mp.fidelity)} `{mp.fidelity:.2f}`")
                c4.caption(f"⚠️ {mp.leak}" if mp.leak else "_no leak_")
        if m.invariants_preserved:
            with st.expander("Preserved"):
                for inv in m.invariants_preserved:
                    st.markdown(f"- ✔ {inv}")
        if m.invariants_broken:
            with st.expander("Broken"):
                for inv in m.invariants_broken:
                    st.markdown(f"- ✖ {inv}")


def render_move(move: Move, idx: int) -> None:
    with st.container(border=True):
        st.markdown(f"**Move {idx}: {move.actor}**")
        st.markdown(f"_{move.action}_")
        st.markdown(f"**→** {move.consequence}")
        if move.obstacle:
            st.caption(f"🚧 {move.obstacle}")


def render_solution(sol: Solution, idx: int) -> None:
    conf_color = "🟢" if sol.confidence >= 0.7 else ("🟡" if sol.confidence >= 0.5 else "🔴")
    with st.container(border=True):
        st.markdown(
            f"**Solution {idx}** {conf_color} confidence `{sol.confidence:.0%}`"
        )
        st.caption(f"_Metaphor: {sol.metaphor_idea}_")
        st.markdown(f"**→ {sol.original_domain_translation}**")
        if sol.caveats:
            with st.expander("Caveats"):
                for c in sol.caveats:
                    st.markdown(f"- ⚠️ {c}")


# ---------------------------------------------------------------------------
# Left: chat (adapts to current phase)
# ---------------------------------------------------------------------------

pipeline: Pipeline = st.session_state.pipeline
phase: str = st.session_state.phase

with chat_col:
    st.subheader("Conversation")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Phase: Definer ---
    if phase == "definer":
        prompt = st.chat_input("Describe your problem…")
        if prompt:
            _push_msg("user", prompt)
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Definer extracting structure…"):
                        problem = pipeline.run_definer(prompt)
                    p = problem
                    summary_msg = (
                        f"Extracted **{len(p.entities)} entities**, "
                        f"**{len(p.relations)} relations**, "
                        f"**{len(p.tensions)} tensions**.\n\n"
                        f"_Summary:_ {p.summary}"
                    )
                    if p.unknowns:
                        summary_msg += "\n\n**Open questions:**\n" + "\n".join(
                            f"- {u}" for u in p.unknowns
                        )
                    st.markdown(summary_msg)
                    _push_msg("assistant", summary_msg)
                    st.session_state.phase = "transformer"
                    st.rerun()
                except Exception as e:
                    err = f"⚠️ Definer failed: `{_format_error(e)}`"
                    st.error(err)
                    _push_msg("assistant", err)

    # --- Phase: Transformer (pick a metaphor) ---
    elif phase == "transformer":
        if not pipeline.session.metaphor_candidates:
            if st.button("🎲 Generate 3 metaphors", type="primary", use_container_width=True):
                with st.spinner("Running 3 Transformers in parallel…"):
                    try:
                        candidates = pipeline.run_transformer(n=3)
                        msg = (
                            f"Generated **{len(candidates)} metaphor worlds**. "
                            "Pick one from the panel on the right."
                        )
                        _push_msg("assistant", msg)
                        with st.chat_message("assistant"):
                            st.markdown(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Transformer failed: `{_format_error(e)}`")
        else:
            st.info("Pick a metaphor from the panel →")
            if st.button("🔁 Re-roll metaphors", use_container_width=True):
                pipeline.session.metaphor_candidates = []
                pipeline.session.chosen_metaphor = None
                st.rerun()

    # --- Phase: Explorer (autonomous generation, user curates) ---
    elif phase == "explorer":
        chosen = pipeline.session.chosen_metaphor
        n_moves = len(pipeline.session.moves)
        if chosen:
            domain_name = chosen.domain.replace("_", " ").title()
            st.caption(
                f"Exploring **{domain_name}** — the Explorer proposes moves, "
                f"you curate. Move count: **{n_moves}**."
            )

        # --- Control row: Generate / Try different / Undo --------------
        col_gen, col_diff, col_undo = st.columns([3, 3, 2])

        def _run_explorer(directive: str | None, force_different: bool) -> None:
            try:
                spinner_text = (
                    "Explorer trying a fundamentally different strategy…"
                    if force_different
                    else "Explorer proposing next move…"
                )
                with st.spinner(spinner_text):
                    move = pipeline.run_explorer_turn(
                        directive=directive,
                        force_different=force_different,
                    )
                move_msg = (
                    f"**Move {len(pipeline.session.moves)} — {move.actor}**\n\n"
                    f"_{move.action}_\n\n"
                    f"**→** {move.consequence}\n\n"
                    f"🚧 _{move.obstacle}_"
                )
                _push_msg("assistant", move_msg)
                st.session_state.steering_input = ""  # clear steering after use
                st.rerun()
            except Exception as e:
                err = f"⚠️ Explorer failed: `{_format_error(e)}`"
                st.error(err)
                _push_msg("assistant", err)

        # Read steering text once so all three buttons can pass it in
        steering = st.session_state.get("steering_input", "")

        with col_gen:
            btn_label = "🎲 Generate first move" if n_moves == 0 else "🎲 Continue exploring"
            if st.button(btn_label, type="primary", use_container_width=True):
                _run_explorer(directive=steering or None, force_different=False)

        with col_diff:
            disabled = n_moves == 0
            if st.button(
                "🔄 Try different angle",
                use_container_width=True,
                disabled=disabled,
                help="Force the next move to use a strategy structurally unlike all prior moves.",
            ):
                _run_explorer(directive=steering or None, force_different=True)

        with col_undo:
            disabled = n_moves == 0
            if st.button(
                "↩️ Undo last",
                use_container_width=True,
                disabled=disabled,
                help="Remove the most recent move (e.g. if it broke the metaphor or felt off).",
            ):
                popped = pipeline.undo_last_move()
                if popped:
                    _push_msg(
                        "assistant",
                        f"_(Undid Move {n_moves}: {popped.actor} — {popped.action[:60]}…)_",
                    )
                    st.rerun()

        # --- Optional steering text ------------------------------------
        st.text_area(
            "Optional steering for the next move",
            value=steering,
            key="steering_input",
            height=68,
            placeholder=(
                "Leave empty for full autonomy. Or steer: 'focus on the quieter "
                "members', 'try a structural rule change', 'the last consequence "
                "wasn't realistic, redo it'…"
            ),
        )

        # --- Hint when there's enough material to translate -----------
        if n_moves >= 5:
            st.info(
                f"You have **{n_moves} moves** — usually plenty for the Translator. "
                "Consider proceeding to solutions."
            )

        if pipeline.session.moves:
            if st.button(
                "🔁 Translate moves to solutions →",
                type="secondary" if n_moves < 3 else "primary",
                use_container_width=True,
                help="End the exploration phase. Each move becomes one candidate solution.",
            ):
                st.session_state.phase = "translator"
                st.rerun()

    # --- Phase: Translator ---
    elif phase == "translator":
        if not pipeline.session.solutions:
            if st.button(
                "⚙️ Run Translator", type="primary", use_container_width=True
            ):
                with st.spinner("Translator mapping insights back to original domain…"):
                    try:
                        solutions = pipeline.run_translator()
                        sol_msg = (
                            f"Generated **{len(solutions)} solution(s)**. "
                            "See the panel for details."
                        )
                        _push_msg("assistant", sol_msg)
                        with st.chat_message("assistant"):
                            st.markdown(sol_msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Translator failed: `{_format_error(e)}`")
        else:
            # Show solutions in chat column
            for i, sol in enumerate(pipeline.session.solutions, 1):
                render_solution(sol, i)

            # Baseline comparison
            st.divider()
            if st.session_state.baseline_text is None:
                if st.button("🔍 Show baseline LLM answer (no metaphor)", use_container_width=True):
                    with st.spinner("Generating baseline…"):
                        try:
                            baseline = pipeline.run_baseline()
                            st.session_state.baseline_text = baseline
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Baseline failed: `{_format_error(e)}`")
            else:
                with st.expander("📊 Baseline (direct LLM, no metaphor)", expanded=True):
                    st.markdown(st.session_state.baseline_text)

            if st.button("← Back to Explorer", use_container_width=True):
                st.session_state.phase = "explorer"
                st.rerun()


# ---------------------------------------------------------------------------
# Right: structure panel (adapts to phase)
# ---------------------------------------------------------------------------

with structure_col:
    session = pipeline.session

    if phase == "definer" and session.problem is None:
        st.subheader("Problem structure")
        st.caption("Describe your problem in the chat to begin.")

    elif phase in ("definer", "transformer") and session.problem is not None:
        st.subheader("Problem structure")
        render_problem_panel(session.problem)

        if session.metaphor_candidates:
            st.divider()
            st.subheader("Metaphor worlds")
            chosen = session.chosen_metaphor
            for i, m in enumerate(session.metaphor_candidates):
                render_metaphor_card(m, i, chosen is not None and chosen.domain == m.domain)

    elif phase == "explorer":
        chosen = session.chosen_metaphor
        if chosen:
            st.subheader(f"World: {chosen.domain.replace('_', ' ').title()}")
            st.caption(chosen.domain_intro)
            with st.expander("Mapping table", expanded=False):
                for mp in chosen.mappings:
                    st.markdown(
                        f"- **{mp.original}** → *{mp.metaphor}* "
                        f"{_fidelity_color(mp.fidelity)}"
                    )
                    if mp.leak:
                        st.caption(f"  ⚠️ {mp.leak}")

        st.divider()
        st.subheader(f"Move log ({len(session.moves)})")
        if not session.moves:
            st.caption("No moves yet — make a move in the chat.")
        for i, move in enumerate(session.moves, 1):
            render_move(move, i)

    elif phase == "translator":
        st.subheader("Solutions")
        if not session.solutions:
            st.caption("Run the Translator to see solutions here.")
        else:
            for i, sol in enumerate(session.solutions, 1):
                render_solution(sol, i)

        st.divider()
        st.subheader("Move log")
        for i, move in enumerate(session.moves, 1):
            render_move(move, i)
