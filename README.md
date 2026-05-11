# HealNet

HealNet is an MCP Superpower for Prompt Opinion that turns raw FHIR data into a clear care plan in seconds.

If a reviewer opens one healthcare repo, this should feel immediately useful: it reduces chart-reading noise, highlights what matters, and produces an action-focused summary that can be shown live in a demo.

## What It Shows

- Real healthcare interoperability with MCP + FHIR context
- A practical workflow for chart review and care-gap detection
- A judge-friendly demo path that works even without a live FHIR server
- A clean story: input patient context, output actionable next steps

## Why It Matters

HealNet is designed to save clinicians and care coordinators time by turning raw chart data into a clear, actionable summary. The goal is not just to answer questions, but to make the next step obvious.

## Why It Catches Attention

- It solves a real workflow problem instead of being a generic chatbot
- It shows both explainable logic and optional generative AI
- It works with demo data, but is structured for real FHIR integration

## Tools

- `summarize_patient_chart`
- `identify_care_gaps_tool`
- `draft_follow_up_plan`
- `generate_patient_message`
- `demo_payload`

## Notes

- MCP Superpower with FHIR context support
- Deterministic care-gap logic with optional LLM wording
- Demo-friendly fallback data included

## Files

- `src/healnet/server.py`
- `src/healnet/fhir.py`
- `src/healnet/care_gaps.py`
- `src/healnet/demo_bundle.json`
- `run_demo.ps1`
- `deploy_public.ps1`

## Quick Run

```powershell
.\run_demo.ps1 -Mode validate
```

```powershell
.\run_demo.ps1 -Mode server
```
