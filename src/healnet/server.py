from __future__ import annotations

import json
import os
from types import MethodType
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .care_gaps import build_next_steps, identify_care_gaps
from .fhir import load_patient_snapshot

_FHIR_CONTEXT_EXTENSION = "ai.promptopinion/fhir-context"
_DEFAULT_FHIR_SCOPES: list[dict[str, str | bool]] = [
    {"name": "patient/Patient.rs", "required": True},
    {"name": "patient/Observation.rs"},
    {"name": "patient/Condition.rs"},
    {"name": "patient/MedicationRequest.rs"},
    {"name": "patient/Encounter.rs"},
]


def _add_fhir_context_extension(
    mcp_server: FastMCP,
    scopes: list[dict[str, str | bool]] | None = None,
    extension_name: str = _FHIR_CONTEXT_EXTENSION,
) -> None:
    """Expose Prompt Opinion FHIR context capability for Superpower discovery."""
    selected_scopes = _DEFAULT_FHIR_SCOPES if scopes is None else scopes
    original_get_capabilities = mcp_server._mcp_server.get_capabilities

    def get_capabilities(self, notification_options, experimental_capabilities):
        caps = original_get_capabilities(notification_options, experimental_capabilities)
        existing_extensions = getattr(caps, "extensions", None) or {}
        caps.extensions = {
            **existing_extensions,
            extension_name: {
                "scopes": [
                    {
                        "name": str(scope.get("name", "")),
                        "required": bool(scope.get("required", False)),
                    }
                    for scope in selected_scopes
                ]
            },
        }
        return caps

    mcp_server._mcp_server.get_capabilities = MethodType(get_capabilities, mcp_server._mcp_server)


def create_server() -> FastMCP:
    host = os.getenv("HEALNET_HOST", "127.0.0.1").strip()
    port_text = os.getenv("HEALNET_PORT", "9000").strip()
    try:
        port = int(port_text)
    except ValueError:
        port = 9000

    server = FastMCP(
        "HealNet Superpower MCP",
        instructions=(
            "A healthcare MCP Superpower for chart summarization, care-gap detection, "
            "and follow-up plan generation using SHARP/FHIR context."
        ),
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )
    _add_fhir_context_extension(server)
    return server


mcp = create_server()


def _parse_context(raw_context: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw_context is None:
        return {}
    if isinstance(raw_context, dict):
        return raw_context
    raw_context = raw_context.strip()
    if not raw_context:
        return {}
    try:
        parsed = json.loads(raw_context)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_param(*, explicit: str | None, context: dict[str, Any], context_keys: list[str], env_key: str | None = None) -> str | None:
    if explicit:
        return explicit
    for key in context_keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if env_key:
        value = os.getenv(env_key)
        if value:
            return value
    return None


async def _llm_chat(messages: list[dict[str, str]]) -> str | None:
    base_url = os.getenv("HEALNET_LLM_BASE_URL")
    api_key = os.getenv("HEALNET_LLM_API_KEY")
    model = os.getenv("HEALNET_LLM_MODEL", "gpt-4o-mini")
    if not base_url or not api_key:
        return None
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        return None


def _format_patient_context(snapshot: dict[str, Any]) -> str:
    patient = snapshot.get("patient") or {}
    conditions = ", ".join(item.get("text", "") for item in snapshot.get("conditions") or []) or "none"
    meds = ", ".join(item.get("text", "") for item in snapshot.get("medications") or []) or "none"
    allergies = ", ".join(item.get("text", "") for item in snapshot.get("allergies") or []) or "none"
    observations = "; ".join(
        f"{item.get('text', '')}={item.get('value')} ({item.get('date', 'unknown')})"
        for item in snapshot.get("observations") or []
    ) or "none"
    return (
        f"Patient: {patient.get('name')} | Age: {patient.get('age')} | Gender: {patient.get('gender')}\n"
        f"Conditions: {conditions}\n"
        f"Medications: {meds}\n"
        f"Allergies: {allergies}\n"
        f"Observations: {observations}"
    )


async def _build_summary(snapshot: dict[str, Any], gaps: list[dict[str, Any]], audience: str) -> str:
    base_context = _format_patient_context(snapshot)
    gap_text = "\n".join(f"- {gap['title']}: {gap['reason']}" for gap in gaps) or "- No major gaps detected."
    llm_summary = await _llm_chat(
        [
            {
                "role": "system",
                "content": (
                    "You are HealNet, a concise healthcare chart summarizer. "
                    "Write clinically useful but short outputs for a hackathon demo."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Audience: {audience}\n\n"
                    f"Chart:\n{base_context}\n\n"
                    f"Care gaps:\n{gap_text}\n\n"
                    "Produce a short summary and next steps in plain language."
                ),
            },
        ]
    )
    if llm_summary:
        return llm_summary

    patient = snapshot.get("patient") or {}
    conditions = ", ".join(item.get("text", "") for item in snapshot.get("conditions") or []) or "no major conditions listed"
    summary_lines = [
        f"{patient.get('name')} is a {patient.get('age')} year old {patient.get('gender')} patient.",
        f"Active conditions: {conditions}.",
        f"Notable issues: {', '.join(gap['title'] for gap in gaps) if gaps else 'none'}.",
    ]
    return " ".join(summary_lines)


@mcp.tool()
async def summarize_patient_chart(
    patient_id: str,
    sharp_context: str | None = None,
    fhir_base_url: str | None = None,
    fhir_bearer_token: str | None = None,
    audience: str = "clinician",
) -> dict[str, Any]:
    """Summarize a patient's chart from SHARP/FHIR context."""
    context = _parse_context(sharp_context)
    resolved_patient_id = _resolve_param(explicit=patient_id, context=context, context_keys=["patient_id", "patientId", "subject_id"])
    resolved_base_url = _resolve_param(explicit=fhir_base_url, context=context, context_keys=["fhir_base_url", "fhirBaseUrl", "fhir_url"], env_key="FHIR_BASE_URL")
    resolved_token = _resolve_param(explicit=fhir_bearer_token, context=context, context_keys=["fhir_bearer_token", "fhirBearerToken", "fhir_token"], env_key="FHIR_BEARER_TOKEN")

    snapshot = await load_patient_snapshot(
        patient_id=resolved_patient_id or patient_id,
        fhir_base_url=resolved_base_url,
        bearer_token=resolved_token,
    )
    gaps = identify_care_gaps(snapshot)
    summary = await _build_summary(snapshot, gaps, audience)
    return {
        "summary": summary,
        "patient": snapshot.get("patient"),
        "conditions": snapshot.get("conditions"),
        "medications": snapshot.get("medications"),
        "allergies": snapshot.get("allergies"),
        "warnings": snapshot.get("warnings"),
    }


@mcp.tool()
async def identify_care_gaps_tool(
    patient_id: str,
    sharp_context: str | None = None,
    fhir_base_url: str | None = None,
    fhir_bearer_token: str | None = None,
) -> dict[str, Any]:
    """Return structured care gaps for a patient."""
    context = _parse_context(sharp_context)
    resolved_patient_id = _resolve_param(explicit=patient_id, context=context, context_keys=["patient_id", "patientId", "subject_id"])
    resolved_base_url = _resolve_param(explicit=fhir_base_url, context=context, context_keys=["fhir_base_url", "fhirBaseUrl", "fhir_url"], env_key="FHIR_BASE_URL")
    resolved_token = _resolve_param(explicit=fhir_bearer_token, context=context, context_keys=["fhir_bearer_token", "fhirBearerToken", "fhir_token"], env_key="FHIR_BEARER_TOKEN")

    snapshot = await load_patient_snapshot(
        patient_id=resolved_patient_id or patient_id,
        fhir_base_url=resolved_base_url,
        bearer_token=resolved_token,
    )
    gaps = identify_care_gaps(snapshot)
    return {
        "patient": snapshot.get("patient"),
        "care_gaps": gaps,
        "warnings": snapshot.get("warnings"),
    }


@mcp.tool()
async def draft_follow_up_plan(
    patient_id: str,
    sharp_context: str | None = None,
    fhir_base_url: str | None = None,
    fhir_bearer_token: str | None = None,
) -> dict[str, Any]:
    """Draft a concise follow-up plan from the patient's chart."""
    context = _parse_context(sharp_context)
    resolved_patient_id = _resolve_param(explicit=patient_id, context=context, context_keys=["patient_id", "patientId", "subject_id"])
    resolved_base_url = _resolve_param(explicit=fhir_base_url, context=context, context_keys=["fhir_base_url", "fhirBaseUrl", "fhir_url"], env_key="FHIR_BASE_URL")
    resolved_token = _resolve_param(explicit=fhir_bearer_token, context=context, context_keys=["fhir_bearer_token", "fhirBearerToken", "fhir_token"], env_key="FHIR_BEARER_TOKEN")

    snapshot = await load_patient_snapshot(
        patient_id=resolved_patient_id or patient_id,
        fhir_base_url=resolved_base_url,
        bearer_token=resolved_token,
    )
    gaps = identify_care_gaps(snapshot)
    next_steps = build_next_steps(snapshot, gaps)
    narrative = await _build_summary(snapshot, gaps, audience="care coordinator")
    return {
        "patient": snapshot.get("patient"),
        "follow_up_plan": next_steps,
        "summary": narrative,
        "care_gaps": gaps,
        "warnings": snapshot.get("warnings"),
    }


@mcp.tool()
async def generate_patient_message(
    patient_id: str,
    sharp_context: str | None = None,
    fhir_base_url: str | None = None,
    fhir_bearer_token: str | None = None,
) -> dict[str, Any]:
    """Generate a patient-friendly message based on the current plan."""
    context = _parse_context(sharp_context)
    resolved_patient_id = _resolve_param(explicit=patient_id, context=context, context_keys=["patient_id", "patientId", "subject_id"])
    resolved_base_url = _resolve_param(explicit=fhir_base_url, context=context, context_keys=["fhir_base_url", "fhirBaseUrl", "fhir_url"], env_key="FHIR_BASE_URL")
    resolved_token = _resolve_param(explicit=fhir_bearer_token, context=context, context_keys=["fhir_bearer_token", "fhirBearerToken", "fhir_token"], env_key="FHIR_BEARER_TOKEN")

    snapshot = await load_patient_snapshot(
        patient_id=resolved_patient_id or patient_id,
        fhir_base_url=resolved_base_url,
        bearer_token=resolved_token,
    )
    gaps = identify_care_gaps(snapshot)
    patient = snapshot.get("patient") or {}
    first_name = patient.get("name", "there").split(" ")[0]
    if gaps:
        message = (
            f"Hi {first_name}, we reviewed your recent record and want to help you stay on track. "
            f"Please follow up on: {', '.join(gap['title'] for gap in gaps[:3])}."
        )
    else:
        message = f"Hi {first_name}, your recent record looks stable. Keep up with your routine follow-up plan."
    return {
        "patient": snapshot.get("patient"),
        "message": message,
        "warnings": snapshot.get("warnings"),
    }


@mcp.tool()
async def demo_payload(
    patient_id: str,
    sharp_context: str | None = None,
    fhir_base_url: str | None = None,
    fhir_bearer_token: str | None = None,
) -> dict[str, Any]:
    """Return a compact payload with summary, care gaps, follow-up plan, and patient message for demo/judging."""
    context = _parse_context(sharp_context)
    resolved_patient_id = _resolve_param(explicit=patient_id, context=context, context_keys=["patient_id", "patientId", "subject_id"])
    resolved_base_url = _resolve_param(explicit=fhir_base_url, context=context, context_keys=["fhir_base_url", "fhirBaseUrl", "fhir_url"], env_key="FHIR_BASE_URL")
    resolved_token = _resolve_param(explicit=fhir_bearer_token, context=context, context_keys=["fhir_bearer_token", "fhirBearerToken", "fhir_token"], env_key="FHIR_BEARER_TOKEN")

    snapshot = await load_patient_snapshot(
        patient_id=resolved_patient_id or patient_id,
        fhir_base_url=resolved_base_url,
        bearer_token=resolved_token,
    )
    gaps = identify_care_gaps(snapshot)
    plan = build_next_steps(snapshot, gaps)
    summary = await _build_summary(snapshot, gaps, audience="judge")
    msg_result = await generate_patient_message(patient_id=resolved_patient_id or patient_id, sharp_context=sharp_context, fhir_base_url=resolved_base_url, fhir_bearer_token=resolved_token)

    return {
        "summary": summary,
        "patient": snapshot.get("patient"),
        "care_gaps": gaps,
        "follow_up_plan": plan,
        "patient_message": msg_result.get("message") if isinstance(msg_result, dict) else None,
        "warnings": snapshot.get("warnings"),
    }


def main() -> None:
    transport = os.getenv("HEALNET_TRANSPORT", "stdio").strip().lower()
    if transport in {"http", "streamable-http", "streamable_http"}:
        mcp.run(transport="streamable-http")
    elif transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
