# Sparrow Scope Guard

Detect scope creep before it becomes unpaid work by comparing explicit requests with explicit approvals. Built for small business owners and Sparrow's approval audits. This tool computes differences; it does not discover obligations or infer the meaning of a contract.

Hypothesis: a deterministic CLI with planted-ground-truth tests gives an owner a trustworthy list of scope approval differences. The local acceptance target is 200 synthetic records, every planted case found, zero false positives, exactly reconciled counts and hypothetical exposure, and a complete demo under five seconds. Real-world accuracy and value remain unmeasured.

## Quickstart

Python 3.10+ and setuptools 68+ are required. Runtime has no third-party dependencies, network requests, language-model calls, database, or GPU use. From the repo root:

```powershell
python -m pip install --no-deps --no-build-isolation -e .
ssg fixtures --out demo
ssg run --input demo
ssg report --format md
python -m pytest -q
```

If your Python Scripts directory is absent from PATH, use `python -m sparrow_scope_guard.cli` in place of `ssg`, or add the Scripts directory printed by pip to your session PATH. No online installation is needed when setuptools and pytest are already available locally. `ssg report` reads the last successful run from `.ssg/result.json`. A failed run preserves that file; do not confuse it with a new result. Use separate `--state` paths for independent runs.

For the smallest hand-written five-record example, run `ssg run --input examples/five` then `ssg report --format md`. Its synthetic ground truth is three flagged engagements, 90 unapproved minutes, two new deliverables and 9000 hypothetical exposure cents.

## Input format

Only UTF-8 JSONL records are supported, with optional blank lines and `#` header comments. CSV and YAML are rejected with a named format error, never silently ignored. A directory can contain `manifest.json`:

```json
{
  "as_of": "2026-09-30",
  "files": ["records.jsonl"],
  "synthetic": false,
  "label": "Henry entered real inputs"
}
```

Manifest filenames must be unique local basenames. With no manifest, all files except `expectations.json` are treated as inputs; supply `--as-of YYYY-MM-DD`. An empty directory with no cutoff defaults to the explicit sentinel 1970-01-01 and produces zero totals. Manifest labels are descriptive; record provenance governs reports. No system-clock date is used.

Each JSONL line has exactly these fields. This example is hypothetical and synthetic, not Henry's real data:

```json
{"id":"example-1","client":"Synthetic example","synthetic":true,"source":"synthetic_fixture","date":"2026-09-30","approved_minutes":120,"requested_minutes":150,"hourly_rate_cents":6000,"approved_deliverables":["draft"],"requested_deliverables":["draft","revision"]}
```

| Field | Contract |
| --- | --- |
| id | Unique engagement snapshot ID, nonempty string |
| client | Nonempty client name |
| synthetic | Boolean, true for illustrative or fixture records |
| source | `synthetic_fixture` when synthetic, otherwise `henry_entered` |
| date | ISO date, no later than the explicit as_of cutoff |
| approved_minutes | Total explicitly approved minutes, integer |
| requested_minutes | Total requested minutes, integer |
| hourly_rate_cents | Explicit hourly price in integer cents |
| approved_deliverables | Unique list of approved deliverable names |
| requested_deliverables | Unique list of requested deliverable names |

Henry's own real inputs must be hand entered by him with `synthetic: false` and `source: "henry_entered"`. This is an author declaration, not independently verified identity or provenance. Never mark illustrative records real. Keep real trial records local and out of commits. Do not include confidential client data in a public repository.

One record represents one independent engagement, not a stream of tasks or repeated snapshots. Consolidate repeated requests before running, or totals will double count. All records in a run must use the same currency and cents convention; the tool cannot infer or convert currency. String lengths are limited to 10000 characters, lists to 1000 items, and integer amounts to 0 through 100000000. Booleans are not integers. Duplicate IDs, duplicate deliverables, unknown or missing fields, negative values, future dates and oversized values reject the entire input with a named error. Unicode and Windows path strings are supported. U+2014 punctuation is rejected in user strings to preserve the no-em-dash output contract; use a hyphen.

## Computation and honesty boundary

An engagement is flagged when requested minutes exceed approved minutes or the requested deliverables contain a name absent from approvals. Deliverable comparison is exact and case sensitive. Unapproved minutes equal `max(0, requested_minutes - approved_minutes)`. Hypothetical billable exposure equals unapproved minutes times hourly rate cents divided by 60, rounded half up to an integer cent per engagement, then summed. Decimal arithmetic prevents binary floating-point drift. Deliverables with no explicit duration are flagged but assigned no inferred price. Removing a deliverable does not cancel extra time.

The example above yields 30 unapproved minutes, one new deliverable, and 3000 cents of **hypothetical** exposure. Exposure is neither lost revenue nor money saved. Prices are inputs; requested minutes are not measured time spent. No time saved or money saved is reported because no measured baseline is collected. Reports explicitly say savings are not measured. The tool makes no prediction about whether a client will pay, whether a request is contractually covered, or whether the work will actually occur.

Every report includes a provenance banner and an ID-by-ID source list. Case details show the input minute totals, rate and new deliverables, allowing every figure to be traced to inputs. `ssg run` prints only counts and directs the reader to the provenance report; fixture generation announces SYNTHETIC data. Saved JSON includes the banner. No timestamp, random identifier or absolute input path is embedded in results. Equal inputs and cutoff dates produce byte-identical output. There is no random seed because generation uses a fixed repeating pattern.

## Commands

| Command | Purpose and example |
| --- | --- |
| fixtures | Generate labelled data: `ssg fixtures --out demo` |
| run | Compute and save: `ssg run --input demo --state .ssg/result.json` |
| report | Render saved results: `ssg report --format json --out report.json` |
| audit | Print approval differences and provenance directly: `ssg audit --input demo` |
| quote | Draft hypothetical change-order figures: `ssg quote --input demo --id engagement-001` |

`run`, `audit` and `quote` accept `--as-of` to override the manifest cutoff. `quote` without `--id` covers all cases; with `--id` all totals and provenance are restricted to that engagement, including a zero quote for an unflagged engagement. A quote still requires client approval and is not an invoice or measured revenue. All commands provide `--help` and an example. `report` accepts `--state`, `--format md|json`, and optional `--out`. Success exits 0; named failures exit 2. Markdown case details use JSON escaping to preserve long and multiline inputs.

## Architecture

```text
fixtures.py -> labelled JSONL + manifest + hand-computed expectations
                                  |
cli.py -> parse + validate -> core.py pure comparisons
                                  |
                           saved local result
                                  |
report.py -> Markdown / JSON + provenance + honesty labels
```

Core code performs no I/O. Report writes and saved-run writes use a temporary file followed by atomic replacement; on write failure the temporary file is removed and an existing destination is preserved. Fixture generation writes its three files directly and should target a fresh directory. Malformed JSON names file and line as ParseError. Schema failures identify the offending field and file/line where applicable. Missing directories or manifest files produce MissingInput and a correction hint. Bad report paths produce WriteError. No records are silently discarded. Malformed or manually edited saved results must be regenerated with `run`; the state is a local computed artifact, not a second user input format.

## Fixture labelling and evidence

`records.jsonl` begins with a SYNTHETIC comment and every record has `synthetic: true`. JSON does not allow comments, so the manifest and expectations use both `synthetic: true` and an explicit SYNTHETIC label. The 200 records comprise four groups of 50: clean, 30 extra minutes only, one extra deliverable only, and both. Hand arithmetic: 150 flagged IDs, 100 times 30 = 3000 unapproved minutes, 100 new deliverables, and 100 times 3000 = 300000 hypothetical exposure cents. Expectations are maintained independently of the engine and are never read by it. Editing an input changes the computed report; editing expectations does not change it.

The tests include a separate five-record hand-written case, empty input, malformed inputs, schema errors, negative and excessive values, future dates, duplicates, Unicode, long strings, Windows paths, output write failure, deterministic bytes, both render formats and all commands. See EVIDENCE.md for the local measured run. Synthetic correctness validates arithmetic under this schema, not semantic detection of scope creep in free text.

## Two-week improvement hook and verdict

Start the evidence window on the first real use, recording that start date locally. After fourteen days, measure the primary metric: engagement classification error rate against a hand-checked sample, `(false positives + false negatives) / sample size`. Record sample size, checked labels, tool labels, run count and any paid audit revenue. An empty sample is unmeasured, not zero error. No real trial or elapsed evidence window is claimed by this build.

If error exceeds 10 percent, fix the single largest documented cause and recheck, or kill with a recorded reason. If the tool is never used, kill it with that finding. Record the final verdict and evidence after the window in VERDICT.md: expand for daily use or revenue; integrate for substantial overlap with a sibling project; commercialise for a buyer willing to pay as-is; maintain as portfolio evidence otherwise; kill for no use or unmet acceptance criteria. Build completion is not evidence of product demand.
