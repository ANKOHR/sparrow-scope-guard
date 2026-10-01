"""Synthetic fixed-pattern fixtures, no randomness or estimated truth."""
import json
from pathlib import Path


def fixture_records(count=200):
    return [{"id": f"engagement-{i:03d}", "client": f"Synthetic client {i}",
             "synthetic": True, "source": "synthetic_fixture", "date": "2026-09-30",
             "approved_minutes": 120, "requested_minutes": 150 if i % 4 in (1, 3) else 120,
             "hourly_rate_cents": 6000, "approved_deliverables": ["draft"],
             "requested_deliverables": ["draft", "revision"] if i % 4 in (2, 3) else ["draft"]}
            for i in range(count)]


def generate(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "records.jsonl").write_text("# SYNTHETIC fixture data, not real clients\n" +
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fixture_records()), encoding="utf-8")
    # Four groups of 50: clean, minutes only, deliverables only, both.
    expectations = {"synthetic": True, "label": "SYNTHETIC hand-computed expectations",
                    "record_count": 200, "flagged_count": 150, "unapproved_minutes": 3000,
                    "new_deliverable_count": 100, "hypothetical_exposure_cents": 300000,
                    "flagged_ids": [f"engagement-{i:03d}" for i in range(200) if i % 4 != 0]}
    (out / "expectations.json").write_text(json.dumps(expectations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"synthetic": True, "label": "SYNTHETIC fixture manifest",
        "as_of": "2026-09-30", "files": ["records.jsonl"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
