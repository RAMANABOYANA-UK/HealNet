# HealNet

HealNet is an MCP server for healthcare workflows in Prompt Opinion. It uses SHARP/FHIR context to summarize a patient chart, identify care gaps, and generate a follow-up plan.

## Overview

HealNet is designed to support care review and coordination tasks in a way that is explainable, reproducible, and compatible with real FHIR data.

## Capabilities

- `summarize_patient_chart`
- `identify_care_gaps_tool`
- `draft_follow_up_plan`
- `generate_patient_message`
- `demo_payload`

## Notes

- Supports SHARP/FHIR launch context
- Uses deterministic care-gap logic with optional LLM-generated wording
- Includes bundled demo data for offline evaluation

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Validate the local workflow:

```powershell
.\run_demo.ps1 -Mode validate
```

Start the MCP server:

```powershell
.\run_demo.ps1 -Mode server
```

## Deployment

```powershell
.\deploy_public.ps1
```

The HTTP endpoint is exposed on port `9000` when deployed with Docker Compose.
