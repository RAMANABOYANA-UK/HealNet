# HealNet

HealNet is an MCP Superpower for Prompt Opinion. It reads SHARP/FHIR context, summarizes a patient chart, detects care gaps, and drafts a follow-up plan.

## What It Shows

- Real healthcare interoperability with MCP + FHIR context
- A practical workflow for chart review and care-gap detection
- A judge-friendly demo path that works even without a live FHIR server

## Why It Matters

HealNet is designed to save clinicians and care coordinators time by turning raw chart data into a clear, actionable summary.

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
