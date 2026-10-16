"""Execute one frozen solution against hidden cases in a separate process."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import gzip
import importlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.support import CaseTimeout, accepts, deadline, exact_digest, unpack


def check(solution_root, payload, case_timeout=2):
    output = {"task_id": payload["task_id"], "status": "PASS", "cases_total": len(payload["cases"]),
              "cases_checked": 0, "failure": None}
    # The only candidate files on its import path are the evaluation copy.
    sys.path.insert(0, str(solution_root))
    captured = io.StringIO()
    try:
        with redirect_stdout(captured), redirect_stderr(captured), deadline(case_timeout):
            function = getattr(importlib.import_module("src.solution"), payload["entry_point"])
    except Exception as exc:
        output.update(status="TIMEOUT" if isinstance(exc, CaseTimeout) else "ERROR",
                      failure={"type": type(exc).__name__, "message": str(exc)[:1000]})
        return output
    for index, case in enumerate(payload["cases"]):
        output["cases_checked"] += 1
        args = deepcopy(case["args"])
        expected = unpack(case["expected"]) if "expected" in case else None
        try:
            with redirect_stdout(captured), redirect_stderr(captured), deadline(case_timeout):
                actual = function(*args)
                valid = (exact_digest(actual) == case["expected_digest"] if "expected_digest" in case
                         else accepts(payload["task_id"], case["args"], actual, expected, payload["atol"]))
            if not valid:
                output.update(status="FAIL", failure={"type": "AssertionError", "case_index": index,
                              "arguments": repr(case["args"])[:2000], "expected": case.get("expected_preview", repr(expected))[:2000],
                              "actual": repr(actual)[:2000]})
                break
        except Exception as exc:
            output.update(status="TIMEOUT" if isinstance(exc, CaseTimeout) else "FAIL",
                          failure={"type": type(exc).__name__, "case_index": index,
                                   "arguments": repr(case["args"])[:2000], "message": str(exc)[:2000]})
            break
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--case-timeout", type=float, default=2)
    args = parser.parse_args()
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    with gzip.open(args.cases, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    print(json.dumps(check(args.workspace, payload, args.case_timeout), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
