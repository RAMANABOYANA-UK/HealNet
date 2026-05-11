# HealNet

HealNet is my healthcare MCP Superpower built for Prompt Opinion.

I built it to solve one practical problem: clinicians and care coordinators spend too much time reading scattered chart data before deciding what to do next.

Instead of acting like a generic chatbot, HealNet takes SHARP/FHIR context and produces focused, actionable outputs that support real care workflow decisions.

## What I Built

- A chart summarization flow for the current patient context
- Deterministic care-gap detection with evidence-backed findings
- A follow-up planning output with concrete next steps
- A patient-friendly message generator
- A compact demo payload for one-shot evaluation

The MCP tools exposed by HealNet are:

- `summarize_patient_chart`
- `identify_care_gaps_tool`
- `draft_follow_up_plan`
- `generate_patient_message`
- `demo_payload`

## Core Idea

The core design is intentional:

- Deterministic clinical logic is used for critical findings, so outputs stay explainable.
- Generative AI is optional and used only to improve language quality, not to decide clinical facts.
- The same project works in both demo mode and real integration mode.

This gives a better balance between safety, usefulness, and demo quality.

## What Makes HealNet Different

Most healthcare demos either look impressive but are hard to trust, or are rule-only systems with poor usability.

HealNet is different because it combines:

- Standards-first interoperability (MCP + FHIR context)
- Explainable and auditable care-gap reasoning
- Practical outputs that are immediately usable in coordination workflows
- A realistic path from hackathon demo to real deployment

## Why This Work Matters

The value of HealNet is not just that it answers questions. It shortens the path from data to action.

That is the main goal of this project: reduce review overhead, surface what matters, and help teams act faster with clearer context.

## Current Status

- Implemented as a working MCP Superpower
- Integrated with SHARP/FHIR-style context handling
- Includes deterministic gap logic and optional LLM wording layer
- Includes demo-safe fallback data and validation coverage

This repository is the implementation of that full idea, not just a concept draft.

```text
http://<host>:9000/mcp
```
