# Metaphor Machine — Implementation Plan

> **Course:** Applied Generative AI, TU Wien, SS 2026
> **Topic:** #2 Metaphor Machine
> **Team:** 3 people (~300h total)
> **Stack:** Python 3.11 · Streamlit · LiteLLM (Anthropic + OpenAI) · Pydantic
> **Deliverables:** Poster (3×A3) + PoC (this repo) + screencast + CHANGES.md

This document is the working plan: architecture, agent design, what to build sprint-by-sprint, the answers to the questions your team wrote in the Excalidraw, and the risks to watch.

---

## 1. Goal & success criteria

We are **not** building "a chatbot that suggests analogies". We are building a pipeline that:

1. **Extracts structure** from a vague problem (entities, relationships, constraints, goals, tensions).
2. **Transforms** that structure into a different domain *preserving relational fidelity*.
3. **Explores** the metaphor world interactively with the user — generating concrete moves, obstacles, and candidate solutions.
4. **Translates** insights back to the original domain.
5. **Flags where the analogy leaks** — this is explicitly a learning goal and is often the most valuable output.

**Definition of "it works":** for at least 3 seed problems (one mechanical, one organizational, one social), the system produces a metaphor with ≥4 structural correspondences AND surfaces ≥1 idea the user rates as "non-obvious" AND correctly flags at least one place where the metaphor breaks down.

---

## 2. Architecture overview

The Excalidraw sketch is essentially right. The refinement is to make **structure a first-class artifact** (not just chat) and to keep the four agents narrowly scoped.

```
                           ┌────────────────────────────────┐
                           │            STREAMLIT UI         │
                           │  (chat + structure panel + 🎲) │
                           └───────────────┬────────────────┘
                                           │
                                           ▼
        ┌──────────────────────────  PIPELINE / ORCHESTRATOR  ──────────────────────────┐
        │                                                                                │
        │  ┌─────────────┐    ┌──────────────────┐    ┌────────────────┐    ┌────────┐  │
        │  │  DEFINER    │───▶│  TRANSFORMER ×N  │───▶│   EXPLORER      │───▶│ TRANS- │  │
        │  │  agent      │    │  agent           │    │   agent (loop)  │    │ LATOR  │  │
        │  └─────────────┘    └──────────────────┘    └────────────────┘    └────────┘  │
        │        │                    │                       │                    │     │
        │        ▼                    ▼                       ▼                    ▼     │
        │   ProblemSpec          MetaphorSpec             MoveLog            Solution    │
        │   (Pydantic)           (Pydantic, ×N)           (Pydantic)         (Pydantic)  │
        └────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                              ┌──────────────────────────┐
                              │  STORAGE (markdown +     │
                              │  JSON sidecar per run)   │
                              └──────────────────────────┘
```

### The four agents

| Agent | Job | Temperature | Output |
|---|---|---|---|
| **Definer** | Talk to the user, extract `ProblemSpec` (entities, relations, constraints, goals, tensions). Asks max 5 clarifying questions. | low (0.2) | `ProblemSpec` |
| **Transformer** | Given `ProblemSpec`, propose **3 metaphor domains** with explicit per-element mappings. Run 3 instances in parallel to get diverse domains. | high (0.9) + diversity prompt | 3× `MetaphorSpec` |
| **Explorer** | Inside the chosen metaphor, play out scenarios. Generates *moves*, obstacles, candidate strategies. Conversational with user. | medium (0.7) | `MoveLog` |
| **Translator** | Pull each metaphor-move back to the original domain via the mapping table. Explicitly flag mappings that broke. | low (0.3) | `Solution` |

These are **stateless agents** that read/write Pydantic objects. The orchestrator owns the state; this is much easier to debug than passing chat history around.

### Why this beats the "one big agent" approach

A single agent collapses into generic advice ("just collaborate to find the treasure!") because every token has to do every job. Splitting the work means each prompt can be **narrow, opinionated, and adversarial** ("you are not allowed to use the words 'collaborate', 'communicate', 'align'"). This is the core insight the assignment is pushing.

---

## 3. Data schemas (the contracts between agents)

Defined in `src/metaphor_machine/core/`. Everything is Pydantic so we get free validation + JSON serialization for storage.

```python
class Entity(BaseModel):
    name: str
    role: str            # "actor" | "resource" | "obstacle" | "environment"
    attributes: list[str]

class Relation(BaseModel):
    source: str          # entity name
    target: str
    kind: str            # "depends_on" | "competes_with" | "transforms" | ...
    strength: float = 0.5

class ProblemSpec(BaseModel):
    raw_user_text: str
    summary: str
    entities: list[Entity]
    relations: list[Relation]
    constraints: list[str]
    goals: list[str]
    tensions: list[str]               # contradictions in the problem
    unknowns: list[str]               # what the Definer still wants to know

class Mapping(BaseModel):
    original: str                     # entity / relation in source domain
    metaphor: str                     # what it becomes in target domain
    fidelity: float                   # 0–1, how well it preserves structure
    leak: str | None = None           # where this mapping breaks down

class MetaphorSpec(BaseModel):
    domain: str                       # "pirate adventure"
    domain_intro: str                 # 3–4 sentence world-building
    mappings: list[Mapping]
    invariants_preserved: list[str]
    invariants_broken: list[str]

class Move(BaseModel):
    actor: str                        # entity in the metaphor
    action: str
    consequence: str
    obstacle: str | None = None

class Solution(BaseModel):
    metaphor_idea: str                # original idea in metaphor space
    original_domain_translation: str  # translated back
    confidence: float
    caveats: list[str]                # places the analogy may have misled us
```

---

## 4. The hard parts (and how we beat them)

### 4.1 Preventing generic-advice collapse

This is the project's headline risk. Mitigations, in priority order:

1. **Forbid weasel words in the Explorer system prompt.** Hard list: "collaborate", "communicate", "align", "synergy", "leverage", "stakeholder", "best practice", "find a way". Penalize any output containing them; regenerate with the offending word quoted back.
2. **Force concrete entity names.** The Explorer must reference entities from the `MetaphorSpec.mappings` by name — never "the team", always "Captain Reyes". Symbolic check after generation.
3. **Require ≥1 obstacle per move.** Schema-enforced via Pydantic — `Move.obstacle` is optional in the type but required by a post-generation validator.
4. **Demand structural fidelity in the Transformer.** Ask for ≥4 mappings AND a `leak` field on each. A mapping with `fidelity > 0.9` and `leak == None` triggers a regeneration ("you're being lazy, find where it breaks").
5. **Use temperature deliberately.** Definer/Translator low (factual); Transformer high (variety); Explorer medium (creative but grounded).

### 4.2 Reliable structure extraction

Use **JSON mode / structured outputs** end-to-end. Anthropic supports tool-use schemas, OpenAI has `response_format`. LiteLLM normalizes both. If a response fails Pydantic validation, retry up to 2× with the error message appended ("Your previous response had this validation error: ...").

### 4.3 Diversity of proposed domains

Spawn 3 Transformer instances in parallel, each with a different *style hint* drawn from a seeded pool (`examples/domains/*.yaml` — pirate, ecosystem, kitchen, courtroom, sports, fluid dynamics, video game, ...). Then run a quick "diversity check" prompt that picks the 3 most structurally different.

### 4.4 Keeping the user in control

Every step of the pipeline produces an artifact the user can **edit in the UI** before the next step runs. The Excalidraw sketch implied this; we make it explicit. Specifically:
- After Definer: editable `ProblemSpec` panel.
- After Transformer: user picks 1 of 3 metaphors, can rewrite any mapping.
- During Explorer: user can branch the conversation, reject a move, or jump back.
- After Translator: user marks solutions as "interesting / obvious / wrong".

---

## 5. Answers to the Excalidraw questions

> **"Wie wird das gespeichert?"**
Per session: one folder `data/runs/<timestamp>-<slug>/` containing `problem.md` (rendered ProblemSpec), `metaphors.md` (all 3 candidates), `transcript.md` (the Explorer chat), `solutions.md` (final Translator output), and `session.json` (the raw Pydantic blob, for replay). Markdown for humans, JSON for programmatic reload.

> **"Macht es Sinn mit der Temperatur rumzuspielen? Können wir das über die API steuern?"**
Yes and yes. LiteLLM passes `temperature` to both Anthropic and OpenAI. The four agents get different defaults (see table in §2). The sidebar exposes per-agent overrides so we can A/B during the poster prep.

> **"Sollen wir dem Agent etwas aktiv verbieten?"**
Yes — see §4.1. The forbidden-words list is the single highest-leverage thing we can do to prevent generic-advice collapse. Make it a config file (`src/metaphor_machine/prompts/forbidden_words.yaml`) so we can iterate without code changes.

> **"Wollen wir aus der alten Domain mögliche Lösungen mitgeben?"**
**No** during the Transformer step (it would bias the metaphor). **Yes** at the very end as a comparison: the Translator can optionally generate a "baseline LLM answer" and the user sees both side-by-side. This actually doubles as our evaluation story for the poster: "look how different (and better) the metaphor-derived ideas are vs. the baseline".

> **"Dem User direkt mehrere verschiedene Domains anbieten, die von mehreren Agents erstellt werden?"**
Yes — 3 parallel Transformer runs (§4.3). User picks one. The other two stay accessible ("try this idea in a different metaphor") because the cost is already paid.

> **"Grundsätzlich verschiedene Example Domains aufstellen?"**
Yes — `examples/domains/*.yaml`. Each seed defines: domain name, vocabulary list, archetypal entities, typical relations. Used as **style hints**, not as fixed templates. Start with ~8 seeds covering a broad space: mechanical (fluid dynamics, ecosystem), social (medieval kingdom, sports league), narrative (pirate adventure, heist movie), abstract (kitchen, garden).

> **"Soll der Ursprungs-Prompt Examples beinhalten? Falls ja, wie stark schrenken wir uns damit ein?"**
Yes for *format* (1-shot showing what a good `ProblemSpec` looks like), no for *content* (no example problems — that primes the model toward those domains). Few-shot the schema, not the answer.

> **"UI?"**
Streamlit. Three-column layout: chat (left), live `ProblemSpec`/`MetaphorSpec` editor (center), session timeline + 🎲 "try another metaphor" button (right). Streamlit's `st.chat_message` + `st.session_state` covers 90% of what we need.

---

## 6. Sprint plan (8 weeks → 18.06.2026 deadline)

> Today is 2026-05-23, so we have ~4 weeks until submission and the poster session sits inside that window. The plan below is compressed accordingly.

### Sprint 1 — Skeleton & Definer (week 1, by 2026-05-30)
- [x] Repo + structure + CI-lite (just `ruff check` on push)
- [ ] LiteLLM wrapper with retries (`src/metaphor_machine/llm/client.py`)
- [ ] Pydantic schemas (`core/schemas.py`)
- [ ] **Definer agent** end-to-end with structured outputs
- [ ] Streamlit hello-world that runs the Definer and shows the `ProblemSpec`
- [ ] 3 seed problems written down in `tests/fixtures/problems.yaml`

### Sprint 2 — Transformer & seed domains (week 2, by 2026-06-06)
- [ ] 8 seed domains in `examples/domains/`
- [ ] **Transformer agent** with parallel runs + diversity selection
- [ ] Forbidden-words enforcement utility (regen loop)
- [ ] UI: show 3 metaphors as cards, user picks one, can edit mappings
- [ ] **Poster v1** drafted (sections: title, abstract, problem, approach diagram)

### Sprint 3 — Explorer & Translator (week 3, by 2026-06-13)
- [ ] **Explorer agent** with move generation, obstacle requirement
- [ ] **Translator agent** with leak-flagging
- [ ] Storage layer (markdown + JSON sidecar)
- [ ] Baseline-LLM-answer toggle for comparison
- [ ] **Poster session** — bring laptop with live demo

### Sprint 4 — Polish + submission (week 4, by 2026-06-18)
- [ ] Incorporate poster-session feedback → `CHANGES.md`
- [ ] Tests for each agent (smoke + JSON-schema-validity)
- [ ] Screencast (~3-5 min walkthrough)
- [ ] Final poster revision
- [ ] Hand-in ZIP

### Work split suggestion (3 people)
- **Person A — Pipeline & LLM plumbing:** LiteLLM wrapper, schemas, orchestrator, storage, tests.
- **Person B — Agents & prompts:** Definer, Transformer, Explorer, Translator + their prompt templates + seed domains + forbidden-words tuning.
- **Person C — UI & evaluation:** Streamlit app, editable panels, baseline-comparison view, screencast, poster.

Sync points: end of each sprint, plus a brief weekly check-in. Prompt iteration is the bottleneck — Person B should not wait for Person A's pipeline; both work against the same Pydantic contract.

---

## 7. Risks & open questions

| Risk | Mitigation |
|---|---|
| Generic-advice collapse | §4.1 — forbidden words, named entities, obstacle requirement |
| Structured output failures (esp. with smaller models) | LiteLLM JSON mode + Pydantic retry loop (max 2) |
| Latency (4 sequential agents + 3 parallel Transformers ≈ 20s) | Stream tokens in UI; show progress per agent; cache by `(problem_hash, agent, model)` |
| API cost during prompt iteration | Default to `claude-haiku-4-5` for dev, switch to `claude-sonnet-4-6` for "real" runs (sidebar toggle) |
| Evaluating "is the idea actually good?" | Pre-poster: 5 friends try 3 problems each; rate ideas 1–5 on novelty + actionability; report numbers on poster |
| Scope creep (especially around UI) | UI is a Streamlit prototype, not a product. Three columns, no fancy animations. |

### Things we explicitly punted
- Vector DB / RAG over domain knowledge — not needed; seed domains are small enough to inline.
- Multi-turn memory across sessions — out of scope; each problem is a fresh session.
- Fine-tuning — prompt engineering + structured outputs is sufficient for the assignment's learning goals.
- Graphical game — assignment explicitly says text is fine.

---

## 8. Evaluation story for the poster

We need numbers. Plan:

1. Curate **5 problems** (mix of mechanical, organizational, social).
2. For each problem, generate **(a)** baseline LLM answer (single prompt, "give me 3 ideas to solve X"), **(b)** Metaphor Machine output.
3. Have **8–10 people** rate both anonymously on:
   - *Novelty* (1–5): "would I have thought of this myself?"
   - *Actionability* (1–5): "could I do something with this tomorrow?"
   - *Specificity* (1–5): "does it talk about MY problem or anyone's problem?"
4. Plot mean ± std per problem, both methods. This becomes the **Results** panel of the poster.

This is small-n and not publishable, but it's exactly what the rubric is looking for under "creativity" and "scope/complexity".

---

## 9. Reference notes

- LiteLLM docs: https://docs.litellm.ai
- Anthropic tool use / structured output: https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
- Streamlit chat UI: https://docs.streamlit.io/develop/api-reference/chat
- Assignment text: see TUWEL, course `Applied Generative AI SS2026`

The original architecture sketch lives at `docs/architecture-sketch.excalidraw` — open it in https://excalidraw.com to edit.
