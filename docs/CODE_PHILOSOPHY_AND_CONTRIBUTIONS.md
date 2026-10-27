# PsyCoLab code philosophy: simple science, modular growth, stable official protocols

**Audience:** researchers, students, maintainers, reviewers and AI coding assistants.

**Status:** project design principles and contribution policy. Read this before authoring an experiment, changing the framework, or asking an AI to make a pull request. This is a long-lived guide to *intent*, not a claim that every part of the event-first migration is already implemented. The implementation status and staged acceptance evidence live in [the event-first architecture plan](EVENT_FIRST_ARCHITECTURE.md) and [session-event examples](SESSION_EVENTS.md).

## The guiding idea

> **The experiment Python file describes the science. The shared framework executes it. The TUI helps researchers find, inspect and run it; the TUI does not own the experimental logic.**

Prefer the **simplest readable representation that faithfully executes the intended experiment**. An experiment should read like a chronological description of what a participant experiences, together with explicit rules for what each response changes. Simple-looking code that hides scientific decisions, loses provenance, or gives different results is not an improvement.

PsyCoLab should remain useful when there are ten experiments, a hundred experiments, or many independent laboratories. Adding a normal experiment from supported components must not require a new TUI screen, a private runner, or changes to the framework.

## Who owns what?

| Layer | Authoritative responsibility | Typical researcher action |
| --- | --- | --- |
| **Stimulus library** | Reusable appearance, physical/angular parameters, parameter validation and rendering, currently through `src/psychophysics_lab/stimulus_library.py` and supported external libraries | Select an existing stimulus or author one clear `LibraryStimulus` class |
| **Experiment Python file** | Parameters, session opening, event order, stimulus placement, response meanings, condition selection, updates, termination and result definition | Edit one local experiment file, or configure already-declared inputs |
| **Shared framework** | Validated event execution, presentation, adaptive algorithms, simulation, recording, recovery, profiles and provenance | Reuse; change only for genuine shared capabilities |
| **TUI** | Generic discovery, inspection, existing declared-parameter editing, calibration guidance and run control | Inspect or run without making the TUI a required code editor |
| **Lab-owned external extensions** | Locally developed experiments/stimuli, explicitly trusted and independently versioned | Iterate freely without modifying the official checkout |
| **Official repository** | Curated, reviewed and stable reference implementations | Consume updates; submit focused PRs for genuine fixes or accepted new work |

**A declared `ConfigField` remains a legitimate, useful parameter control**: the TUI can select a run value and store a local preset. But an experiment feature need not be turned into a `ConfigField`, and a new event must not require bespoke TUI logic. The Python protocol is authoritative; a previously selected TUI/preset value may override a newly edited Python *default*. Review should explain the effective source rather than silently assuming a default was used.

## What researchers should see in an experiment

The intended **event-first researcher-facing narrative** is:

1. **PARAMETERS:** editable values, units, accepted bounds, defaults and scientific meanings.
2. **SESSION START — ONCE:** an optional participant-ready screen, start key, settling fixation or instructions.
3. **TRIAL EVENTS — REPEATED:** an explicit chronological list of fixation, stimulus, interval, response and optional audio events.
4. **SCIENTIFIC RULES:** how conditions are selected, how responses are interpreted, and how subsequent stimulus parameters are updated.
5. **STOPPING AND RESULTS:** termination, exclusions, estimator, saved measurements and their meaning.
6. **FRAMEWORK REGISTRATION:** a short final connection to the shared execution system.

Keep the scientifically important choices in the experiment file. Name any genuinely reusable functions so that a reader can locate their purpose immediately. Avoid a chain of anonymous adapters merely to make a short event list possible.

**Event lists are plans, not frozen images.** Reusable lists/functions specify *which kind* of event comes next; the current condition and adaptive state supply the *effective parameters* for each trial. The new stimulus contrast or probe value may depend on the previous response. These updates remain explicit, validated, and outside the timing-critical drawing code.

For a concrete example of the **already supported Stage A** opening:

```python
from psychophysics_lab.researcher import WaitForKey, Show

SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="fixation", duration=1000),
]

# Disable without changing the framework:
# SESSION_START = []
```

The opening is passed through `experiment(..., session_start=SESSION_START)` and occurs *once*, before Trial 1. Readiness is **not** a scientific response or staircase update, and Trial 1's actual response is retained. A readiness screen is the **intended default for official experiments as they migrate**, but researchers can choose an empty session sequence for a protocol that does not need one. The current official experiment files have not all been migrated merely because Stage A exists.

Small functions returning flat event lists may be composed like Lego pieces. There should be **one canonical event representation and one execution path**, shared across real presentation, simulation and Review. The existing `TrialTimeline` and other supported legacy authoring APIs remain available through the staged migration.

## The official repository is a stable reference, not a shared scratchpad

**Once accepted into the official repository, an experiment or stimulus is a curated scientific reference.** Users normally change *selected parameters* or local presets, not its source code or scientific identity. An official experiment's documented defaults, temporal structure, response meaning, adaptive calculations, and estimators must not drift casually when other contributions arrive.

This does **not** mean official code can never change. A reproduced bug, scientific correction, necessary compatibility repair, or explicitly approved protocol revision may justify a **small, reviewed and tested PR**, with the behavioural change, rationale, versioning and backwards-compatibility impact clearly stated.

- **An individual laboratory may experiment freely in its own external extension or branch**, using a distinct identity. Local work should not overwrite official experiments or official stimulus classes.
- **An ordinary contribution must not replace an existing official experiment** because the contributor has a preferred variant or a newer version of their own code. Existing official identities and behaviour take precedence. A scientifically different variant should have its **own identity**, usually remaining local until reviewed for promotion.
- **Expand the official catalogue by promoting finished, validated, documented, maintainable new experiments or stimuli.** Promotion is deliberate and reviewed, never automatic when an extension becomes Ready.
- If two contributions claim the same identity, **resolve the collision explicitly**. Do not silently shadow the official component, relabel prior run data, or switch participants to a different scientific protocol.

A contributor can propose an improvement to an official protocol; approval depends on evidence, not on who authored it. Keep the accepted protocol stable for everyone else.

## Build locally, then propose promotion

A typical contributor workflow is:

1. **Start in a separate lab extension root** (or an isolated development branch); never use the installed official framework files as the only copy of new research.
2. Reuse the public `LibraryStimulus`, event and `RunContext` interfaces. Make each local experiment uniquely named and maintain an explicit, distinct source identity.
3. Write the event sequence and scientific rules so another researcher can explain them without reading the core engine.
4. Exercise drafts using the existing development and simulation paths; test contrast limits, timing intentions, condition coverage, accepted input and saved results. Acquire hardware evidence separately where scientific conclusions need it.
5. Preserve source fingerprints, settings, validation results, expected outputs and representative examples.
6. When scientifically finished, **open a focused PR proposing promotion** into the established official locations, with documentation, tests and attribution. Maintainers decide whether it belongs in the shared catalogue.
7. After acceptance, treat that official source as stable; continue experimental variants in separate, clearly identified lab components.

External Python executes with the user's permissions; trusting an extension is an explicit safety decision, **not** a sandbox. “Software Ready” and “physically qualified for acquisition” are different claims. Never mutate historical participant records to fit a new source version.

See [laboratory extensions](LABORATORY_EXTENSIONS.md), [contributing experiments](CONTRIBUTING_EXPERIMENTS.md), and [safe Git updates](SAFE_UPDATES_AND_LOCAL_WORK.md).

## What does *not* belong in the TUI

Do not add a custom setup page, toggle, duplicated parameter store or event-specific execution branch merely because one experiment introduces a new fixation, beep, response sequence, or local stimulus.

The TUI may generically display the **actual declared session and trial event plan**, the effective settings, their source, and whether a value is user-editable or derived. It may continue to edit existing validated fields. But it must not *reconstruct another version* of the experimental logic or be required for a Python-authored experiment to exist.

The scalable design is: **new experiment file + existing shared vocabulary = no new TUI experiment-specific code**. A genuinely new *shared event type* can justify extending the canonical framework and its generic inspection, with tests.

## Guardrails for scientific correctness

- Keep **one** validated renderer/presentation engine, **one** canonical recording contract, and **one** authoritative adaptive method per applicable protocol. Do not create a parallel runner or event DSL to simplify authoring.
- Distinguish **scientific input**, **derived value**, **selected local configuration** and **fixed invariant**. Declare meaningful units and bounds; never hide a scientific choice in an arbitrary callback or hard-coded duplicate.
- State what the task actually asks: spatial alternatives, single-interval judgements and two-interval judgements are not interchangeable. Preserve response mapping and scoring.
- Keep response-dependent updates *between* presentations, never as unpredictable file IO or arbitrary Python callbacks during the timed draw.
- Test event order, actual resolved stimulus parameters, accepted responses, per-condition updates, termination, staircase histories, scientific summaries, and deterministic simulations. Where appropriate compare against frozen software baseline fixtures.
- Store the source identity, selected configuration, intended event plan, effective values and observed software events in reproducible provenance. A code change that changes the protocol must be identifiable in saved runs.
- Protect calibration, external participant data and existing run readers. Software-timestamp success is **not** evidence of verified photon onset, luminance, sound onset or input latency.

## Instructions for maintainers and AI coding assistants

When asked to build, simplify, fix or migrate PsyCoLab:

1. **Read this document and the current repository's accepted baseline, authoring contract, extension guide and relevant event-first stage notes first.** Check current source and Git status; treat older examples as historical context, not automatic implementation instructions.
2. Identify whether the request concerns a **run parameter**, a **local experiment/stimulus**, a **new official candidate**, a **bug fix to an official protocol**, or a **shared framework feature**. Choose the narrowest appropriate layer.
3. Preserve existing accepted scientific behaviour unless a behavioural change has been deliberately approved. Never silently change default response rules, strength definitions, timing plans, condition distributions, analysis or calibration gates.
4. Prefer a direct readable event list and named scientific rules to more adapters. Reuse shared primitives before inventing abstraction; write the smallest amount of code that makes the actual scientific intention clearer.
5. Do not force features through the TUI, add new per-experiment UI wiring, duplicate configuration sources, create alternative registries, or restore the old monolithic/file-mediated event implementation.
6. Do not overwrite an official experiment or stimulus with a contributor's competing implementation. Develop distinct protocols in uniquely identified extensions and propose **separate reviewed promotions**.
7. Keep existing official and third-party interfaces compatible during staged migration; test representative experiments before touching all registered experiments.
8. Run relevant targeted and full regression checks, preserve historical run/data compatibility, and report exactly what changed and why. Windows is the present acceptance target; hardware acquisition requires independent laboratory qualification.
9. Work on isolated branches/worktrees; make reviewable PRs. **Never merge, release, tag, delete old run data, remove compatibility paths or alter local calibration without explicit approval.**
10. Judge success by whether a newcomer can read one experiment file plus its stimulus class, state the sequence and scientific rules correctly, and modify a local experiment **without changing the framework or TUI**.

## Maintenance decision rule

Before accepting any new code, ask:

> **Does this make the scientific procedure easier to read, more reliable to execute, or safer to reproduce—without taking control away from the experiment file?**

If it adds a new abstraction, new TUI dependency or new maintenance burden without satisfying that test, prefer the simpler existing structure.

The philosophy should remain stable even while its implementation evolves. Amend this guide deliberately through reviewed changes, rather than allowing individual AI tasks to redefine the architecture implicitly.
