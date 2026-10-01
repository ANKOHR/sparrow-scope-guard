"""Pure scope comparisons. Exposure is hypothetical, never measured savings."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


class SchemaError(ValueError):
    """An explicit input contract was violated."""


FIELDS = {"id", "client", "synthetic", "source", "date", "approved_minutes",
          "requested_minutes", "hourly_rate_cents", "approved_deliverables",
          "requested_deliverables"}


def validate(record, as_of):
    if not isinstance(record, dict):
        raise SchemaError("record: expected object")
    if set(record) != FIELDS:
        raise SchemaError(f"fields: missing={sorted(FIELDS-set(record))}, unknown={sorted(set(record)-FIELDS)}")
    for field in ("id", "client", "source"):
        if not isinstance(record[field], str) or not 1 <= len(record[field]) <= 10000:
            raise SchemaError(f"{field}: expected nonempty string of at most 10000 characters")
        if chr(0x2014) in record[field]:
            raise SchemaError(f"{field}: unsupported U+2014 punctuation; use a hyphen")
    if type(record["synthetic"]) is not bool:
        raise SchemaError("synthetic: expected boolean")
    if record["source"] != ("synthetic_fixture" if record["synthetic"] else "henry_entered"):
        raise SchemaError("source: must be synthetic_fixture or henry_entered matching synthetic")
    for field in ("approved_minutes", "requested_minutes", "hourly_rate_cents"):
        if type(record[field]) is not int or not 0 <= record[field] <= 100000000:
            raise SchemaError(f"{field}: expected integer between 0 and 100000000")
    try:
        if not isinstance(record["date"], str) or date.fromisoformat(record["date"]) > date.fromisoformat(as_of):
            raise ValueError()
    except (TypeError, ValueError):
        raise SchemaError("date: expected ISO date no later than as_of") from None
    for field in ("approved_deliverables", "requested_deliverables"):
        value = record[field]
        if not isinstance(value, list) or len(value) > 1000 or any(
            not isinstance(x, str) or not 1 <= len(x) <= 10000 for x in value
        ):
            raise SchemaError(f"{field}: expected at most 1000 nonempty strings of at most 10000 characters")
        if len(set(value)) != len(value):
            raise SchemaError(f"{field}: duplicate deliverables")
        if any(chr(0x2014) in x for x in value):
            raise SchemaError(f"{field}: unsupported U+2014 punctuation; use a hyphen")
    return record


def analyze(records, as_of):
    """One independent snapshot per engagement; sum rounded exposure cents."""
    try:
        date.fromisoformat(as_of)
    except (TypeError, ValueError):
        raise SchemaError("as_of: expected ISO date") from None
    seen, cases, provenance = set(), [], []
    total_minutes = total_cents = new_count = 0
    for record in sorted(records, key=lambda r: str(r.get("id", "")) if isinstance(r, dict) else ""):
        validate(record, as_of)
        if record["id"] in seen:
            raise SchemaError(f"id: duplicate {record['id']!r}")
        seen.add(record["id"])
        provenance.append({"id": record["id"], "synthetic": record["synthetic"], "source": record["source"]})
        extra = max(0, record["requested_minutes"] - record["approved_minutes"])
        additions = sorted(set(record["requested_deliverables"]) - set(record["approved_deliverables"]))
        cents = int((Decimal(extra) * record["hourly_rate_cents"] / 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if extra or additions:
            cases.append({"id": record["id"], "client": record["client"], "unapproved_minutes": extra,
                          "new_deliverables": additions, "hypothetical_exposure_cents": cents,
                          "hourly_rate_cents": record["hourly_rate_cents"],
                          "approved_minutes": record["approved_minutes"], "requested_minutes": record["requested_minutes"]})
        total_minutes += extra
        total_cents += cents
        new_count += len(additions)
    return {"as_of": as_of, "record_count": len(seen), "flagged_count": len(cases),
            "unapproved_minutes": total_minutes, "new_deliverable_count": new_count,
            "hypothetical_exposure_cents": total_cents, "cases": cases, "provenance": provenance,
            "savings": "Not measured: no baseline supplied.",
            "limitation": "Only explicit approval differences are detected; deliverables have no inferred price."}
