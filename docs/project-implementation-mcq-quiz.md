# Metaphor Machine: Multiple-Choice Quiz

These are **multi-select** questions. Each question can have **zero, one, several, or all** correct answers.

Tick all options you think are correct before opening the answer block. In Markdown renderers that support task lists, the boxes can be checked directly.

## Question 1

Why does the project keep a central `Pipeline` instead of letting each agent call the next one directly?

- [ ] A. It prevents agents from needing their own prompts.  
- [ ] B. It keeps workflow state in one place.  
- [ ] C. It lets each agent keep a separate copy of the full session.  
- [ ] D. It lets the pipeline enforce phase order and preconditions.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** The pipeline owns the session and controls the order of Definer, Transformer, Explorer, Translator, and Judge calls. Agents still need prompts, and Pydantic validation is still necessary.

</details>

## Question 2

Which design choice best explains why the agents are mostly stateless?

- [ ] A. State belongs to `Session`, while agents are reusable LLM call wrappers.  
- [ ] B. Stateless agents guarantee deterministic LLM output.  
- [ ] C. Stateless agents mean the app cannot save sessions.  
- [ ] D. Stateless agents make it easier to rebuild them when model or language changes.

<details>
<summary>Show answer</summary>

**Correct answers:** A, D

**Explanation:** Session state is centralized, and cached agents can be dropped and rebuilt with new configuration. Statelessness does not imply deterministic output.

</details>

## Question 3

A Transformer call returns JSON with the right top-level fields, but one mapping has `fidelity: 1.4`. Which guardrail should catch this?

- [ ] A. The Streamlit layout code, because it renders fidelity values.  
- [ ] B. Pydantic validation on the `Mapping` schema.  
- [ ] C. The Judge, because it compares final answers.  
- [ ] D. The Markdown renderer, because tables cannot show values above `1.0`.

<details>
<summary>Show answer</summary>

**Correct answers:** B

**Explanation:** `Mapping.fidelity` is constrained with `ge=0.0` and `le=1.0`, so schema validation should reject out-of-range values before they become reliable session state.

</details>

## Question 4

Why is the Definer separated from the Transformer?

- [ ] A. The Definer is the only agent allowed to call LiteLLM.  
- [ ] B. The Definer extracts problem structure, while the Transformer uses that structure to create metaphors.  
- [ ] C. It avoids mixing factual extraction with creative metaphor generation.  
- [ ] D. The Transformer can only work with raw unstructured text.

<details>
<summary>Show answer</summary>

**Correct answers:** B, C

**Explanation:** The Definer and Transformer have different jobs and different temperature needs. The Transformer can receive structured data, and all agents can call the LLM through the shared client.

</details>

## Question 5

The Definer overwrites `raw_user_text` with the original input after the LLM returns. Why is that useful?

- [ ] A. It forces the model to produce German output.  
- [ ] B. It prevents the Transformer from running.  
- [ ] C. It guarantees the exact user text is preserved even if the model paraphrases it.  
- [ ] D. It helps the baseline later answer the original prompt rather than a distorted version.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** The raw text is part of the problem record and is also useful for direct baseline generation. It is unrelated to language selection or blocking the Transformer.

</details>

## Question 6

Why does the Definer use a relatively low default temperature?

- [ ] A. Its task is extraction rather than creative generation.  
- [ ] B. Low temperature makes API keys optional.  
- [ ] C. Pydantic only validates outputs generated at temperature `0.2`.  
- [ ] D. Low temperature helps make structured extraction more stable.

<details>
<summary>Show answer</summary>

**Correct answers:** A, D

**Explanation:** The Definer should be precise and stable. API keys and Pydantic validation are not determined by the temperature value.

</details>

## Question 7

What is the main conceptual risk if the Definer suggests solutions too early?

- [ ] A. The saved Markdown files cannot be rendered.  
- [ ] B. The system may skip the intended metaphor reasoning loop.  
- [ ] C. The provider registry will lose model options.  
- [ ] D. Later agents may inherit a biased problem framing.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** The Definer should describe the problem, not solve it. Early solutions can bias or short-circuit the later metaphor-based exploration.

</details>

## Question 8

Which statements about Pydantic schemas are correct in this project?

- [ ] A. They remove the need for careful prompting.  
- [ ] B. They define the structured contract between agents.  
- [ ] C. They validate LLM outputs before those outputs enter session state.  
- [ ] D. They make the LLM response semantically perfect.

<details>
<summary>Show answer</summary>

**Correct answers:** B, C

**Explanation:** Schemas enforce shape and constraints. They do not replace prompting or guarantee that a valid answer is also high quality.

</details>

## Question 9

Why are `Mapping.leak` and `invariants_broken` important?

- [ ] A. They are used to select the cheapest LLM provider.  
- [ ] B. They prove that a metaphor is unusable.  
- [ ] C. They document where the analogy fails or oversimplifies.  
- [ ] D. They help the Translator produce caveats.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** Leaks and broken invariants are quality controls for metaphor reasoning. They do not choose providers, and a metaphor can still be useful even when it has limitations.

</details>

## Question 10

Why does the Transformer have a higher default temperature than the Definer?

- [ ] A. High temperature guarantees valid JSON.  
- [ ] B. It benefits from more creative variation when generating metaphor worlds.  
- [ ] C. It is expected to produce different candidate domains.  
- [ ] D. High temperature is required by `ThreadPoolExecutor`.

<details>
<summary>Show answer</summary>

**Correct answers:** B, C

**Explanation:** Metaphor generation is more creative than extraction. Temperature does not guarantee JSON validity and has no relation to threading.

</details>

## Question 11

What is the tradeoff between seeded Transformer mode and free domain mode?

- [ ] A. Seeded mode disables Pydantic validation.  
- [ ] B. Free domain mode skips the Transformer.  
- [ ] C. Seeded mode is more guided and controllable.  
- [ ] D. Free domain mode may discover less obvious metaphor domains.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** Seeded mode narrows the search space with curated hints. Free mode lets the model invent a domain. Both still use the Transformer and structured validation.

</details>

## Question 12

Why does the pipeline run several Transformer calls in parallel?

- [ ] A. It guarantees the first candidate is always the best.  
- [ ] B. LLM calls are slow, and candidates are independent enough to generate concurrently.  
- [ ] C. It lets the Judge evaluate while the Definer is still running.  
- [ ] D. It helps produce several candidate metaphors for user selection.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** Parallel generation improves responsiveness and gives the user options. It does not rank quality by position or overlap with earlier pipeline stages.

</details>

## Question 13

Why does the pipeline keep partial Transformer errors in `last_transformer_errors`?

- [ ] A. To automatically lower API prices.  
- [ ] B. To replace failed candidates with baseline answers.  
- [ ] C. To surface silent failures when only some parallel runs succeed.  
- [ ] D. To let the UI explain why fewer metaphor candidates appeared than requested.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** Some parallel runs can fail while others succeed. The errors are retained so the UI can warn the user and support retrying.

</details>

## Question 14

Why is a diversity filter applied after Transformer runs?

- [ ] A. To validate API keys.  
- [ ] B. To prefer candidates from meaningfully different domains.  
- [ ] C. To translate moves back to the original problem.  
- [ ] D. To avoid showing three near-duplicates when multiple runs converge.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** The filter is a simple heuristic to improve variety among candidate metaphor worlds. It is not about credentials or translation.

</details>

## Question 15

Why does the Explorer stay inside the metaphor world instead of directly discussing the original problem?

- [ ] A. It preserves a clear separation between metaphor exploration and back-translation.  
- [ ] B. It prevents users from choosing a metaphor.  
- [ ] C. It lets the Explorer modify the original `ProblemSpec` directly.  
- [ ] D. It forces the Translator to explicitly map ideas back later.

<details>
<summary>Show answer</summary>

**Correct answers:** A, D

**Explanation:** The Explorer develops ideas inside the metaphor. The Translator later closes the loop. Validation still matters.

</details>

## Question 16

Why does the Explorer require an `obstacle` field?

- [ ] A. Obstacles are used as API credentials.  
- [ ] B. Obstacles are required because Streamlit cannot render empty strings.  
- [ ] C. Obstacles force moves to include resistance, tradeoffs, or constraints.  
- [ ] D. Obstacles make the generated move less generic.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** Requiring an obstacle improves narrative and reasoning quality. It is not a Streamlit or credential requirement.

</details>

## Question 17

Why does the Explorer check for forbidden generic phrases?

- [ ] A. To make the output shorter than the baseline.  
- [ ] B. To reduce vague business-speak and force more concrete moves.  
- [ ] C. To select which provider API key should be used.  
- [ ] D. To prevent the model from falling back to generic advice.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** The forbidden-word list pushes the Explorer away from generic phrasing. It does not guarantee correctness or shorter output.

</details>

## Question 18

What is the conceptual purpose of "Try different angle" in the Explorer phase?

- [ ] A. It asks for a structurally different strategy from prior moves.  
- [ ] B. It deletes the selected metaphor.  
- [ ] C. It helps avoid repetitive exploration.  
- [ ] D. It changes the LLM provider automatically.

<details>
<summary>Show answer</summary>

**Correct answers:** A, C

**Explanation:** The feature steers the next move toward strategic diversity. It does not alter provider or metaphor selection.

</details>

## Question 19

Why does the Translator require generated Explorer moves before producing solutions?

- [ ] A. The Transformer cannot produce mappings unless solutions already exist.  
- [ ] B. The Judge requires the Translator to run before the Explorer.  
- [ ] C. Its job is to translate metaphor-space actions back into the original domain.  
- [ ] D. Without moves, there is no metaphor insight to translate.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

**Explanation:** The Translator is not a direct solver in the normal pipeline. It converts Explorer moves into `Solution` objects.

</details>

## Question 20

Why does each `Solution` include confidence and caveats?

- [ ] A. They replace the need to show the translated solution text.  
- [ ] B. They communicate uncertainty caused by imperfect metaphor mappings.  
- [ ] C. They are required by LiteLLM for billing.  
- [ ] D. They make limitations visible to the user.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** Confidence and caveats prevent overclaiming. They supplement the translation; they do not replace it.

</details>

## Question 21

What is the role of `Translator.baseline()`?

- [ ] A. It generates a direct no-metaphor answer for comparison.  
- [ ] B. It creates the final `MetaphorSpec`.  
- [ ] C. It chooses which Explorer move should be undone.  
- [ ] D. It provides a reference point for judging whether the metaphor detour helped.

<details>
<summary>Show answer</summary>

**Correct answers:** A, D

**Explanation:** The baseline is a direct answer to the same problem. It is compared against the metaphor answer. Anonymization happens in the Judge.

</details>

## Question 22

Why is the Judge comparison blind?

- [ ] A. To prevent Pydantic from validating the verdict.  
- [ ] B. To avoid rewarding an answer simply because it is labeled "metaphor".  
- [ ] C. To hide the original problem from the Judge.  
- [ ] D. To reduce method-label bias in the comparison.

<details>
<summary>Show answer</summary>

**Correct answers:** B, D

**Explanation:** The Judge sees neutral labels A/B. It still sees the problem and returns structured output.

</details>

## Question 23

Why is A/B order randomized in Judge runs?

- [ ] A. Randomization makes the baseline more creative.  
- [ ] B. Randomization is needed for `json.loads`.  
- [ ] C. LLM judges may prefer whichever answer appears first.  
- [ ] D. Randomization helps audit or reduce position bias.

<details>
<summary>Show answer</summary>

**Correct answers:** C, D

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

A user selects `openai/gpt-4o`, but no `OPENAI_API_KEY` is configured. What is the guardrail value of checking this before the LLM call?

- [ ] A. It turns an avoidable provider failure into a clearer configuration error.  
- [ ] B. It prevents retry logic from wasting time on a problem retries cannot fix.  
- [ ] C. It automatically falls back to an Anthropic model with the same prompt.  
- [ ] D. It validates that the model's final JSON matches the target schema.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Missing API keys are configuration errors, not transient provider failures. The early check gives a more useful message and avoids pointless retries. Schema validation is handled elsewhere.

</details>

## Question 29

Which testing risk remains even when `METAPHOR_MOCK=1` makes the full pipeline pass?

- [ ] A. Real models may still produce malformed or low-quality outputs not covered by fixtures.  
- [ ] B. Provider-specific behavior and rate limits are not exercised.  
- [ ] C. Pydantic schemas are completely bypassed in mock mode.  
- [ ] D. The pipeline cannot be tested end-to-end in mock mode.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Mock mode is good for deterministic offline tests, but it cannot fully simulate provider behavior or real LLM failure modes. The mocked outputs are still validated against schemas.

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

Why is `session.json` a safer replay artifact than the rendered Markdown files?

- [ ] A. It preserves typed structure instead of relying on re-parsing prose and tables.  
- [ ] B. It can be validated when loaded back into Pydantic models.  
- [ ] C. It hides all generated content from the user.  
- [ ] D. It prevents the saved session from containing bad model output in the first place.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** JSON is structured and loadable; Markdown is mainly for human inspection. Saving JSON does not retroactively prove the content is good, but loading can validate its shape.

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

The Transformer produces a metaphor with only two mappings, but the JSON is otherwise schema-valid. Why is an extra quality check needed beyond Pydantic?

- [ ] A. Pydantic can validate shape and field constraints, but not whether the metaphor is rich enough.  
- [ ] B. The project has a domain-specific expectation that major entities and relations should be mapped.  
- [ ] C. Pydantic cannot parse any nested list fields.  
- [ ] D. The Judge must always repair `MetaphorSpec` before the Explorer sees it.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Schema validation says the object has the right structure. The Transformer adds project-specific quality checks, such as requiring enough mappings and discouraging suspicious high-fidelity mappings without leaks.

</details>

## Question 39

What guardrail does the Translator's caveat requirement add to the final answer?

- [ ] A. It makes analogy limitations visible instead of presenting all translations as equally reliable.  
- [ ] B. It encourages the model to connect back to mapping leaks and fidelity limits.  
- [ ] C. It guarantees the user will follow the advice correctly.  
- [ ] D. It prevents the baseline answer from being generated.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Caveats are a reasoning guardrail against overconfident back-translation. They do not control user behavior or baseline generation.

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

Which proposed "guardrails" would actually weaken the project?

- [ ] A. Trusting raw LLM text directly instead of validating it against Pydantic schemas.  
- [ ] B. Keeping old metaphors and moves after the user changes the extracted problem structure.  
- [ ] C. Checking required API keys before provider calls.  
- [ ] D. Recording whether the Judge saw the metaphor answer first or second.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Skipping validation and keeping stale downstream state both increase risk. API-key checks and judge-order recording are useful guardrails.

</details>

## Question 42

Which user actions or system checks protect against the Definer misunderstanding the original problem?

- [ ] A. Showing the extracted structure before metaphor generation.  
- [ ] B. Allowing the user to edit entities, relations, goals, constraints, and tensions.  
- [ ] C. Automatically treating the first metaphor candidate as ground truth in interactive mode.  
- [ ] D. Clearing downstream artifacts if the corrected problem invalidates previous results.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B, D

**Explanation:** The UI exposes the structure so the user can correct it, and the pipeline clears stale downstream results after correction. Automatically treating a metaphor as ground truth would be the opposite of a guardrail.

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

Which guardrail is specifically aimed at prompt-format failures rather than reasoning quality?

- [ ] A. Extracting the first JSON object from a response that may contain Markdown fences.  
- [ ] B. Re-prompting when Pydantic validation fails.  
- [ ] C. Asking the Judge to compare novelty and relevance.  
- [ ] D. Asking the Transformer to list broken invariants.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** JSON extraction and validation retries handle output-format/schema failures. Judge criteria and broken invariants address answer quality and analogy quality rather than raw response formatting.

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

Which things are **not** fully solved by the project's guardrails?

- [ ] A. A schema-valid but unhelpful metaphor.  
- [ ] B. A Judge verdict that still has subtle model bias despite randomization.  
- [ ] C. A missing required provider API key for a known model.  
- [ ] D. A Transformer output with `fidelity` outside the allowed numeric range.

<details>
<summary>Show answer</summary>

**Correct answers:** A, B

**Explanation:** Guardrails reduce risk but do not guarantee quality or fully eliminate judge bias. Missing keys and invalid numeric ranges are much more directly caught by provider checks and Pydantic constraints.

</details>
