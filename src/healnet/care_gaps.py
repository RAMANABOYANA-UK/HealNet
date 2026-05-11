from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class CareGap:
    priority: str
    title: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            return None


def _resource_text(resource: dict[str, Any]) -> str:
    chunks: list[str] = []
    code = resource.get("code") or {}
    if isinstance(code, dict):
        text = code.get("text")
        if text:
            chunks.append(text)
        for coding in code.get("coding") or []:
            display = coding.get("display")
            if display:
                chunks.append(display)
    med = resource.get("medicationCodeableConcept") or {}
    if isinstance(med, dict) and med.get("text"):
        chunks.append(med["text"])
    return " ".join(chunks).lower()


def _latest_observation(observations: list[dict[str, Any]], keywords: tuple[str, ...]) -> dict[str, Any] | None:
    matches: list[tuple[datetime | None, dict[str, Any]]] = []
    for observation in observations:
        text = _resource_text(observation)
        if not any(keyword in text for keyword in keywords):
            continue
        effective = _parse_datetime(observation.get("effectiveDateTime") or observation.get("effectiveInstant"))
        matches.append((effective, observation))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=UTC), reverse=True)
    return matches[0][1]


def _latest_value(observation: dict[str, Any] | None) -> float | None:
    if not observation:
        return None
    value_quantity = observation.get("valueQuantity") or {}
    if isinstance(value_quantity, dict):
        value = value_quantity.get("value")
        if isinstance(value, (int, float)):
            return float(value)
    if observation.get("component"):
        values: list[float] = []
        for component in observation.get("component") or []:
            quantity = component.get("valueQuantity") or {}
            if isinstance(quantity, dict) and isinstance(quantity.get("value"), (int, float)):
                values.append(float(quantity["value"]))
        if values:
            return values[0]
    return None


def _latest_bp(observations: list[dict[str, Any]]) -> dict[str, float | str] | None:
    candidates: list[tuple[datetime | None, dict[str, Any]]] = []
    for observation in observations:
        text = _resource_text(observation)
        if "blood pressure" not in text and "systolic" not in text and "diastolic" not in text:
            continue
        effective = _parse_datetime(observation.get("effectiveDateTime") or observation.get("effectiveInstant"))
        candidates.append((effective, observation))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=UTC), reverse=True)
    resource = candidates[0][1]
    systolic = None
    diastolic = None
    for component in resource.get("component") or []:
        component_text = _resource_text(component)
        quantity = component.get("valueQuantity") or {}
        if not isinstance(quantity, dict):
            continue
        value = quantity.get("value")
        if not isinstance(value, (int, float)):
            continue
        if "systolic" in component_text:
            systolic = float(value)
        elif "diastolic" in component_text:
            diastolic = float(value)
    if systolic is None or diastolic is None:
        quantities = [
            component.get("valueQuantity", {}).get("value")
            for component in resource.get("component") or []
            if isinstance(component.get("valueQuantity"), dict)
        ]
        numeric = [float(value) for value in quantities if isinstance(value, (int, float))]
        if len(numeric) >= 2:
            systolic, diastolic = numeric[:2]
    if systolic is None or diastolic is None:
        return None
    return {
        "date": (candidates[0][0].date().isoformat() if candidates[0][0] else "unknown"),
        "systolic": systolic,
        "diastolic": diastolic,
    }


def identify_care_gaps(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    patient = snapshot.get("patient") or {}
    observations = snapshot.get("observations") or []
    encounters = snapshot.get("encounters") or []
    conditions = snapshot.get("conditions") or []
    age = patient.get("age")

    gaps: list[CareGap] = []

    latest_encounter_dates = [
        _parse_datetime(encounter.get("date"))
        for encounter in encounters
        if encounter.get("date")
    ]
    latest_encounter_dates = [item for item in latest_encounter_dates if item is not None]
    if not latest_encounter_dates or max(latest_encounter_dates) < datetime.now(UTC) - timedelta(days=365):
        gaps.append(
            CareGap(
                priority="medium",
                title="No recent clinical follow-up",
                reason="No completed encounter is available in the last 12 months.",
                evidence={"last_encounter": max(latest_encounter_dates).date().isoformat() if latest_encounter_dates else None},
            )
        )

    condition_texts = " ".join((condition.get("text") or "") for condition in conditions).lower()
    has_diabetes = any(token in condition_texts for token in ["diabetes", "a1c"])
    has_hypertension = any(token in condition_texts for token in ["hypertension", "high blood pressure", "htn"])

    if has_diabetes:
        latest_a1c = _latest_observation(observations, ("a1c", "hemoglobin", "hba1c"))
        latest_a1c_value = _latest_value(latest_a1c)
        latest_a1c_date = _parse_datetime(latest_a1c.get("effectiveDateTime") if latest_a1c else None)
        if not latest_a1c_date or latest_a1c_date < datetime.now(UTC) - timedelta(days=180):
            gaps.append(
                CareGap(
                    priority="high",
                    title="HbA1c overdue",
                    reason="Diabetes is present, but a recent HbA1c result is missing or stale.",
                    evidence={"latest_a1c": latest_a1c_value, "latest_a1c_date": latest_a1c_date.date().isoformat() if latest_a1c_date else None},
                )
            )
        elif latest_a1c_value is not None and latest_a1c_value >= 8.0:
            gaps.append(
                CareGap(
                    priority="high",
                    title="HbA1c above target",
                    reason="Recent HbA1c suggests glycemic control is above typical care targets.",
                    evidence={"latest_a1c": latest_a1c_value, "latest_a1c_date": latest_a1c_date.date().isoformat() if latest_a1c_date else None},
                )
            )

    if has_hypertension:
        latest_bp = _latest_bp(observations)
        bp_date = _parse_datetime(latest_bp["date"] if latest_bp else None)
        if not bp_date or bp_date < datetime.now(UTC) - timedelta(days=180):
            gaps.append(
                CareGap(
                    priority="high",
                    title="Blood pressure follow-up overdue",
                    reason="Hypertension is present, but a recent blood pressure reading is missing or stale.",
                    evidence={"latest_bp": latest_bp},
                )
            )
        elif latest_bp and (float(latest_bp["systolic"]) >= 140 or float(latest_bp["diastolic"]) >= 90):
            gaps.append(
                CareGap(
                    priority="high",
                    title="Blood pressure above goal",
                    reason="Recent blood pressure remains elevated.",
                    evidence={"latest_bp": latest_bp},
                )
            )

    if age is not None and age >= 50:
        has_colorectal_screening = any("colorectal" in _resource_text(obs) or "colon" in _resource_text(obs) for obs in observations)
        if not has_colorectal_screening:
            gaps.append(
                CareGap(
                    priority="medium",
                    title="Preventive screening not visible",
                    reason="A colorectal screening result is not visible in the available chart data.",
                    evidence={"age": age},
                )
            )

    def _evidence_summary(evidence: dict[str, Any]) -> str:
        parts: list[str] = []
        if not evidence:
            return ""
        a1c = evidence.get("latest_a1c")
        if a1c is not None:
            parts.append(f"HbA1c={a1c}")
        a1c_date = evidence.get("latest_a1c_date")
        if a1c_date:
            parts.append(f"A1cDate={a1c_date}")
        bp = evidence.get("latest_bp") or {}
        if isinstance(bp, dict) and bp.get("systolic") is not None and bp.get("diastolic") is not None:
            parts.append(f"BP={int(bp['systolic'])}/{int(bp['diastolic'])}")
        last_enc = evidence.get("last_encounter")
        if last_enc:
            parts.append(f"LastEncounter={last_enc}")
        return ", ".join(parts)

    deduped: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for gap in gaps:
        if gap.title in seen_titles:
            continue
        seen_titles.add(gap.title)
        deduped.append(
            {
                "priority": gap.priority,
                "title": gap.title,
                "reason": gap.reason,
                "evidence": gap.evidence,
                "evidence_summary": _evidence_summary(gap.evidence),
            }
        )
    return deduped


def build_next_steps(snapshot: dict[str, Any], gaps: list[dict[str, Any]]) -> list[str]:
    patient = snapshot.get("patient") or {}
    suggestions: list[str] = []
    title_set = {gap["title"] for gap in gaps}

    if "HbA1c overdue" in title_set or "HbA1c above target" in title_set:
        suggestions.append("Order or review HbA1c and adjust diabetes care plan if needed.")
    if "Blood pressure follow-up overdue" in title_set or "Blood pressure above goal" in title_set:
        suggestions.append("Confirm blood pressure with a repeat measurement and reconcile antihypertensive therapy.")
    if "No recent clinical follow-up" in title_set:
        suggestions.append("Schedule a follow-up visit or outreach call to close the care loop.")
    if "Preventive screening not visible" in title_set:
        suggestions.append("Check whether colorectal screening was completed outside the imported chart and reconcile records.")

    if not suggestions:
        suggestions.append("No major care gaps were detected in the available data; continue routine follow-up.")

    name = patient.get("name") or "the patient"
    suggestions.insert(0, f"Review the chart for {name} and confirm the care plan in context of the most recent FHIR data.")
    return suggestions
