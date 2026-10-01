"""Local CLI. Input errors are named, and writes replace atomically."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import SchemaError, analyze, validate
from .fixtures import generate
from .report import render


class InputError(ValueError):
    pass


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from None
    except UnicodeError as exc:
        raise InputError(f"ParseError: {path}: line 1: invalid UTF-8: {exc}") from None


def load_input(directory, as_of=None):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}: use ssg fixtures --out <dir> or supply an existing input directory")
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict) or set(manifest) != {"as_of", "files", "synthetic", "label"}:
            raise InputError(f"SchemaError: {manifest_path}: line 1: manifest fields must be as_of, files, synthetic, label")
        if type(manifest["synthetic"]) is not bool or not isinstance(manifest["label"], str):
            raise InputError(f"SchemaError: {manifest_path}: line 1: synthetic must be boolean and label must be string")
        as_of = as_of or manifest["as_of"]
        files = manifest["files"]
        if not isinstance(files, list) or any(not isinstance(f, str) or Path(f).name != f or f in ("manifest.json", "expectations.json") for f in files) or len(set(files)) != len(files):
            raise InputError(f"SchemaError: {manifest_path}: line 1: files must be unique local basenames")
    else:
        files = sorted(p.name for p in directory.iterdir() if p.is_file() and p.name != "expectations.json")
    if not as_of:
        if files:
            raise InputError(f"SchemaError: {directory}: line 1: as_of required via manifest or --as-of")
        as_of = "1970-01-01"
    records = []
    for name in files:
        path = directory / name
        if not path.is_file():
            raise InputError(f"MissingInput: {path}: line 1: manifest file missing; correct files or regenerate fixtures")
        if path.suffix != ".jsonl":
            raise InputError(f"SchemaError: {path}: line 1: unsupported format; use JSONL")
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeError:
            raise InputError(f"ParseError: {path}: line 1: invalid UTF-8") from None
        for number, line in enumerate(lines, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"ParseError: {path}: line {number}: {exc.msg}") from None
            try:
                validate(record, as_of)
                if any(r["id"] == record["id"] for r in records):
                    raise SchemaError(f"id: duplicate {record['id']!r}")
            except SchemaError as exc:
                raise InputError(f"SchemaError: {path}: line {number}: {exc}") from None
            records.append(record)
    return analyze(records, as_of)


def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(content)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"WriteError: {path}: {exc}") from None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare explicit scope approvals with requests. No predictions or measured savings.")
    commands = parser.add_subparsers(dest="command", required=True)
    f = commands.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: ssg fixtures --out demo")
    f.add_argument("--out", required=True)
    for name, help_text in (("run", "Compute scope differences"), ("audit", "List engagements exceeding approved scope"), ("quote", "Draft hypothetical change-order figures from explicit rates")):
        p = commands.add_parser(name, help=help_text, description=help_text, epilog=f"Example: ssg {name} --input demo")
        p.add_argument("--input", required=True)
        p.add_argument("--as-of", help="Explicit ISO cutoff date; overrides manifest")
        if name == "run":
            p.add_argument("--state", default=".ssg/result.json")
        if name == "quote":
            p.add_argument("--id", help="Select one engagement")
    p = commands.add_parser("report", help="Render saved results with provenance", epilog="Example: ssg report --format md")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--state", default=".ssg/result.json")
    p.add_argument("--out", help="Atomically write report instead of stdout")
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 SYNTHETIC records. Exposure figures are hypothetical.")
        elif args.command == "report":
            state = Path(args.state)
            if not state.is_file():
                raise InputError(f"MissingInput: {state}: run ssg run --input <dir> first")
            result = read_json(state)
            try:
                output = render(result, args.format)
            except (KeyError, TypeError, ValueError):
                raise InputError(f"SchemaError: {state}: line 1: invalid saved result fields") from None
            if args.out:
                atomic_write(args.out, output)
            else:
                sys.stdout.write(output)
        else:
            result = load_input(args.input, args.as_of)
            if args.command == "run":
                atomic_write(args.state, render(result, "json"))
                print(f"Computed {result['record_count']} records; {result['flagged_count']} flagged. Hypothetical exposure only. Run ssg report for provenance.")
            else:
                if args.command == "quote" and args.id:
                    if args.id not in {p['id'] for p in result['provenance']}:
                        raise InputError(f"MissingInput: unknown engagement id {args.id!r}")
                    result["cases"] = [c for c in result["cases"] if c["id"] == args.id]
                    result["provenance"] = [p for p in result["provenance"] if p["id"] == args.id]
                    result["record_count"] = 1
                    result["flagged_count"] = len(result["cases"])
                    result["unapproved_minutes"] = sum(c["unapproved_minutes"] for c in result["cases"])
                    result["new_deliverable_count"] = sum(len(c["new_deliverables"]) for c in result["cases"])
                    result["hypothetical_exposure_cents"] = sum(c["hypothetical_exposure_cents"] for c in result["cases"])
                sys.stdout.write(render(result, "md"))
        return 0
    except (InputError, SchemaError, OSError) as exc:
        print(str(exc) if isinstance(exc, InputError) else f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
