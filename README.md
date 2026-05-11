# HealNet

HealNet is an MCP Superpower for Prompt Opinion. It reads SHARP/FHIR context, summarizes a patient chart, detects care gaps, and drafts a follow-up plan.

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
