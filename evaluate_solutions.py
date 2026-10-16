"""Offline visible/hidden evaluation of saved Ark solutions. Never calls a model."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from evaluation.support import ROOT, sha256
from run_benchmark import execute, positive_int

FIELDS = ["task_id", "visible_status", "hidden_status", "overall_status", "visible_seconds", "hidden_seconds",
          "hidden_cases_total", "hidden_cases_checked", "hidden_error_type", "visible_exit_code", "hidden_exit_code"]
SUITE = ROOT / "evaluation"


def fingerprints(path):
    return {str(p.relative_to(path)): sha256(p) for p in sorted(path.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def save_csv(path, rows):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_rows(path, tasks, suite):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("Invalid existing evaluation CSV header")
        rows = list(reader)
    seen = set()
    valid = {"PASS", "FAIL", "TIMEOUT", "ERROR"}
    for row in rows:
        try:
            if (set(row) != set(FIELDS) or None in row.values() or row["task_id"] not in tasks
                    or row["task_id"] in seen or any(row[key] not in valid for key in ("visible_status", "hidden_status", "overall_status"))):
                raise ValueError
            total, checked = int(row["hidden_cases_total"]), int(row["hidden_cases_checked"])
            if total != suite["tasks"][row["task_id"]]["cases"] or not 0 <= checked <= total:
                raise ValueError
            if row["hidden_status"] == "PASS" and checked != total:
                raise ValueError
            if (row["overall_status"] == "PASS") != (row["visible_status"] == row["hidden_status"] == "PASS"):
                raise ValueError
            for key in ("visible_seconds", "hidden_seconds"):
                number = float(row[key])
                if not math.isfinite(number) or number < 0:
                    raise ValueError
            for key in ("visible_exit_code", "hidden_exit_code"):
                int(row[key])
        except (ValueError, TypeError):
            raise ValueError("Invalid existing evaluation CSV record; no tasks were skipped") from None
        seen.add(row["task_id"])
    return rows


def validate_suite():
    metadata = json.loads((SUITE / "manifest.json").read_text())
    if set(metadata["tasks"]) != {f"he_{i:03d}" for i in range(164)}:
        raise ValueError("Hidden suite must cover exactly all 164 tasks")
    if sha256(SUITE / "support.py") != metadata["support_sha256"]:
        raise ValueError("Hidden oracle changed; rebuild and validate the suite")
    if sha256(SUITE / "vendor/HumanEvalPlus-v0.1.10.jsonl.gz") != metadata["dataset_sha256"]:
        raise ValueError("HumanEval+ vendor archive changed")
    if sha256(SUITE / "vendor/HumanEval.jsonl.gz") != metadata["original_dataset_sha256"]:
        raise ValueError("HumanEval vendor archive changed")
    for task, entry in metadata["tasks"].items():
        for directory, suffix, key in (("hidden", ".json.gz", "cases_sha256"), ("references", ".py", "reference_sha256")):
            if sha256(SUITE / directory / (task + suffix)) != entry[key]:
                raise ValueError(f"Hidden suite file changed: {task}/{directory}")
        if entry["cases"] < 1 or entry["reference_visible_status"] != "PASS":
            raise ValueError(f"Unvalidated task: {task}")
    return metadata


def evaluate_task(task, source, visible_tests, output, python, timeout, case_timeout, suite):
    info = suite["tasks"][task]
    original_hashes = fingerprints(source)
    with tempfile.TemporaryDirectory(prefix=f"offline-{task}-") as temporary:
        workspace = Path(temporary)
        shutil.copytree(source, workspace / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(visible_tests, workspace / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        snapshot_hashes = fingerprints(workspace / "src")
        start = time.monotonic()
        visible_code, stdout, stderr, timed_out = execute(
            [str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_solution.py"], workspace, timeout)
        visible_seconds = round(time.monotonic() - start, 3)
        visible_status = "TIMEOUT" if timed_out else "PASS" if visible_code == 0 else "FAIL"
        (output / "traces" / f"{task}.visible.log").write_text(stdout + stderr, encoding="utf-8")
        if fingerprints(workspace / "src") != snapshot_hashes:
            raise ValueError(f"Visible evaluation changed the solution copy: {task}")
        start = time.monotonic()
        hidden_code, stdout, stderr, timed_out = execute(
            [str(python), str(SUITE / "hidden_worker.py"), "--workspace", str(workspace),
             "--cases", str(SUITE / "hidden" / f"{task}.json.gz"), "--case-timeout", str(case_timeout)], workspace, timeout)
        hidden_seconds = round(time.monotonic() - start, 3)
        (output / "traces" / f"{task}.hidden.log").write_text(stdout + stderr, encoding="utf-8")
        if timed_out:
            hidden = {"status": "TIMEOUT", "cases_total": info["cases"], "cases_checked": 0,
                      "failure": {"type": "TaskTimeout", "message": "Worker exceeded task time limit"}}
        elif hidden_code:
            hidden = {"status": "ERROR", "cases_total": info["cases"], "cases_checked": 0,
                      "failure": {"type": "WorkerError", "message": stderr[-2000:]}}
        else:
            hidden = json.loads(stdout)
            if (hidden["task_id"] != task or hidden["cases_total"] != info["cases"]
                    or hidden["status"] not in {"PASS", "FAIL", "ERROR", "TIMEOUT"}
                    or not 0 <= hidden["cases_checked"] <= info["cases"]
                    or (hidden["status"] == "PASS" and hidden["cases_checked"] != info["cases"])):
                raise ValueError(f"Invalid hidden worker result: {task}")
        if fingerprints(workspace / "src") != snapshot_hashes:
            raise ValueError(f"Hidden evaluation changed the solution copy: {task}")
    if fingerprints(source) != original_hashes:
        raise ValueError(f"Source solutions changed during evaluation: {task}")
    save_json(output / "traces" / f"{task}.hidden.json", hidden)
    overall = "PASS" if visible_status == hidden["status"] == "PASS" else "TIMEOUT" if "TIMEOUT" in (visible_status, hidden["status"]) else "ERROR" if hidden["status"] == "ERROR" else "FAIL"
    return dict(zip(FIELDS, [task, visible_status, hidden["status"], overall, visible_seconds, hidden_seconds,
                            info["cases"], hidden["cases_checked"], (hidden.get("failure") or {}).get("type", "None"),
                            visible_code, hidden_code]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Existing benchmark run, e.g. results/generic-prompts-01")
    parser.add_argument("--output", type=Path, help="New directory outside the source run")
    parser.add_argument("--python", type=Path, default=ROOT.parent / "ark/.venv/bin/python")
    parser.add_argument("--timeout", type=positive_int, default=60, help="Seconds per visible/hidden worker")
    parser.add_argument("--case-timeout", type=positive_int, default=2)
    parser.add_argument("--task", action="append")
    parser.add_argument("--validate-references", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate_references == bool(args.run):
            parser.error("Choose either --run or --validate-references")
        suite = validate_suite()
        python = args.python.expanduser().absolute()
        probe = subprocess.run([str(python), "-c", "import sys,pytest; print(sys.version); print(pytest.__version__)"],
                               capture_output=True, text=True, timeout=30)
        if probe.returncode:
            raise ValueError(probe.stderr)
        source_run = args.run.expanduser().resolve() if args.run else None
        source_manifest = json.loads((source_run / "manifest.json").read_text()) if source_run else None
        tasks = sorted(source_manifest["tasks"] if source_manifest else suite["tasks"])
        if args.task:
            unknown = set(args.task) - set(tasks)
            if unknown:
                raise ValueError(f"Unknown tasks: {sorted(unknown)}")
            tasks = [task for task in tasks if task in args.task]
        name = source_run.name if source_run else "reference-validation"
        output = (args.output or ROOT / "evaluation_results" / name).expanduser().resolve()
        protected = (SUITE, ROOT / "results", ROOT / "humaneval_official_workspaces")
        if output == ROOT or any(output.is_relative_to(path) for path in protected) or (source_run and (output.is_relative_to(source_run) or source_run.is_relative_to(output))):
            raise ValueError("Output must be a separate evaluation directory")
        sources = {}
        for task in tasks:
            if source_run:
                source = source_run / "workspaces" / task / "src"
                visible = source_run / "workspaces" / task / "tests"
                for relative, digest in source_manifest["task_files_sha256"].items():
                    if relative.startswith(task + "/tests/") and sha256(source_run / "workspaces" / relative) != digest:
                        raise ValueError(f"Saved visible tests changed: {task}")
                if source_manifest["task_files_sha256"].get(task + "/src/solution.py") != suite["tasks"][task]["source_sha256"]:
                    raise ValueError(f"Suite specification does not match source run: {task}")
                sources[task] = {"src": fingerprints(source), "tests": fingerprints(visible)}
                if not (source / "solution.py").is_file():
                    raise ValueError(f"Missing solution: {source}")
            else:
                sources[task] = {"reference": suite["tasks"][task]["reference_sha256"]}
        expected = {"schema_version": 1, "source_run": str(source_run) if source_run else None,
                    "source_manifest_sha256": sha256(source_run / "manifest.json") if source_run else None,
                    "suite_sha256": sha256(SUITE / "manifest.json"), "evaluator_sha256": sha256(__file__),
                    "worker_sha256": sha256(SUITE / "hidden_worker.py"), "python": str(python),
                    "python_environment": probe.stdout.strip(), "timeout": args.timeout,
                    "case_timeout": args.case_timeout, "tasks": tasks, "source_files": sources}
        output.mkdir(parents=True, exist_ok=True)
        with (output / ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("This evaluation is already running") from None
            manifest_path = output / "manifest.json"
            if manifest_path.exists() and json.loads(manifest_path.read_text()) != expected:
                raise ValueError("Evaluation inputs changed; choose another --output directory")
            if not manifest_path.exists():
                if (output / "results.csv").exists():
                    raise ValueError("Results without manifest; choose another --output directory")
                save_json(manifest_path, expected)
            (output / "traces").mkdir(exist_ok=True)
            csv_path = output / "results.csv"
            rows = read_rows(csv_path, tasks, suite)
            completed = {row["task_id"] for row in rows}
            for index, task in enumerate(tasks, 1):
                if task in completed:
                    continue
                if source_run:
                    source, visible = source_run / "workspaces" / task / "src", source_run / "workspaces" / task / "tests"
                    if {"src": fingerprints(source), "tests": fingerprints(visible)} != sources[task]:
                        raise ValueError(f"Source inputs changed: {task}")
                    row = evaluate_task(task, source, visible, output, python, args.timeout, args.case_timeout, suite)
                else:
                    with tempfile.TemporaryDirectory(prefix="reference-source-") as temp:
                        source = Path(temp)
                        shutil.copy2(SUITE / "references" / f"{task}.py", source / "solution.py")
                        (source / "__init__.py").touch()
                        visible = ROOT / "humaneval_official_workspaces" / task / "tests"
                        if sha256(visible / "test_solution.py") != suite["tasks"][task]["visible_tests_sha256"]:
                            raise ValueError(f"Visible tests changed since suite build: {task}")
                        row = evaluate_task(task, source, visible, output, python, args.timeout, args.case_timeout, suite)
                rows.append(row)
                save_csv(csv_path, rows)
                print(f"[{index}/{len(tasks)}] {task}: visible={row['visible_status']} hidden={row['hidden_status']} ({row['hidden_cases_checked']}/{row['hidden_cases_total']} checked)", flush=True)
            summary = {"tasks": len(rows), "visible": dict(Counter(row["visible_status"] for row in rows)),
                       "hidden": dict(Counter(row["hidden_status"] for row in rows)),
                       "overall": dict(Counter(row["overall_status"] for row in rows)),
                       "failed_tasks": [row["task_id"] for row in rows if row["overall_status"] != "PASS"]}
            save_json(output / "summary.json", summary)
            print(json.dumps(summary, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Repeat the same command to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
