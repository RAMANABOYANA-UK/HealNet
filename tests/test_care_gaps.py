import asyncio
from healnet.fhir import load_patient_snapshot
from healnet.care_gaps import identify_care_gaps


def test_identify_care_gaps_demo():
    async def run():
        snapshot = await load_patient_snapshot(patient_id="healnet-demo", fhir_base_url=None, bearer_token=None)
        gaps = identify_care_gaps(snapshot)
        assert isinstance(gaps, list)
        # Expect at least one high-priority gap in demo bundle
        titles = [g["title"].lower() for g in gaps]
        assert any("hba1c" in t or "a1c" in t or "hba1c" in t or "a1c" in t or "hba1c" in t for t in titles) or any("blood pressure" in t or "bp" in t or "blood" in t for t in titles)

    asyncio.run(run())
