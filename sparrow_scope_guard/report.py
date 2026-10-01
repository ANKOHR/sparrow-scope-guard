"""Deterministic reports with explicit provenance and hypothetical labels."""
import json


def render(result, format="md"):
    synthetic = [r["id"] for r in result["provenance"] if r["synthetic"]]
    real = [r["id"] for r in result["provenance"] if not r["synthetic"]]
    banner = f"Data provenance: {len(synthetic)} synthetic fixture records; {len(real)} real records declared Henry-entered by the input author (not independently verified)."
    if format == "json":
        return json.dumps({"banner": banner, **result}, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    lines = ["# Sparrow Scope Guard", "", banner, "",
             f"As of: {result['as_of']}", f"Records: {result['record_count']}",
             f"Flagged engagements: {result['flagged_count']}",
             f"Unapproved minutes: {result['unapproved_minutes']}",
             f"New deliverables: {result['new_deliverable_count']}",
             f"Hypothetical billable exposure (cents, currency unspecified): {result['hypothetical_exposure_cents']}",
             "Exposure is hypothetical, not lost revenue or measured savings. Each case rounds half up to cents.",
             result["savings"], result["limitation"], "", "## Cases", ""]
    # JSON quoting prevents user strings from injecting Markdown lines or headings.
    for c in result["cases"]:
        lines.append(f"* {json.dumps(c, ensure_ascii=False, sort_keys=True)}")
    lines += ["", "## Input provenance by engagement", ""]
    lines += [f"* {json.dumps(p, sort_keys=True, ensure_ascii=False)}" for p in result["provenance"]]
    return "\n".join(lines) + "\n"
