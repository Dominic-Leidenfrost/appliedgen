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
from metaphor_machine.prompts.language import resolve_language  # noqa: E402
from metaphor_machine.storage.markdown_store import (  # noqa: E402
    MarkdownStore,
    load_session_from_json,
)


# ---------------------------------------------------------------------------
# i18n: UI strings (Python-side, separate from agent output language)
# ---------------------------------------------------------------------------
# Streamlit labels are kept short and in just two languages — we don't
# attempt a full i18n library. Keys are the English label.

I18N: dict[str, dict[str, str]] = {
    "en": {},  # English is the canonical, no translation needed
    "de": {
        # --- Sidebar header / status ---
        "Connected": "Verbunden",
        "No API key found. Set one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` or `OPENROUTER_API_KEY` in `.env`, then restart `streamlit run` (the .env is only read at startup). Or run with `METAPHOR_MOCK=1`.": (
            "Kein API-Key gefunden. Trage einen von `ANTHROPIC_API_KEY`, "
            "`OPENAI_API_KEY`, `GEMINI_API_KEY` oder `OPENROUTER_API_KEY` "
            "in `.env` ein und starte `streamlit run` neu (die .env wird "
            "nur beim Start gelesen). Oder starte mit `METAPHOR_MOCK=1`."
        ),
        "**Mock mode** — no LLM calls.": "**Mock-Modus** — keine LLM-Aufrufe.",
        "**Active model:** _mock fixtures_ (no LLM calls)": (
            "**Aktives Modell:** _Mock-Daten_ (keine LLM-Aufrufe)"
        ),
        # --- Model picker ---
        "Provider": "Anbieter",
        "Model": "Modell",
        "Only models whose provider has an API key are listed.": (
            "Nur Modelle deren Anbieter einen API-Key hinterlegt hat."
        ),
        "🔍 Filter": "🔍 Filter",
        "e.g. 'claude', 'gemini', 'mistral', 'free'…": "z.B. 'claude', 'gemini', 'mistral', 'free'…",
        "Fetching OpenRouter catalog…": "OpenRouter-Katalog wird geladen…",
        "Could not fetch OpenRouter catalog (offline?). Falling back to curated list.": (
            "OpenRouter-Katalog nicht erreichbar (offline?). Fallback auf kuratierte Liste."
        ),
        "_No matches — type a different filter._": "_Keine Treffer — anderen Filter eingeben._",
        "✏️ Custom model string (advanced)": "✏️ Eigener Modell-String (erweitert)",
        "LiteLLM model string": "LiteLLM Modell-String",
        "Leave blank to use the dropdown choice above. Useful for brand-new models not in our registry.": (
            "Leer lassen um die Dropdown-Auswahl oben zu verwenden. "
            "Nützlich für ganz neue Modelle die noch nicht in der Registry sind."
        ),
        "Per-agent temperatures": "Temperatur pro Agent",
        "Definer": "Definer",
        "Transformer": "Transformer",
        "Explorer": "Explorer",
        "Translator": "Translator",
        "Default temperature": "Standard-Temperatur",
        # --- Sidebar buttons / actions ---
        "💾 Save session": "💾 Sitzung speichern",
        "🔄 Reset session": "🔄 Sitzung zurücksetzen",
        # --- Phase progress (sidebar) ---
        "1. Definer": "1. Definer",
        "2. Transformer": "2. Transformer",
        "3. Explorer": "3. Explorer",
        "4. Translator": "4. Translator",
        "{done}/{total} stages": "{done}/{total} Phasen",
        # --- Top / phase headers ---
        "🎭 Metaphor Machine": "🎭 Metaphor Machine",
        "Describe your problem → the Definer extracts its structure → (soon) it gets mapped into a metaphor world to brainstorm in.": (
            "Beschreibe dein Problem → der Definer extrahiert die Struktur → "
            "es wird in eine Metapher-Welt überführt, in der du brainstormen kannst."
        ),
        # --- Chat column ---
        "Conversation": "Konversation",
        "Describe your problem…": "Beschreibe dein Problem…",
        "Definer is extracting structure...": "Definer extrahiert die Struktur…",
        "⚠️ Definer failed: `{err}`": "⚠️ Definer-Fehler: `{err}`",
        # --- Transformer phase ---
        "Generate 3 metaphor candidates": "3 Metaphern generieren",
        "⚙️ Generate 3 metaphors": "⚙️ 3 Metaphern generieren",
        "Generating 3 metaphors in parallel (one per seed domain)…": (
            "Generiere 3 Metaphern parallel (eine pro Seed-Domain)…"
        ),
        "Generated {n} metaphor candidate(s). Pick one to begin exploring.": (
            "{n} Metaphern generiert. Wähle eine aus um die Erkundung zu starten."
        ),
        "Only {got} of {want} metaphors succeeded — {fail_count} failed silently.": (
            "Nur {got} von {want} Metaphern erfolgreich — {fail_count} fehlgeschlagen."
        ),
        "Retry failed runs": "Fehlgeschlagene Läufe wiederholen",
        "Pick a metaphor from the panel →": "Wähle eine Metapher aus dem Panel →",
        "Select": "Auswählen",
        # --- Explorer phase ---
        "Exploring **{domain}** — the Explorer proposes moves, you curate. Move count: **{n}**.": (
            "Erkunde **{domain}** — der Explorer schlägt Züge vor, du kuratierst. "
            "Anzahl Züge: **{n}**."
        ),
        "Steering text (gets sent with the NEXT click below)": (
            "Lenkungstext (wird beim NÄCHSTEN Button-Klick unten mitgesendet)"
        ),
        "Leave empty for full autonomy. Or steer: 'focus on the quieter members', 'try a structural rule change', 'the last consequence wasn't realistic, redo it'…": (
            "Leer lassen für volle Autonomie. Oder lenken: 'fokussiere auf die "
            "leiseren Mitglieder', 'versuch eine Regeländerung', 'die letzte "
            "Konsequenz war unrealistisch, mach sie neu'…"
        ),
        "🎲 Generate first move": "🎲 Ersten Zug generieren",
        "🎲 Continue exploring": "🎲 Weiter erkunden",
        "🔄 Try different angle": "🔄 Anderen Ansatz versuchen",
        "↩️ Undo last": "↩️ Letzten Zug rückgängig",
        "Force the next move to use a strategy structurally unlike all prior moves.": (
            "Erzwingt einen strukturell anderen Ansatz als alle bisherigen Züge."
        ),
        "Remove the most recent move (e.g. if it broke the metaphor or felt off).": (
            "Entfernt den letzten Zug (z.B. wenn er die Metapher gebrochen hat)."
        ),
        "Explorer proposing next move…": "Explorer plant den nächsten Zug…",
        "Explorer trying a fundamentally different strategy…": (
            "Explorer versucht eine fundamental andere Strategie…"
        ),
        "You have **{n} moves** — usually plenty for the Translator. Consider proceeding to solutions.": (
            "Du hast **{n} Züge** — meistens reichlich für den Translator. "
            "Vielleicht jetzt zu den Lösungen weitergehen."
        ),
        "🔁 Translate moves to solutions →": "🔁 Züge in Lösungen übersetzen →",
        "End the exploration phase. Each move becomes one candidate solution.": (
            "Beendet die Erkundungsphase. Jeder Zug wird zu einer Lösung."
        ),
        "⚠️ Explorer failed: `{err}`": "⚠️ Explorer-Fehler: `{err}`",
        # --- Translator phase ---
        "⚙️ Run Translator": "⚙️ Translator starten",
        "Translator mapping insights back to original domain…": (
            "Translator übersetzt Einsichten zurück in die Original-Domäne…"
        ),
        "Generated **{n} solution(s)**. See the panel for details.": (
            "**{n} Lösung(en)** generiert. Details rechts."
        ),
        "🔍 Show baseline LLM answer (no metaphor)": (
            "🔍 Baseline-Antwort anzeigen (ohne Metapher)"
        ),
        "Generating baseline…": "Baseline wird generiert…",
        "📊 Baseline (direct LLM, no metaphor)": "📊 Baseline (direktes LLM, ohne Metapher)",
        "← Back to Explorer": "← Zurück zum Explorer",
        "⚠️ Translator failed: `{err}`": "⚠️ Translator-Fehler: `{err}`",
        "⚠️ Baseline failed: `{err}`": "⚠️ Baseline-Fehler: `{err}`",
        # --- Structure panel ---
        "Problem structure": "Problemstruktur",
        "Summary:": "Zusammenfassung:",
        "Entities ({n})": "Entitäten ({n})",
        "Relations ({n})": "Relationen ({n})",
        "Tensions ({n})": "Spannungen ({n})",
        "_(none detected)_": "_(keine erkannt)_",
        "Constraints / Goals": "Einschränkungen / Ziele",
        "Raw JSON": "Roh-JSON",
        "Mappings ({n})": "Mappings ({n})",
        "Preserved": "Erhalten",
        "Broken": "Gebrochen",
        "Caveats": "Vorbehalte",
        "**Move {idx}: {actor}**": "**Zug {idx}: {actor}**",
        "**Solution {idx}**": "**Lösung {idx}**",
        # --- Misc / save ---
        "Saved to `{name}`": "Gespeichert nach `{name}`",
        "Last saved: `{name}`": "Zuletzt gespeichert: `{name}`",
        "(Undid Move {n}: {actor} — {action_short}…)": (
            "(Zug {n} rückgängig gemacht: {actor} — {action_short}…)"
        ),
        "Metaphor **{domain}** selected. Click **🎲 Generate first move** below — the Explorer will propose moves and you curate (steer, redo, or accept).": (
            "Metapher **{domain}** ausgewählt. Klicke unten auf "
            "**🎲 Ersten Zug generieren** — der Explorer schlägt Züge "
            "vor und du kuratierst (lenken, neu machen, akzeptieren)."
        ),
        # --- Sidebar: provider/model status ---
        "No provider has a key set. Add a key to `.env` and restart, or run with `METAPHOR_MOCK=1`.": (
            "Kein Anbieter hat einen Key hinterlegt. Trage einen Key in "
            "`.env` ein und starte neu, oder starte mit `METAPHOR_MOCK=1`."
        ),
        "Fetching Gemini models…": "Lade Gemini-Modelle…",
        "Could not fetch Gemini model list (bad key or offline?). Falling back to curated list.": (
            "Gemini-Modellliste nicht abrufbar (Key falsch oder offline?). "
            "Fallback auf kuratierte Liste."
        ),
        "Active": "Aktiv",
        "no key for `{env}`": "kein Key für `{env}`",
        "no key for this provider": "kein Key für diesen Anbieter",
        "Switched to {model}": "Modell gewechselt: {model}",
        "Switched to {lang_name}": "Sprache: {lang_name}",
        # --- Import session ---
        "Import session": "Sitzung importieren",
        "Saved sessions": "Gespeicherte Sitzungen",
        "Pick a previously saved session from data/runs/.": (
            "Wähle eine vorher gespeicherte Sitzung aus data/runs/."
        ),
        "Load": "Laden",
        "Upload session.json": "session.json hochladen",
        "External session from another machine.": (
            "Externe Sitzung von einer anderen Maschine."
        ),
        "Load uploaded session": "Hochgeladene Sitzung laden",
        "No saved sessions in data/runs/ yet.": (
            "Noch keine gespeicherten Sitzungen in data/runs/."
        ),
        "Loaded session ({source}).": "Sitzung geladen ({source}).",
        "Error": "Fehler",
        "Error details": "Fehlerdetails",
        # --- Structure / right panel ---
        "Describe your problem in the chat to begin.": (
            "Beschreibe dein Problem im Chat um zu beginnen."
        ),
        "Metaphor worlds": "Metaphern-Welten",
        "World": "Welt",
        "Mapping table": "Mapping-Tabelle",
        "Move log": "Zug-Verlauf",
        "No moves yet — generate one with the buttons on the left.": (
            "Noch keine Züge — generiere einen über die Buttons links."
        ),
        "Solutions": "Lösungen",
        "Run the Translator to see solutions here.": (
            "Klicke 'Translator starten' um Lösungen zu sehen."
        ),
        "Will be sent with the next click below:": (
            "Wird mit dem nächsten Klick mitgesendet:"
        ),
        # --- Misc ---
        "confidence": "Konfidenz",
        "Metaphor": "Metapher",
        "e.g. {example}": "z.B. {example}",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Translate a UI string. Falls back to the key (English) if missing."""
    return I18N.get(lang, {}).get(key, key)

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


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_gemini_models(api_key: str) -> list[tuple[str, str]]:
    """Fetch the current list of Gemini models via Google's public ListModels.

    Requires the user's GEMINI_API_KEY (passed in the URL — that's how
    Google's API works). Returns [(display_name, litellm_model_id), …]
    filtered to models that support generateContent (i.e. chat / text gen,
    not embedding-only). Returns [] on any failure → caller falls back to
    the curated list in providers.py.
    """
    import json as _json
    from urllib.error import URLError
    from urllib.parse import quote
    from urllib.request import Request, urlopen

    if not api_key:
        return []

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={quote(api_key)}"
        req = Request(url, headers={"User-Agent": "metaphor-machine/0.1"})
        with urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
    except (URLError, TimeoutError, _json.JSONDecodeError, OSError):
        return []

    out: list[tuple[str, str]] = []
    for m in data.get("models", []):
        full_name = m.get("name", "")  # e.g. "models/gemini-2.5-pro"
        if not full_name.startswith("models/"):
            continue
        model_id = full_name[len("models/") :]
        methods = m.get("supportedGenerationMethods", [])
        # Skip embedding-only and other non-chat models
        if "generateContent" not in methods:
            continue
        display = m.get("displayName") or model_id
        out.append((f"{display}  ·  {model_id}", f"gemini/{model_id}"))
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
# Language toggle, persisted across reloads via Pipeline.
if "language" not in st.session_state:
    st.session_state.language = st.session_state.pipeline.language


# ---------------------------------------------------------------------------
# Top header row: title (left) + language toggle (right)
# ---------------------------------------------------------------------------

head_left, head_lang = st.columns([6, 1])
with head_lang:
    lang_choice = st.segmented_control(
        label="Language",
        options=["EN", "DE"],
        default=st.session_state.language.upper(),
        label_visibility="collapsed",
        key="lang_seg_ctrl",
    ) if hasattr(st, "segmented_control") else st.radio(
        label="Language",
        options=["EN", "DE"],
        index=0 if st.session_state.language == "en" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="lang_seg_ctrl",
    )
    new_lang = (lang_choice or "EN").lower()
    if new_lang != st.session_state.language:
        st.session_state.language = new_lang
        st.session_state.pipeline.set_language(new_lang)  # type: ignore[arg-type]
        lang_name = "Deutsch" if new_lang == "de" else "English"
        st.toast(
            t("Switched to {lang_name}", new_lang).format(lang_name=lang_name),
            icon="🌐",
        )
        st.rerun()

LANG = st.session_state.language  # convenience alias for translators below


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
        st.warning(t("**Mock mode** — no LLM calls.", LANG))
    elif not connected:
        st.error(
            t(
                "No API key found. Set one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, "
                "`GEMINI_API_KEY` or `OPENROUTER_API_KEY` in `.env`, then restart "
                "`streamlit run` (the .env is only read at startup). "
                "Or run with `METAPHOR_MOCK=1`.",
                LANG,
            )
        )
    else:
        st.success(f"{t('Connected', LANG)}: {', '.join(connected)}")

    # ---- Two-step model picker: Provider → Model ----
    # Curated list for Anthropic/OpenAI/Gemini (their catalogs are small and
    # we want sensible defaults). For OpenRouter we fetch the live catalog —
    # 300+ models — and add a text-filter so it stays usable.
    current_model = st.session_state.pipeline.model

    available_provs = [p for p in PROVIDERS if p.is_available()]

    if mock_enabled():
        st.info(t("**Active model:** _mock fixtures_ (no LLM calls)", LANG))
    elif not available_provs:
        st.warning(
            t(
                "No provider has a key set. Add a key to `.env` and restart, "
                "or run with `METAPHOR_MOCK=1`.",
                LANG,
            )
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
            t("Provider", LANG),
            options=[p.display for p in available_provs],
            index=prov_default_idx,
            key="provider_choice",
        )
        provider = next(p for p in available_provs if p.display == prov_label)

        # --- Step 2: Model (different UX for OpenRouter vs others) -------
        chosen_id: str | None = None

        # Providers that support live model-list fetching. Falls back to
        # the curated registry list if the fetch fails (offline, bad key,
        # rate limited, etc.).
        live_providers = {"openrouter", "gemini"}
        if provider.key in live_providers:
            if provider.key == "openrouter":
                spinner_msg = t("Fetching OpenRouter catalog…", LANG)
            else:
                spinner_msg = t("Fetching Gemini models…", LANG)
            with st.spinner(spinner_msg):
                if provider.key == "openrouter":
                    catalog = _fetch_openrouter_models()
                else:  # gemini
                    catalog = _fetch_gemini_models(os.getenv("GEMINI_API_KEY", ""))

            if not catalog:
                if provider.key == "openrouter":
                    fallback_msg = t(
                        "Could not fetch OpenRouter catalog (offline?). "
                        "Falling back to curated list.",
                        LANG,
                    )
                else:
                    fallback_msg = t(
                        "Could not fetch Gemini model list (bad key or offline?). "
                        "Falling back to curated list.",
                        LANG,
                    )
                st.warning(fallback_msg)
                catalog = [(m.display, m.model_id) for m in provider.models]

            # Filter input only makes sense when the catalog is big.
            # OpenRouter ~300 models: filter is essential. Gemini ~10-30:
            # filter is optional but doesn't hurt.
            search = st.text_input(
                t("🔍 Filter", LANG),
                value="",
                key=f"{provider.key}_filter",
                placeholder=t("e.g. 'claude', 'gemini', 'mistral', 'free'…", LANG),
            )
            filtered = (
                [(n, mid) for n, mid in catalog if search.lower() in n.lower()]
                if search
                else catalog
            )
            if not filtered:
                st.caption(t("_No matches — type a different filter._", LANG))
                chosen_id = current_model
            else:
                # Try to keep the user's current model selected if it survives the filter
                default_model_idx = next(
                    (i for i, (_, mid) in enumerate(filtered) if mid == current_model),
                    0,
                )
                model_label = st.selectbox(
                    f"{t('Model', LANG)} ({len(filtered)} / {len(catalog)})",
                    options=[n for n, _ in filtered],
                    index=default_model_idx,
                    key=f"{provider.key}_live_model_choice",
                )
                chosen_id = next(mid for n, mid in filtered if n == model_label)
        else:
            # Curated list for Anthropic/OpenAI/Gemini
            default_model_idx = next(
                (i for i, m in enumerate(provider.models) if m.model_id == current_model),
                0,
            )
            model_label = st.selectbox(
                t("Model", LANG),
                options=[m.display for m in provider.models],
                index=default_model_idx,
                key=f"{provider.key}_model_choice",
            )
            chosen_id = next(
                m.model_id for m in provider.models if m.display == model_label
            )

        # --- Custom override (always available, hidden by default) -------
        with st.expander(t("✏️ Custom model string (advanced)", LANG)):
            custom = st.text_input(
                t("LiteLLM model string", LANG),
                value="",
                placeholder=t("e.g. {example}", LANG).format(example=provider.default_model()),
                key="custom_model",
                help=t(
                    "Leave blank to use the dropdown choice above. "
                    "Useful for brand-new models not in our registry.",
                    LANG,
                ),
            )
            if custom.strip():
                chosen_id = custom.strip()

        # --- Apply choice ------------------------------------------------
        if chosen_id and chosen_id != st.session_state.pipeline.model:
            st.session_state.pipeline.set_model(chosen_id)
            st.toast(
                t("Switched to {model}", LANG).format(model=chosen_id),
                icon="🔄",
            )

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
        active_label = t("Active", LANG)
        if key_ok:
            missing_part = ""
        elif provider_env:
            missing_part = " — " + t("no key for `{env}`", LANG).format(env=provider_env)
        else:
            missing_part = " — " + t("no key for this provider", LANG)
        st.caption(f"{'🟢' if key_ok else '🔴'} {active_label}: `{active}`{missing_part}")

    with st.expander(t("Per-agent temperatures", LANG)):
        st.slider(t("Definer", LANG), 0.0, 1.5, 0.2, 0.1, key="temp_definer")
        st.slider(t("Transformer", LANG), 0.0, 1.5, 0.9, 0.1, key="temp_transformer")
        st.slider(t("Explorer", LANG), 0.0, 1.5, 0.7, 0.1, key="temp_explorer")
        st.slider(t("Translator", LANG), 0.0, 1.5, 0.3, 0.1, key="temp_translator")

    st.divider()

    # Phase progress
    session = st.session_state.pipeline.session
    steps = [
        (t("1. Definer", LANG), session.problem is not None),
        (t("2. Transformer", LANG), bool(session.metaphor_candidates)),
        (t("3. Explorer", LANG), bool(session.moves)),
        (t("4. Translator", LANG), bool(session.solutions)),
    ]
    done = sum(1 for _, ok in steps if ok)
    st.progress(
        done / len(steps),
        text=t("{done}/{total} stages", LANG).format(done=done, total=len(steps)),
    )
    for name, ok in steps:
        st.markdown(f"{'✅' if ok else '⏳'} {name}")

    st.divider()

    # Save session
    if session.problem is not None:
        if st.button(t("💾 Save session", LANG), use_container_width=True):
            store = MarkdownStore(ROOT / "data" / "runs")
            slug = (session.problem.summary[:30].replace(" ", "_").lower() or "session")
            saved = store.save(session, slug=slug)
            st.session_state.saved_path = str(saved)
            st.success(t("Saved to `{name}`", LANG).format(name=saved.name))
    if st.session_state.saved_path:
        st.caption(
            t("Last saved: `{name}`", LANG).format(
                name=Path(st.session_state.saved_path).name
            )
        )

    if st.button(t("🔄 Reset session", LANG), use_container_width=True):
        st.session_state.pipeline = Pipeline()
        st.session_state.messages = []
        st.session_state.phase = "definer"
        st.session_state.baseline_text = None
        st.session_state.saved_path = None
        st.rerun()

    # --- Import a saved session -----------------------------------------
    def _phase_for(s: Session) -> str:
        """Decide which phase to land in based on what's already filled in."""
        if s.solutions:
            return "translator"
        if s.moves:
            return "explorer"
        if s.metaphor_candidates:
            return "transformer"  # show metaphors so user can pick (or already chose)
        return "definer"

    def _apply_loaded_session(session: Session, source_label: str) -> None:
        """Replace the running Pipeline with one that wraps the loaded session."""
        new_pl = Pipeline(session=session)
        st.session_state.pipeline = new_pl
        st.session_state.messages = []
        st.session_state.phase = _phase_for(session)
        st.session_state.baseline_text = None
        st.session_state.saved_path = None
        st.toast(
            t("Loaded session ({source}).", LANG).format(source=source_label),
            icon="📂",
        )

    with st.expander("📂 " + t("Import session", LANG)):
        store_for_list = MarkdownStore(ROOT / "data" / "runs")
        saved_folders = store_for_list.list_sessions()
        if saved_folders:
            options = ["—"] + [f.name for f in saved_folders]
            choice = st.selectbox(
                t("Saved sessions", LANG),
                options=options,
                index=0,
                key="import_pick",
                help=t("Pick a previously saved session from data/runs/.", LANG),
            )
            if choice != "—" and st.button(
                "📥 " + t("Load", LANG),
                use_container_width=True,
                key="btn_load_local",
            ):
                folder = next(f for f in saved_folders if f.name == choice)
                try:
                    loaded = store_for_list.load(folder)
                    _apply_loaded_session(loaded, choice)
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ {t('Error', LANG)}: {type(e).__name__}: {e}")
        else:
            st.caption(t("No saved sessions in data/runs/ yet.", LANG))

        uploaded = st.file_uploader(
            t("Upload session.json", LANG),
            type=["json"],
            key="import_upload",
            help=t("External session from another machine.", LANG),
        )
        if uploaded is not None and st.button(
            "📥 " + t("Load uploaded session", LANG),
            use_container_width=True,
            key="btn_load_upload",
        ):
            try:
                loaded = load_session_from_json(uploaded.getvalue())
                _apply_loaded_session(loaded, uploaded.name)
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ {t('Error', LANG)}: {type(e).__name__}: {e}")


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
    st.markdown(f"**{t('Summary:', LANG)}** {problem.summary}")
    with st.expander(
        t("Entities ({n})", LANG).format(n=len(problem.entities)), expanded=True
    ):
        for e in problem.entities:
            attrs = ", ".join(e.attributes) or t("_(none detected)_", LANG)
            st.markdown(f"- **{e.name}** _({e.role})_ — {attrs}")
    with st.expander(
        t("Relations ({n})", LANG).format(n=len(problem.relations)), expanded=False
    ):
        for r in problem.relations:
            st.markdown(f"- `{r.source}` --{r.kind}--> `{r.target}` _(str {r.strength:.1f})_")
    with st.expander(
        t("Tensions ({n})", LANG).format(n=len(problem.tensions)), expanded=True
    ):
        for t_ in problem.tensions:
            st.markdown(f"- ⚡ {t_}")
        if not problem.tensions:
            st.caption(t("_(none detected)_", LANG))
    with st.expander(t("Constraints / Goals", LANG), expanded=False):
        for c in problem.constraints:
            st.markdown(f"- ⛔ {c}")
        for g in problem.goals:
            st.markdown(f"- 🎯 {g}")
    with st.expander(t("Raw JSON", LANG), expanded=False):
        st.json(problem.model_dump())


def render_metaphor_card(m: MetaphorSpec, idx: int, chosen: bool) -> None:
    with st.container(border=True):
        col_title, col_pick = st.columns([5, 1])
        with col_title:
            prefix = "✅ " if chosen else ""
            st.markdown(f"#### {prefix}{m.domain.replace('_', ' ').title()}")
        with col_pick:
            if not chosen and st.button(
                t("Select", LANG), key=f"pick_{idx}", use_container_width=True
            ):
                st.session_state.pipeline.session.chosen_metaphor = m
                st.session_state.phase = "explorer"
                _push_msg(
                    "assistant",
                    t(
                        "Metaphor **{domain}** selected. Click **🎲 Generate first move** "
                        "below — the Explorer will propose moves and you curate (steer, "
                        "redo, or accept).",
                        LANG,
                    ).format(domain=m.domain.replace("_", " ").title()),
                )
                st.rerun()
        st.caption(m.domain_intro)
        with st.expander(
            t("Mappings ({n})", LANG).format(n=len(m.mappings)), expanded=chosen
        ):
            for mp in m.mappings:
                c1, c2, c3, c4 = st.columns([3, 3, 1, 3])
                c1.markdown(f"**{mp.original}**")
                c2.markdown(f"→ *{mp.metaphor}*")
                c3.markdown(f"{_fidelity_color(mp.fidelity)} `{mp.fidelity:.2f}`")
                c4.caption(f"⚠️ {mp.leak}" if mp.leak else "_no leak_")
        if m.invariants_preserved:
            with st.expander(t("Preserved", LANG)):
                for inv in m.invariants_preserved:
                    st.markdown(f"- ✔ {inv}")
        if m.invariants_broken:
            with st.expander(t("Broken", LANG)):
                for inv in m.invariants_broken:
                    st.markdown(f"- ✖ {inv}")


def render_move(move: Move, idx: int) -> None:
    with st.container(border=True):
        st.markdown(
            t("**Move {idx}: {actor}**", LANG).format(idx=idx, actor=move.actor)
        )
        st.markdown(f"_{move.action}_")
        st.markdown(f"**→** {move.consequence}")
        if move.obstacle:
            st.caption(f"🚧 {move.obstacle}")


def render_solution(sol: Solution, idx: int) -> None:
    conf_color = "🟢" if sol.confidence >= 0.7 else ("🟡" if sol.confidence >= 0.5 else "🔴")
    with st.container(border=True):
        sol_label = t("**Solution {idx}**", LANG).format(idx=idx)
        conf_label = t("confidence", LANG)
        st.markdown(f"{sol_label} {conf_color} {conf_label} `{sol.confidence:.0%}`")
        st.caption(f"_{t('Metaphor', LANG)}: {sol.metaphor_idea}_")
        st.markdown(f"**→ {sol.original_domain_translation}**")
        if sol.caveats:
            with st.expander(t("Caveats", LANG)):
                for c in sol.caveats:
                    st.markdown(f"- ⚠️ {c}")


# ---------------------------------------------------------------------------
# Left: chat (adapts to current phase)
# ---------------------------------------------------------------------------

pipeline: Pipeline = st.session_state.pipeline
phase: str = st.session_state.phase

with chat_col:
    st.subheader(t("Conversation", LANG))

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Phase: Definer ---
    if phase == "definer":
        prompt = st.chat_input(t("Describe your problem…", LANG))
        if prompt:
            _push_msg("user", prompt)
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    with st.spinner(t("Definer is extracting structure...", LANG)):
                        problem = pipeline.run_definer(prompt)
                    p = problem
                    if LANG == "de":
                        summary_msg = (
                            f"Extrahiert: **{len(p.entities)} Entitäten**, "
                            f"**{len(p.relations)} Relationen**, "
                            f"**{len(p.tensions)} Spannungen**.\n\n"
                            f"_Zusammenfassung:_ {p.summary}"
                        )
                        if p.unknowns:
                            summary_msg += "\n\n**Offene Fragen:**\n" + "\n".join(
                                f"- {u}" for u in p.unknowns
                            )
                    else:
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
                    err = t("⚠️ Definer failed: `{err}`", LANG).format(err=_format_error(e))
                    st.error(err)
                    _push_msg("assistant", err)

    # --- Phase: Transformer (pick a metaphor) ---
    elif phase == "transformer":
        if not pipeline.session.metaphor_candidates:
            if st.button(
                t("⚙️ Generate 3 metaphors", LANG),
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(
                    t("Generating 3 metaphors in parallel (one per seed domain)…", LANG)
                ):
                    try:
                        candidates = pipeline.run_transformer(n=3)
                        msg = t(
                            "Generated {n} metaphor candidate(s). Pick one to begin exploring.",
                            LANG,
                        ).format(n=len(candidates))
                        _push_msg("assistant", msg)
                        with st.chat_message("assistant"):
                            st.markdown(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(
                            t("⚠️ Definer failed: `{err}`", LANG)
                            .replace("Definer", "Transformer")
                            .format(err=_format_error(e))
                        )
        else:
            # Surface silent partial failures (e.g. 2 of 3 succeeded)
            n_got = len(pipeline.session.metaphor_candidates)
            errors = getattr(pipeline, "last_transformer_errors", [])
            if n_got < 3 and errors:
                fail_count = len(errors)
                st.warning(
                    t(
                        "Only {got} of {want} metaphors succeeded — {fail_count} failed silently.",
                        LANG,
                    ).format(got=n_got, want=3, fail_count=fail_count)
                )
                # Show first error for diagnostics
                with st.expander("🔍 " + t("Error details", LANG)):
                    for err_line in errors:
                        st.code(err_line)
                if st.button(t("Retry failed runs", LANG), use_container_width=True):
                    # Re-roll all of them
                    pipeline.session.metaphor_candidates = []
                    pipeline.session.chosen_metaphor = None
                    pipeline.last_transformer_errors = []
                    st.rerun()
            st.info(t("Pick a metaphor from the panel →", LANG))

    # --- Phase: Explorer (autonomous generation, user curates) ---
    elif phase == "explorer":
        chosen = pipeline.session.chosen_metaphor
        n_moves = len(pipeline.session.moves)
        if chosen:
            domain_name = chosen.domain.replace("_", " ").title()
            st.caption(
                t(
                    "Exploring **{domain}** — the Explorer proposes moves, you curate. "
                    "Move count: **{n}**.",
                    LANG,
                ).format(domain=domain_name, n=n_moves)
            )

        def _run_explorer(directive: str | None, force_different: bool) -> None:
            try:
                spinner_text = t(
                    "Explorer trying a fundamentally different strategy…"
                    if force_different
                    else "Explorer proposing next move…",
                    LANG,
                )
                with st.spinner(spinner_text):
                    move = pipeline.run_explorer_turn(
                        directive=directive,
                        force_different=force_different,
                    )
                move_msg = (
                    t("**Move {idx}: {actor}**", LANG).format(
                        idx=len(pipeline.session.moves), actor=move.actor
                    )
                    + f"\n\n_{move.action}_\n\n**→** {move.consequence}\n\n🚧 _{move.obstacle}_"
                )
                _push_msg("assistant", move_msg)
                # Clear steering ONLY AFTER it has been consumed; do not
                # mutate st.session_state.steering_input directly during
                # the same run as the text_area widget — Streamlit forbids
                # that. Use a sentinel flag instead, processed at the top
                # of the next rerun.
                st.session_state.clear_steering_on_next_run = True
                st.rerun()
            except Exception as e:
                err = t("⚠️ Explorer failed: `{err}`", LANG).format(err=_format_error(e))
                st.error(err)
                _push_msg("assistant", err)

        # Process pending steering-clear signal from a previous run BEFORE
        # creating the widget (Streamlit doesn't allow mutating widget
        # state after the widget is instantiated).
        if st.session_state.get("clear_steering_on_next_run"):
            st.session_state.steering_input = ""
            st.session_state.clear_steering_on_next_run = False

        # --- STEERING TEXT FIRST (visible above the buttons) ----------
        # Putting the text input ABOVE the buttons makes the flow obvious:
        # 1) type optional steering (or leave blank)
        # 2) click one of the buttons below — your text gets sent with that click.
        st.text_area(
            t("Steering text (gets sent with the NEXT click below)", LANG),
            value=st.session_state.get("steering_input", ""),
            key="steering_input",
            height=80,
            placeholder=t(
                "Leave empty for full autonomy. Or steer: 'focus on the quieter "
                "members', 'try a structural rule change', 'the last consequence "
                "wasn't realistic, redo it'…",
                LANG,
            ),
        )
        steering = st.session_state.get("steering_input", "")

        # Visual cue: arrow pointing from text → buttons, so it's obvious
        # the text input feeds into the buttons.
        if steering.strip():
            st.caption("⬇️ " + t("Will be sent with the next click below:", LANG))

        # --- Control row: Generate / Try different / Undo --------------
        col_gen, col_diff, col_undo = st.columns([3, 3, 2])

        with col_gen:
            btn_label = (
                t("🎲 Generate first move", LANG) if n_moves == 0
                else t("🎲 Continue exploring", LANG)
            )
            if st.button(btn_label, type="primary", use_container_width=True):
                _run_explorer(directive=steering or None, force_different=False)

        with col_diff:
            disabled = n_moves == 0
            if st.button(
                t("🔄 Try different angle", LANG),
                use_container_width=True,
                disabled=disabled,
                help=t(
                    "Force the next move to use a strategy structurally unlike all prior moves.",
                    LANG,
                ),
            ):
                _run_explorer(directive=steering or None, force_different=True)

        with col_undo:
            disabled = n_moves == 0
            if st.button(
                t("↩️ Undo last", LANG),
                use_container_width=True,
                disabled=disabled,
                help=t(
                    "Remove the most recent move (e.g. if it broke the metaphor or felt off).",
                    LANG,
                ),
            ):
                popped = pipeline.undo_last_move()
                if popped:
                    _push_msg(
                        "assistant",
                        t(
                            "(Undid Move {n}: {actor} — {action_short}…)",
                            LANG,
                        ).format(
                            n=n_moves, actor=popped.actor, action_short=popped.action[:60]
                        ),
                    )
                    st.rerun()

        # --- Hint when there's enough material to translate -----------
        if n_moves >= 5:
            st.info(
                t(
                    "You have **{n} moves** — usually plenty for the Translator. "
                    "Consider proceeding to solutions.",
                    LANG,
                ).format(n=n_moves)
            )

        if pipeline.session.moves:
            if st.button(
                t("🔁 Translate moves to solutions →", LANG),
                type="secondary" if n_moves < 3 else "primary",
                use_container_width=True,
                help=t(
                    "End the exploration phase. Each move becomes one candidate solution.",
                    LANG,
                ),
            ):
                st.session_state.phase = "translator"
                st.rerun()

    # --- Phase: Translator ---
    elif phase == "translator":
        if not pipeline.session.solutions:
            if st.button(
                t("⚙️ Run Translator", LANG),
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(
                    t("Translator mapping insights back to original domain…", LANG)
                ):
                    try:
                        solutions = pipeline.run_translator()
                        sol_msg = t(
                            "Generated **{n} solution(s)**. See the panel for details.",
                            LANG,
                        ).format(n=len(solutions))
                        _push_msg("assistant", sol_msg)
                        with st.chat_message("assistant"):
                            st.markdown(sol_msg)
                        st.rerun()
                    except Exception as e:
                        st.error(
                            t("⚠️ Translator failed: `{err}`", LANG).format(
                                err=_format_error(e)
                            )
                        )
        else:
            # Show solutions in chat column
            for i, sol in enumerate(pipeline.session.solutions, 1):
                render_solution(sol, i)

            # Baseline comparison
            st.divider()
            if st.session_state.baseline_text is None:
                if st.button(
                    t("🔍 Show baseline LLM answer (no metaphor)", LANG),
                    use_container_width=True,
                ):
                    with st.spinner(t("Generating baseline…", LANG)):
                        try:
                            baseline = pipeline.run_baseline()
                            st.session_state.baseline_text = baseline
                            st.rerun()
                        except Exception as e:
                            st.error(
                                t("⚠️ Baseline failed: `{err}`", LANG).format(
                                    err=_format_error(e)
                                )
                            )
            else:
                with st.expander(
                    t("📊 Baseline (direct LLM, no metaphor)", LANG), expanded=True
                ):
                    st.markdown(st.session_state.baseline_text)

            if st.button(t("← Back to Explorer", LANG), use_container_width=True):
                st.session_state.phase = "explorer"
                st.rerun()


# ---------------------------------------------------------------------------
# Right: structure panel (adapts to phase)
# ---------------------------------------------------------------------------

with structure_col:
    session = pipeline.session

    if phase == "definer" and session.problem is None:
        st.subheader(t("Problem structure", LANG))
        st.caption(t("Describe your problem in the chat to begin.", LANG))

    elif phase in ("definer", "transformer") and session.problem is not None:
        st.subheader(t("Problem structure", LANG))
        render_problem_panel(session.problem)

        if session.metaphor_candidates:
            st.divider()
            st.subheader(t("Metaphor worlds", LANG))
            chosen = session.chosen_metaphor
            for i, m in enumerate(session.metaphor_candidates):
                render_metaphor_card(m, i, chosen is not None and chosen.domain == m.domain)

    elif phase == "explorer":
        chosen = session.chosen_metaphor
        if chosen:
            st.subheader(
                f"{t('World', LANG)}: {chosen.domain.replace('_', ' ').title()}"
            )
            st.caption(chosen.domain_intro)
            with st.expander(t("Mapping table", LANG), expanded=False):
                for mp in chosen.mappings:
                    st.markdown(
                        f"- **{mp.original}** → *{mp.metaphor}* "
                        f"{_fidelity_color(mp.fidelity)}"
                    )
                    if mp.leak:
                        st.caption(f"  ⚠️ {mp.leak}")

        st.divider()
        st.subheader(f"{t('Move log', LANG)} ({len(session.moves)})")
        if not session.moves:
            st.caption(t("No moves yet — generate one with the buttons on the left.", LANG))
        for i, move in enumerate(session.moves, 1):
            render_move(move, i)

    elif phase == "translator":
        st.subheader(t("Solutions", LANG))
        if not session.solutions:
            st.caption(t("Run the Translator to see solutions here.", LANG))
        else:
            for i, sol in enumerate(session.solutions, 1):
                render_solution(sol, i)

        st.divider()
        st.subheader(t("Move log", LANG))
        for i, move in enumerate(session.moves, 1):
            render_move(move, i)
