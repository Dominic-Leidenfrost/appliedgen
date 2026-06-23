# Metaphor Machine: Multiple-Choice Quiz

These are **multi-select** questions. Each question can have **zero, one, several, or all** correct answers.

Tick all options you think are correct before opening the answer block. In Markdown renderers that support task lists, the boxes can be checked directly.

## Question 1

Why does the project keep a central `Pipeline` instead of letting each agent call the next one directly?

- [ ] A. It keeps workflow state in one place.  
- [ ] B. It lets the pipeline enforce phase order and preconditions.  
- [ ] C. It prevents agents from needing their own prompts.  
- [ ] D. It makes Pydantic validation unnecessary.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The pipeline owns the session and controls the order of Definer, Transformer, Explorer, Translator, and Judge calls. Agents still need prompts, and Pydantic validation is still necessary.

</details>

## Question 2

Which design choice best explains why the agents are mostly stateless?

- [ ] A. State belongs to `Session`, while agents are reusable LLM call wrappers.  
- [ ] B. Stateless agents make it easier to rebuild them when model or language changes.  
- [ ] C. Stateless agents mean the app cannot save sessions.  
- [ ] D. Stateless agents guarantee deterministic LLM output.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Session state is centralized, and cached agents can be dropped and rebuilt with new configuration. Statelessness does not imply deterministic output.

</details>

## Question 3

Which statement about the `Session` object is conceptually most accurate?

- [ ] A. It is the source of truth for the current run's problem, metaphor, moves, and solutions.  
- [ ] B. It is a provider registry for available models.  
- [ ] C. It is a prompt template shared by all agents.  
- [ ] D. It is used only by the command-line smoke test.

<details>
<summary>Show answer</summary>

**Correct answers:** A

**Explanation:** `Session` stores the evolving state of one user run. Providers, prompts, and CLI behavior are handled elsewhere.

</details>

## Question 4

Why is the Definer separated from the Transformer?

- [ ] A. The Definer extracts problem structure, while the Transformer uses that structure to create metaphors.  
- [ ] B. It avoids mixing factual extraction with creative metaphor generation.  
- [ ] C. The Transformer cannot receive Pydantic objects.  
- [ ] D. The Definer is the only agent allowed to call LiteLLM.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Definer and Transformer have different jobs and different temperature needs. The Transformer can receive structured data, and all agents can call the LLM through the shared client.

</details>

## Question 5

The Definer overwrites `raw_user_text` with the original input after the LLM returns. Why is that useful?

- [ ] A. It guarantees the exact user text is preserved even if the model paraphrases it.  
- [ ] B. It helps the baseline later answer the original prompt rather than a distorted version.  
- [ ] C. It forces the model to produce German output.  
- [ ] D. It prevents the Transformer from running.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The raw text is part of the problem record and is also useful for direct baseline generation. It is unrelated to language selection or blocking the Transformer.

</details>

## Question 6

Why does the Definer use a relatively low default temperature?

- [ ] A. Its task is extraction rather than creative generation.  
- [ ] B. Low temperature makes API keys optional.  
- [ ] C. Low temperature helps make structured extraction more stable.  
- [ ] D. Pydantic only validates outputs generated at temperature `0.2`.

<details>
<summary>Show answer</summary>

**Correct answers:** A, C

**Explanation:** The Definer should be precise and stable. API keys and Pydantic validation are not determined by the temperature value.

</details>

## Question 7

What is the main conceptual risk if the Definer suggests solutions too early?

- [ ] A. The system may skip the intended metaphor reasoning loop.  
- [ ] B. Later agents may inherit a biased problem framing.  
- [ ] C. The saved Markdown files cannot be rendered.  
- [ ] D. The provider registry will lose model options.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Definer should describe the problem, not solve it. Early solutions can bias or short-circuit the later metaphor-based exploration.

</details>

## Question 8

Which statements about Pydantic schemas are correct in this project?

- [ ] A. They define the structured contract between agents.  
- [ ] B. They validate LLM outputs before those outputs enter session state.  
- [ ] C. They remove the need for careful prompting.  
- [ ] D. They make the LLM response semantically perfect.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Schemas enforce shape and constraints. They do not replace prompting or guarantee that a valid answer is also high quality.

</details>

## Question 9

Why are `Mapping.leak` and `invariants_broken` important?

- [ ] A. They document where the analogy fails or oversimplifies.  
- [ ] B. They help the Translator produce caveats.  
- [ ] C. They are used to select the cheapest LLM provider.  
- [ ] D. They prove that a metaphor is unusable.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Leaks and broken invariants are quality controls for metaphor reasoning. They do not choose providers, and a metaphor can still be useful even when it has limitations.

</details>

## Question 10

Why does the Transformer have a higher default temperature than the Definer?

- [ ] A. It benefits from more creative variation when generating metaphor worlds.  
- [ ] B. It is expected to produce different candidate domains.  
- [ ] C. High temperature guarantees valid JSON.  
- [ ] D. High temperature is required by `ThreadPoolExecutor`.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Metaphor generation is more creative than extraction. Temperature does not guarantee JSON validity and has no relation to threading.

</details>

## Question 11

What is the tradeoff between seeded Transformer mode and free domain mode?

- [ ] A. Seeded mode is more guided and controllable.  
- [ ] B. Free domain mode may discover less obvious metaphor domains.  
- [ ] C. Seeded mode disables Pydantic validation.  
- [ ] D. Free domain mode skips the Transformer.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Seeded mode narrows the search space with curated hints. Free mode lets the model invent a domain. Both still use the Transformer and structured validation.

</details>

## Question 12

Why does the pipeline run several Transformer calls in parallel?

- [ ] A. LLM calls are slow, and candidates are independent enough to generate concurrently.  
- [ ] B. It helps produce several candidate metaphors for user selection.  
- [ ] C. It guarantees the first candidate is always the best.  
- [ ] D. It lets the Judge evaluate while the Definer is still running.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Parallel generation improves responsiveness and gives the user options. It does not rank quality by position or overlap with earlier pipeline stages.

</details>

## Question 13

Why does the pipeline keep partial Transformer errors in `last_transformer_errors`?

- [ ] A. To surface silent failures when only some parallel runs succeed.  
- [ ] B. To let the UI explain why fewer metaphor candidates appeared than requested.  
- [ ] C. To automatically lower API prices.  
- [ ] D. To replace failed candidates with baseline answers.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Some parallel runs can fail while others succeed. The errors are retained so the UI can warn the user and support retrying.

</details>

## Question 14

Why is a diversity filter applied after Transformer runs?

- [ ] A. To prefer candidates from meaningfully different domains.  
- [ ] B. To avoid showing three near-duplicates when multiple runs converge.  
- [ ] C. To validate API keys.  
- [ ] D. To translate moves back to the original problem.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The filter is a simple heuristic to improve variety among candidate metaphor worlds. It is not about credentials or translation.

</details>

## Question 15

Why does the Explorer stay inside the metaphor world instead of directly discussing the original problem?

- [ ] A. It preserves a clear separation between metaphor exploration and back-translation.  
- [ ] B. It forces the Translator to explicitly map ideas back later.  
- [ ] C. It prevents users from choosing a metaphor.  
- [ ] D. It means the Explorer never needs validation.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Explorer develops ideas inside the metaphor. The Translator later closes the loop. Validation still matters.

</details>

## Question 16

Why does the Explorer require an `obstacle` field?

- [ ] A. Obstacles force moves to include resistance, tradeoffs, or constraints.  
- [ ] B. Obstacles make the generated move less generic.  
- [ ] C. Obstacles are used as API credentials.  
- [ ] D. Obstacles are required because Streamlit cannot render empty strings.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Requiring an obstacle improves narrative and reasoning quality. It is not a Streamlit or credential requirement.

</details>

## Question 17

Why does the Explorer check for forbidden generic phrases?

- [ ] A. To reduce vague business-speak and force more concrete moves.  
- [ ] B. To prevent the model from falling back to generic advice.  
- [ ] C. To make the output shorter than the baseline.  
- [ ] D. To guarantee the move is objectively correct.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The forbidden-word list pushes the Explorer away from generic phrasing. It does not guarantee correctness or shorter output.

</details>

## Question 18

What is the conceptual purpose of "Try different angle" in the Explorer phase?

- [ ] A. It asks for a structurally different strategy from prior moves.  
- [ ] B. It helps avoid repetitive exploration.  
- [ ] C. It deletes the selected metaphor.  
- [ ] D. It changes the LLM provider automatically.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The feature steers the next move toward strategic diversity. It does not alter provider or metaphor selection.

</details>

## Question 19

Why does the Translator require generated Explorer moves before producing solutions?

- [ ] A. Its job is to translate metaphor-space actions back into the original domain.  
- [ ] B. Without moves, there is no metaphor insight to translate.  
- [ ] C. The Transformer cannot produce mappings unless solutions already exist.  
- [ ] D. The Judge requires the Translator to run before the Explorer.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Translator is not a direct solver in the normal pipeline. It converts Explorer moves into `Solution` objects.

</details>

## Question 20

Why does each `Solution` include confidence and caveats?

- [ ] A. They communicate uncertainty caused by imperfect metaphor mappings.  
- [ ] B. They make limitations visible to the user.  
- [ ] C. They replace the need to show the translated solution text.  
- [ ] D. They are required by LiteLLM for billing.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Confidence and caveats prevent overclaiming. They supplement the translation; they do not replace it.

</details>

## Question 21

What is the role of `Translator.baseline()`?

- [ ] A. It generates a direct no-metaphor answer for comparison.  
- [ ] B. It provides a reference point for judging whether the metaphor detour helped.  
- [ ] C. It creates the final `MetaphorSpec`.  
- [ ] D. It anonymizes answers for the Judge.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The baseline is a direct answer to the same problem. It is compared against the metaphor answer. Anonymization happens in the Judge.

</details>

## Question 22

Why is the Judge comparison blind?

- [ ] A. To avoid rewarding an answer simply because it is labeled "metaphor".  
- [ ] B. To reduce method-label bias in the comparison.  
- [ ] C. To prevent Pydantic from validating the verdict.  
- [ ] D. To hide the original problem from the Judge.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Judge sees neutral labels A/B. It still sees the problem and returns structured output.

</details>

## Question 23

Why is A/B order randomized in Judge runs?

- [ ] A. LLM judges may prefer whichever answer appears first.  
- [ ] B. Randomization helps audit or reduce position bias.  
- [ ] C. Randomization makes the baseline more creative.  
- [ ] D. Randomization is needed for `json.loads`.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Random order controls for position bias. It does not change answer content or JSON parsing.

</details>

## Question 24

Which statements about the Judge's criteria are correct?

- [ ] A. They focus on answer usefulness rather than how the answer was produced.  
- [ ] B. They include specificity, actionability, novelty, and relevance.  
- [ ] C. They include provider cost and token latency.  
- [ ] D. They are used by the Definer to extract relations.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The criteria evaluate the substance of two answers. They are not cost metrics and are not used by the Definer.

</details>

## Question 25

Why does the project use a relative win-rate instead of absolute correctness?

- [ ] A. The target task is open-ended, so ground truth is hard to define.  
- [ ] B. Pairwise comparison can still show whether the metaphor pipeline beats a direct baseline.  
- [ ] C. Absolute correctness is already guaranteed by Pydantic.  
- [ ] D. Win-rate measures how many YAML domains were loaded.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The system produces creative problem-solving advice, where no single correct answer exists. Win-rate gives a practical relative metric.

</details>

## Question 26

Why does `LLMClient.structured()` validate output even after instructing the model to return JSON?

- [ ] A. LLMs can still produce malformed or wrapped JSON.  
- [ ] B. Field types and constraints still need to be checked.  
- [ ] C. Validation is only needed for Anthropic models.  
- [ ] D. Validation replaces the need to call the model.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Prompt instructions are not enough. The client extracts and validates JSON against Pydantic schemas.

</details>

## Question 27

What is the benefit of using LiteLLM in this project?

- [ ] A. It provides a common interface across multiple model providers.  
- [ ] B. It lets the project switch models using provider/model strings.  
- [ ] C. It guarantees all providers support identical model behavior.  
- [ ] D. It replaces Streamlit.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** LiteLLM abstracts provider calls. Different providers can still behave differently, and the UI remains Streamlit.

</details>

## Question 28

Why does the provider registry check for API keys before calling the model?

- [ ] A. It can fail earlier with a clearer error message.  
- [ ] B. It maps known model strings to required environment variables.  
- [ ] C. It stores generated solutions.  
- [ ] D. It converts model output to Pydantic objects.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The registry knows which provider key is required for known model strings. Structured conversion happens in the LLM client.

</details>

## Question 29

Why is mock mode useful for this project?

- [ ] A. It allows tests without real API keys or network calls.  
- [ ] B. It exercises the pipeline with predictable canned outputs.  
- [ ] C. It improves the quality of real model responses.  
- [ ] D. It disables schemas so tests can ignore structure.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Mock mode is for reliable offline testing and development. It does not improve real LLM behavior or remove schema validation.

</details>

## Question 30

Which workflow dependencies are enforced conceptually by the pipeline?

- [ ] A. The Transformer needs a defined problem.  
- [ ] B. The Explorer needs a chosen metaphor.  
- [ ] C. The Translator needs generated moves.  
- [ ] D. The Judge needs translated solutions to compare against a baseline.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B, C, D

**Explanation:** All four dependencies match the intended phase order: define, transform, explore, translate, then evaluate.

</details>

## Question 31

Why are model and language choices persisted under `data/cache/`?

- [ ] A. Streamlit reruns and reloads should not reset user preferences.  
- [ ] B. These preferences are machine configuration rather than session transcript content.  
- [ ] C. They are required to reconstruct old Explorer moves.  
- [ ] D. They store all API keys.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Model and language preferences survive reloads. They are separate from saved run artifacts and do not store API keys.

</details>

## Question 32

Why are schema field names kept in English even when German output is selected?

- [ ] A. The JSON keys are part of the code contract and Pydantic model shape.  
- [ ] B. Translating keys such as `summary` or `entities` would break validation.  
- [ ] C. German values are not supported by the agents.  
- [ ] D. English keys force the final answer to be English.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The keys must remain stable for validation and downstream code. The text values inside those fields can still be German.

</details>

## Question 33

What is the main reason session saving writes both Markdown and JSON?

- [ ] A. Markdown is readable for humans.  
- [ ] B. JSON preserves structured data for loading or replay.  
- [ ] C. Markdown is needed for Pydantic validation.  
- [ ] D. JSON is needed for Streamlit button rendering.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Markdown is for inspection and presentation; JSON is for structured reconstruction. Pydantic validates parsed data, not Markdown.

</details>

## Question 34

Why does loading a saved session validate JSON through Pydantic models?

- [ ] A. It detects files that do not match the expected session shape.  
- [ ] B. It reconstructs typed objects such as `ProblemSpec`, `Move`, and `Solution`.  
- [ ] C. It improves the LLM's future creativity.  
- [ ] D. It changes saved Markdown into provider credentials.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Loading uses Pydantic to rebuild structured session objects and reject invalid shapes.

</details>

## Question 35

Which statement best captures the role of the Streamlit app?

- [ ] A. It drives the pipeline interactively and renders the current session state.  
- [ ] B. It owns all core reasoning logic instead of the `src/metaphor_machine` package.  
- [ ] C. It provides UI controls for phases, model choice, language, saving, and evaluation.  
- [ ] D. It replaces all tests.

<details>
<summary>Show answer</summary>

**Correct answers:** A, C

**Explanation:** Streamlit is the UI layer. Core reasoning remains in the package code, and tests are separate.

</details>

## Question 36

Why does editing the extracted problem before metaphor generation matter more than editing later text?

- [ ] A. The problem structure is the root input for metaphor generation.  
- [ ] B. Mistakes in entities or relations can propagate into all downstream metaphors and solutions.  
- [ ] C. Later agents ignore the problem entirely.  
- [ ] D. Editing the problem automatically improves the provider API key.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Downstream agents build on the structured problem. Later agents still use context, but a wrong root structure can distort the whole run.

</details>

## Question 37

Which statements about curated seed domains are correct?

- [ ] A. They guide the Transformer toward specific metaphor families.  
- [ ] B. They can improve controllability but may limit surprise.  
- [ ] C. They guarantee every mapping has perfect fidelity.  
- [ ] D. They replace the need for the user's problem text.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Seeds provide domain hints. They do not guarantee mapping quality and do not replace the actual problem.

</details>

## Question 38

Which statements about a `MetaphorSpec` are correct?

- [ ] A. It represents one candidate metaphor world.  
- [ ] B. It contains mappings from original concepts to metaphor concepts.  
- [ ] C. It is the same thing as a final `Solution`.  
- [ ] D. It is generated after the Translator runs.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** `MetaphorSpec` is created by the Transformer before exploration and translation.

</details>

## Question 39

Which statements about a `Solution` are correct?

- [ ] A. It contains the original-domain translation of a metaphor move.  
- [ ] B. It can include caveats derived from analogy leaks.  
- [ ] C. It is produced before the Explorer generates moves.  
- [ ] D. It stores the selected model string.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Solutions are Translator outputs based on Explorer moves. Model choice is stored separately.

</details>

## Question 40

Which statements about the win-rate calculation are correct?

- [ ] A. Ties count as half a metaphor win.  
- [ ] B. It summarizes repeated pairwise Judge comparisons.  
- [ ] C. It proves the metaphor answer is correct for every user.  
- [ ] D. It depends on the number of files in `examples/domains/`.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Win-rate is a relative preference metric. It does not prove universal correctness and is unrelated to domain file count.

</details>

## Question 41

Which statements about API key handling are correct?

- [ ] A. API keys are hard-coded inside `Pipeline`.  
- [ ] B. API keys are saved inside `session.json`.  
- [ ] C. API keys are stored inside each `ProblemSpec`.  
- [ ] D. API keys are generated automatically by the Judge.

<details>
<summary>Show answer</summary>

**Correct answers:** None

**Explanation:** API keys are expected through environment variables such as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY`.

</details>

## Question 42

Which statements about the Definer's intended behavior are correct?

- [ ] A. It should choose the final metaphor domain.  
- [ ] B. It should generate final translated solutions.  
- [ ] C. It should run the blind A/B evaluation.  
- [ ] D. It should save Markdown files to disk.

<details>
<summary>Show answer</summary>

**Correct answers:** None

**Explanation:** The Definer only extracts problem structure. Transformer, Translator, Judge, and storage handle the other responsibilities.

</details>

## Question 43

Why is the project designed with separate agents instead of one large prompt that does everything?

- [ ] A. Separate agents make it impossible for LLM output to be malformed.  
- [ ] B. Separate agents let each step use a different prompt, schema, and temperature.  
- [ ] C. Separate agents remove the need for user interaction.  
- [ ] D. Separate agents guarantee that metaphor-based answers always beat the baseline.

<details>
<summary>Show answer</summary>

**Correct answers:** B

**Explanation:** The separation lets the project tune each stage for its role. It does not guarantee correctness or eliminate validation and user interaction.

</details>

## Question 44

A user corrects the extracted `ProblemSpec` after metaphors and moves have already been generated. Why does the pipeline clear downstream state?

- [ ] A. Because downstream artifacts may now be based on the wrong problem structure.  
- [ ] B. Because Pydantic requires every update to start from an empty session.  
- [ ] C. Because the UI cannot display old moves after an edit.  
- [ ] D. Because old metaphor candidates become provider API keys.

<details>
<summary>Show answer</summary>

**Correct answers:** A

**Explanation:** The problem structure is the root input for metaphor generation. If it changes, old metaphors, moves, and solutions may silently mix two different problem definitions.

</details>

## Question 45

The Transformer asks for mapping leaks and broken invariants. What conceptual role do these fields play?

- [ ] A. They make the analogy's limits explicit so later translations can be more cautious.  
- [ ] B. They are used to hide the metaphor answer from the Judge.  
- [ ] C. They force the Transformer to admit that structural fit is partial, not perfect.  
- [ ] D. They replace the need for `confidence` in `Solution`.

<details>
<summary>Show answer</summary>

**Correct answers:** A, C

**Explanation:** Leaks and broken invariants document where the metaphor stops matching the original problem. They help prevent overconfident translations.

</details>

## Question 46

Why is the Judge comparison blind and randomized?

- [ ] A. To reduce the chance that the Judge favors an answer because it appears first.  
- [ ] B. To prevent the Judge from knowing whether an answer came from the metaphor pipeline.  
- [ ] C. To make the baseline answer shorter.  
- [ ] D. To avoid running the Translator.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** The Judge sees neutral A/B labels, and the answer order is randomized. This helps reduce method-label bias and position bias.

</details>

## Question 47

Why does the project compare against a direct baseline instead of only showing the metaphor output?

- [ ] A. Open-ended tasks usually lack a single ground-truth answer, so relative comparison is more practical.  
- [ ] B. The baseline proves that the metaphor answer is objectively correct.  
- [ ] C. The baseline gives a reference point for whether the metaphor detour adds value.  
- [ ] D. The baseline is required because LiteLLM cannot return structured output.

<details>
<summary>Show answer</summary>

**Correct answers:** A, C

**Explanation:** The baseline makes evaluation comparative: did the metaphor pipeline produce a better answer than simply asking the model directly?

</details>

## Question 48

Why does `LLMClient.structured()` still extract and validate JSON even when the prompt says "Respond only with valid JSON"?

- [ ] A. LLMs can still wrap JSON in prose or Markdown fences despite instructions.  
- [ ] B. Pydantic validation checks semantic shape, types, and constraints after parsing.  
- [ ] C. LiteLLM always returns Python objects directly, so JSON extraction is unnecessary.  
- [ ] D. Validation is only needed in mock mode.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Prompting helps, but LLMs can still return imperfect formatting or invalid fields. The client defensively extracts JSON and validates it.

</details>

## Question 49

Why are the schema field names kept in English even when German output is selected?

- [ ] A. The field names are part of the programmatic contract between agents.  
- [ ] B. Translating field names would break Pydantic model validation.  
- [ ] C. German output is only supported in the Streamlit UI, not in agent values.  
- [ ] D. Keeping English field names prevents the model from generating German text values.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Pydantic expects keys like `summary`, `entities`, and `relations`. The generated values can be German, but the JSON keys must stay stable.

</details>

## Question 50

Which implementation detail best supports offline development and tests?

- [ ] A. `METAPHOR_MOCK=1` routes LLM calls to canned fixtures.  
- [ ] B. `ThreadPoolExecutor` stores API keys in memory.  
- [ ] C. The Judge disables schemas during tests.  
- [ ] D. Markdown files replace all structured objects.

<details>
<summary>Show answer</summary>

**Correct answers:** A

**Explanation:** Mock mode returns deterministic fixture data and avoids real LLM calls. The other options do not describe the test strategy.

</details>

## Question 51

Which conceptual issue does the "free domains" option address?

- [ ] A. Curated seed domains can constrain the range of metaphors.  
- [ ] B. Some problems may benefit from a metaphor outside the preset domain list.  
- [ ] C. Seed domains prevent Pydantic validation from working.  
- [ ] D. Free domains remove the need to choose a metaphor.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Free domain mode widens the metaphor search space. It does not disable validation or remove the user's selection step.

</details>

## Question 52

Which conceptual tradeoff is introduced by using curated seed domains for the Transformer?

- [ ] A. Seed domains can improve diversity and controllability, but may limit surprising metaphor choices.  
- [ ] B. Seed domains remove the need to check mapping quality.  
- [ ] C. Seed domains make the Transformer deterministic even at high temperature.  
- [ ] D. Seed domains guarantee that every metaphor preserves all original invariants.

<details>
<summary>Show answer</summary>

**Correct answers:** A

**Explanation:** Curated seeds guide the model toward known metaphor families and make candidate generation easier to control. The tradeoff is that they can narrow the search space.

</details>
