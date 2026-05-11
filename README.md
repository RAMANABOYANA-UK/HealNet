# HealNet Superpower (MCP)

HealNet is a healthcare Superpower built as an MCP server for Prompt Opinion.
It provides reusable tools that any agent can call for FHIR chart review,
care-gap detection, and follow-up planning.

## Submission Type

- Superpower: MCP
- Project Name: HealNet
- Focus: SHARP/FHIR-aware clinical workflow assistance

## Included MCP Tools

- summarize_patient_chart
- identify_care_gaps_tool
- draft_follow_up_plan
- generate_patient_message

## Prompt Opinion Compatibility

HealNet includes the Prompt Opinion FHIR capability extension:

- ai.promptopinion/fhir-context
- Requested scopes:
	- patient/Patient.rs (required)
	- patient/Observation.rs
	- patient/Condition.rs
	- patient/MedicationRequest.rs
	- patient/Encounter.rs

This ensures HealNet is recognized as an MCP Superpower with FHIR launch context support.

## Project Structure

- src/healnet/server.py: MCP tools and server wiring
- src/healnet/fhir.py: FHIR loader and demo fallback
- src/healnet/care_gaps.py: deterministic care-gap logic
- src/healnet/demo_bundle.json: bundled demo patient
- test_tools.py: quick end-to-end validation

## Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run (Local / stdio)

```powershell
python -m healnet.server
```

## Run (HTTP MCP for platform integration)

```powershell
$env:HEALNET_TRANSPORT="http"
$env:HEALNET_HOST="127.0.0.1"
$env:HEALNET_PORT="9000"
python -m healnet.server
```

## Environment Variables

- FHIR_BASE_URL
- FHIR_BEARER_TOKEN
- HEALNET_LLM_BASE_URL
- HEALNET_LLM_API_KEY
- HEALNET_LLM_MODEL
- HEALNET_TRANSPORT
- HEALNET_HOST
- HEALNET_PORT

If FHIR_BASE_URL is not set, HealNet automatically uses the bundled demo patient.

## Validation

```powershell
python test_tools.py
```

Expected outcome: loads demo patient, detects care gaps, and produces follow-up plan output.