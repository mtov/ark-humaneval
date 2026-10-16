"""Regression tests for the offline evaluator; no model or network access."""
import ast
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.support import accepts, expected_fields, pack, unpack
import evaluate_solutions as evaluator
import run_benchmark as runner


def invoke_worker(tmp_path, source, payload, timeout=2):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src/__init__.py").touch()
    (workspace / "src/solution.py").write_text(source)
    cases = tmp_path / "hidden.json.gz"
    cases.write_bytes(gzip.compress(json.dumps(payload).encode()))
    result = subprocess.run([sys.executable, str(ROOT / "evaluation/hidden_worker.py"),
                             "--workspace", str(workspace), "--cases", str(cases),
                             "--case-timeout", str(timeout)], cwd=workspace,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_suite_covers_all_tasks_and_reference_hashes():
    suite = evaluator.validate_suite()
    assert len(suite["tasks"]) == 164
    assert suite["total_cases"] == sum(meta["cases"] for meta in suite["tasks"].values())
    for task, metadata in suite["tasks"].items():
        payload = json.load(gzip.open(ROOT / "evaluation/hidden" / (task + ".json.gz"), "rt"))
        assert payload["task_id"] == task
        assert len(payload["cases"]) == metadata["cases"] > 0
        assert len({json.dumps(case["args"], sort_keys=True) for case in payload["cases"]}) == len(payload["cases"])
        assert not (ROOT / "humaneval_official_workspaces" / task / "evaluation").exists()


def test_serialization_preserves_nested_container_types():
    original = (1, [2, (3.5, None)], {"a": (True, False)})
    encoded = json.loads(json.dumps(pack(original)))
    assert unpack(encoded) == original
    assert isinstance(unpack(encoded), tuple)


def test_rounding_oracles_do_not_penalize_exact_decimal_answers():
    from decimal import Decimal, ROUND_HALF_UP
    payload = json.load(gzip.open(ROOT / "evaluation/hidden/he_099.json.gz", "rt"))
    for case in payload["cases"]:
        assert unpack(case["expected"]) == int(Decimal(case["args"][0]).to_integral_value(rounding=ROUND_HALF_UP))


def test_upstream_specification_bugs_are_filtered_for_every_case():
    from build_hidden_suite import oracle_matches_spec
    assert not oracle_matches_spec("he_091", ["I"], 0)
    assert not oracle_matches_spec("he_141", ["éxxample.exe"], "Yes")
    for task in ("he_091", "he_141"):
        payload = json.load(gzip.open(ROOT / "evaluation/hidden" / (task + ".json.gz"), "rt"))
        assert all(oracle_matches_spec(task, case["args"], unpack(case["expected"])) for case in payload["cases"])


def test_multiple_valid_roots_and_closest_pair_ties_are_accepted():
    assert accepts("he_032", [[-6, 11, -6, 1]], 2.0, 1.0, 1e-4)
    assert not accepts("he_032", [[-6, 11, -6, 1]], 4.0, 1.0, 1e-4)
    assert accepts("he_020", [[0, 2, 4]], (2, 4), (0, 2), 0)
    assert not accepts("he_020", [[0, 2, 4]], (0, 4), (0, 2), 0)
    assert not accepts("he_020", [[0, 2]], (0, 0), (0, 2), 0)


def test_large_exact_outputs_use_hashes_but_float_outputs_keep_tolerance(tmp_path):
    value = "a" * 6000
    payload = {"task_id": "he_000", "entry_point": "f", "atol": 0,
               "cases": [{"args": [], **expected_fields(value)}]}
    assert "expected_digest" in payload["cases"][0]
    assert "expected" in expected_fields([float(i) for i in range(1000)])
    assert invoke_worker(tmp_path, "def f():\n    return 'a' * 6000\n", payload)["status"] == "PASS"


@pytest.mark.parametrize("source,status", [
    ("def f(x):\n    return x + 1\n", "PASS"),
    ("def f(x):\n    return 5\n", "FAIL"),
    ("def f(x):\n    raise ValueError('bad')\n", "FAIL"),
    ("def f(x):\n    while True: pass\n", "TIMEOUT"),
])
def test_worker_detects_correctness_exceptions_and_timeouts(tmp_path, source, status):
    payload = {"task_id": "he_000", "entry_point": "f", "atol": 0,
               "cases": [{"args": [4], "expected": 5}, {"args": [9], "expected": 10}]}
    result = invoke_worker(tmp_path, source, payload, timeout=0.1)
    assert result["status"] == status
    assert result["cases_total"] == 2
    if status == "PASS":
        assert result["cases_checked"] == 2


def test_hidden_suite_catches_he145_memorized_examples(tmp_path):
    source = (ROOT / "results/generic-prompts-01/workspaces/he_145/src/solution.py").read_text()
    payload = {"task_id": "he_145", "entry_point": "order_by_points", "atol": 0,
               "cases": [{"args": [[1, -1]], "expected": [-1, 1]}]}
    result = invoke_worker(tmp_path, source, payload)
    assert result["status"] == "FAIL"
    assert result["failure"]["actual"] == "[1, -1]"


def test_evaluation_preserves_source_and_separates_statuses(tmp_path):
    suite = evaluator.validate_suite()
    source = tmp_path / "saved/src"
    source.mkdir(parents=True)
    (source / "__init__.py").touch()
    (source / "solution.py").write_text("def order_by_points(nums):\n    return list(nums)\n")
    tests = tmp_path / "saved/tests"
    tests.mkdir()
    (tests / "__init__.py").touch()
    (tests / "test_solution.py").write_text("from src.solution import order_by_points\ndef test_solution():\n    assert order_by_points([1]) == [1]\n")
    output = tmp_path / "report"
    (output / "traces").mkdir(parents=True)
    before = evaluator.fingerprints(source)
    row = evaluator.evaluate_task("he_145", source, tests, output, Path(sys.executable), 10, 2, suite)
    assert row["visible_status"] == "PASS"
    assert row["hidden_status"] == row["overall_status"] == "FAIL"
    assert evaluator.fingerprints(source) == before
    assert (output / "traces/he_145.hidden.json").is_file()


def test_truncated_evaluation_csv_is_rejected(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text(",".join(evaluator.FIELDS) + "\nhe_000,PASS\n")
    with pytest.raises(ValueError, match="CSV"):
        evaluator.read_rows(path, ["he_000"], {"tasks": {"he_000": {"cases": 1}}})


def test_hidden_files_are_not_in_runtime_snapshot(tmp_path):
    ark = ROOT.parent / "ark"
    if not (ark / "run_ark.py").is_file():
        pytest.skip("Sibling Ark checkout not available")
    runtime = tmp_path / "snapshot"
    runtime.mkdir()
    expected = {"ark_files_sha256": {str(path.relative_to(ark)): runner.file_hash(path)
                                    for path in runner.ark_files(ark)}}
    snapshot = runner.prepare_snapshot(SimpleNamespace(ark_dir=ark), runtime, expected)
    assert not (snapshot / "evaluation").exists()
    task = tmp_path / "task"
    task.mkdir()
    (task / "prompt.txt").write_text("Implement f")
    (task / "src").mkdir()
    (task / "src/solution.py").write_text("def f(): pass\n")
    (task / "evaluation").mkdir()
    (task / "evaluation/secret.txt").write_text("must not be copied")
    code = f"import sys; from pathlib import Path; sys.path.insert(0,{str(snapshot / 'src')!r}); from ark import inputs; inputs.RUNTIME_WORKSPACE_PATH=Path({str(snapshot / 'ark-workspace')!r}); inputs.prepare_runtime_workspace(Path({str(task)!r})); assert not (inputs.RUNTIME_WORKSPACE_PATH/'evaluation').exists()"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
