# HealNet

Healthcare MCP Superpower for Prompt Opinion.

## Purpose

HealNet converts SHARP/FHIR context into actionable outputs for care coordination:

- patient chart summary
- prioritized care-gap findings
- follow-up plan
- patient-facing message

## Exposed MCP Tools

- `summarize_patient_chart`
- `identify_care_gaps_tool`
- `draft_follow_up_plan`
- `generate_patient_message`
- `demo_payload`

## Key Characteristics

- MCP-compatible and Prompt Opinion ready
- deterministic care-gap logic with evidence fields
- optional LLM layer for narrative wording
- offline-safe demo mode via bundled FHIR sample

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Local Validation

```powershell
.\run_demo.ps1 -Mode validate
```

## Run MCP Server

```powershell
.\run_demo.ps1 -Mode server
```

## Deploy (Docker Compose)

```powershell
.\deploy_public.ps1
```

Server endpoint:

```text
http://<host>:9000/mcp
```
