# Metaphor Machine: Implementation Study Guide

This guide summarizes the implementation details of the Applied Generative AI
course project and gives practice multiple-choice questions with answers and
explanations.

## 1. Project Purpose

The project is called **Metaphor Machine**. It is an interactive multi-agent
system that helps users solve open-ended problems by translating the original
problem into a metaphor domain, exploring ideas inside that domain, and then
translating the insights back into the original domain.

The basic reasoning loop is:

1. Extract the structure of the user's problem.
2. Map that structure into a metaphor world.
3. Explore possible actions inside the metaphor world.
4. Translate those actions back into concrete solutions.
5. Optionally compare the metaphor-based answer against a direct LLM baseline.

The main user interface is a Streamlit app in `app/streamlit_app.py`.

## 2. Repository Structure

Important folders and files:

| Path | Purpose |
|---|---|
| `app/streamlit_app.py` | Streamlit UI and interactive workflow |
| `src/metaphor_machine/core/pipeline.py` | Orchestrates the whole multi-agent flow |
| `src/metaphor_machine/core/schemas.py` | Pydantic data contracts shared by agents |
| `src/metaphor_machine/agents/` | Agent implementations: Definer, Transformer, Explorer, Translator, Judge |
| `src/metaphor_machine/llm/` | Provider-agnostic LLM wrapper, mock mode, provider registry |
| `src/metaphor_machine/prompts/` | Prompt helpers, language handling, forbidden words, domain loading |
| `src/metaphor_machine/storage/markdown_store.py` | Saves and loads sessions as Markdown plus JSON |
| `src/metaphor_machine/evaluation.py` | Batch evaluation logic using LLM-as-Judge |
| `examples/domains/` | YAML seed domains used by the Transformer |
| `tests/` | Unit and integration tests |

## 3. Main Architecture

The implementation uses a **pipeline plus stateless agents** architecture.

The `Pipeline` class owns the session state and decides which agent runs when.
The individual agents are mostly stateless: each one has a name, a system
prompt, an `LLMConfig`, and a language preference.

The session state is represented by the `Session` dataclass in
`core/pipeline.py`. It stores:

- `raw_input`
- `problem`
- `metaphor_candidates`
- `chosen_metaphor`
- `moves`
- `solutions`

This separation is important. Agents generate structured outputs, while the
pipeline stores those outputs and enforces the workflow order.

## 4. Agent Flow

### Definer Agent

File: `src/metaphor_machine/agents/definer.py`

The Definer converts raw user text into a `ProblemSpec`.

Its job is extraction, not creativity. It must not suggest solutions or use
metaphors. It identifies:

- entities
- relations
- constraints
- goals
- tensions
- unknowns

It uses structured LLM output validated by Pydantic. The code also overwrites
`spec.raw_user_text` with the original user input to guarantee that the raw
input round-trips correctly even if the model paraphrases it.

Default temperature: `0.2`, because extraction should be relatively stable.

### Transformer Agent

File: `src/metaphor_machine/agents/transformer.py`

The Transformer maps a `ProblemSpec` into a `MetaphorSpec`.

It can run in two modes:

- **Seeded mode**: uses YAML domain hints from `examples/domains/`.
- **Free domain mode**: asks the model to invent a non-obvious metaphor domain.

The pipeline runs multiple Transformer calls in parallel using
`ThreadPoolExecutor`. Each call produces one metaphor candidate. The pipeline
then applies a simple diversity filter that prefers different domain names.

The Transformer validates quality and can re-prompt once if:

- fewer than four mappings are produced
- a mapping has very high fidelity but no leak

Default temperature: `0.9`, because metaphor generation benefits from
creativity.

### Explorer Agent

File: `src/metaphor_machine/agents/explorer.py`

The Explorer operates inside the chosen metaphor world. It generates one
`Move` at a time.

A move contains:

- `actor`
- `action`
- `consequence`
- `obstacle`

The Explorer is designed to be autonomous. The user can steer it, ask for a
different angle, or undo the last move, but the Explorer proposes concrete
actions itself.

The Explorer validates its output and can regenerate if the move violates
rules. For example:

- the obstacle must not be empty
- forbidden generic phrases must not appear
- the actor should refer to a known metaphor entity

Default temperature: `0.7`.

### Translator Agent

File: `src/metaphor_machine/agents/translator.py`

The Translator maps Explorer moves back into original-domain solutions.

For every move, it produces one `Solution` with:

- `metaphor_idea`
- `original_domain_translation`
- `confidence`
- `caveats`

The caveats are important because metaphors are imperfect. The Translator uses
mapping leaks to explain where the analogy may mislead.

It also has a `baseline()` method that asks the LLM directly for solutions
without using metaphors. That baseline is later used for comparison.

Default temperature: `0.3`, because translation should be concrete and less
random than metaphor generation.

### Judge Agent

File: `src/metaphor_machine/agents/judge.py`

The Judge compares two answers:

- the Metaphor Machine answer
- the direct baseline answer

The comparison is blind. The answers are shown as Answer A and Answer B, and
their order is randomized to reduce position bias. The Judge evaluates:

- specificity
- actionability
- novelty
- relevance

The raw A/B result is then de-anonymized back into `metaphor`, `baseline`, or
`tie`.

Default temperature: `0.0`, because judging should be reproducible.

## 5. Core Data Schemas

File: `src/metaphor_machine/core/schemas.py`

The project uses Pydantic models as contracts between agents.

Important schemas:

| Schema | Purpose |
|---|---|
| `ProblemSpec` | Structured representation of the user's original problem |
| `Entity` | A concrete actor, resource, obstacle, or environment item |
| `Relation` | A connection between two entities |
| `MetaphorSpec` | A candidate metaphor world |
| `Mapping` | Maps one original concept to one metaphor concept |
| `Move` | One Explorer action inside the metaphor world |
| `Solution` | Back-translated original-domain solution |
| `JudgeVerdict` | Raw blind A/B judge result |
| `ComparisonResult` | De-anonymized judge result |

Pydantic validation is central because LLM output is unreliable unless it is
checked against strict schemas.

## 6. LLM Integration

File: `src/metaphor_machine/llm/client.py`

The project uses **LiteLLM** as a provider-agnostic interface. This lets the
same code call different providers such as Anthropic, OpenAI, Gemini,
OpenRouter, and Groq.

The `LLMClient` supports two main call styles:

- `chat(...)`: returns raw text
- `structured(...)`: returns a Pydantic model instance

For structured output, the client:

1. Adds a JSON schema hint to the prompt.
2. Calls the LLM.
3. Extracts JSON from the response.
4. Validates it with Pydantic.
5. Re-prompts on validation errors, up to a small retry limit.

Mock mode is enabled with `METAPHOR_MOCK=1`. In mock mode, the project uses
canned responses from `llm/mock.py` instead of real API calls. This is useful
for tests, demos, and development without API keys.

## 7. Provider Registry

File: `src/metaphor_machine/llm/providers.py`

The provider registry stores:

- provider display names
- required environment variables
- curated model options
- help text

The function `check_key_for_model()` checks whether the correct API key is
available before an LLM call. For example, Anthropic models require
`ANTHROPIC_API_KEY`, while OpenAI models require `OPENAI_API_KEY`.

## 8. Domain Seeds

File: `src/metaphor_machine/prompts/domains.py`

Seed domains are loaded from YAML files under `examples/domains/`.

Each domain includes information such as:

- name
- display name
- description
- vocabulary
- archetypal entities
- typical relations

The Transformer uses these as style hints. They guide the metaphor domain but
do not directly solve the problem.

The function `pick_diverse()` tries to choose domains from different parts of
the seed pool so that the generated metaphor candidates are not too similar.

## 9. Language Support

File: `src/metaphor_machine/prompts/language.py`

The project supports English and German output. The schema field names stay in
English, but the text values inside the JSON output should be generated in the
selected language.

Language preference is resolved in this order:

1. explicit argument
2. persisted cache file
3. `METAPHOR_LANGUAGE` environment variable
4. default language, English

Language and model choices are persisted under `data/cache/` so Streamlit page
reloads do not reset the user's selection.

## 10. Storage

File: `src/metaphor_machine/storage/markdown_store.py`

Sessions are saved as both Markdown and JSON.

The Markdown files are human-readable:

- `problem.md`
- `metaphors.md`
- `transcript.md`
- `solutions.md`

The JSON files are machine-readable:

- `problem.json`
- `metaphors.json`
- `moves.json`
- `solutions.json`
- `session.json`

The full `session.json` can be loaded later to reconstruct a `Session`.

## 11. Streamlit UI

File: `app/streamlit_app.py`

The UI implements the same phases as the pipeline:

1. Definer
2. Transformer
3. Explorer
4. Translator

It also provides:

- model selection
- language selection
- per-agent temperature controls
- free-domain toggle
- session saving and loading
- baseline comparison
- LLM-as-Judge evaluation
- German and English UI labels

The Streamlit app stores interactive UI state in `st.session_state`, while the
actual project state lives inside the `Pipeline.session`.

## 12. Evaluation

File: `src/metaphor_machine/evaluation.py`

The evaluation logic runs the full pipeline on one or more problems, generates
a direct baseline answer, and then compares the two answers using the Judge.

The headline metric is a **win-rate** for the Metaphor Machine. Ties count as
half a win:

```text
win_rate = (metaphor_wins + 0.5 * ties) / number_of_runs
```

This is useful because open-ended creative problem solving usually has no
single ground-truth answer.

## 13. Testing Strategy

The tests use mock mode heavily, so they do not need real API keys.

Important test areas include:

- schema validation
- LLM client behavior
- pipeline integration
- session loading
- model persistence
- language behavior
- Definer editing
- Explorer validation
- Judge and evaluation behavior

The integration tests verify that the full call chain works with mocked LLM
responses:

```text
user_text -> Pipeline -> Agent -> LLMClient -> Pydantic -> Session
```

## Practice Questions

The multi-select practice quiz is now in [project-implementation-mcq-quiz.md](project-implementation-mcq-quiz.md). The answers are hidden behind expandable sections so you can reveal them after trying each question.

## Quick Exam Tips

- Remember the agent order: **Definer -> Transformer -> Explorer -> Translator
  -> Judge**.
- Remember the key schemas: `ProblemSpec`, `MetaphorSpec`, `Move`, `Solution`,
  `ComparisonResult`.
- The pipeline owns state; agents produce structured outputs.
- Pydantic protects the system from malformed LLM output.
- LiteLLM abstracts over multiple providers.
- Mock mode allows tests and demos without real LLM calls.
- The Judge compares against a baseline blindly to reduce bias.
- Leaks and caveats are important because metaphors are useful but imperfect.
