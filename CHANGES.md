# What we added based on the feedback

We got repeated feedback that it was hard to tell if the system's answers were actually good.

There is no single correct answer for these problems, so we could not compare our output to a fixed ground truth. Because of that, we added an LLM judge.

The idea is simple:

- generate the normal Metaphor Machine answer,
- generate a direct baseline answer without metaphor,
- hide which one is which,
- let a third model compare both answers,
- report which one is better overall and on a few clear criteria.

## Why we added the judge

We added this because reviewers often asked things like:

- How do you know the answer is any good?
- Can you show some metric or evaluation?
- Can you compare it to a normal LLM answer?
- Can you reduce bias and define clearer evaluation rules?

The judge is our answer to that feedback.

## What this gives us

The judge compares the metaphor answer and the baseline answer blindly. It looks at:

- specificity,
- actionability,
- novelty,
- relevance.

This helps in a few ways:

- We now have a structured way to compare answers.
- We can report a win rate over many problems.
- We can show the comparison in the app as a concrete example.
- We reduce simple position bias by randomizing answer order.

This does not make the evaluation fully objective, but it is much better than only saying that the answers "look interesting".

## What we did not add

### We did not add other languages, TTS, queues, or scalability work

These are useful ideas, but they are outside the main problem we wanted to solve here. The main goal was to improve evaluation.

### The metaphor-generation workflow itself does not become more autonomous

We did not add a more autonomous feedback loop or stronger self-improvement workflow.

Reason:

- this would require even more tokens,
- we are limited in our resources.

So we chose to spend our resources on evaluation first.

### We did not solve the "true objective metric" problem

We tried to improve this with the judge, but truly objective evaluation is very hard here because this is a natural language problem.

To get a more objective metric, we would probably need:

- a strong ground truth,
- or a large high-quality dataset with labeled answers.

That is much harder to build, and was out of scope for this step.

## In short

Based on the feedback, we added a judge to compare our metaphor-based answer against a normal baseline answer in a more structured and fair way.

This gives us a practical evaluation method, even if it is not a perfect objective benchmark.

## Our interpretation of the evaluation judge

We ran our evaluation with very limited resources, and in these runs the LLM judge mostly preferred the baseline answer. This suggests that we could still improve the judge setup to make it more neutral. At the same time, judging solutions to open-ended problems is naturally very subjective. We also think the judge may be biased toward the normal baseline answer, because that style is closer to the kind of answer LLMs are usually trained to produce and may therefore look more "correct" to the judge.
