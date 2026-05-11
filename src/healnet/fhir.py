from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _resource_display_name(resource: dict[str, Any]) -> str:
    names = resource.get("name") or []
    if names:
        name = names[0]
        given = " ".join(name.get("given") or [])
        family = name.get("family") or ""
        return " ".join(part for part in [given, family] if part).strip()
    return resource.get("id") or "Unknown patient"


def _resource_text(resource: dict[str, Any]) -> str:
    text = resource.get("code", {}).get("text")
    if text:
        return text
    med = resource.get("medicationCodeableConcept", {}).get("text")
    if med:
        return med
    return resource.get("resourceType", "")


@dataclass
class FHIRBundle:
    patient: dict[str, Any]
    conditions: list[dict[str, Any]]
    medications: list[dict[str, Any]]
    allergies: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    encounters: list[dict[str, Any]]
    immunizations: list[dict[str, Any]]
    warnings: list[str]


class FHIRClient:
    def __init__(self, base_url: str | None, bearer_token: str | None = None, *, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.bearer_token = bearer_token
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("FHIR base URL is not configured.")
        headers = {"Accept": "application/fhir+json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=params)
            response.raise_for_status()
            return response.json()

    async def get_patient(self, patient_id: str) -> dict[str, Any]:
        return await self._get_json(f"Patient/{patient_id}")

    async def search(self, resource_type: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        bundle = await self._get_json(resource_type, params=params)
        entries = bundle.get("entry") or []
        results: list[dict[str, Any]] = []
        for entry in entries:
            resource = entry.get("resource")
            if isinstance(resource, dict):
                results.append(resource)
        return results


async def load_bundle_from_path(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _entry_resources(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for entry in bundle.get("entry") or []:
        resource = entry.get("resource")
        if isinstance(resource, dict):
            resources.append(resource)
    return resources


def _bundle_to_snapshot(bundle: dict[str, Any], *, warnings: list[str] | None = None) -> dict[str, Any]:
    resources = _entry_resources(bundle)
    patient = next((resource for resource in resources if resource.get("resourceType") == "Patient"), {})
    conditions = [resource for resource in resources if resource.get("resourceType") == "Condition"]
    medications = [resource for resource in resources if resource.get("resourceType") == "MedicationRequest"]
    allergies = [resource for resource in resources if resource.get("resourceType") == "AllergyIntolerance"]
    observations = [resource for resource in resources if resource.get("resourceType") == "Observation"]
    encounters = [resource for resource in resources if resource.get("resourceType") == "Encounter"]
    immunizations = [resource for resource in resources if resource.get("resourceType") == "Immunization"]

    birth_date = patient.get("birthDate")
    age = None
    if birth_date:
        parsed = _parse_datetime(birth_date)
        if parsed:
            today = datetime.now(UTC)
            age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))

    summary_patient = {
        "id": patient.get("id"),
        "name": _resource_display_name(patient),
        "gender": patient.get("gender"),
        "birthDate": birth_date,
        "age": age,
        "telecom": patient.get("telecom") or [],
        "text": _resource_display_name(patient),
    }

    condition_summaries = [{"text": _resource_text(resource), "status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")} for resource in conditions]
    medication_summaries = [{"text": _resource_text(resource), "status": resource.get("status")} for resource in medications]
    allergy_summaries = [{"text": _resource_text(resource), "status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")} for resource in allergies]

    observation_summaries: list[dict[str, Any]] = []
    for resource in observations:
        effective = resource.get("effectiveDateTime") or resource.get("effectiveInstant")
        value = resource.get("valueQuantity", {}).get("value")
        if value is None:
            component_values = [component.get("valueQuantity", {}).get("value") for component in resource.get("component") or []]
            component_values = [item for item in component_values if item is not None]
            value = component_values[:2] if component_values else None
        observation_summaries.append({"text": _resource_text(resource), "date": effective, "value": value})

    encounter_summaries: list[dict[str, Any]] = []
    for resource in encounters:
        period = resource.get("period") or {}
        date = period.get("start") or period.get("end")
        encounter_summaries.append({"text": resource.get("class", {}).get("code") or "Encounter", "date": date, "status": resource.get("status")})

    immunization_summaries = [{"text": _resource_text(resource), "date": resource.get("occurrenceDateTime") or resource.get("date")} for resource in immunizations]

    return {
        "patient": summary_patient,
        "conditions": condition_summaries,
        "medications": medication_summaries,
        "allergies": allergy_summaries,
        "observations": observation_summaries,
        "encounters": encounter_summaries,
        "immunizations": immunization_summaries,
        "warnings": warnings or [],
    }


async def load_patient_snapshot(
    *,
    patient_id: str,
    fhir_base_url: str | None,
    bearer_token: str | None,
    allow_demo_fallback: bool = True,
) -> dict[str, Any]:
    client = FHIRClient(fhir_base_url, bearer_token)
    if not client.available:
        demo_path = Path(__file__).with_name("demo_bundle.json")
        return _bundle_to_snapshot(await load_bundle_from_path(demo_path), warnings=["FHIR base URL was not configured; loaded bundled demo data instead."])

    try:
        patient = await client.get_patient(patient_id)
        bundle = {
            "resourceType": "Bundle",
            "entry": [{"resource": patient}],
        }
        for resource_type in ["Condition", "MedicationRequest", "AllergyIntolerance", "Observation", "Encounter", "Immunization"]:
            try:
                resources = await client.search(resource_type, {"patient": patient_id, "_count": 100})
                bundle["entry"].extend({"resource": resource} for resource in resources)
            except Exception:
                # If a resource type fails, continue with what's available.
                continue
        return _bundle_to_snapshot(bundle)
    except Exception as exc:
        # Prefer detailed httpx exceptions when possible
        warning_msg = None
        try:
            import httpx

            if isinstance(exc, httpx.RequestError):
                warning_msg = f"FHIR request failed: network error ({exc})."
            elif isinstance(exc, httpx.HTTPStatusError):
                warning_msg = f"FHIR request failed: HTTP {exc.response.status_code} {exc.response.reason_phrase}."
        except Exception:
            pass

        if warning_msg is None:
            warning_msg = f"FHIR request failed: {exc}."

        if not allow_demo_fallback:
            raise
        demo_path = Path(__file__).with_name("demo_bundle.json")
        warnings = [f"{warning_msg} Loaded bundled demo data instead."]
        return _bundle_to_snapshot(await load_bundle_from_path(demo_path), warnings=warnings)
