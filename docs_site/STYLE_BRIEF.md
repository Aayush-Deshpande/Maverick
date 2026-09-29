# Style brief for ANUMAAN documentation writers

This file is the shared brief for every article in this corpus. Read it before writing anything. It is not published; it exists to keep 45+ articles, written separately, sounding like one publication.

## Audience and purpose

This is the public technical documentation site for Project ANUMAAN, built for DRDO / Smart India Hackathon Problem Statement 26054. It will be hosted on its own domain, separate from the code repository. The reader is a technical evaluator: a DRDO scientist, an SIH judge, or an engineer assessing the system. They are competent, skeptical, and will not be impressed by marketing language. They will be impressed by precision.

## What this is not

This is not a code audit. Do not write sentences like "this file is hardcoded," "this module is disconnected from the live path," "the repository has legacy architecture," "this component is incomplete," or "this value is mocked." The reader does not care about the repository's internal history of what got wired up when. They care about the engineering system as it stands.

Where a genuine capability boundary matters to correctly understanding the system, describe it in engineering terms: what the current implementation covers, what a fuller deployment would add, what has been validated against and what remains to be validated on real flight hardware. State it once, plainly, as a scope statement, not as an apology or a confession.

## Voice

Write like a senior propulsion or avionics engineer explaining their own system to a peer. Confident, precise, unhurried. Short declarative sentences mixed with longer explanatory ones. No hedging filler ("it's worth noting that," "it should be mentioned that"). No hype ("cutting-edge," "revolutionary," "game-changing," "state-of-the-art" used as a filler adjective, "seamless," "robust" as a placeholder word, "powerful," "next-generation"). No AI-assistant tics: no "Let's dive in," no "In today's world," no rhetorical questions used as section openers, no "It's important to note," no summarizing what you are about to say before you say it.

Do not use em dashes anywhere, in any article. Use a period, a comma, a colon, or restructure the sentence. This applies to every single article without exception.

Do not use rhetorical questions as headers or hooks (avoid "But what does this actually mean?" style writing).

Do not editorialize about how good, novel, or impressive ANUMAAN is. Let the engineering carry that. State what the system does and how it does it, correctly and specifically, and the reader will draw their own conclusion.

## Structure

Each article should read as a self-contained technical article, not a wiki stub. Use this pattern as a default, adapting section presence and order to the subject rather than forcing every article into an identical mold:

```
# Title

2 to 4 paragraph introduction: what this subsystem is, why it exists, one sentence
of context linking it to the overall system.

## The problem
The specific engineering problem this subsystem addresses.

## Why it matters
Operational and technical significance, tied to the problem statement or to
UAV propulsion reliability generally.

## Our approach
How ANUMAAN addresses the problem, at the level of a design decision.

## How it works
The actual mechanism: pipeline stages, data flow, method.

## Architecture
A Mermaid diagram (see rules below).

## Mathematics / algorithms
Where the subsystem has real mathematical content, explain it. Use inline
LaTeX-style notation in plain text or code blocks as appropriate for Markdown
(e.g. `R = P(sortie completes | health, profile, environment)`), not invented
imagery.

## Example
A concrete worked example grounded in the actual system: a real fault mode
from the fault matrix, a real engine profile, a real mission phase.

## Integration
How this subsystem connects to the rest of ANUMAAN: what feeds it, what it
feeds.

## Validation
What supports this subsystem: tests, characterization runs, experiments,
demonstrated behavior. Be specific and be truthful. Do not invent numbers,
datasets, or results that are not in the source material provided.

## Related systems
Links to 2 to 5 other articles in this corpus, using relative Markdown links.
```

Not every article needs every section. A dataset article or a journey chapter will look different. Use judgment; the goal is a coherent article, not a filled-in form.

## Diagrams

Every major article includes at least one Mermaid diagram (`flowchart LR` or `flowchart TB`). Rules:

- Monochrome, neutral, no color directives, no `style` fills, no emoji in node labels
- No more than about 10 to 12 nodes per diagram
- Node labels are short technical terms, not full sentences
- The diagram must answer a specific engineering question (data flow, layer boundary, pipeline stage order), stated in a one-line caption above or below it
- Use subgraphs to show layer or boundary groupings where useful

## Accuracy discipline

Every specific technical claim, equation, fault name, dataset name, module name, or number in these articles must trace back to material actually found in the repository (source code, `docs/`, `docs/study/`, `docs/audit/`, `docs/reliability/`, `REPORT/`, `UpdatedReport/`, git history) or to the official SIH problem statement text. If the research material provided to you does not contain a specific number or result, do not invent one. Describe the method and what it produces in general terms instead of fabricating a headline figure.

Where the underlying repository documentation itself already states something precisely and well (for example, the mission reliability module's own explanation of why hazard rates compose correctly and health-index thresholds do not), draw on that reasoning directly rather than inventing a weaker version.

Do not claim validation against real DRDO flight data, real aircraft, or classified information anywhere. The honest framing throughout is: physics grounded in published engine specifications, methods validated through simulation, testing, and public reference datasets where used, with real-aircraft integration described as the natural next deployment step rather than something already done.

## Terminology consistency

- The project name is always "ANUMAAN" (not "Anumaan" mid-sentence unless it starts a sentence).
- The novelty-detection layer is always called "Bio-Inspired Sparse Novelty Coding" on first mention in an article, and may be called "the novelty layer" or "sparse novelty coding" afterward. Never call it a generic deep learning classifier. It is a sparse random-projection / FlyHash-family method, not a trained neural classifier.
- The problem statement is "SIH Problem Statement 26054" or "PS-26054" on later mentions.
- Engine platforms: Rotax 912 iS, Rotax 914, Rotax 915 iS, Austro AE300, VRDE Jayem 2.2L. Use these exact names.
- Refer to the operator interface as "the ground control station" or "the GCS," not "the dashboard" as a primary term (dashboard is acceptable as a casual synonym mid-paragraph).
- Do not use the word "legacy" to describe any still-functioning part of the system. If two architectural paths exist, describe them by what they do or by name, not by an implied hierarchy of old versus new.

## File format

Plain Markdown. Use `#` for the title (one per file), `##` for major sections. Use tables where they aid comparison. Use fenced code blocks for equations, file paths, and Mermaid diagrams. No HTML embeds.

## Length

Aim for genuine substance: roughly 600 to 1400 words per article depending on subject depth, excluding diagrams and tables. A subject with real mathematical or architectural depth (physics core, mission reliability, novelty coding) should run longer than a reference or glossary-style page.
