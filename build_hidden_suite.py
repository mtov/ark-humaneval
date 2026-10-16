"""Build a reproducible hidden suite from pinned HumanEval+ inputs and references.

No model calls, third-party Python packages, or network access are required.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
import gzip
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

from evaluation.support import ROOT, accepts, deadline, expected_fields, sha256

SUITE = ROOT / "evaluation"
VENDOR = SUITE / "vendor"
PLUS = VENDOR / "HumanEvalPlus-v0.1.10.jsonl.gz"
BASE = VENDOR / "HumanEval.jsonl.gz"
DATASET_SHA256 = "272720b90ac375502c8ed23cd791c2a93dfb22a911641a494da74a426c09f101"
SEED = 20261016


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return {row["task_id"]: row for row in map(json.loads, stream)}


def load_function(code, entry, filename):
    namespace = {}
    exec(compile(code, filename, "exec"), namespace)
    return namespace[entry]


def key(args):
    return json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def known_inputs(problem, task_dir):
    known = {key(args) for args in problem["base_input"]}
    tree = ast.parse((task_dir / "tests/test_solution.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "candidate":
            try:
                known.add(key([ast.literal_eval(arg) for arg in node.args]))
            except (ValueError, TypeError, SyntaxError):
                pass
    return known


def specification(code, entry):
    node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == entry)
    strings = [n.value.value for n in node.body if isinstance(n, ast.Expr)
               and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]
    return re.sub(r"\s+", " ", strings[0]).strip()


def oracle_matches_spec(task_id, args, expected):
    """Conservative filters for concrete specification bugs shared by both upstream oracles."""
    if task_id == "he_099":
        correct = int(Decimal(args[0]).to_integral_value(rounding=ROUND_HALF_UP))
        return expected == correct
    if task_id == "he_091":
        # A sentence consisting of the word I still starts with the word I.
        correct = sum(bool(re.match(r"\s*I(?:\s|$)", sentence)) for sentence in re.split(r"[.?!]", args[0]))
        return expected == correct
    if task_id == "he_141":
        # The statement explicitly specifies ASCII letters and ASCII digits.
        value = args[0]
        valid = bool(re.fullmatch(r"[a-zA-Z][^.]*\.(?:txt|exe|dll)", value, flags=re.DOTALL))
        valid = valid and sum(character in "0123456789" for character in value) <= 3
        return expected == ("Yes" if valid else "No")
    return True


def build_task(task_id):
    number = int(task_id[3:])
    random.seed(SEED + number)
    problem = load(PLUS)[f"HumanEval/{number}"]
    original = load(BASE)[f"HumanEval/{number}"]
    task_dir = ROOT / "humaneval_official_workspaces" / task_id
    source = task_dir / "src/solution.py"
    reference_code = problem["prompt"] + problem["canonical_solution"]
    assert specification(source.read_text(), problem["entry_point"]) == specification(reference_code, problem["entry_point"])
    reference_path = SUITE / "references" / f"{task_id}.py"
    reference_path.write_text(reference_code, encoding="utf-8")
    reference = load_function(reference_code, problem["entry_point"], str(reference_path))
    original_reference = load_function(original["prompt"] + original["canonical_solution"], original["entry_point"], "OpenAI reference")
    if task_id in {"he_055", "he_063"}:
        # Preserve the original recurrence while avoiding exponential recomputation.
        original_namespace = original_reference.__globals__
        original_reference = lru_cache(maxsize=None)(original_reference)
        original_namespace[original["entry_point"]] = original_reference
    contract = load_function(problem["prompt"] + problem["contract"] + "\n    return True\n", problem["entry_point"], "HumanEval+ input contract")
    # A known independent implementation must also pass the supplied visible suite.
    with tempfile.TemporaryDirectory(prefix=f"hidden-reference-{task_id}-") as temporary:
        temp = Path(temporary)
        (temp / "src").mkdir()
        (temp / "src/__init__.py").touch()
        (temp / "src/solution.py").write_text(reference_code)
        tests = (task_dir / "tests/test_solution.py").read_text()
        (temp / "test_visible.py").write_text(tests)
        checked = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_visible.py"],
                                 cwd=temp, capture_output=True, text=True, timeout=60,
                                 env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if checked.returncode:
            raise ValueError(f"Reference fails visible tests: {task_id}\n{checked.stdout}\n{checked.stderr}")
    seen = known_inputs(problem, task_dir)
    cases = []
    excluded = Counter()
    excluded_examples = []
    inputs = list(problem["plus_input"])
    # Fixed, independently derived edge cases for the audit findings.
    targeted = {"he_145": [[[1, -1]], [[21, -21]], [[2, -2, 12, -12]]],
                "he_109": [[[2, 1, 3]], [[3, 1, 2]], [[4, 1, 3, 2]]],
                "he_132": [["[]][]]"], ["[][]]]"], ["[[]][]"]]}
    inputs = targeted.get(task_id, []) + inputs
    # Shuffle only the public extra inputs, retaining targeted edges first.
    offset = len(targeted.get(task_id, []))
    tail = inputs[offset:]
    random.Random(SEED + number).shuffle(tail)
    inputs[offset:] = tail
    for args in inputs:
        identity = key(args)
        if identity in seen:
            excluded["visible_or_duplicate_input"] += 1
            continue
        seen.add(identity)
        try:
            with deadline(1):
                contract(*deepcopy(args))
        except Exception as exc:
            excluded[f"contract_{type(exc).__name__}"] += 1
            continue
        try:
            with deadline(1):
                expected = reference(*deepcopy(args))
                if not oracle_matches_spec(task_id, args, expected):
                    raise ValueError("Upstream oracle conflicts with an independently checked specification rule")
                if not accepts(task_id, args, expected, expected, problem["atol"]):
                    raise ValueError("Reference violates task property")
                fields = expected_fields(expected)
            # Reject disputed cases instead of penalizing a candidate on an uncertain oracle.
            with deadline(1):
                other = original_reference(*deepcopy(args))
                if not accepts(task_id, args, other, expected, problem["atol"]):
                    raise ValueError("Reference disagreement")
        except Exception as exc:
            excluded[f"oracle_{type(exc).__name__}"] += 1
            if len(excluded_examples) < 20:
                excluded_examples.append({"arguments": repr(args)[:500], "type": type(exc).__name__, "reason": str(exc)[:200]})
            continue
        cases.append({"args": args, **fields})
    if not cases:
        raise ValueError(f"No validated novel cases for {task_id}")
    payload = {"task_id": task_id, "entry_point": problem["entry_point"], "atol": problem["atol"], "cases": cases}
    destination = SUITE / "hidden" / f"{task_id}.json.gz"
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    # mtime=0 keeps rebuilding byte-for-byte reproducible.
    destination.write_bytes(gzip.compress(encoded, mtime=0))
    return {"entry_point": problem["entry_point"], "cases": len(cases), "excluded": dict(excluded),
            "excluded_examples": excluded_examples,
            "cases_sha256": sha256(destination), "reference_sha256": sha256(reference_path),
            "source_sha256": sha256(source), "visible_tests_sha256": sha256(task_dir / "tests/test_solution.py"),
            "reference_visible_status": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    if sha256(PLUS) != DATASET_SHA256:
        parser.error("HumanEval+ vendor hash mismatch")
    if args.worker:
        result = build_task(args.worker)
        print(json.dumps(result))
        return 0
    if not 1 <= args.jobs <= 8:
        parser.error("--jobs must be between 1 and 8")
    for name in ("hidden", "references"):
        (SUITE / name).mkdir(exist_ok=True)
    def worker(number):
        task = f"he_{number:03d}"
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", task],
                                cwd=ROOT, capture_output=True, text=True, timeout=180,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if result.returncode:
            raise ValueError(f"{task}: {result.stderr}\n{result.stdout}")
        metadata = json.loads(result.stdout)
        print(f"{task}: {metadata['cases']} validated hidden cases", flush=True)
        return task, metadata
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        tasks = dict(pool.map(worker, range(164)))
    metadata = {"schema_version": 1, "dataset": "HumanEval+ v0.1.10", "seed": SEED,
                "dataset_sha256": DATASET_SHA256, "original_dataset_sha256": sha256(BASE),
                "builder_sha256": sha256(__file__), "support_sha256": sha256(SUITE / "support.py"),
                "tasks": tasks, "total_cases": sum(task["cases"] for task in tasks.values())}
    (SUITE / "manifest.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"Suite built: {len(tasks)} tasks / {metadata['total_cases']} cases", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
