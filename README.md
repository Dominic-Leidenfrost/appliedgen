# Metaphor Machine

An interactive multi-agent system that maps a user-defined problem into a *metaphor domain* (pirate adventure, fluid dynamics, medieval kingdom, sports league, ...), explores solutions in that domain together with the user, and translates the insights back to the original problem.

Course project for **Applied Generative AI (TU Wien, SS 2026)**.

---

## Why metaphors

LLMs are strong at chain-of-thought reasoning *within* a frame, but they collapse to generic advice when the frame is unhelpful. Recasting a problem ("step counter ↔ frequency-space peaks", "non-linear data ↔ kernel-trick lift") often turns an impossible problem into a trivial one. The Metaphor Machine does this transformation explicitly: extract structure → map to a new domain → solve there → translate back → flag where the analogy leaks.

---

## Quickstart

Requires **Python 3.11+**.

```bash
# 1. Clone
git clone https://github.com/Dominic-Leidenfrost/appliedgen.git
cd appliedgen

# 2. Create a venv (any tool works; example uses the stdlib)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install deps
pip install -r requirements.txt

# 4. Configure at least one LLM provider
cp .env.example .env
# then edit .env and paste an ANTHROPIC_API_KEY and/or OPENAI_API_KEY

# 5. Run the UI
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501`.

### CLI / smoke test (no UI)

```bash
python -m metaphor_machine.cli "I have a small team and too many priorities."
```

---

## Repository layout

```
.
├── app/                          # Streamlit UI
├── src/metaphor_machine/
│   ├── agents/                   # 4 agents (definer, transformer, explorer, translator)
│   ├── core/                     # pipeline, schemas (Problem, Metaphor, Session)
│   ├── llm/                      # provider-agnostic client (LiteLLM)
│   ├── prompts/                  # versioned prompt templates
│   └── storage/                  # markdown-based session persistence
├── examples/domains/             # seed metaphor domains (yaml)
├── docs/
│   ├── architecture-sketch.excalidraw
│   └── ...
├── data/runs/                    # session transcripts (gitignored)
├── tests/
├── PLAN.md                       # detailed implementation plan & roadmap
├── pyproject.toml
└── README.md
```

---

## Configuration

All configuration is done through environment variables (or the in-app sidebar).

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required if using Claude models |
| `OPENAI_API_KEY` | — | Required if using GPT models |
| `METAPHOR_DEFAULT_MODEL` | `anthropic/claude-sonnet-4-6` | Any LiteLLM model string |
| `METAPHOR_DEFAULT_TEMPERATURE` | `0.7` | Higher for exploration, lower for extraction |
| `METAPHOR_DATA_DIR` | `./data/runs` | Where session markdown files are written |

The UI sidebar can override the model and temperature per agent (useful for the "low temp for extraction, high temp for exploration" pattern described in `PLAN.md`).

---

## Development

```bash
pip install -e ".[dev]"
pytest                  # run tests
ruff check src tests    # lint
ruff format src tests   # format
```

---

## Team

Group of 3 — Applied Generative AI, SS 2026, TU Wien.

## License

For coursework. Not licensed for redistribution.
